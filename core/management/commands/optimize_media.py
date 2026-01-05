import os
from django.core.management.base import BaseCommand
from django.conf import settings
from PIL import Image

class Command(BaseCommand):
    help = 'Aggressively compresses all existing images in the MEDIA_ROOT to improve performance'

    def handle(self, *args, **options):
        total_saved_space = 0
        images_processed = 0
        
        # 1. Define Supported Formats
        valid_extensions = {'.jpg', '.jpeg', '.png'}
        
        self.stdout.write("🚀 Starting Image Optimization...")

        # 2. Walk through every folder in your Media directory
        for root, dirs, files in os.walk(settings.MEDIA_ROOT):
            for filename in files:
                ext = os.path.splitext(filename)[1].lower()
                
                if ext in valid_extensions:
                    file_path = os.path.join(root, filename)
                    
                    try:
                        # Get original size
                        original_size = os.path.getsize(file_path)
                        
                        # 3. Open Image
                        with Image.open(file_path) as img:
                            
                            # Skip if already small (optional, e.g., < 50KB)
                            if original_size < 50 * 1024: 
                                continue

                            # 4. Resize huge images (Max width 1200px is usually enough for web)
                            max_width = 1200
                            if img.width > max_width:
                                ratio = max_width / img.width
                                new_height = int(img.height * ratio)
                                img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
                            
                            # 5. Compress
                            # We save to a temporary buffer or overwrite directly
                            # Convert RGBA to RGB if saving as JPEG to avoid crash
                            if ext in ['.jpg', '.jpeg'] and img.mode == 'RGBA':
                                img = img.convert('RGB')
                                
                            # Save with Optimization
                            # quality=80 is "visually lossless" but much smaller
                            img.save(file_path, optimize=True, quality=80)
                        
                        # Calculate Savings
                        new_size = os.path.getsize(file_path)
                        saved = original_size - new_size
                        if saved > 0:
                            total_saved_space += saved
                            images_processed += 1
                            self.stdout.write(f"✅ Optimized: {filename} (Saved {saved/1024:.2f} KB)")
                        
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"❌ Failed: {filename} - {e}"))

        # Summary
        mb_saved = total_saved_space / (1024 * 1024)
        self.stdout.write(self.style.SUCCESS(f"\n🎉 DONE! Processed {images_processed} images."))
        self.stdout.write(self.style.SUCCESS(f"💾 Total Space Saved: {mb_saved:.2f} MB"))