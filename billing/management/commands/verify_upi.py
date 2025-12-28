import imaplib
import email
import re
from django.core.management.base import BaseCommand
from django.conf import settings
from billing.models import Order
from enrollments.models import UserEnrollment

# Helper to strip HTML tags if the email is HTML-only
def clean_html(raw_html):
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, ' ', raw_html)
    return cleantext

class Command(BaseCommand):
    help = 'Checks HDFC Alert emails for UPI payment confirmations'

    def handle(self, *args, **kwargs):
        self.stdout.write("🔌 Connecting to Gmail...")
        
        try:
            mail = imaplib.IMAP4_SSL('imap.gmail.com')
            mail.login(settings.UPI_VERIFICATION_EMAIL_HOST_USER, settings.UPI_VERIFICATION_EMAIL_HOST_PASSWORD)
            mail.select('inbox')
            
            # Search for HDFC Alerts
            # Change 'ALL' to 'UNSEEN' in production to avoid re-reading old emails
            status, data = mail.search(None, '(FROM "alerts@hdfcbank.net")')
            
            email_ids = data[0].split()
            # Process last 10 emails only
            latest_email_ids = email_ids[-10:] 
            
            self.stdout.write(f"🔍 Checking last {len(latest_email_ids)} emails from HDFC...")

            for num in reversed(latest_email_ids):
                status, msg_data = mail.fetch(num, '(RFC822)')
                msg = email.message_from_bytes(msg_data[0][1])
                subject = msg.get("Subject", "")
                
                # --- ROBUST BODY EXTRACTION ---
                body = ""
                html_body = ""
                
                if msg.is_multipart():
                    for part in msg.walk():
                        content_type = part.get_content_type()
                        content_disposition = str(part.get("Content-Disposition"))

                        if "attachment" in content_disposition:
                            continue

                        try:
                            payload = part.get_payload(decode=True)
                            if payload:
                                decoded_payload = payload.decode(errors="ignore")
                                if content_type == "text/plain":
                                    body += decoded_payload
                                elif content_type == "text/html":
                                    html_body += decoded_payload
                        except:
                            pass
                else:
                    try:
                        payload = msg.get_payload(decode=True)
                        if payload:
                            body = payload.decode(errors="ignore")
                    except:
                        pass

                # Fallback: If no plain text, use the HTML body stripped of tags
                if not body.strip() and html_body:
                    body = clean_html(html_body)

                # Clean up whitespace
                body = " ".join(body.split())

                # --- MATCHING LOGIC ---
                # Only look at Credit Alerts
                if "credited" in body.lower() or "received" in body.lower():
                    
                    self.stdout.write(f"   --------------------------------")
                    self.stdout.write(f"   Checking: {subject}")

                    # Regex 1: Amount (Handles "Rs. 1,000.00" or "Rs 1.00")
                    amount_match = re.search(r"(?:Rs\.?|INR)\s*([\d,]+\.?\d{0,2})", body, re.IGNORECASE)
                    
                    # Regex 2: VPA (Handles "by VPA user@bank" or "from VPA user@bank")
                    vpa_match = re.search(r"(?:by|from)\s+VPA\s+([a-zA-Z0-9\.\-_]+@[a-zA-Z0-9\.\-_]+)", body, re.IGNORECASE)

                    # Regex 3: UTR / Reference Number (Based on HDFC format)
                    # Pattern: "reference number is 536100250991"
                    utr_match = re.search(r"reference number is\s+(?P<utr>\d+)", body, re.IGNORECASE)

                    if vpa_match and amount_match:
                        raw_amount = amount_match.group(1).replace(',', '') # Remove commas
                        extracted_amount = float(raw_amount)
                        extracted_vpa = vpa_match.group(1)
                        
                        # Extract UTR if found, else None
                        extracted_utr = utr_match.group('utr') if utr_match else None

                        self.stdout.write(self.style.SUCCESS(f"   💰 FOUND: ₹{extracted_amount} from {extracted_vpa} (UTR: {extracted_utr})"))

                        # Verify against Database
                        try:
                            # We look for a PENDING order with matching VPA and Amount
                            order = Order.objects.get(
                                payer_upi_id__iexact=extracted_vpa,
                                total_amount=extracted_amount,
                                status=Order.OrderStatus.PENDING
                            )
                            
                            # 1. Mark as PAID
                            order.status = Order.OrderStatus.PAID
                            
                            # 2. Save External ID (UTR)
                            if extracted_utr:
                                order.external_transaction_id = extracted_utr
                                
                            order.save()
                            
                            # 3. Enroll User
                            order_item = order.items.first()
                            if order_item:
                                UserEnrollment.objects.get_or_create(
                                    user=order.user, item=order_item.item, source_order=order
                                )
                            
                            self.stdout.write(self.style.SUCCESS(f"   ✅ SUCCESS: Order {order.transaction_id} finalized."))
                            
                        except Order.DoesNotExist:
                            self.stdout.write(f"      (No matching pending order in DB)")
                    else:
                        self.stdout.write(f"      (Regex failed to extract Data)")

            mail.close()
            mail.logout()
            self.stdout.write("Done.")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {e}"))