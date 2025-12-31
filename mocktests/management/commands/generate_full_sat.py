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
GEMINI_API_KEY = getattr(settings, "GEMINI_API_KEY", "") 

# Use 'gemini-1.5-flash' for speed/cost, or 'gemini-1.5-pro' for maximum reasoning quality
MODEL_NAME = "gemini-3-pro-preview" 

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

BLUEPRINT_RW = [
    # --- CRAFT & STRUCTURE (approx 28%) ---
    ("Craft & Structure", "Words in Context", 4),
    ("Craft & Structure", "Text Structure and Purpose", 3),
    ("Craft & Structure", "Cross-Text Connections", 1),
    
    # --- INFORMATION & IDEAS (approx 26%) ---
    ("Information & Ideas", "Central Ideas and Details", 2),
    ("Information & Ideas", "Command of Evidence (Textual)", 2),
    ("Information & Ideas", "Command of Evidence (Quantitative)", 2),
    ("Information & Ideas", "Inferences", 2),
    
    # --- STANDARD ENGLISH CONVENTIONS (approx 26%) ---
    ("Standard English Conventions", "Boundaries (Punctuation)", 3),
    ("Standard English Conventions", "Form, Structure, and Sense (Grammar)", 3),
    
    # --- EXPRESSION OF IDEAS (approx 20%) ---
    ("Expression of Ideas", "Rhetorical Synthesis", 2),
    ("Expression of Ideas", "Transitions", 3),
]
# Total: 27 Questions (Correct)


BLUEPRINT_MATH = [
    # --- ALGEBRA (approx 35% -> 7-8 Qs) ---
    ("Algebra", "Linear equations in one variable", 2),
    ("Algebra", "Linear inequalities in one or two variables", 2),
    ("Algebra", "Systems of two linear equations", 2),
    ("Algebra", "Linear functions", 1),
    
    # --- ADVANCED MATH (approx 35% -> 7-8 Qs) ---
    ("Advanced Math", "Quadratic equations and functions", 2),
    ("Advanced Math", "Exponential functions", 2),
    ("Advanced Math", "Nonlinear equations and systems", 2), # Increased to 2
    ("Advanced Math", "Equivalent expressions", 1),
    
    # --- PROBLEM-SOLVING & DATA ANALYSIS (approx 15% -> 3-4 Qs) ---
    ("Problem-Solving", "Ratios, rates, proportional relationships", 1), # Reduced to 1
    ("Problem-Solving", "Percentages", 1),
    ("Problem-Solving", "Probability and conditional probability", 1),
    ("Data Analysis", "Scatterplots and linear models", 1), 
    # Removed "Statistics" to fit the 22-question limit while keeping high-yield topics
    
    # --- GEOMETRY & TRIGONOMETRY (approx 15% -> 3-4 Qs) ---
    ("Geometry", "Area and volume", 1),
    ("Geometry", "Lines, angles, and triangles", 1),
    ("Geometry", "Circles", 1),
    ("Geometry", "Right triangles and trigonometry", 1),
]
# Total: 22 Questions (Correct)

