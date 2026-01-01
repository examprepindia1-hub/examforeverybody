import imaplib
import email
import re
import socket
import datetime
import pytz
from bs4 import BeautifulSoup
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from billing.models import Order

# --- CONFIGURATION ---
# Set a strict timeout so the script doesn't hang forever
socket.setdefaulttimeout(30) 

class Command(BaseCommand):
    help = 'Enterprise HDFC UPI Verification (With Atomic Safety & Amount Handling)'

    # --- REGEX PATTERNS (TUNED) ---
    # Matches: "Rs. 1.00" (Handles commas and decimals)
    REGEX_AMOUNT = r"Rs\.?\s*([\d,]+\.?\d{0,2})"
    
    # Matches: "by VPA jsamyak100-1@okaxis"
    # Logic: Captures until the next space to avoid grabbing names like "SAMYAK"
    REGEX_VPA = r"by\s+VPA\s+([a-zA-Z0-9\.\-_]+@[a-zA-Z0-9\.\-_]+)"
    
    # Matches: "reference number is 636758035286"
    REGEX_UTR = r"reference number is\s+(?P<utr>\d+)"

    def handle(self, *args, **kwargs):
        print("🔌 Connecting to IMAP Server...")
        
        try:
            mail = imaplib.IMAP4_SSL('imap.gmail.com')
            mail.login(settings.UPI_VERIFICATION_EMAIL_HOST_USER, settings.UPI_VERIFICATION_EMAIL_HOST_PASSWORD)
            
            mail.select('UPI_ALERTS') 

            # --- TIMEZONE FIX (IST) ---
            # Ensures we search the correct "days" relative to Indian banking hours
            now_utc = timezone.now()
            ist_timezone = pytz.timezone('Asia/Kolkata')
            now_ist = now_utc.astimezone(ist_timezone)
            
            # Search last 3 days to cover weekends/holidays
            search_date = now_ist - datetime.timedelta(days=3)
            date_search_str = search_date.strftime("%d-%b-%Y")
            
            # Query: UNSEEN emails from HDFC
            query = f'(UNSEEN FROM "alerts@hdfcbank.net" SINCE "{date_search_str}")'
            
            print(f"   🇮🇳 Current Time (IST): {now_ist}")
            
            status, data = mail.search(None, query)
            email_ids = data[0].split()
            
            if not email_ids:
                print("   ℹ️ No new unread payment alerts.")
                return

            print(f"🔍 Found {len(email_ids)} unread emails...")

            for num in email_ids:
                try:
                    self.process_single_email(mail, num)
                except Exception as e:
                    print(f"   ❌ Critical Error on Email {num}: {e}")

            mail.close()
            mail.logout()
            print("Done.")

        except Exception as e:
            print(f"🔥 IMAP Connection Failed: {e}")

    def process_single_email(self, mail, num):
        # 1. Fetch Email
        _, msg_data = mail.fetch(num, '(RFC822)')
        msg = email.message_from_bytes(msg_data[0][1])
        
        # 2. Extract Body
        body_text = self.extract_body(msg)
        clean_body = " ".join(body_text.split())

        # 3. Validation: Must be a credit alert
        if "credited" not in clean_body.lower():
            return

        # 4. Regex Extraction
        amount_match = re.search(self.REGEX_AMOUNT, clean_body, re.IGNORECASE)
        vpa_match = re.search(self.REGEX_VPA, clean_body, re.IGNORECASE)
        utr_match = re.search(self.REGEX_UTR, clean_body, re.IGNORECASE)

        if not (amount_match and vpa_match):
            # print(f"   ⚠️ Regex Failed. Snippet: {clean_body[:50]}")
            return

        # 5. Data Cleaning
        extracted_amount = Decimal(amount_match.group(1).replace(',', ''))
        # Remove trailing dots/spaces from VPA
        extracted_vpa = vpa_match.group(1).strip().rstrip('.')
        extracted_utr = utr_match.group('utr') if utr_match else None

        print(f"   Processing: {extracted_vpa} | ₹{extracted_amount} | UTR: {extracted_utr}")

        try:
            # START ATOMIC BLOCK (All or Nothing)
            with transaction.atomic():
                
                # -------------------------------------------------------
                # CASE A: EXACT MATCH (Success)
                # -------------------------------------------------------
                # Checks PENDING, TIMED_OUT (Revival), and INCORRECT_AMOUNT (Correction)
                success_order = Order.objects.select_for_update().filter(
                    payer_upi_id__iexact=extracted_vpa,
                    total_amount=extracted_amount,
                    status__in=[
                        Order.OrderStatus.PENDING, 
                        Order.OrderStatus.TIMED_OUT
                    ]
                ).order_by('-created').first()

                if success_order:
                    if success_order.status == Order.OrderStatus.PAID:
                        print(f"   ⚠️ Order {success_order.id} is already PAID.")
                        return

                    # 1. Update Order
                    success_order.status = Order.OrderStatus.PAID
                    if extracted_utr:
                        success_order.external_transaction_id = extracted_utr
                    success_order.save()
                    
                    # 2. Enroll User (Must succeed or we Rollback)
                    from enrollments.models import UserEnrollment
                    
                    order_item = success_order.items.first()
                    if not order_item:
                        raise ValueError(f"Order {success_order.id} has no items to enroll!")

                    UserEnrollment.objects.get_or_create(
                        user=success_order.user, 
                        item=order_item.item, 
                        source_order=success_order
                    )
                    
                    print(f"   ✅ SUCCESS: Order {success_order.id} Paid & Enrolled!")
                    return # Exit function success

                # -------------------------------------------------------
                # CASE B: PARTIAL/WRONG PAYMENT (Warning)
                # -------------------------------------------------------
                # If we are here, Amount didn't match. Find VPA match in PENDING.
                wrong_order = Order.objects.select_for_update().filter(
                    payer_upi_id__iexact=extracted_vpa,
                    status=Order.OrderStatus.PENDING
                ).order_by('-created').first()

                if wrong_order:
                    print(f"   ⚠️ WRONG AMOUNT: User paid ₹{extracted_amount}, expected ₹{wrong_order.total_amount}")
                    wrong_order.status = Order.OrderStatus.INCORRECT_AMOUNT
                    wrong_order.save()
                    return

                # -------------------------------------------------------
                # CASE C: ORPHAN (No Match)
                # -------------------------------------------------------
                print(f"   ❌ ORPHAN: No matching order found for {extracted_vpa}")

        except Exception as e:
            # CRITICAL: This catches Enrollment errors and auto-rollbacks the transaction
            print(f"   🔥 ROLLBACK: Transaction failed for {extracted_vpa}. Error: {e}")

    def extract_body(self, msg):
        """Robustly extracts text from email."""
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

        if text_content.strip():
            return text_content
        if html_content:
            soup = BeautifulSoup(html_content, "html.parser")
            return soup.get_text(separator=" ")
        return ""