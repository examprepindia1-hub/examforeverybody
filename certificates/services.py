from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from io import BytesIO
import textwrap

def generate_certificate_pdf(certificate):
    """
    Generates a PDF certificate for the given Certificate instance.
    Returns: bytes
    """
    buffer = BytesIO()
    
    # Create the PDF object, using the buffer as its "file."
    c = canvas.Canvas(buffer, pagesize=landscape(letter))
    width, height = landscape(letter)
    
    # --- DESIGN ---
    
    # 1. Border
    c.setStrokeColor(colors.darkblue)
    c.setLineWidth(5)
    c.rect(0.5*inch, 0.5*inch, width - 1*inch, height - 1*inch)
    
    # 2. Header
    c.setFont("Helvetica-Bold", 36)
    c.setFillColor(colors.darkblue)
    c.drawCentredString(width / 2, height - 2 * inch, "Certificate of Completion")
    
    # 3. Sub-header
    c.setFont("Helvetica", 14)
    c.setFillColor(colors.black)
    c.drawCentredString(width / 2, height - 2.5 * inch, "This is to certify that")
    
    # 4. User Name
    user_name = f"{certificate.user.first_name} {certificate.user.last_name}".strip() or certificate.user.email
    c.setFont("Helvetica-Bold", 30)
    c.setFillColor(colors.black)
    c.drawCentredString(width / 2, height - 3.2 * inch, user_name)
    
    # 5. Course/Test Title
    c.setFont("Helvetica", 14)
    c.drawCentredString(width / 2, height - 4 * inch, "has successfully completed the")
    
    item_title = certificate.item.title
    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(width / 2, height - 4.5 * inch, item_title)
    
    # 6. Verification ID & Date
    c.setFont("Helvetica", 10)
    c.setFillColor(colors.gray)
    
    date_str = certificate.created.strftime("%B %d, %Y")
    c.drawCentredString(width / 2, 1.5 * inch, f"Issued on: {date_str}")
    c.drawCentredString(width / 2, 1.2 * inch, f"Certificate ID: {certificate.certificate_id}")
    
    # 7. Signature Line (Mock)
    c.line(width - 3*inch, 1.8*inch, width - 1*inch, 1.8*inch)
    c.setFont("Helvetica", 10)
    c.drawString(width - 2.8*inch, 1.6*inch, "Director, ExamPrepIndia")
    
    c.showPage()
    c.save()
    
    buffer.seek(0)
    return buffer.getvalue()
