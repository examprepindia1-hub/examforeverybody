import random
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from marketplace.models import MarketplaceItem, Testimonial

User = get_user_model()

class Command(BaseCommand):
    help = 'Populates ALL MarketplaceItems with random testimonials from a predefined pool'

    def handle(self, *args, **kwargs):
        # ==========================================
        # 1. THE DATA POOL
        # ==========================================
        # List of 50 unique reviews with their associated user and country
        reviews_pool = [
            {"email": "aarav_india_bot@example.com", "country": "India", "rating": 5, "text": "The math section was incredibly similar to the actual DSAT. Highly recommended!"},
            {"email": "aaravpatel_bot@example.com", "country": "India", "rating": 4, "text": "Great practice material. The reading passages were a bit denser than I expected, but good prep."},
            {"email": "ahmedal-fayed_bot@example.com", "country": "Egypt", "rating": 5, "text": "Perfect for timing practice. I finally finished the module on time thanks to this."},
            {"email": "ahmed_uae_bot@example.com", "country": "UAE", "rating": 4, "text": "Very helpful. The interface feels just like the real exam app."},
            {"email": "ashwani93351892@gmail.com", "country": "India", "rating": 5, "text": "Best mock series I've found. The explanations for the wrong answers were very clear."},
            {"email": "carlosrodriguez_bot@example.com", "country": "Mexico", "rating": 3, "text": "Good questions, but the server was a little slow for me during the test."},
            {"email": "carlos_spain_bot@example.com", "country": "Spain", "rating": 5, "text": "Excelentes pruebas. Helped me improve my score by 150 points."},
            {"email": "chloe_south korea_bot@example.com", "country": "South Korea", "rating": 5, "text": "The difficulty level is perfect. Harder than Bluebook but prepares you well."},
            {"email": "elena_italy_bot@example.com", "country": "Italy", "rating": 4, "text": "Really good structure. I wish there were more geometry questions, though."},
            {"email": "elenarossi_bot@example.com", "country": "Italy", "rating": 5, "text": "Fantastic resource. The adaptive nature of the test felt very realistic."},
            {"email": "emma_uk_bot@example.com", "country": "UK", "rating": 4, "text": "Solid practice. The vocabulary questions were tricky!"},
            {"email": "emmawilson_bot@example.com", "country": "UK", "rating": 5, "text": "Loved it. It gave me a realistic score prediction."},
            {"email": "fatimakhan_bot@example.com", "country": "Pakistan", "rating": 4, "text": "Good value. The analytics after the test helped me see my weak areas."},
            {"email": "garimapats20@gmail.com", "country": "India", "rating": 5, "text": "Totally worth it. The algebra questions were exactly what I needed to practice."},
            {"email": "hans_germany_bot@example.com", "country": "Germany", "rating": 5, "text": "Efficient and accurate. A must-do before the real SAT."},
            {"email": "hansmueller_bot@example.com", "country": "Germany", "rating": 3, "text": "It was okay. Some questions felt a bit repetitive compared to Test 02."},
            {"email": "isabella_argentina_bot@example.com", "country": "Argentina", "rating": 5, "text": "I felt so much more confident after taking this. Great interface."},
            {"email": "jfbhrn@clowmail.com", "country": "USA", "rating": 2, "text": "The content is good, but I had some login issues at the start."},
            {"email": "jsamyak100@gmail.com", "country": "India", "rating": 5, "text": "Excellent set of questions. The advanced math section really challenged me."},
            {"email": "kwame_ghana_bot@example.com", "country": "Ghana", "rating": 4, "text": "Very practical. It mimics the pressure of the real exam well."},
            {"email": "kwamemensah_bot@example.com", "country": "Ghana", "rating": 5, "text": "Highly recommended for anyone aiming for 1500+."},
            {"email": "lars_denmark_bot@example.com", "country": "Denmark", "rating": 4, "text": "Good English practice. The grammar section was very detailed."},
            {"email": "larsjensen_bot@example.com", "country": "Denmark", "rating": 5, "text": "Clean, fast, and effective. The results analysis is top-notch."},
            {"email": "liamthompson_bot@example.com", "country": "USA", "rating": 3, "text": "Decent practice, but I found the reading comprehension slightly easier than the real thing."},
            {"email": "liam_usa_bot@example.com", "country": "USA", "rating": 5, "text": "This saved my prep. The explanations for the difficult math problems are a lifesaver."},
            {"email": "lucas_brazil_bot@example.com", "country": "Brazil", "rating": 5, "text": "Muito bom! The questions cover all the necessary topics."},
            {"email": "lucassilva_bot@example.com", "country": "Brazil", "rating": 4, "text": "Good test. Helped me identify my pacing issues in Module 2."},
            {"email": "mugubo779@robot-mail.com", "country": "Canada", "rating": 1, "text": "Not what I expected. I encountered a bug in the submission process."},
            {"email": "myduci3832@fivermail.com", "country": "Vietnam", "rating": 4, "text": "Very challenging math questions. Good for high achievers."},
            {"email": "priya_india_bot@example.com", "country": "India", "rating": 5, "text": "The standard of questions is very high. Matches the actual exam pattern perfectly."},
            {"email": "priyasharma_bot@example.com", "country": "India", "rating": 5, "text": "Loved the user experience. Smooth and distraction-free."},
            {"email": "pyhuqy5424@givmail.com", "country": "Philippines", "rating": 3, "text": "It's okay for practice, but I've seen better explanations elsewhere."},
            {"email": "sarah_canada_bot@example.com", "country": "Canada", "rating": 5, "text": "Absolutely essential. I felt like I had already taken the test when I walked into the exam center."},
            {"email": "sarahjenkins_bot@example.com", "country": "USA", "rating": 4, "text": "Great for drilling specific topics. I improved my grammar score significantly."},
            {"email": "sophiedubois_bot@example.com", "country": "France", "rating": 5, "text": "Super! The best mock test platform I have used so far."},
            {"email": "sophie_france_bot@example.com", "country": "France", "rating": 4, "text": "Very helpful for non-native speakers to get used to the phrasing."},
            {"email": "sykozi2639@blondmail.com", "country": "Poland", "rating": 2, "text": "Too difficult. I don't think the real SAT is this hard."},
            {"email": "tyagiakash630@gmail.com", "country": "India", "rating": 5, "text": "10/10. The layout is exactly like the real exam. Great confidence booster."},
            {"email": "vinilan590@m3player.com", "country": "Singapore", "rating": 4, "text": "Precise and well-timed. Good mix of easy and hard questions."},
            {"item": "vowep95589@dubokutv.com", "country": "Australia", "rating": 5, "text": "Impressive question bank. I didn't see any repeated questions."},
            {"email": "weichen_bot@example.com", "country": "China", "rating": 5, "text": "Excellent resource. The math section is rigorous."},
            {"email": "wei_china_bot@example.com", "country": "China", "rating": 4, "text": "Very useful. Helped me get my score from 1350 to 1480."},
            {"email": "yuki_japan_bot@example.com", "country": "Japan", "rating": 5, "text": "The text explanations are very easy to understand. Thank you!"},
            {"email": "yukitanaka_bot@example.com", "country": "Japan", "rating": 4, "text": "Good practice for reading speed. The timer feature is very useful."},
            {"email": "zigimo657@spicysoda.com", "country": "Turkey", "rating": 3, "text": "Decent, but the user dashboard could be a bit more user-friendly."},
            {"email": "aarav_india_bot@example.com", "country": "India", "rating": 5, "text": "Tried this one after Test 01. Consistency in quality is amazing."},
            {"email": "priyasharma_bot@example.com", "country": "India", "rating": 4, "text": "Good refresher. I took this a week before my exam and it helped calm my nerves."},
            {"email": "liam_usa_bot@example.com", "country": "USA", "rating": 5, "text": "Another great test. The variety of question types is spot on."},
            {"email": "wei_china_bot@example.com", "country": "China", "rating": 5, "text": "Highly effective. I recommend this to all my classmates."},
            {"email": "sophie_france_bot@example.com", "country": "France", "rating": 4, "text": "Solid. The reading passages were interesting and challenging."},
        ]

        self.stdout.write("Starting bulk testimonial import...")
        
        # ==========================================
        # 2. PREPARE USERS
        # ==========================================
        # To avoid DB hits in the loop, let's ensure all users exist first
        # and store them in a dictionary keyed by email.
        user_map = {}
        for row in reviews_pool:
            email = row.get('email', row.get('item')) # Handling typo in data where email might be in 'item' key
            if not email or '@' not in email: continue # Skip invalid data

            username = email.split('@')[0]
            user, created = User.objects.get_or_create(
                email=email,
                defaults={'username': username}
            )
            if created:
                user.set_password('TestPass123!')
                user.save()
            user_map[email] = user
            
        self.stdout.write(f"Prepared {len(user_map)} users.")

        # ==========================================
        # 3. DISTRIBUTE REVIEWS TO ALL ITEMS
        # ==========================================
        items = MarketplaceItem.objects.all()
        
        if not items.exists():
            self.stdout.write(self.style.WARNING("No MarketplaceItems found! Please create some items first."))
            return

        total_added = 0

        for item in items:
            # For each item, we pick a random number of reviews (e.g., between 3 and 7)
            # This makes the data look natural (some items have more reviews than others)
            num_reviews = random.randint(3, 7)
            
            # Select random entries from the pool
            # We use 'min' to handle cases where pool size < num_reviews
            selected_reviews = random.sample(reviews_pool, min(len(reviews_pool), num_reviews))

            for review_data in selected_reviews:
                email = review_data.get('email', review_data.get('item'))
                user = user_map.get(email)
                
                if not user: 
                    continue

                try:
                    # We use get_or_create to prevent crashing if we run the script twice
                    # and to respect the 'unique_together' constraint
                    obj, created = Testimonial.objects.get_or_create(
                        item=item,
                        user=user,
                        defaults={
                            'rating': review_data['rating'],
                            'text': review_data['text'],
                            'country': review_data['country']
                        }
                    )
                    if created:
                        total_added += 1
                        
                except IntegrityError:
                    # Double safety net for race conditions or constraint violations
                    continue
            
            self.stdout.write(f"Processed item: {item.title}")

        self.stdout.write(self.style.SUCCESS(f"-----------------------------------"))
        self.stdout.write(self.style.SUCCESS(f"Successfully added {total_added} testimonials across {items.count()} items."))