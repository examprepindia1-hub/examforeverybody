from django.core.management.base import BaseCommand
from marketplace.models import MarketplaceItem, MarketplaceCatalog
from core.image_utils import compress_image
from django.core.files import File

class Command(BaseCommand):
    help = 'Compresses all existing images to WebP format to optimize load times.'

    def handle(self, *args, **options):
        self.stdout.write("Starting image optimization...")
        
        # 1. Optimize Marketplace Items
        items = MarketplaceItem.objects.filter(thumbnail_image__isnull=False).exclude(thumbnail_image='')
        count = 0
        
        for item in items:
            try:
                # Check if already optimized (simple check by extension)
                if item.thumbnail_image.name.lower().endswith('.webp'):
                    self.stdout.write(f"Skipping {item.title} (Already WebP)")
                    continue

                self.stdout.write(f"Optimizing {item.title}...")
                
                # Perform Compression
                # We need to open the file, compress it, and save it back
                with item.thumbnail_image.open('rb') as f:
                    compressed_file = compress_image(f)
                
                if compressed_file:
                    # Save the new file. ensure we don't trigger the model.save recursion if we were using signals
                    # We are using model.save, but our model.save checks for InMemoryUploadedFile. 
                    # create a File object from the compressed bytes
                    
                    item.thumbnail_image.save(compressed_file.name, compressed_file, save=True)
                    self.stdout.write(self.style.SUCCESS(f"Saved {item.title}"))
                    count += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed to process {item.title}: {e}"))

        self.stdout.write(self.style.SUCCESS(f"Optimization Complete. Processed {count} images."))
