import qrcode
from io import BytesIO
from django.core.files import File
from django.conf import settings

def generate_upi_qr_image(order_id, amount, merchant_vpa, merchant_name):
    """
    Generates a UPI QR code image object compatible with Django ImageField.
    """
    # 1. Construct the UPI URL
    # format: upi://pay?pa={merchant_vpa}&pn={name}&am={amount}&tn={order_id}&cu=INR
    upi_url = f"upi://pay?pa={merchant_vpa}&pn={merchant_name}&am={amount}&tn={order_id}&cu=INR"
    
    # 2. Create QR Object
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(upi_url)
    qr.make(fit=True)

    # 3. Generate Image
    img = qr.make_image(fill_color="black", back_color="white")
    
    # 4. Save to BytesIO (Memory) to save to Django Field
    blob = BytesIO()
    img.save(blob, 'PNG')
    return blob