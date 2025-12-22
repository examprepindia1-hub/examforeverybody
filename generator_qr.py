import qrcode
import os

def generate_upi_qr(upi_id, name, amount, order_id, filename="payment_qr.png"):
    """
    Generates a UPI QR code and saves it to the disk.
    """
    
    # 1. Construct the UPI URL
    # format: upi://pay?pa={upi_id}&pn={name}&am={amount}&tn={order_id}
    # We use f-strings to inject the variables securely.
    upi_url = f"upi://pay?pa={upi_id}&pn={name}&am={amount}&tn={order_id}"
    
    print(f"Generating QR for URL: {upi_url}")

    # 2. Create the QR Code object
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H, # High error correction
        box_size=10,
        border=4,
    )
    
    # 3. Add data to the QR object
    qr.add_data(upi_url)
    qr.make(fit=True)

    # 4. Create the image
    img = qr.make_image(fill_color="black", back_color="white")

    # 5. Save the image
    img.save(filename)
    print(f"Success! QR code saved as '{filename}' in: {os.getcwd()}")

# --- Configuration ---
# Replace these with your actual details
MY_UPI_ID = "9582929093@hdfc"    # Your UPI ID (VPA)
MY_NAME = "ExamForEverybody"   # Your Name or Business Name
AMOUNT = "1.00"                # Amount (Use string to avoid float errors)
ORDER_ID = "Order-1001"        # Unique Reference / Transaction Note

# --- Run the function ---
if __name__ == "__main__":
    generate_upi_qr(MY_UPI_ID, MY_NAME, AMOUNT, ORDER_ID)