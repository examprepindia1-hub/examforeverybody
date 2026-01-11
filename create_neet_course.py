import os
import django
from django.utils.text import slugify

# Setup Django Environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from marketplace.models import MarketplaceItem
from courses.models import CourseAttributes, CourseModule, CourseLesson

def create_course():
    # 1. Create Marketplace Item
    title = "NEET-UG: Diversity in Living World (Unit 1)"
    slug = slugify(title)
    
    print(f"Creating Course: {title}")
    
    item, created = MarketplaceItem.objects.get_or_create(
        slug=slug,
        defaults={
            'title': title,
            'description': "Comprehensive coverage of Unit 1 for NEET-UG aspirants. Covers The Living World, Biological Classification, Plant Kingdom, and Animal Kingdom.",
            'item_type': MarketplaceItem.ItemType.VIDEO_COURSE,
            'price': 49.99,
            'is_active': True,
        }
    )
    
    if created:
        print("  - MarketplaceItem created.")
    else:
        print("  - MarketplaceItem already exists.")

    # 2. Create Course Attributes
    course_attr, created = CourseAttributes.objects.get_or_create(
        item=item,
        defaults={
            'course_level': 'BEGINNER',
            'what_you_will_learn': "Understanding of Taxonomy, Classification systems, and detailed study of Plant and Animal Kingdoms.",
            'requirements': "Class 10th Biology basics."
        }
    )
    
    # 3. Create Modules (Chapters)
    modules_data = [
        {
            "title": "Chapter 1: The Living World",
            "lessons": [
                {"title": "What is Living?", "duration": 15, "video": "https://www.youtube.com/embed/dQw4w9WgXcQ"}, # Placeholder
                {"title": "Diversity in the Living World", "duration": 20, "video": ""},
                {"title": "Taxonomic Categories", "duration": 25, "video": ""},
                {"title": "Taxonomical Aids", "duration": 15, "video": ""}
            ]
        },
        {
            "title": "Chapter 2: Biological Classification",
            "lessons": [
                {"title": "Kingdom Monera", "duration": 30, "video": ""},
                {"title": "Kingdom Protista", "duration": 25, "video": ""},
                {"title": "Kingdom Fungi", "duration": 35, "video": ""},
                {"title": "Kingdom Plantae & Animalia (Brief)", "duration": 10, "video": ""},
                {"title": "Viruses, Viroids and Lichens", "duration": 20, "video": ""}
            ]
        },
        {
            "title": "Chapter 3: Plant Kingdom",
            "lessons": [
                {"title": "Algae", "duration": 25, "video": ""},
                {"title": "Bryophytes", "duration": 25, "video": ""},
                {"title": "Pteridophytes", "duration": 25, "video": ""},
                {"title": "Gymnosperms", "duration": 20, "video": ""},
                {"title": "Angiosperms", "duration": 20, "video": ""}
            ]
        },
        {
            "title": "Chapter 4: Animal Kingdom",
            "lessons": [
                {"title": "Basis of Classification", "duration": 30, "video": ""},
                {"title": "Phylum Porifera to Platyhelminthes", "duration": 35, "video": ""},
                {"title": "Phylum Aschelminthes to Annelida", "duration": 30, "video": ""},
                {"title": "Phylum Arthropoda to Hemichordata", "duration": 40, "video": ""},
                {"title": "Phylum Chordata", "duration": 45, "video": ""}
            ]
        }
    ]

    for i, mod_data in enumerate(modules_data, 1):
        module, _ = CourseModule.objects.get_or_create(
            course=course_attr,
            title=mod_data['title'],
            defaults={'order': i}
        )
        print(f"  - Module: {module.title}")
        
        for j, lesson_data in enumerate(mod_data['lessons'], 1):
            CourseLesson.objects.get_or_create(
                module=module,
                title=lesson_data['title'],
                defaults={
                    'duration_minutes': lesson_data['duration'],
                    'video_url': lesson_data.get('video', ''),
                    'order': j,
                    'rich_text_content': f"Detailed notes for {lesson_data['title']}..."
                }
            )
            print(f"    - Lesson: {lesson_data['title']}")

    print("✅ Course Creation Complete!")

if __name__ == '__main__':
    create_course()
