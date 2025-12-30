import imaplib
import email
import re
import logging
import socket
import datetime
from bs4 import BeautifulSoup
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from billing.models import Order, PaymentAuditLog
from enrollments.models import UserEnrollment

# --- CONFIGURATION ---
# Set a strict timeout so the script doesn't hang forever if Gmail is slow
socket.setdefaulttimeout(30) 

# Configure Logging (Output shows in console or your log files)
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Enterprise-grade HDFC UPI payment verification scanner'

    # --- CENTRALIZED REGEX PATTERNS ---
    # Matches: "Rs. 1,200.00" or "INR 500"
    REGEX_AMOUNT = r"(?:Rs\.?|INR)\s*([\d,]+\.?\d{0,2})"
    # Matches: "by VPA user@upi" or "from VPA user@upi"
    REGEX_VPA = r"(?:by|from)\s+VPA\s+([a-zA-Z0-9\.\-_]+@[a-zA-Z0-9\.\-_]+)"
    # Matches: "reference number is 123456789"
    REGEX_UTR = r"reference number is\s+(?P<utr>\d+)"

    def handle(self, *args, **kwargs):
        logger.info("🔌 Connecting to IMAP Server...")
        
        try:
            mail = imaplib.IMAP4_SSL('imap.gmail.com')
            mail.login(settings.UPI_VERIFICATION_EMAIL_HOST_USER, settings.UPI_VERIFICATION_EMAIL_HOST_PASSWORD)
            
            # Select the specific folder/label
            mail.select('UPI_ALERTS') 

            # --- TIMEZONE SAFETY FIX ---
            # Search from YESTERDAY to handle timezone boundaries (e.g., 11:59 PM payments)
            yesterday = timezone.now() - datetime.timedelta(days=1)
            date_search_str = yesterday.strftime("%d-%b-%Y")
            
            # Query: UNSEEN emails from HDFC received SINCE yesterday
            query = f'(UNSEEN FROM "alerts@hdfcbank.net" SINCE "{date_search_str}")'
            status, data = mail.search(None, query)
            
            email_ids = data[0].split()
            
            if not email_ids:
                logger.info("   No new payment alerts found.")
                return

            logger.info(f"🔍 Found {len(email_ids)} emails to process.")

            for num in email_ids:
                try:
                    self.process_single_email(mail, num)
                except Exception as e:
                    logger.error(f"   ❌ Critical failure on email ID {num}: {e}", exc_info=True)

            mail.close()
            mail.logout()
            logger.info("Done.")

        except Exception as e:
            logger.critical(f"IMAP Connection Failed: {e}", exc_info=True)

    def process_single_email(self, mail, num):
        """Processes a single email with full audit logging and locking."""
        
        # 1. Fetch Email
        _, msg_data = mail.fetch(num, '(RFC822)')
        msg = email.message_from_bytes(msg_data[0][1])
        
        # 2. Extract Metadata
        # Message-ID is unique globally. We use it to prevent processing the same email twice.
        message_id = msg.get("Message-ID", "").strip()
        sender = msg.get("From", "")
        subject = msg.get("Subject", "")

        # --- IDEMPOTENCY CHECK ---
        # If we have already successfully processed this Message-ID, skip it.
        if PaymentAuditLog.objects.filter(email_message_id=message_id, is_processed=True).exists():
            logger.warning(f"   ⚠️ Skipping duplicate email (already processed): {message_id}")
            return

        # 3. Extract & Clean Body
        body_text = self.extract_body(msg)
        clean_body = " ".join(body_text.split()) # Normalize whitespace

        # 4. Initialize Audit Log (Record the attempt)
        audit_log, created = PaymentAuditLog.objects.get_or_create(
            email_message_id=message_id,
            defaults={
                'sender': sender,
                'subject': subject,
                'raw_body_text': clean_body[:5000] # Save start of body for debugging
            }
        )

        try:
            # 5. Filter Non-Credit Alerts
            if "credited" not in clean_body.lower() and "received" not in clean_body.lower():
                audit_log.processing_error = "Ignored: Not a credit alert"
                audit_log.save()
                return

            # 6. Regex Extraction
            amount_match = re.search(self.REGEX_AMOUNT, clean_body, re.IGNORECASE)
            vpa_match = re.search(self.REGEX_VPA, clean_body, re.IGNORECASE)
            utr_match = re.search(self.REGEX_UTR, clean_body, re.IGNORECASE)

            if not (amount_match and vpa_match):
                audit_log.processing_error = "Regex Failure: Could not extract Amount or VPA"
                audit_log.save()
                logger.warning(f"   ⚠️ Regex failed for email {message_id}")
                return

            # Data Formatting
            extracted_amount = Decimal(amount_match.group(1).replace(',', ''))
            extracted_vpa = vpa_match.group(1).strip()
            extracted_utr = utr_match.group('utr') if utr_match else None
            
            # Update Audit Log with extracted data
            audit_log.extracted_amount = extracted_amount
            audit_log.extracted_vpa = extracted_vpa
            audit_log.extracted_utr = extracted_utr
            audit_log.save()

            logger.info(f"   Processing: {extracted_vpa} | ₹{extracted_amount} | UTR: {extracted_utr}")

            # 7. BUSINESS LOGIC (Atomic Transaction + DB Locking)
            with transaction.atomic():
                # Lock the row immediately to prevent race conditions
                order = Order.objects.select_for_update().filter(
                    payer_upi_id__iexact=extracted_vpa,
                    total_amount=extracted_amount,
                    status=Order.OrderStatus.PENDING
                ).first()

                if not order:
                    audit_log.processing_error = f"No Matching PENDING Order found in DB"
                    audit_log.save()
                    logger.info(f"   ❌ No Pending Order: {extracted_vpa} - {extracted_amount}")
                    return

                # Double-check status (Redundant but safe)
                if order.status == Order.OrderStatus.PAID:
                    audit_log.processing_error = "Order was already PAID (Race condition avoided)"
                    audit_log.save()
                    return

                # --- SUCCESS PATH ---
                # A. Update Order
                order.status = Order.OrderStatus.PAID
                if extracted_utr:
                    order.external_transaction_id = extracted_utr
                order.save()

                # B. Enroll User
                order_item = order.items.first()
                if order_item:
                    UserEnrollment.objects.get_or_create(
                        user=order.user, 
                        item=order_item.item, 
                        source_order=order
                    )
                
                # C. Finalize Audit Log
                audit_log.is_processed = True
                audit_log.processing_error = None # Clear any previous errors
                audit_log.save()
                
                logger.info(f"   ✅ SUCCESS: Order {order.transaction_id} marked PAID.")

        except Exception as e:
            audit_log.processing_error = f"System Exception: {str(e)}"
            audit_log.save()
            raise e

    def extract_body(self, msg):
        """Robustly extracts text from email using BeautifulSoup."""
        text_content = ""
        html_content = ""

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                payload = part.get_payload(decode=True)
                
                if not payload: continue
                
                if content_type == "text/plain":
                    text_content += payload.decode(errors="ignore")
                elif content_type == "text/html":
                    html_content += payload.decode(errors="ignore")
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                text_content = payload.decode(errors="ignore")

        # Priority 1: Plain Text (Safest)
        if text_content.strip():
            return text_content
        
        # Priority 2: HTML parsed to Text
        if html_content:
            soup = BeautifulSoup(html_content, "html.parser")
            return soup.get_text(separator=" ")
        
        return ""