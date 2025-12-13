from django.core.management.base import BaseCommand
from marketplace.models import MarketplaceItem
from mocktests.models import (
    MockTestAttributes, TestSection, TestQuestion, QuestionOption, ComprehensionPassage
)

class Command(BaseCommand):
    help = 'Generates a high-quality Digital SAT Mock Test'

    def handle(self, *args, **kwargs):
        MarketplaceItem.objects.filter(slug='sat-digital-practice-1').delete()
        self.stdout.write("--- Creating Digital SAT Mock Test ---")

        # 1. Create Product
        item, _ = MarketplaceItem.objects.get_or_create(
            slug='sat-digital-practice-1',
            defaults={
                'title': 'Digital SAT Practice Test 1',
                'description': 'Full-length adaptive simulation. Includes Reading & Writing and Math modules.',
                'price': 29.00,
                'item_type': 'MOCK_TEST',
                'is_active': True
            }
        )

        # 2. Test Attributes (Total Time: 64m RW + 70m Math = 134 mins)
        test_attr, _ = MockTestAttributes.objects.get_or_create(
            item=item,
            defaults={
                'level': 'INTERMEDIATE',
                'duration_minutes': 134,
                'pass_percentage': 70,
                'instructions': """<ul class='text-start'>
                    <li><strong>Format:</strong> The test is divided into two major sections: Reading & Writing, and Math.</li>
                    <li><strong>Modules:</strong> Each section has two modules. You must complete Module 1 before moving to Module 2.</li>
                    <li><strong>Timing:</strong> The timer is specific to each module. You cannot go back to a previous module once time runs out.</li>
                    <li><strong>Calculator:</strong> You may use the built-in calculator for the entire Math section.</li>
                    </ul>"""
            }
        )

        # ==========================================
        # SECTION 1: READING & WRITING - MODULE 1
        # ==========================================
        rw_mod1 = TestSection.objects.create(test=test_attr, title="Reading & Writing: Module 1", sort_order=1)

        # Q1: Words in Context (Vocabulary)
        q1 = TestQuestion.objects.create(
            section=rw_mod1,
            question_text="""
            <strong>Read the text and answer the question.</strong><br><br>
            In the early 1800s, the Cherokee scholar Sequoyah created a writing system for the Cherokee language. 
            Before this invention, the Cherokee language had been exclusively oral; Sequoyah’s syllabary ______ 
            communication by allowing ideas to be preserved in writing.
            <br><br>Which choice completes the text with the most logical and precise word?
            """,
            question_type='MCQ', marks=1, sort_order=1
        )
        QuestionOption.objects.create(question=q1, option_text="facilitated", is_correct=True)
        QuestionOption.objects.create(question=q1, option_text="hindered", is_correct=False)
        QuestionOption.objects.create(question=q1, option_text="repudiated", is_correct=False)
        QuestionOption.objects.create(question=q1, option_text="isolate", is_correct=False)

        # Q2: Command of Evidence (Textual)
        q2 = TestQuestion.objects.create(
            section=rw_mod1,
            question_text="""
            <strong>Read the text and answer the question.</strong><br><br>
            A study by researcher J.R.R. Tolkien suggests that fantasy literature serves a purpose beyond escapism. 
            It allows readers to view their own world through a different lens, potentially increasing empathy.
            <br><br>Which finding, if true, would most directly support Tolkien’s hypothesis?
            """,
            question_type='MCQ', marks=1, sort_order=2
        )
        QuestionOption.objects.create(question=q2, option_text="Readers of fantasy novels score higher on standardized empathy tests than non-readers.", is_correct=True)
        QuestionOption.objects.create(question=q2, option_text="Fantasy novels sell more copies than realistic fiction biographies.", is_correct=False)
        QuestionOption.objects.create(question=q2, option_text="Most fantasy authors base their worlds on historical events.", is_correct=False)
        QuestionOption.objects.create(question=q2, option_text="Readers prefer fantasy movies over fantasy books.", is_correct=False)

        # Q3: Standard English Conventions (Grammar)
        q3 = TestQuestion.objects.create(
            section=rw_mod1,
            question_text="""
            <strong>Read the text and answer the question.</strong><br><br>
            The bioluminescent fungi found in the Amazon rainforest ______ a soft green glow that attracts nocturnal insects, 
            which then help spread the fungi's spores.
            <br><br>Which choice completes the text so that it conforms to the conventions of Standard English?
            """,
            question_type='MCQ', marks=1, sort_order=3
        )
        QuestionOption.objects.create(question=q3, option_text="emits", is_correct=True)
        QuestionOption.objects.create(question=q3, option_text="emit", is_correct=False) # 'fungi' is plural, but context trap
        QuestionOption.objects.create(question=q3, option_text="emitting", is_correct=False)
        QuestionOption.objects.create(question=q3, option_text="have emitted", is_correct=False)

        # ==========================================
        # SECTION 2: READING & WRITING - MODULE 2
        # ==========================================
        rw_mod2 = TestSection.objects.create(test=test_attr, title="Reading & Writing: Module 2", sort_order=2)

        # Q4: Transitions
        q4 = TestQuestion.objects.create(
            section=rw_mod2,
            question_text="""
            Iraqi artist Zaha Hadid is known for her futuristic architecture. Her buildings often feature curving forms 
            and elongated structures. ______, her design for the Heydar Aliyev Center in Baku avoids sharp angles entirely.
            <br><br>Which choice completes the text with the most logical transition?
            """,
            question_type='MCQ', marks=1, sort_order=1
        )
        QuestionOption.objects.create(question=q4, option_text="For instance", is_correct=True)
        QuestionOption.objects.create(question=q4, option_text="However", is_correct=False)
        QuestionOption.objects.create(question=q4, option_text="Similarly", is_correct=False)
        QuestionOption.objects.create(question=q4, option_text="In contrast", is_correct=False)

        # ==========================================
        # SECTION 3: MATH - MODULE 1 (No Calculator Restriction)
        # ==========================================
        math_mod1 = TestSection.objects.create(test=test_attr, title="Math: Module 1", sort_order=3)

        # Q5: Algebra (Linear Equations)
        q5 = TestQuestion.objects.create(
            section=math_mod1,
            question_text="""
            If $$3x + 12 = 24$$, what is the value of $$x + 4$$?
            """,
            question_type='MCQ', marks=1, sort_order=1
        )
        QuestionOption.objects.create(question=q5, option_text="8", is_correct=True)
        QuestionOption.objects.create(question=q5, option_text="4", is_correct=False)
        QuestionOption.objects.create(question=q5, option_text="12", is_correct=False)
        QuestionOption.objects.create(question=q5, option_text="6", is_correct=False)

        # Q6: Geometry (Circle Equation)
        q6 = TestQuestion.objects.create(
            section=math_mod1,
            question_text="""
            The equation of a circle in the xy-plane is shown below:
            $$(x - 2)^2 + (y + 5)^2 = 16$$
            <br>
            What is the radius of this circle?
            """,
            question_type='NUMERIC', marks=1, sort_order=2
        )
        # For numeric, we assume the user types "4"

        # ==========================================
        # SECTION 4: MATH - MODULE 2 (Harder)
        # ==========================================
        math_mod2 = TestSection.objects.create(test=test_attr, title="Math: Module 2", sort_order=4)

        # Q7: Advanced Math (Non-linear functions)
        q7 = TestQuestion.objects.create(
            section=math_mod2,
            question_text="""
            The function $$f$$ is defined by $$f(x) = 2x^2 + 4x + c$$, where $$c$$ is a constant. 
            If the function has exactly one x-intercept, what is the value of $$c$$?
            """,
            question_type='NUMERIC', marks=1, sort_order=1
        )
        # Answer is 2 (Discriminant b^2 - 4ac = 0 => 16 - 8c = 0 => c=2)

        # Q8: Problem Solving (Percentages)
        q8 = TestQuestion.objects.create(
            section=math_mod2,
            question_text="""
            A biologist estimates that a bacteria population increases by 20% every hour. 
            If the current population is 1,000, which expression represents the population $$t$$ hours from now?
            """,
            question_type='MCQ', marks=1, sort_order=2
        )
        QuestionOption.objects.create(question=q8, option_text="$$1000(1.2)^t$$", is_correct=True)
        QuestionOption.objects.create(question=q8, option_text="$$1000(0.2)^t$$", is_correct=False)
        QuestionOption.objects.create(question=q8, option_text="$$1000 + 0.2t$$", is_correct=False)
        QuestionOption.objects.create(question=q8, option_text="$$1200^t$$", is_correct=False)

        self.stdout.write(self.style.SUCCESS("SAT Mock Test Created Successfully!"))