import google.genai as genai
from google.genai import types
import json
import io
import time
import re
import matplotlib
import concurrent.futures
import threading

# --- FORCE NON-INTERACTIVE (Prevents Popups) ---
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
import numpy as np
# -----------------------------------------------

from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from marketplace.models import MarketplaceItem
from mocktests.models import (
    MockTestAttributes, TestSection, TestQuestion, QuestionOption, QuestionMedia
)

# --- CONFIGURATION ---
GEMINI_API_KEY = getattr(settings, "GEMINI_API_KEY", "AIzaSyBU0QOvQ7YKfFO5JuGmIEaI60DpiAkyDy8")
# Use the latest stable model available to you. 
# If 'gemini-3' fails, switch to 'gemini-2.0-flash-exp' or 'gemini-1.5-flash'
MODEL_NAME = "gemini-3-flash-preview" 

# SAT VISUAL STYLE
SAT_STYLE_GUIDE = """
plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.size': 10,
    'axes.spines.top': False,
    'axes.spines.right': False,
    'axes.grid': True,
    'grid.alpha': 0.3
})
"""

# ==============================================================================
#  BLUEPRINTS
# ==============================================================================
BLUEPRINT_RW = [
    ("Craft & Structure", "Words in Context", 5),
    ("Craft & Structure", "Text Structure and Purpose", 4),
    ("Craft & Structure", "Cross-Text Connections", 2),
    ("Information & Ideas", "Command of Evidence (Textual)", 3),
    ("Information & Ideas", "Command of Evidence (Quantitative)", 3),
    ("Information & Ideas", "Inferences", 2),
    ("Standard English Conventions", "Boundaries (Punctuation)", 3),
    ("Standard English Conventions", "Form, Structure, and Sense (Grammar)", 3),
    ("Expression of Ideas", "Transitions", 2)
]

BLUEPRINT_MATH = [
    ("Algebra", "Linear equations in one variable", 2),
    ("Algebra", "Linear inequalities in one or two variables", 2),
    ("Algebra", "Systems of two linear equations", 2),
    ("Advanced Math", "Quadratic equations and functions", 2),
    ("Advanced Math", "Exponential functions", 2),
    ("Advanced Math", "Nonlinear equations and systems", 1),
    ("Problem-Solving", "Ratios, rates, proportional relationships", 3),
    ("Problem-Solving", "Probability and conditional probability", 2),
    ("Geometry", "Area and volume", 2),
    ("Geometry", "Lines, angles, and triangles", 2),
    ("Geometry", "Circles", 1),
    ("Data Analysis", "Scatterplots and linear models", 1)
]

