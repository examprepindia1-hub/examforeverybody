import os
import django
from django.utils.text import slugify

# Setup Django Environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from marketplace.models import MarketplaceItem
from courses.models import CourseAttributes, CourseModule, CourseLesson

def create_text_course():
    # 1. Create Marketplace Item
    title = "Python for Data Science: Text Guide"
    slug = slugify(title)
    
    print(f"Creating Text Course: {title}")
    
    item, created = MarketplaceItem.objects.get_or_create(
        slug=slug,
        defaults={
            'title': title,
            'description': "A comprehensive text-based guide to Python for Data Science. No videos, just pure knowledge.",
            'item_type': MarketplaceItem.ItemType.TEXT_COURSE,
            'price': 29.99,
            'is_active': True,
        }
    )
    
    if created:
        print("  - MarketplaceItem created.")
    else:
        print("  - MarketplaceItem already exists.")
        # Ensure it's a TEXT_COURSE
        item.item_type = MarketplaceItem.ItemType.TEXT_COURSE
        item.save()

    # 2. Create Course Attributes
    course_attr, created = CourseAttributes.objects.get_or_create(
        item=item,
        defaults={
            'course_level': 'INTERMEDIATE',
            'what_you_will_learn': "Python syntax, Pandas, NumPy, and Matplotlib.",
            'requirements': "Basic programming knowledge."
        }
    )
    
    # 3. Create Modules (Chapters)
    modules_data = [
        {
            "title": "Module 1: Python Basics",
            "lessons": [
                {"title": "Introduction to Python", "content": "Python is a high-level, interpreted programming language..."},
                {"title": "Variables and Types", "content": "Variables are containers for storing data values..."},
            ]
        },
        {
            "title": "Module 2: Data Analysis",
            "lessons": [
                {"title": "Pandas DataFrames", "content": "Pandas is a fast, powerful, flexible and easy to use open source data analysis and manipulation tool..."},
                {"title": "NumPy Arrays", "content": "NumPy is the fundamental package for scientific computing in Python..."},
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
                    'duration_minutes': 10, # Text reading time
                    'video_url': '', # No Video
                    'order': j,
                    'rich_text_content': lesson_data['content'] * 20 # Make it longer
                }
            )
            print(f"    - Lesson: {lesson_data['title']}")

    print("✅ Text Course Creation Complete!")

if __name__ == '__main__':
    create_text_course()
