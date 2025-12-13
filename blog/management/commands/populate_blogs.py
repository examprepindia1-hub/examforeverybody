from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from blog.models import Post
from marketplace.models import MarketplaceItem
from mocktests.models import MockTestAttributes

User = get_user_model()

class Command(BaseCommand):
    help = 'Clears old blogs and adds 5 high-quality SAT specific posts.'

    def handle(self, *args, **kwargs):
        self.stdout.write("--- Starting SAT Content Update ---")

        # 1. DELETE OLD BLOGS
        count = Post.objects.count()
        Post.objects.all().delete()
        self.stdout.write(self.style.WARNING(f"Deleted {count} existing blog posts."))

        # 2. GET AUTHOR
        author = User.objects.filter(is_superuser=True).first()
        if not author:
            self.stdout.write(self.style.ERROR("No superuser found. Please create one."))
            return

        # 3. ENSURE A PRODUCT EXISTS (For the Rich Cards to work)
        # We create a specific SAT product so the shortcodes [[item:sat-digital-bundle]] work.
        sat_item, _ = MarketplaceItem.objects.get_or_create(
            slug='sat-digital-bundle',
            defaults={
                'title': 'Digital SAT Prep Bundle 2025',
                'description': 'Full-length adaptive mock tests, 500+ practice questions, and video solutions.',
                'price': 49.00,
                'item_type': 'MOCK_TEST',
                'is_active': True
            }
        )
        # Add attributes to it just in case
        MockTestAttributes.objects.get_or_create(item=sat_item, defaults={'level': 'INTERMEDIATE', 'duration_minutes': 134})
        
        self.stdout.write(self.style.SUCCESS(f"Ensured product '{sat_item.title}' exists for blog linking."))

        # 4. DEFINE THE 5 BLOG POSTS
        blogs_data = [
            {
                "title": "What is the Digital SAT? Why take it? And How to Prepare?",
                "content": f"""The SAT (Scholastic Assessment Test) has undergone a massive transformation. It is no longer the pen-and-paper giant of the past; welcome to the **Digital SAT**.

### What is the Digital SAT?
The Digital SAT is a standardized test widely used for college admissions in the United States and other countries. It measures literacy, numeracy, and writing skills needed for academic success in college.
* **Duration:** Shorter! Now only 2 hours and 14 minutes.
* **Format:** Adaptive. If you do well in the first module, the second module becomes harder (and worth more points).
* **Tools:** You get a built-in graphing calculator (Desmos) for the entire math section.

### Why take the SAT?
Even though some colleges are "test-optional," submitting a strong SAT score gives you a massive edge.
1.  **Scholarships:** Many merit-based scholarships require an SAT score.
2.  **Placement:** High scores can exempt you from introductory college courses.
3.  **Differentiation:** In a pool of straight-A students, a 1500+ SAT score makes you stand out.

### How to Prepare (3-Step Strategy)
1.  **Diagnostic Test:** Take a full-length mock test blindly to see where you stand.
2.  **Concept Building:** Don't just practice; learn the grammar rules and math formulas first.
3.  **Adaptive Practice:** Since the real test is adaptive, practicing on paper books is no longer enough. You need a digital engine.

**Start your preparation with our Adaptive Mock Test series:**
[[item:sat-digital-bundle]]
"""
            },
            {
                "title": "SAT Syllabus 2025: Exam Pattern & Result Analysis",
                "content": f"""Understanding the battlefield is half the victory. The Digital SAT is divided into two main sections: **Reading & Writing** and **Math**.

### 1. Reading & Writing (RW) Section
* **Structure:** Two modules (32 mins each).
* **Question Count:** 54 questions total.
* **Syllabus:**
    * *Craft & Structure:* Vocabulary in context, text structure.
    * *Information & Ideas:* Central ideas, command of evidence.
    * *Standard English Conventions:* Grammar, punctuation, sentence structure.
    * *Expression of Ideas:* Rhetorical synthesis, transitions.

### 2. Math Section
* **Structure:** Two modules (35 mins each).
* **Question Count:** 44 questions total.
* **Syllabus:**
    * *Algebra:* Linear equations, systems.
    * *Advanced Math:* Quadratics, polynomials, non-linear equations.
    * *Problem Solving:* Ratios, percentages, probability.
    * *Geometry & Trigonometry:* Area, volume, angles, sin/cos/tan.

### Result Analysis: How is it scored?
The SAT is scored on a scale of **400 to 1600**.
* **RW:** 200–800 points.
* **Math:** 200–800 points.

**What is a "Good" Score?**
* **1200+:** Good (Top 25%) - Gets you into solid state universities.
* **1400+:** Excellent (Top 5%) - Competitive for top-tier schools.
* **1500+:** Elite (Top 1%) - Required for Ivies (MIT, Stanford, Harvard).

Want to know your predicted score? Take our diagnostic test now:
[[item:sat-digital-bundle]]
"""
            },
            {
                "title": "Top Books for SAT Preparation (And Why You Need More)",
                "content": """While digital tools are essential for the new format, good old-fashioned books are still great for building concepts. Here are the top 4 recommendations from our experts.

### 1. The Official Digital SAT Study Guide (College Board)
* **Why:** It is from the makers of the test.
* **Best For:** Understanding the official question types and format.

### 2. SAT Prep Black Book (Mike Barrett)
* **Why:** It teaches you *how* to take the test, focusing on strategies and "hacks" rather than just pure content.
* **Best For:** Strategy and mindset.

### 3. Barron's Digital SAT Premium
* **Why:** Known for being harder than the actual test. If you can crack Barron's, the real SAT will feel easy.
* **Best For:** High achievers aiming for 1500+.

### 4. Princeton Review Digital SAT Prep
* **Why:** Comprehensive content review and plenty of drills.
* **Best For:** Students starting from scratch.

### ⚠️ Important Warning
The new SAT is **Adaptive**. Books are static—they cannot simulate the experience of the second module getting harder based on your performance in the first. 
To truly be ready, you **must** practice on a digital platform that mimics the Bluebook app.

**Get the real Digital SAT experience here:**
[[item:sat-digital-bundle]]
"""
            },
            {
                "title": "Top Universities Accepting SAT Scores",
                "content": """The SAT opens doors to the most prestigious institutions in the world. Here is a breakdown of top universities where a high SAT score is a golden ticket.

### The Ivy League (USA)
1.  **Harvard University:** Recently reinstated the standardized testing requirement. Aim for 1520+.
2.  **Princeton University:** Highly competitive. Average SAT: 1510-1570.
3.  **Yale University:** Requires test scores again. Focus on a balanced score.

### Top Tech Schools (USA)
1.  **MIT (Massachusetts Institute of Technology):** One of the first to bring back the SAT requirement. Math score matters most (Aim for 800/800).
2.  **CalTech:** extremely rigorous selection.
3.  **Stanford:** Test-optional but strongly recommended for engineering applicants.

### Best Public Universities (USA)
1.  **UC Berkeley & UCLA:** (Note: The UC system is currently test-blind, meaning they *don't* look at SAT scores).
2.  **University of Michigan:** Strongly considers SAT.
3.  **Georgia Tech:** Requires SAT/ACT for all applicants.

### Universities Outside the US
* **National University of Singapore (NUS):** Accepts SAT for international students.
* **University of Toronto (Canada):** Highly values SAT scores for US/International curriculum students.
"""
            },
            {
                "title": "Top Countries Accepting SAT Scores",
                "content": """Think the SAT is just for the USA? Think again. Your score is a global currency recognized by universities in over 80 countries.

### 1. United States 🇺🇸
The home of the SAT. Over 4,000 universities accept it. It is essential for scholarships and admissions to top-tier private and public colleges.

### 2. Canada 🇨🇦
Most major Canadian universities (U of Toronto, UBC, McGill) accept the SAT as a substitute for other entrance exams or as a way to strengthen an application from an international student.

### 3. Singapore 🇸🇬
Top Asian universities like **NUS** and **NTU** require SAT scores from students who do not hold A-Levels or IB diplomas. The cut-offs are high (usually 1450+).

### 4. Australia 🇦🇺
Universities like the **University of Melbourne** and **University of Sydney** allow American curriculum students (and many internationals) to use SAT scores for direct entry, bypassing foundation years.

### 5. United Kingdom 🇬🇧 & Europe 🇪🇺
* **UK:** While A-Levels are standard, top UK unis (Oxford, Cambridge, LSE) accept SAT + AP scores from US-system students.
* **Italy:** Bocconi University accepts SAT in lieu of their internal entrance test.
* **Finland & Netherlands:** Several English-taught programs accept the SAT for international admissions.

**Ready to take your SAT prep global?**
[[item:sat-digital-bundle]]
"""
            }
        ]

        # 5. CREATE BLOGS
        for data in blogs_data:
            post = Post.objects.create(
                title=data["title"],
                author=author,
                content=data["content"],
                status='published',
                # Set the first one (Intro) as featured
                is_featured=(data["title"].startswith("What is"))
            )
            # Add a default image if you have one, or handle it in the loop
            self.stdout.write(self.style.SUCCESS(f"Created Blog: {post.title}"))

        self.stdout.write(self.style.SUCCESS("--- Done! SAT Content Loaded. ---"))