class Command(BaseCommand):
    help = 'The Ultimate Parallel SAT Generator (Fastest & Best Quality)'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Delete existing test and start fresh')
        parser.add_argument('--workers', type=int, default=4, help='Number of parallel requests')

    def handle(self, *args, **options):
        if not GEMINI_API_KEY:
            self.stdout.write(self.style.ERROR("Error: GEMINI_API_KEY is missing."))
            return

        self.client = genai.Client(api_key=GEMINI_API_KEY)
        self.lock = threading.Lock() 
        
        self.log(f"--- 🚀 Starting Ultimate SAT Generation ({MODEL_NAME}) ---")
        self.log(f"--- ⚡ Parallel Workers: {options['workers']} ---")

        # 1. Setup Exam
        item, test_attr = self.setup_exam_structure(options['force'])
        
        # 2. Execute Plan
        modules_config = [
            ("Reading & Writing", 1, "Medium", BLUEPRINT_RW),
            ("Reading & Writing", 2, "Hard",   BLUEPRINT_RW),
            ("Math",              1, "Medium", BLUEPRINT_MATH),
            ("Math",              2, "Hard",   BLUEPRINT_MATH),
        ]

        for subject, mod_num, diff, blueprint in modules_config:
            self.generate_module_parallel(test_attr, subject, mod_num, diff, blueprint, options['workers'])

        self.log(self.style.SUCCESS(f"✅ EXAM COMPLETE: '{item.title}' is ready!"))

    def log(self, message):
        """Thread-safe logging"""
        with self.lock:
            self.stdout.write(message)

    def setup_exam_structure(self, force_restart):
        slug = 'sat-digital-ultimate-v1'
        if force_restart:
            MarketplaceItem.objects.filter(slug=slug).delete()

        item, _ = MarketplaceItem.objects.get_or_create(
            slug=slug,
            defaults={
                'title': 'Digital SAT: Ultimate Edition',
                'description': 'The most advanced AI-generated SAT simulation. High-performance, style-consistent, and blueprint-accurate.',
                'price': 59.00,
                'item_type': 'MOCK_TEST',
                'is_active': True
            }
        )
        test_attr, _ = MockTestAttributes.objects.get_or_create(
            item=item,
            defaults={'exam_type': 'SAT_ADAPTIVE', 'duration_minutes': 134, 'pass_percentage': 70}
        )
        return item, test_attr

    def generate_module_parallel(self, test_attr, subject, module_num, difficulty, blueprint, max_workers):
        section_title = f"{subject}: Module {module_num}"
        sort_offset = 0 if subject == "Reading & Writing" else 2
        
        section, _ = TestSection.objects.get_or_create(
            test=test_attr,
            title=section_title,
            defaults={'sort_order': module_num + sort_offset, 'section_duration': 32 if subject[0]=='R' else 35}
        )

        total_needed = sum(item[2] for item in blueprint)
        if section.questions.count() >= total_needed:
            self.log(f"  ✓ {section_title} complete. Skipping.")
            return

        if section.questions.count() > 0:
            section.questions.all().delete()

        self.log(f"  ... Generating {section_title} ({difficulty}) using {max_workers} threads")

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for domain, sub_topic, count in blueprint:
                futures.append(
                    executor.submit(self.run_topic_batch, section, subject, domain, sub_topic, difficulty, count)
                )
            
            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    self.log(self.style.ERROR(f"      x Thread Error: {e}"))

    def run_topic_batch(self, section, subject, domain, sub_topic, difficulty, count):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                questions_data = self.call_gemini_json_mode(subject, domain, sub_topic, difficulty, count)
                
                if not isinstance(questions_data, list) or len(questions_data) == 0:
                     raise ValueError("Empty JSON returned")

                with transaction.atomic():
                    for q_data in questions_data:
                        self.save_question_to_db(section, q_data)
                
                self.log(f"      + {sub_topic}: Saved {len(questions_data)} Qs")
                return

            except Exception as e:
                sleep_time = (attempt + 1) * 2 + (id(threading.current_thread()) % 3)
                time.sleep(sleep_time)
        
        self.log(self.style.ERROR(f"      x Failed topic {sub_topic} after retries"))

    def call_gemini_json_mode(self, subject, domain, sub_topic, difficulty, count):
        image_rule = "python_code: null"
        if "Geometry" in domain or "Scatterplots" in sub_topic or "Quantitative" in sub_topic:
            image_rule = f"""
            IMAGE REQUIRED: Provide 'python_code' (matplotlib).
            - Use standard library: `import matplotlib.pyplot as plt`.
            - Apply this style at start: `{SAT_STYLE_GUIDE}`
            - Create clear, professional SAT-style graphs.
            - NO plt.show().
            """

        # --- UPDATED PROMPT WITH STRICT FORMATTING RULES ---
        prompt = f"""
        Role: Senior SAT Exam Writer. 
        Task: Create {count} {difficulty} questions.
        Context: {subject} > {domain} > {sub_topic}
        
        STRICT QUALITY & FORMATTING RULES:
        1. Options: Plain text only (e.g. "5", NOT "A) 5" or "(B) 10").
        2. {image_rule}
        3. MATH NOTATION (CRITICAL):
           - Use SINGLE DOLLAR SIGNS ($x$) for variables/math inside sentences.
           - Use DOUBLE DOLLAR SIGNS ($$x=y$$) ONLY for standalone equations on their own line.
           - For systems of equations, use a cases block: $$ \\begin{{cases}} 2x+y=10 \\\\ x-y=5 \\end{{cases}} $$
        4. Distractors: Must be plausible common errors.
        5. Explanations: Step-by-step clarity.
        
        Output JSON:
        [{{ "question_text": "...", "type": "MCQ"|"NUMERIC", "options": ["..."], "correct_answer": "...", "explanation": "...", "python_code": "..." }}]
        """
        
        response = self.client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        
        return json.loads(response.text)

    def clean_text(self, text):
        if not text: return ""
        text = str(text).strip()
        text = re.sub(r'^(Option\s+)?\d+[\)\.]\s*', '', text)
        text = re.sub(r'^(Option\s+)?[A-Da-d][\)\.]\s*', '', text)
        text = re.sub(r'^\([A-Da-d]\)\s*', '', text)
        return text.strip()

    def save_question_to_db(self, section, data):
        q_type = data.get('type', 'MCQ').upper()
        q_text = self.clean_text(data.get('question_text'))
        
        if not q_text: return

        correct_raw = self.clean_text(str(data.get('correct_answer')))
        options_raw = [self.clean_text(o) for o in data.get('options', []) if self.clean_text(o)]
        
        if q_type == 'MCQ' and correct_raw and options_raw:
            match_found = any(o.lower() == correct_raw.lower() for o in options_raw)
            if not match_found:
                if len(options_raw) >= 4:
                    options_raw[-1] = correct_raw
                else:
                    options_raw.append(correct_raw)

        question = TestQuestion.objects.create(
            section=section,
            question_text=q_text,
            question_type=q_type,
            correct_answer_value=correct_raw if q_type == 'NUMERIC' else None,
            explanation=data.get('explanation'),
            marks=1,
            sort_order=section.questions.count() + 1
        )

        if q_type == 'MCQ':
            for opt in options_raw:
                is_correct = (opt.lower() == correct_raw.lower())
                QuestionOption.objects.create(question=question, option_text=opt, is_correct=is_correct)

        if data.get('python_code'):
            self.generate_and_save_image(question, data['python_code'])

    def generate_and_save_image(self, question, code_snippet):
        try:
            plt.clf()
            plt.figure(figsize=(5, 4))
            plt.style.use('seaborn-v0_8-whitegrid') 
            
            code_snippet = code_snippet.replace("plt.show()", "")
            
            exec_globals = {'plt': plt, 'np': np}
            exec(code_snippet, exec_globals)
            
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', bbox_inches='tight', dpi=150)
            buffer.seek(0)
            
            file_name = f"ai_gen_q{question.id}.png"
            media = QuestionMedia(question=question)
            media.image.save(file_name, ContentFile(buffer.getvalue()), save=True)
            plt.close()
        except Exception:
            pass