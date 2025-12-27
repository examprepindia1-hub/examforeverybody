import random
from datetime import timedelta
from django.utils import timezone
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from marketplace.models import MarketplaceItem, Testimonial
from django.db import transaction

User = get_user_model()

class Command(BaseCommand):
    help = 'Resets and seeds items with GLOBAL Testimonials, History, and enrollment counts'

    def handle(self, *args, **kwargs):
        self.stdout.write("🧹 Cleaning up old reviews...")
        
        # 1. DELETE ALL EXISTING REVIEWS (Clean Slate)
        Testimonial.objects.all().delete()
        
        self.stdout.write("🌍 Starting Global Data Seeding...")

        # 2. Define Global Personas
        # Diverse names and countries
        global_personas = [
            {"first": "Liam", "last": "Thompson", "country": "USA"},
            {"first": "Emma", "last": "Wilson", "country": "UK"},
            {"first": "Wei", "last": "Chen", "country": "China"},
            {"first": "Ahmed", "last": "Al-Fayed", "country": "UAE"},
            {"first": "Priya", "last": "Sharma", "country": "India"},
            {"first": "Elena", "last": "Rossi", "country": "Italy"},
            {"first": "Yuki", "last": "Tanaka", "country": "Japan"},
            {"first": "Kwame", "last": "Mensah", "country": "Ghana"},
            {"first": "Sophie", "last": "Dubois", "country": "France"},
            {"first": "Lars", "last": "Jensen", "country": "Denmark"},
            {"first": "Carlos", "last": "Rodriguez", "country": "Spain"},
            {"first": "Aarav", "last": "Patel", "country": "India"},
            {"first": "Fatima", "last": "Khan", "country": "Pakistan"},
            {"first": "Lucas", "last": "Silva", "country": "Brazil"},
            {"first": "Sarah", "last": "Jenkins", "country": "Canada"},
            {"first": "Hans", "last": "Mueller", "country": "Germany"},
            {"first": "Chloe", "last": "Kim", "country": "South Korea"},
            {"first": "Isabella", "last": "Martinez", "country": "Argentina"},
        ]
        
        # Create/Get Bot Users
        bots = []
        for p in global_personas:
            username = f"{p['first'].lower()}_{p['country'].lower()}_bot"
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'first_name': p['first'], 
                    'last_name': p['last'],
                    'email': f"{username}@example.com"
                }
            )
            if created:
                user.set_unusable_password()
                user.save()
            bots.append({'user': user, 'country': p['country']})
        
        self.stdout.write(f"✅ Loaded {len(bots)} global bot users.")

        # 3. Content Templates (Focus: Exams, Written Solutions, Blog)
        # Detailed, descriptive, and positive.
        
        review_templates = [
            # Focus: Written Solutions
            "I was struggling to understand *why* I was getting questions wrong. The written solutions in this package are incredibly detailed—they don't just give the answer but explain the logic step-by-step. It's like having a tutor explain it to you.",
            
            # Focus: Exam Interface
            "The mock exam interface is virtually identical to the real test environment. Practicing here helped me manage my anxiety and timing significantly. By the time I sat for the actual exam, it felt like just another practice session.",
            
            # Focus: Blog/Strategy
            "I initially bought this just for the mocks, but the strategy articles on the blog are a hidden gem. The tips on elimination techniques and time management helped me boost my score by 15% alone.",
            
            # Focus: Comprehensive
            "Excellent resource. The question bank is challenging, and the detailed text explanations clear up concepts immediately. I also appreciate the blog updates regarding the syllabus changes—very timely.",
            
            # Focus: Global/General
            "Using this from {country}, and I must say it matches international standards. The written notes are concise yet comprehensive, perfect for last-minute revision.",
            
            # Focus: Difficulty Level
            "The difficulty level of these mock tests is slightly higher than the actual exam, which is exactly what I needed. It over-prepared me in the best way possible. The solutions are rigorous and leave no room for doubt.",
            
            # Focus: Notes/Solutions
            "I prefer reading over watching videos, so the detailed written notes and solution keys were perfect for me. I could skim through topics I knew and deep-dive into the complex ones. Highly recommended.",
        ]

        items = MarketplaceItem.objects.all()

        with transaction.atomic():
            for item in items:
                # --- A. Set Enrollment Count (1500+) ---
                fake_count = random.randint(1500, 4200)
                item.base_enrollment_count = fake_count
                item.save()

                # --- B. Add 5-9 Reviews per item ---
                num_reviews = random.randint(5, 9)
                selected_bots = random.sample(bots, num_reviews)

                for bot_data in selected_bots:
                    user = bot_data['user']
                    country_name = bot_data['country']

                    # Pick a random template and inject country if needed
                    template = random.choice(review_templates)
                    comment_text = template.replace("{country}", country_name)
                    
                    # Generate a random past date (between 2 years ago and yesterday)
                    days_ago = random.randint(1, 730) 
                    past_date = timezone.now() - timedelta(days=days_ago)

                    # Create Testimonial
                    # We check if one exists to respect unique_together, though we cleared all at start
                    if not Testimonial.objects.filter(item=item, user=user).exists():
                        review = Testimonial.objects.create(
                            item=item,
                            user=user,
                            country=country_name,
                            rating=random.choice([4, 5, 5, 5]), # High satisfaction
                            text=comment_text
                        )
                        
                        # MANUALLY UPDATE TIMESTAMP
                        # We must update 'created' after creation because auto_now_add sets it initially
                        review.created = past_date
                        review.save(update_fields=['created'])

                self.stdout.write(f"   -> Updated '{item.title}': {fake_count} students, {num_reviews} reviews (dating back to {past_date.year}).")

        self.stdout.write(self.style.SUCCESS("🎉 Successfully seeded fresh, detailed, global reviews with history!"))