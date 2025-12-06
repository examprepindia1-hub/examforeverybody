import random
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from blog.models import Post
from marketplace.models import MarketplaceItem

User = get_user_model()

class Command(BaseCommand):
    help = 'Populates the blog with 20 initial posts about the product and exams.'

    def handle(self, *args, **kwargs):
        self.stdout.write("Starting blog population...")

        # 1. Get an Author (Admin)
        author = User.objects.filter(is_superuser=True).first()
        if not author:
            self.stdout.write(self.style.ERROR("No superuser found. Please create one first using 'createsuperuser'."))
            return

        # 2. Get some Marketplace Items for Shortcodes
        # We try to find existing items to inject into the blog posts
        items = list(MarketplaceItem.objects.filter(is_active=True))
        item_slug = items[0].slug if items else "sample-item-slug"

        # 3. Define the 20 Blog Data Points
        blogs_data = [
            {
                "title": "5 Strategies to Ace Your SAT Math Section",
                "content": f"""The SAT Math section can be daunting, but with the right approach, you can master it. Here are five proven strategies to boost your score.
                
1. **Master the Basics:** Ensure your algebra and geometry foundations are solid.
2. **Time Management:** Don't get stuck on one hard question. Move on and come back.
3. **Practice Tests:** There is no substitute for real practice.

Speaking of practice, have you tried our dedicated SAT Math Pack? It covers all these topics in depth.

[[item:{item_slug}]]

4. **Calculator Strategy:** Know when to use it and when mental math is faster.
5. **Review Mistakes:** Don't just check your score; analyze *why* you got a question wrong."""
            },
            {
                "title": "Why Mock Tests Are Critical for JEE Advanced Success",
                "content": """Many students focus solely on theory, but JEE Advanced is a test of application and temperament. Taking full-length mock tests helps you build the stamina required for the actual exam day. 

Our platform offers a distraction-free, full-screen environment that simulates the real test exactly. This helps reduce anxiety and improves time management."""
            },
            {
                "title": "Top 10 Vocabulary Words Frequent in GRE",
                "content": "Improving your vocabulary is the fastest way to boost your GRE Verbal score. Words like 'Aberration', 'Capricious', and 'Equivocate' appear frequently. We have compiled a list of 500 must-know words in our study notes section."
            },
            {
                "title": "How to Analyze Your Test Performance on ExamForEverybody",
                "content": "Did you know our dashboard offers a Radar Chart analysis? After submitting a test, go to the 'Detailed Analysis' tab. You will see a breakdown of your strengths and weaknesses by topic. Use this to focus your revision on the areas that need it most, rather than wasting time on what you already know."
            },
            {
                "title": "IELTS Writing Task 2: A Complete Guide",
                "content": f"""Achieving a Band 8.0 in writing requires structure. You need a clear introduction, body paragraphs with examples, and a concise conclusion.
                
If you need specific practice on this, check out our IELTS Academic Workshop:

[[item:{item_slug}]]

It includes live feedback from certified trainers."""
            },
            {
                "title": "The Science of Spaced Repetition",
                "content": "Cramming doesn't work long-term. Spaced repetition is a learning technique that incorporates increasing intervals of time between subsequent review of previously learned material in order to exploit the psychological spacing effect."
            },
            {
                "title": "Introducing Dark Mode for Late Night Studies",
                "content": "We listened to your feedback! ExamForEverybody now supports a system-based Dark Mode theme (coming soon). This reduces eye strain during those late-night revision sessions before the big exam."
            },
            {
                "title": "NEET Physics: Formula Sheet for Mechanics",
                "content": "Mechanics carries a huge weightage in NEET. We have uploaded a free downloadable PDF containing all essential formulas for Newton's Laws, Kinematics, and Rotational Motion. Log in to your dashboard to download it."
            },
            {
                "title": "Success Story: How Anjali Cracked CAT with 99.8 Percentile",
                "content": "Anjali was a working professional with only 2 hours a day to study. By using our 'Weekend Workshop' series and taking consistent micro-tests, she managed to clear IIM-A. Read her full interview here."
            },
            {
                "title": "3 Common Mistakes to Avoid in Online Exams",
                "content": "1. **Not checking internet connectivity:** Always ensure you have a backup connection.\n2. **Exiting Full Screen:** Our system flags this as a violation. Stay focused.\n3. **Ignoring the Timer:** Keep an eye on the clock, but don't let it panic you."
            },
            {
                "title": "Python for Data Science: Where to Start?",
                "content": f"""Data Science is the hottest career of the decade. Start with Python basics: Variables, Loops, and Functions. Once you are comfortable, move to Pandas and NumPy.

We have a beginner-friendly course just for this:
[[item:{item_slug}]]"""
            },
            {
                "title": "Understanding Negative Marking",
                "content": "Guessing can be dangerous. In exams like JEE and NEET, every wrong answer deducts marks. Our platform's 'Guessing Analysis' feature tells you if your guesses are usually lucky or costly. Check your test report today."
            },
            {
                "title": "The Benefits of Peer Learning",
                "content": "Learning alone can be isolating. Use the 'Discussion' tab under every question to ask doubts and answer queries from fellow aspirants. Teaching others is the best way to reinforce your own learning."
            },
            {
                "title": "Time Management Hacks for Slow Readers",
                "content": "Struggling to finish the Reading Comprehension section? Try skimming the first and last sentences of each paragraph before diving in. This gives you a mental map of the passage structure."
            },
            {
                "title": "ExamForEverybody vs. Traditional Coaching",
                "content": "Why pay thousands for a crowded classroom when you can get personalized attention online? Our AI-driven recommendations adapt to YOUR learning pace, not the class average."
            },
            {
                "title": "Updates: New Payment Gateways Added",
                "content": "We have now integrated Stripe and Razorpay to make enrolling in courses easier for international and Indian students. Secure, fast, and reliable transactions are our priority."
            },
            {
                "title": "How to Stay Motivated During Exam Prep",
                "content": "Burnout is real. Take regular breaks using the Pomodoro technique (25 mins work, 5 mins break). Make sure to exercise and sleep well. Your brain needs rest to consolidate memory."
            },
            {
                "title": "Feature Spotlight: The Question Palette",
                "content": "Our exam interface features a smart palette. Blue means 'Marked for Review'. Use this feature! If you are 50% sure, mark it and move on. Come back only if time permits. This strategy saves minutes that add up to marks."
            },
            {
                "title": "Best Books for UPSC Preparation 2025",
                "content": "While our mock tests are great, standard textbooks like Laxmikanth for Polity and Spectrum for History are indispensable. Combine these books with our daily current affairs quiz for the best results."
            },
            {
                "title": "Welcome to the ExamForEverybody Community",
                "content": "We are thrilled to have you here. Our mission is to democratize education. Whether you are in New York or New Delhi, you deserve the best tools to succeed. Happy learning!"
            }
        ]

        # 4. Loop and Create
        created_count = 0
        for data in blogs_data:
            # Check if title exists to avoid duplicates on re-run
            if not Post.objects.filter(title=data["title"]).exists():
                Post.objects.create(
                    title=data["title"],
                    author=author,
                    content=data["content"],
                    status='published',
                    is_featured=(created_count == 0) # Make the first one featured
                )
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"Created: {data['title']}"))
            else:
                self.stdout.write(f"Skipped (Exists): {data['title']}")

        self.stdout.write(self.style.SUCCESS(f"Successfully created {created_count} blog posts."))