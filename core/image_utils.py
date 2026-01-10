import sys
from io import BytesIO
from PIL import Image
from django.core.files.uploadedfile import InMemoryUploadedFile

def compress_image(image_field, max_width=800, quality=80):
    """
    Compresses and resizes an image to WebP format.
    Args:
        image_field: The ImageField file object.
        max_width: Maximum width in pixels.
        quality: Compression quality (1-100).
    Returns:
        InMemoryUploadedFile: The compressed image file.
    """
    if not image_field:
        return None

    # Open the image using Pillow
    img = Image.open(image_field)
    
    # Convert to RGB (required for WebP/JPEG if original is RGBA/P)
    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')

    # Resize if width > max_width
    if img.width > max_width:
        ratio = max_width / float(img.width)
        new_height = int(float(img.height) * ratio)
        img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)

    # Save to BytesIO buffer
    output_io = BytesIO()
    img.save(output_io, format='WEBP', quality=quality, optimize=True)
    output_io.seek(0)

    # Create a new InMemoryUploadedFile
    new_filename = f"{image_field.name.split('.')[0]}.webp"
    return InMemoryUploadedFile(
        output_io,
        'ImageField',
        new_filename,
        'image/webp',
        sys.getsizeof(output_io),
        None
    )
