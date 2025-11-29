# core/management/commands/populate_db.py

import os
import random
from io import BytesIO
from datetime import timedelta
from django.utils import timezone
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from django.db import transaction
from django.core.files.base import ContentFile
from django.conf import settings
# Make sure Pillow is installed: pip install Pillow
from PIL import Image, ImageDraw, ImageFont

# --- IMPORT YOUR MODELS ---
from users.models import CustomUser
from core.models import Category
from marketplace.models import MarketplaceItem,Testimonial
# FIX: Imported the correct model names based on your provided file
from mocktests.models import MockTestAttributes, TestSection, TestQuestion, QuestionOption
from workshops.models import WorkshopAttributes, WorkshopSession

# --- BRAND COLORS FOR IMAGES ---
BRAND_DARK = "#112938"
BRAND_PRIMARY = "#0056D2"
BRAND_ACCENT = "#E59819" # Gold for highlights

class Command(BaseCommand):
    help = 'Populates DB with comprehensive data: users, items, images, questions, and reviews.'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING("Starting comprehensive data population..."))
        
        # Ensure media directories exist
        os.makedirs(os.path.join(settings.MEDIA_ROOT, 'banners'), exist_ok=True)
        os.makedirs(os.path.join(settings.MEDIA_ROOT, 'marketplace_thumbnails'), exist_ok=True)
        
        # Use atomic transaction ensures either everything works or nothing changes
        with transaction.atomic():
            self.clear_data()
            self.generate_static_banners()
            users = self.create_users()
            categories = self.create_categories()
            items = self.create_marketplace_items(users['instructor'], categories)
            
            # --- NEW: Create deep content ---
            self.create_test_content(items['sat_test'])
            self.create_reviews(users['student'], items)
            
        self.stdout.write(self.style.SUCCESS("Success! Database populated with rich, testable data."))

    def clear_data(self):
        self.stdout.write("Clearing existing data...")
        # Delete in specific order due to foreign key constraints
        Testimonial.objects.all().delete()
        QuestionOption.objects.all().delete()
        TestQuestion.objects.all().delete()
        TestSection.objects.all().delete()
        WorkshopSession.objects.all().delete()
        MockTestAttributes.objects.all().delete()
        WorkshopAttributes.objects.all().delete()
        MarketplaceItem.objects.all().delete()
        Category.objects.all().delete()
        CustomUser.objects.filter(is_superuser=False).delete()

    def create_users(self):
        self.stdout.write("Creating users...")
        instructor = CustomUser.objects.create_user(username='instructor', email='instructor@example.com', password='password123', role='INSTRUCTOR', first_name='Dr. Alan', last_name='Turing')
        student = CustomUser.objects.create_user(username='student', email='student@example.com', password='password123', role='STUDENT', first_name='Jane', last_name='Doe')
        # Create another student for variety in reviews
        student2 = CustomUser.objects.create_user(username='student2', email='bob@example.com', password='password123', role='STUDENT', first_name='Bob', last_name='Smith')
        return {'instructor': instructor, 'student': student, 'student2': student2}

    def create_categories(self):
        self.stdout.write("Creating categories...")
        cats = {}
        academics = Category.objects.create(value='ACAD', display_name='Academics')
        languages = Category.objects.create(value='LANG', display_name='Languages')
        entrance = Category.objects.create(value='ENTR', display_name='Entrance Exams')
        
        cats['SAT'] = Category.objects.create(value='SAT', display_name='SAT Prep', parent_category=academics)
        cats['JEE'] = Category.objects.create(value='JEE', display_name='JEE Mains/Advanced', parent_category=entrance)
        cats['IELTS'] = Category.objects.create(value='IELTS', display_name='IELTS Academic', parent_category=languages)
        return cats

    # --- IMAGE GENERATION ---
    def create_branded_image(self, text, width, height, bg_color, text_color="#ffffff", subtext=None):
        img = Image.new('RGB', (width, height), color=bg_color)
        draw = ImageDraw.Draw(img)
        # Use default font as fallback
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()

        # Draw Main Text centered
        text_bbox = draw.textbbox((0, 0), text, font=font_large)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        x = (width - text_width) / 2
        y = (height - text_height) / 2 if not subtext else (height/2) - text_height - 10
        draw.text((x, y), text, fill=text_color, font=font_large, font_size=40) # Increased font size
        
        if subtext:
            subtext_bbox = draw.textbbox((0, 0), subtext, font=font_small)
            st_width = subtext_bbox[2] - subtext_bbox[0]
            st_x = (width - st_width) / 2
            st_y = y + text_height + 20
            draw.text((st_x, st_y), subtext, fill=text_color, font=font_small, font_size=20)

        # Add brand border
        draw.rectangle([(0,0), (width-1, height-1)], outline=BRAND_PRIMARY, width=8)

        buffer = BytesIO()
        img.save(buffer, format='JPEG', quality=90)
        return ContentFile(buffer.getvalue())

    def generate_static_banners(self):
        self.stdout.write("Generating site banners...")
        banner_img = self.create_branded_image("ExamForEverybody", 1920, 600, BRAND_DARK, subtext="Master Your Future.")
        with open(os.path.join(settings.MEDIA_ROOT, 'banners', 'home_hero.jpg'), 'wb') as f: f.write(banner_img.read())
             
        mid_banner = self.create_branded_image("Achieve Your Goals", 1920, 400, BRAND_PRIMARY, subtext="Practice with the best resources.")
        with open(os.path.join(settings.MEDIA_ROOT, 'banners', 'mid_banner.jpg'), 'wb') as f: f.write(mid_banner.read())

    def create_marketplace_items(self, instructor, cats):
        self.stdout.write("Creating marketplace items...")
        created_items = {}

        # 1. SAT Mock Test
        sat_item = MarketplaceItem.objects.create(
            title='SAT Math Masterclass & Practice', slug='sat-math-masterclass',
            description='Comprehensive SAT Math prep with 2 full-length practice tests based on the new digital format.',
            item_type='MOCK_TEST', price=19.99, is_active=True
        )
        sat_item.categories.add(cats['SAT'])
        img_file = self.create_branded_image('SAT MATH Prep', 600, 400, BRAND_DARK)
        sat_item.thumbnail_image.save('sat-thumb.jpg', img_file, save=True)
        # MockTestAttributes is linked O2O, so we pass the item instance itself
        MockTestAttributes.objects.create(item=sat_item, level='INTERMEDIATE', duration_minutes=135, ranking_weight=1.5)
        created_items['sat_test'] = sat_item

        # 2. JEE Physics Test
        jee_item = MarketplaceItem.objects.create(
            title='JEE Advanced Physics Challenge', slug='jee-physics-advanced',
            description='High-difficulty physics problems designed for top JEE Advanced aspirants.',
            item_type='MOCK_TEST', price=24.99, is_active=True
        )
        jee_item.categories.add(cats['JEE'])
        img_file = self.create_branded_image('JEE PHYSICS', 600, 400, '#0a1f2e')
        jee_item.thumbnail_image.save('jee-thumb.jpg', img_file, save=True)
        MockTestAttributes.objects.create(item=jee_item, level='ADVANCED', duration_minutes=180, ranking_weight=2.0)
        created_items['jee_test'] = jee_item

        # 3. Live Workshop
        ws_item = MarketplaceItem.objects.create(
            title="Live Strategy: Cracking the IELTS Speaking Section", slug="ielts-speaking-live",
            description="Join expert instructors live to practice speaking cues and get real-time feedback to boost your band score.",
            item_type='WORKSHOP', price=49.00, is_active=True
        )
        ws_item.categories.add(cats['IELTS'])
        img_file = self.create_branded_image("IELTS LIVE STRATEGY", 600, 400, BRAND_PRIMARY, text_color='#ffffff')
        ws_item.thumbnail_image.save('workshop-thumb.jpg', img_file, save=True)
        ws_attrs = WorkshopAttributes.objects.create(item=ws_item, instructor=instructor, description_long="Full agenda here...", total_duration_hours=2.5)
        WorkshopSession.objects.create(workshop=ws_attrs, start_time=timezone.now() + timedelta(days=5, hours=10), end_time=timezone.now() + timedelta(days=5, hours=12, minutes=30))
        created_items['workshop'] = ws_item

        return created_items

    # --- FIXED FUNCTION: Create Questions & Options based on your models.py ---
    def create_test_content(self, test_item):
        self.stdout.write(f"Creating questions for {test_item.title}...")
        
        # 1. Create a Section
        # FIX: Using correct field names from your models.py
        section = TestSection.objects.create(
            test=test_item.mock_test_details,   # Field name is 'test'
            title="Module 1: Math (No Calculator)",
            sort_order=1                        # Field name is 'sort_order'
        )

        # 2. Create dummy questions
        for i in range(1, 6):
            question = TestQuestion.objects.create(
                section=section,                 # Field name is 'section'
                question_text=f"Question {i}: If 3x + 5 = 20, what is the value of x?", # Field name is 'question_text'
                marks=1,
                sort_order=i,                    # Field name is 'sort_order'
                question_type='MCQ',             # Field name is 'question_type'
                explanation="Subtract 5 from both sides: 3x = 15. Divide by 3: x = 5."
            )

            # 3. Create Options for the question
            options = [("3", False), ("4", False), ("5", True), ("6", False)]
            
            for j, (opt_text, is_correct) in enumerate(options):
                QuestionOption.objects.create(
                    question=question,           # Field name is 'question'
                    option_text=f"Option {chr(65+j)}: {opt_text}", # Field name is 'option_text'
                    is_correct=is_correct
                    # sort_order is not present in your QuestionOption model, removed it.
                )

    # --- NEW FUNCTION: Create Reviews ---
    def create_reviews(self, student_user, items):
        self.stdout.write("Creating student reviews...")
        # Review for SAT Test
        Testimonial.objects.create(
            item=items['sat_test'],
            user=student_user,
            rating=5,
            text="Excellent practice test. The questions were very similar to the actual digital SAT format. Highly recommended!"
        )
        
        # Review for Workshop (using the second student account)
        student2 = CustomUser.objects.get(username='student2')
        Testimonial.objects.create(
            item=items['workshop'],
            user=student2,
            rating=4,
            text="Great session. The instructor was very knowledgeable. I just wish it was a bit longer."
        )