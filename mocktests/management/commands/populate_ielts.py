from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from marketplace.models import MarketplaceItem
from mocktests.models import (
    MockTestAttributes, TestSection, ComprehensionPassage, 
    TestQuestion, QuestionOption
)

class Command(BaseCommand):
    help = 'Generates a sample IELTS Academic Mock Test'

    def handle(self, *args, **kwargs):
        # 1. Create the Exam Product
        item, created = MarketplaceItem.objects.get_or_create(
            slug='ielts-academic-vol-1',
            defaults={
                'title': 'IELTS Academic Full Mock Test 1',
                'description': 'Full-length simulation including Listening, Reading, and Writing sections.',
                'price': 15.00,
                'item_type': 'MOCK_TEST',
                'is_active': True
            }
        )

        # 2. Define Attributes (2 hours 40 mins approx)
        test_attr, _ = MockTestAttributes.objects.get_or_create(
            item=item,
            defaults={
                'level': 'ADVANCED',
                'duration_minutes': 160, # 30 L + 60 R + 60 W + 10 transfer
                'pass_percentage': 60,
                'instructions': """<ul class='text-start'>
                    <li><strong>Listening:</strong> 4 Sections, 40 Questions. Audio plays once only.</li>
                    <li><strong>Reading:</strong> 3 Passages, 40 Questions. Time: 60 mins.</li>
                    <li><strong>Writing:</strong> 2 Tasks. Task 1 (150 words), Task 2 (250 words).</li>
                    </ul>"""
            }
        )
        
        self.stdout.write("--- Creating Sections ---")

        # ==========================================
        # SECTION 1: LISTENING
        # ==========================================
        sec_listening = TestSection.objects.create(test=test_attr, title="Listening (30 mins)", sort_order=1)
        
        # Listening Part 1 (Form Completion)
        q1 = TestQuestion.objects.create(
            section=sec_listening,
            question_text="<strong>Question 1-5:</strong><br>Complete the notes below. Write <strong>ONE WORD AND/OR A NUMBER</strong>.<br><br><strong>Car Rental Inquiry</strong><br>Customer Name: John ______",
            question_type='NUMERIC', # Use Numeric/Text input for fill-in-the-blanks
            marks=1,
            sort_order=1
        )
        # (Note: In production, you would attach a QuestionAudio model here)

        # Listening Part 2 (MCQ)
        q2 = TestQuestion.objects.create(
            section=sec_listening,
            question_text="What facility has recently opened at the park?",
            question_type='MCQ',
            marks=1,
            sort_order=6
        )
        QuestionOption.objects.create(question=q2, option_text="A new café", is_correct=True)
        QuestionOption.objects.create(question=q2, option_text="A tennis court", is_correct=False)
        QuestionOption.objects.create(question=q2, option_text="A swimming pool", is_correct=False)

        # ==========================================
        # SECTION 2: READING
        # ==========================================
        sec_reading = TestSection.objects.create(test=test_attr, title="Reading (60 mins)", sort_order=2)

        # Passage 1
        passage_text = """
        <h3>The History of Tea</h3>
        <p>The story of tea begins in China. According to legend, in 2737 BC, the Chinese emperor Shen Nung was sitting beneath a tree while his servant boiled drinking water, when some leaves from the tree blew into the water...</p>
        <p>(... insert 500 words of dummy text ...)</p>
        """
        p1 = ComprehensionPassage.objects.create(section=sec_reading, content=passage_text)

        # Reading Q1 (True/False/Not Given)
        q_r1 = TestQuestion.objects.create(
            section=sec_reading,
            passage=p1,
            question_text="Do the following statements agree with the information given in the text?<br><strong>TRUE</strong> if the statement agrees<br><strong>FALSE</strong> if it contradicts<br><strong>NOT GIVEN</strong> if no info.<br><br>1. The Emperor invented tea by accident.",
            question_type='MCQ',
            marks=1,
            sort_order=1
        )
        QuestionOption.objects.create(question=q_r1, option_text="TRUE", is_correct=True)
        QuestionOption.objects.create(question=q_r1, option_text="FALSE", is_correct=False)
        QuestionOption.objects.create(question=q_r1, option_text="NOT GIVEN", is_correct=False)

        # ==========================================
        # SECTION 3: WRITING
        # ==========================================
        sec_writing = TestSection.objects.create(test=test_attr, title="Writing (60 mins)", sort_order=3)

        # Task 1
        TestQuestion.objects.create(
            section=sec_writing,
            question_text="<h3>Task 1</h3><p>The chart below shows the number of men and women studying engineering at Australian universities.<br>Summarise the information by selecting and reporting the main features, and make comparisons where relevant.<br><em>Write at least 150 words.</em></p>",
            question_type='ESSAY',
            marks=3, # Weighted differently internally
            sort_order=1
        )
        
        # Task 2
        TestQuestion.objects.create(
            section=sec_writing,
            question_text="<h3>Task 2</h3><p>Some people believe that unpaid community service should be a compulsory part of high school programmes.<br>To what extent do you agree or disagree?<br><em>Write at least 250 words.</em></p>",
            question_type='ESSAY',
            marks=6,
            sort_order=2
        )

        self.stdout.write(self.style.SUCCESS('Successfully created IELTS Mock Test!'))