class Command(BaseCommand):
    help = 'The Ultimate Parallel SAT Generator (Fastest & Best Quality)'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Delete existing test and start fresh')
        parser.add_argument('--workers', type=int, default=4, help='Number of parallel requests')

    def handle(self, *args, **options):
        if not GEMINI_API_KEY or len(GEMINI_API_KEY) < 20:
            self.stdout.write(self.style.ERROR("Error: Invalid or missing GEMINI_API_KEY in settings.py"))
            return

        self.client = genai.Client(api_key=GEMINI_API_KEY)
        self.lock = threading.Lock() 
        
        self.log(f"--- 🚀 Starting Robust SAT Generation ({MODEL_NAME}) ---")
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
        slug = 'sat-mock-test-05'
        if force_restart:
            MarketplaceItem.objects.filter(slug=slug).delete()

        item, _ = MarketplaceItem.objects.get_or_create(
            slug=slug,
            defaults={
                'title': 'SAT Mock Test 5',
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

        # Clear partial data to ensure purity
        if section.questions.count() > 0:
            section.questions.all().delete()

        self.log(f"  ... Generating {section_title} ({difficulty})")

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
                # 1. Generate
                questions_data = self.call_gemini_json_mode(subject, domain, sub_topic, difficulty, count)
                
                if not isinstance(questions_data, list) or len(questions_data) == 0:
                     raise ValueError("Empty JSON returned")

                # 2. VALIDATION GATEKEEPER
                valid_questions = []
                for q in questions_data:
                    is_valid, reason = self.validate_question_data(q)
                    if is_valid:
                        valid_questions.append(q)
                    else:
                        self.log(self.style.WARNING(f"        ⚠️ Rejected Q: {reason}"))

                # If we lost questions due to validation, fail the batch so we retry
                if len(valid_questions) < count:
                    raise ValueError(f"Only {len(valid_questions)}/{count} questions passed validation.")

                # 3. Save Atomic
                with transaction.atomic():
                    for q_data in valid_questions:
                        self.save_question_to_db(section, q_data)
                
                self.log(f"      + {sub_topic}: Saved {len(valid_questions)} Qs")
                return

            except Exception as e:
                self.log(self.style.WARNING(f"      ! Retry '{sub_topic}' ({attempt+1}/{max_retries}): {e}"))
                time.sleep(2)
        
        self.log(self.style.ERROR(f"      x CRITICAL FAIL: '{sub_topic}' failed after 3 retries."))

    def validate_question_data(self, data):
        """
        Ensures the question is perfect before DB insertion.
        Returns: (bool, str_reason)
        """
        # A. Basic Fields
        if not data.get('question_text') or not data.get('correct_answer'):
            return False, "Missing text or answer"

        # B. Option Validation (MCQ Only)
        if data.get('type') == 'MCQ':
            options = data.get('options', [])
            
            # Check 1: Count
            if len(options) != 4:
                return False, f"Invalid option count: {len(options)}"
            
            # Check 2: Duplicates (Normalize to check 5.0 vs 5)
            clean_opts = [str(o).strip().lower() for o in options]
            if len(set(clean_opts)) != len(clean_opts):
                return False, "Duplicate options found"

            # Check 3: Answer Existence
            correct = str(data.get('correct_answer')).strip().lower()
            if correct not in clean_opts:
                # Last ditch effort: if answer is '5' and options has '5.0', it's okay? 
                # No, we want strict matching for DB integrity.
                return False, f"Correct answer '{correct}' not in options {clean_opts}"

            # Check 4: Nonsense Content
            for opt in options:
                if "option" in str(opt).lower() or str(opt).strip() == "":
                    return False, f"Nonsense option detected: {opt}"

        return True, "Valid"

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

        prompt = f"""
        Role: Senior SAT Exam Writer. 
        Task: Create {count} {difficulty} questions.
        Context: {subject} > {domain} > {sub_topic}
        
        STRICT QUALITY RULES:
        1. **DISTINCT OPTIONS:** For MCQs, all 4 options MUST be unique. Do not use synonyms (e.g., "5" and "5.0").
        2. **PLAUSIBLE DISTRACTORS:** Options must make logical sense. No "Option A" placeholders.
        3. **FORMATTING:** - Options: Plain text only (e.g. "5", NOT "A) 5").
           - Math: Use single $ for inline, double $$ for display equations.
        4. {image_rule}
        
        Output JSON:
        [{{ "question_text": "...", "type": "MCQ"|"NUMERIC", "options": ["...", "...", "...", "..."], "correct_answer": "...", "explanation": "...", "python_code": "..." }}]
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
        
        correct_raw = self.clean_text(str(data.get('correct_answer')))
        options_raw = [self.clean_text(o) for o in data.get('options', [])]

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