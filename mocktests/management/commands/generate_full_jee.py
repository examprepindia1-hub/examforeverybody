"""
JEE Mains Contest Generator - Ultimate AI-Powered Exam Generation
==================================================================
Generates a complete JEE Mains exam with:
- Physics (30 questions: 20 MCQ + 10 Numerical)
- Chemistry (30 questions: 20 MCQ + 10 Numerical)  
- Mathematics (30 questions: 20 MCQ + 10 Numerical)

Features:
- Dual image pipeline: Matplotlib (Physics/Math) + RDKit (Chemistry structures)
- Enhanced multi-layer validation
- Comprehensive syllabus coverage
- Proper JEE marking scheme (+4/-1 MCQ, +4/0 Numerical)
"""

import google.genai as genai
from google.genai import types
import json
import io
import time
import re
import concurrent.futures
import threading
import traceback

# --- FORCE NON-INTERACTIVE BACKENDS ---
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

# RDKit for Chemistry Structures
try:
    from rdkit import Chem
    from rdkit.Chem import Draw, AllChem
    from rdkit.Chem.Draw import rdMolDraw2D
    RDKIT_AVAILABLE = True
except ImportError:
    RDKIT_AVAILABLE = False

from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from marketplace.models import MarketplaceItem
from mocktests.models import (
    MockTestAttributes, TestSection, TestQuestion, QuestionOption, QuestionMedia
)

# =============================================================================
# CONFIGURATION
# =============================================================================

GEMINI_API_KEY = getattr(settings, "GEMINI_API_KEY", "AIzaSyDIutO9VfMWfXjFzwzNJi2faOuk3G6TxeU")
MODEL_NAME = "gemini-3-pro-preview"  # Fast and high quality

# Professional Diagram Style
DIAGRAM_STYLE = """
plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.size': 11,
    'axes.spines.top': False,
    'axes.spines.right': False,
    'axes.grid': True,
    'grid.alpha': 0.3,
    'figure.facecolor': 'white',
    'axes.facecolor': 'white'
})
"""

# =============================================================================
# JEE MAINS SYLLABUS BLUEPRINTS
# =============================================================================

# Format: (Domain, Sub-topic, MCQ_count, Numerical_count, needs_image_type)
# needs_image_type: 'matplotlib', 'rdkit', or None

BLUEPRINT_PHYSICS = [
    # --- Class 11 Topics ---
    ("Mechanics", "Kinematics - Motion in 1D and 2D", 2, 1, "matplotlib"),
    ("Mechanics", "Laws of Motion and Friction", 2, 1, "matplotlib"),
    ("Mechanics", "Work, Energy and Power", 1, 1, None),
    ("Mechanics", "Rotational Motion and Moment of Inertia", 2, 1, "matplotlib"),
    ("Mechanics", "Gravitation", 1, 1, None),
    ("Properties of Matter", "Properties of Solids - Elasticity", 1, 0, None),
    ("Properties of Matter", "Fluid Mechanics and Surface Tension", 1, 1, "matplotlib"),
    ("Thermodynamics", "Thermodynamics and Heat Transfer", 2, 1, "matplotlib"),
    ("Thermodynamics", "Kinetic Theory of Gases", 1, 1, None),
    ("Waves", "Oscillations and SHM", 1, 1, "matplotlib"),
    ("Waves", "Waves - Sound and Standing Waves", 1, 0, "matplotlib"),
    
    # --- Class 12 Topics ---
    ("Electrostatics", "Electric Charges, Fields and Potential", 2, 1, "matplotlib"),
    ("Current Electricity", "Current, Resistance and Circuits", 2, 1, "matplotlib"),
    ("Magnetism", "Magnetic Effects of Current", 1, 0, "matplotlib"),
    ("Magnetism", "Electromagnetic Induction and AC", 1, 0, "matplotlib"),
    ("Optics", "Ray Optics - Mirrors and Lenses", 2, 1, "matplotlib"),
    ("Optics", "Wave Optics - Interference and Diffraction", 1, 1, "matplotlib"),
    ("Modern Physics", "Dual Nature of Matter and Photoelectric Effect", 1, 1 , None),
    ("Modern Physics", "Atoms, Nuclei and Radioactivity", 2, 1, None),
    ("Electronics", "Semiconductors and Logic Gates", 1, 0, "matplotlib"),
]
# Total: 20 MCQ + 10 Numerical = 30 Questions

BLUEPRINT_CHEMISTRY = [
    # --- Physical Chemistry ---
    ("Physical Chemistry", "Mole Concept and Stoichiometry", 2, 1, None),
    ("Physical Chemistry", "Atomic Structure and Quantum Numbers", 1, 1, "matplotlib"),
    ("Physical Chemistry", "Chemical Thermodynamics", 2, 1, "matplotlib"),
    ("Physical Chemistry", "Chemical Equilibrium", 1, 1, None),
    ("Physical Chemistry", "Ionic Equilibrium and pH", 1, 1, None),
    ("Physical Chemistry", "Electrochemistry", 2, 1, "matplotlib"),
    ("Physical Chemistry", "Chemical Kinetics and Rate Laws", 2, 1, "matplotlib"),
    ("Physical Chemistry", "Solid State and Crystal Structures", 1, 0, "matplotlib"),
    ("Physical Chemistry", "Solutions and Colligative Properties", 1, 1, None),
    
    # --- Organic Chemistry ---
    ("Organic Chemistry", "General Organic Chemistry - IUPAC and Isomerism", 2, 0, "rdkit"),
    ("Organic Chemistry", "Hydrocarbons - Alkanes, Alkenes, Alkynes", 1, 1, "rdkit"),
    ("Organic Chemistry", "Haloalkanes and Haloarenes", 1, 0, "rdkit"),
    ("Organic Chemistry", "Alcohols, Phenols and Ethers", 1, 1, "rdkit"),
    ("Organic Chemistry", "Aldehydes, Ketones and Carboxylic Acids", 2, 0, "rdkit"),
    ("Organic Chemistry", "Amines and Nitrogen Compounds", 1, 0, "rdkit"),
    ("Organic Chemistry", "Biomolecules and Polymers", 1, 1, "rdkit"),
    
    # --- Inorganic Chemistry ---
    ("Inorganic Chemistry", "Periodic Table and Periodicity", 1, 0, None),
    ("Inorganic Chemistry", "Chemical Bonding and Molecular Structure", 2, 1, "matplotlib"),
    ("Inorganic Chemistry", "s-Block and p-Block Elements", 2, 0, None),
    ("Inorganic Chemistry", "d-Block Elements and Coordination Compounds", 2, 1, "rdkit"),
]
# Total: 20 MCQ + 10 Numerical = 30 Questions

BLUEPRINT_MATHEMATICS = [
    # --- Class 11 Topics ---
    ("Algebra", "Sets, Relations and Functions", 1, 0, None),
    ("Algebra", "Complex Numbers", 2, 1, "matplotlib"),
    ("Algebra", "Quadratic Equations", 1, 1, None),
    ("Algebra", "Permutations and Combinations", 2, 1, None),
    ("Algebra", "Binomial Theorem", 1, 1, None),
    ("Algebra", "Sequences and Series - AP, GP, HP", 2, 1, None),
    ("Algebra", "Matrices and Determinants", 2, 1, None),
    ("Coordinate Geometry", "Straight Lines", 1, 1, "matplotlib"),
    ("Coordinate Geometry", "Conic Sections - Circle, Parabola, Ellipse, Hyperbola", 2, 1, "matplotlib"),
    ("Trigonometry", "Trigonometric Functions and Equations", 1, 0, "matplotlib"),
    
    # --- Class 12 Topics ---
    ("Calculus", "Limits and Continuity", 1, 0, "matplotlib"),
    ("Calculus", "Differentiability and Differentiation", 2, 1, "matplotlib"),
    ("Calculus", "Applications of Derivatives", 1, 1, "matplotlib"),
    ("Calculus", "Indefinite and Definite Integrals", 2, 1, "matplotlib"),
    ("Calculus", "Differential Equations", 1, 1, None),
    ("Vectors and 3D", "Vector Algebra", 1, 0, "matplotlib"),
    ("Vectors and 3D", "Three-Dimensional Geometry", 2, 1, "matplotlib"),
    ("Probability", "Probability and Statistics", 2, 1, "matplotlib"),
    ("Mathematical Reasoning", "Mathematical Reasoning and Logic", 1, 0, None),
]
# Total: 20 MCQ + 10 Numerical = 30 Questions


# =============================================================================
# MAIN COMMAND CLASS
# =============================================================================

class Command(BaseCommand):
    help = 'Generate a complete JEE Mains Contest with AI-powered questions'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Delete existing test and start fresh')
        parser.add_argument('--workers', type=int, default=4, help='Number of parallel API requests')
        parser.add_argument('--dry-run', action='store_true', help='Test with minimal questions')

    def handle(self, *args, **options):
        if not GEMINI_API_KEY or len(GEMINI_API_KEY) < 20:
            self.stdout.write(self.style.ERROR("❌ Error: Invalid or missing GEMINI_API_KEY in settings.py"))
            return

        if not RDKIT_AVAILABLE:
            self.stdout.write(self.style.WARNING("⚠️ RDKit not available. Chemistry structures will use matplotlib fallback."))

        self.client = genai.Client(api_key=GEMINI_API_KEY)
        self.lock = threading.Lock()
        self.dry_run = options['dry_run']
        
        self.log(f"{'='*60}")
        self.log(f"🚀 JEE MAINS CONTEST GENERATOR ({MODEL_NAME})")
        self.log(f"{'='*60}")
        self.log(f"⚡ Parallel Workers: {options['workers']}")
        self.log(f"🧪 RDKit Available: {RDKIT_AVAILABLE}")
        if self.dry_run:
            self.log(f"🔬 DRY RUN MODE - Generating minimal questions")
        self.log(f"{'='*60}\n")

        # 1. Setup Exam Structure
        item, test_attr = self.setup_exam_structure(options['force'])
        
        # 2. Generate All Sections
        sections_config = [
            ("Physics", BLUEPRINT_PHYSICS, 60),
            ("Chemistry", BLUEPRINT_CHEMISTRY, 60),
            ("Mathematics", BLUEPRINT_MATHEMATICS, 60),
        ]

        for subject, blueprint, duration in sections_config:
            self.generate_section(test_attr, subject, blueprint, duration, options['workers'])

        self.log(f"\n{'='*60}")
        self.log(self.style.SUCCESS(f"✅ JEE MAINS CONTEST COMPLETE: '{item.title}'"))
        self.log(f"{'='*60}")
        
        # Print summary
        self.print_summary(test_attr)

    def log(self, message):
        """Thread-safe logging"""
        with self.lock:
            self.stdout.write(message)

    def setup_exam_structure(self, force_restart):
        """Create or retrieve the exam structure in the database"""
        slug = 'jee-main-contest-2026'
        
        if force_restart:
            self.log("🗑️  Force restart: Deleting existing test...")
            MarketplaceItem.objects.filter(slug=slug).delete()

        item, created = MarketplaceItem.objects.get_or_create(
            slug=slug,
            defaults={
                'title': 'JEE Main Contest 2026',
                'description': '''🎯 **Ultimate JEE Mains Simulation**

Experience the most advanced AI-generated JEE Mains practice test with:
- 📚 **90 Questions** across Physics, Chemistry & Mathematics
- ⏱️ **180 Minutes** timed exam environment
- 📊 **Realistic Difficulty** - Easy, Medium & Hard mixed
- 📈 **Detailed Solutions** with step-by-step explanations
- 🖼️ **Visual Diagrams** for complex problems

**Exam Pattern:**
- 20 MCQs + 10 Numerical per subject
- MCQ: +4 correct, -1 wrong
- Numerical: +4 correct, 0 wrong

Perfect preparation for JEE Mains 2026!''',
                'price': 99.00,
                'item_type': 'MOCK_TEST',
                'is_active': True
            }
        )
        
        if created:
            self.log(f"📦 Created new MarketplaceItem: '{item.title}'")
        else:
            self.log(f"📦 Using existing MarketplaceItem: '{item.title}'")

        test_attr, created = MockTestAttributes.objects.get_or_create(
            item=item,
            defaults={
                'exam_type': 'JEE_MAINS',
                'level': 'ADVANCED',
                'duration_minutes': 180,
                'pass_percentage': 25,  # JEE qualifying cutoff varies
                'has_negative_marking': True,
                'negative_marking_percentage': 0.25,  # 25% = 1 mark for 4-mark questions
                'instructions': """<div class="jee-instructions">
<h3>📋 JEE Main Examination Instructions</h3>
<ol>
    <li>Total duration: <strong>180 minutes (3 hours)</strong></li>
    <li>The paper contains <strong>90 questions</strong> (30 per subject)</li>
    <li>Each subject has <strong>20 MCQs + 10 Numerical</strong> value questions</li>
    <li><strong>Marking Scheme:</strong>
        <ul>
            <li>MCQ: +4 for correct, -1 for wrong</li>
            <li>Numerical: +4 for correct, 0 for wrong</li>
        </ul>
    </li>
    <li>You may attempt any <strong>25 questions</strong> from each section</li>
    <li>Use the question palette to navigate between questions</li>
    <li>Calculator is <strong>NOT allowed</strong></li>
</ol>
</div>"""
            }
        )
        
        if created:
            self.log(f"⚙️  Created MockTestAttributes with JEE_MAINS config")
        
        return item, test_attr

    def generate_section(self, test_attr, subject, blueprint, duration, max_workers):
        """Generate all questions for a section (Physics/Chemistry/Math)"""
        section, created = TestSection.objects.get_or_create(
            test=test_attr,
            title=subject,
            defaults={
                'sort_order': {'Physics': 1, 'Chemistry': 2, 'Mathematics': 3}[subject],
                'section_duration': duration
            }
        )

        # Calculate expected totals
        expected_mcq = sum(item[2] for item in blueprint)
        expected_numeric = sum(item[3] for item in blueprint)
        expected_total = expected_mcq + expected_numeric

        current_count = section.questions.count()
        
        if current_count >= expected_total:
            self.log(f"✅ {subject}: Already complete ({current_count}/{expected_total} questions). Skipping.")
            return

        # Clear partial data for clean generation
        if current_count > 0:
            self.log(f"🧹 {subject}: Clearing {current_count} partial questions...")
            section.questions.all().delete()

        self.log(f"\n📝 Generating {subject} ({expected_mcq} MCQ + {expected_numeric} Numerical)...")

        # Parallel generation by topic
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for domain, sub_topic, mcq_count, numeric_count, image_type in blueprint:
                # In dry-run mode, generate only 1 question per topic
                if self.dry_run:
                    mcq_count = min(1, mcq_count)
                    numeric_count = 0
                
                if mcq_count > 0:
                    futures.append(
                        executor.submit(
                            self.generate_topic_questions,
                            section, subject, domain, sub_topic, 
                            'MCQ', mcq_count, image_type
                        )
                    )
                if numeric_count > 0:
                    futures.append(
                        executor.submit(
                            self.generate_topic_questions,
                            section, subject, domain, sub_topic,
                            'NUMERIC', numeric_count, image_type
                        )
                    )
            
            # Wait for all to complete
            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    self.log(self.style.ERROR(f"   ❌ Thread Error: {e}"))

    def generate_topic_questions(self, section, subject, domain, sub_topic, q_type, count, image_type):
        """Generate questions for a specific topic with retries"""
        max_retries = 3
        difficulty_mix = self.get_difficulty_mix(count)
        
        for attempt in range(max_retries):
            try:
                # 1. Call Gemini API
                questions_data = self.call_gemini_api(
                    subject, domain, sub_topic, q_type, count, 
                    difficulty_mix, image_type
                )
                
                if not isinstance(questions_data, list) or len(questions_data) == 0:
                    raise ValueError("Empty or invalid JSON response from API")

                # 2. Validate all questions
                valid_questions = []
                for q in questions_data:
                    is_valid, reason = self.validate_question(q, q_type, image_type)
                    if is_valid:
                        valid_questions.append(q)
                    else:
                        self.log(self.style.WARNING(f"      ⚠️ Rejected: {reason}"))

                # 3. Check if we have enough valid questions
                if len(valid_questions) < count:
                    raise ValueError(f"Only {len(valid_questions)}/{count} questions passed validation")

                # 4. Save to database atomically
                with transaction.atomic():
                    for q_data in valid_questions[:count]:  # Take exactly what we need
                        self.save_question(section, q_data, q_type, image_type)
                
                self.log(f"   ✓ {sub_topic} ({q_type}): Saved {count} questions")
                return

            except Exception as e:
                self.log(self.style.WARNING(f"   ⚠️ Retry {sub_topic} ({attempt+1}/{max_retries}): {str(e)[:100]}"))
                time.sleep(2 * (attempt + 1))  # Exponential backoff
        
        self.log(self.style.ERROR(f"   ❌ FAILED: {sub_topic} ({q_type}) after {max_retries} retries"))

    def get_difficulty_mix(self, count):
        """Return a balanced difficulty distribution"""
        if count == 1:
            return ["Medium"]
        elif count == 2:
            return ["Easy", "Hard"]
        else:
            # For 3+, mix them evenly
            mix = []
            difficulties = ["Easy", "Medium", "Hard"]
            for i in range(count):
                mix.append(difficulties[i % 3])
            return mix

    def call_gemini_api(self, subject, domain, sub_topic, q_type, count, difficulties, image_type):
        """Generate questions using Gemini API with structured prompts"""
        
        # Build image instruction based on type
        image_instruction = "python_code: null (no image needed)"
        smiles_instruction = ""
        
        if image_type == "matplotlib":
            image_instruction = f"""
**IMAGE REQUIRED**: Provide 'python_code' with matplotlib code.
- Import: `import matplotlib.pyplot as plt` and `import numpy as np`
- Apply style: {DIAGRAM_STYLE}
- Create clear, professional JEE-style diagrams
- DO NOT include plt.show()
- Use fig, ax = plt.subplots() pattern
"""
        elif image_type == "rdkit" and RDKIT_AVAILABLE:
            smiles_instruction = """
**MOLECULAR STRUCTURE REQUIRED**: Provide 'smiles' field with valid SMILES notation.
- Use standard SMILES format (e.g., "CCO" for ethanol, "c1ccccc1" for benzene)
- Ensure SMILES is chemically valid and corresponds to the molecule in the question
- For complex molecules, use proper stereochemistry notation
"""
            image_instruction = "python_code: null (using SMILES for structure)"
        elif image_type == "rdkit" and not RDKIT_AVAILABLE:
            # Fallback to matplotlib for chemistry
            image_instruction = """
**DIAGRAM REQUIRED**: Provide 'python_code' with matplotlib to draw molecular structure representation.
- Draw a simplified structural diagram
- Label atoms and bonds clearly
"""

        # Question type specific instructions
        if q_type == "MCQ":
            type_instruction = """
**MCQ Format:**
- Provide exactly 4 unique options
- Options must be plausible (realistic distractors)
- Correct answer must EXACTLY match one of the options
- Do NOT prefix options with A), B), 1., etc.
- Format: "options": ["value1", "value2", "value3", "value4"]
"""
        else:
            type_instruction = """
**NUMERICAL Format:**
- Answer should be a numerical value only
- Provide the exact numerical answer (integer or decimal up to 2 places)
- No units in the answer field
- "options": [] (empty array for numerical)
"""

        difficulty_str = ", ".join(difficulties)
        
        prompt = f"""You are an expert JEE Mains question paper setter with 20+ years of experience.

**TASK**: Generate {count} {q_type} question(s) for JEE Mains examination.

**SUBJECT**: {subject}
**DOMAIN**: {domain}  
**TOPIC**: {sub_topic}
**DIFFICULTIES**: {difficulty_str} (generate questions with this mix of difficulty levels)

**STRICT QUALITY REQUIREMENTS**:

1. **JEE STANDARD**: Questions must match actual JEE Mains difficulty and style
2. **UNIQUE CONTENT**: Each question must be original and non-repetitive
3. **COMPLETE EXPLANATION**: Provide detailed step-by-step solution with:
   - Clear approach/concept used
   - All mathematical steps shown
   - Final answer clearly stated
   - Common mistakes to avoid (optional)

{type_instruction}

4. **MATH FORMATTING**:
   - Use LaTeX: Single $ for inline math, $$ for display equations
   - Example: "Find $\\int x^2 dx$" or "$$E = mc^2$$"

5. {image_instruction}
{smiles_instruction}

**OUTPUT FORMAT** (JSON array):
```json
[
  {{
    "question_text": "Complete question with all necessary data...",
    "type": "{q_type}",
    "difficulty": "Easy|Medium|Hard",
    "options": ["opt1", "opt2", "opt3", "opt4"],
    "correct_answer": "exact_matching_option",
    "explanation": "Detailed step-by-step solution...",
    "python_code": "matplotlib code if image needed, else null",
    "smiles": "SMILES string if molecular structure needed, else null"
  }}
]
```

Generate {count} high-quality questions now:"""

        try:
            response = self.client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.7  # Some creativity but not too random
                )
            )
            
            return json.loads(response.text)
            
        except json.JSONDecodeError as e:
            # Try to extract JSON from response
            text = response.text if hasattr(response, 'text') else str(response)
            match = re.search(r'\[.*\]', text, re.DOTALL)
            if match:
                return json.loads(match.group())
            raise ValueError(f"Could not parse JSON: {e}")

    def validate_question(self, data, expected_type, image_type):
        """
        Multi-layer validation for question quality.
        Returns: (is_valid: bool, reason: str)
        """
        # A. Basic Field Validation
        if not data.get('question_text') or len(str(data.get('question_text'))) < 20:
            return False, "Question text too short or missing"
        
        if not data.get('correct_answer'):
            return False, "Missing correct answer"
        
        if not data.get('explanation') or len(str(data.get('explanation'))) < 50:
            return False, "Explanation too short or missing"

        # B. Type-specific Validation
        q_type = data.get('type', expected_type).upper()
        
        if q_type == 'MCQ':
            options = data.get('options', [])
            
            # Check option count
            if len(options) != 4:
                return False, f"MCQ must have exactly 4 options, got {len(options)}"
            
            # Check for empty or placeholder options
            for i, opt in enumerate(options):
                if not opt or str(opt).strip() == "":
                    return False, f"Option {i+1} is empty"
                if "option" in str(opt).lower() and len(str(opt)) < 10:
                    return False, f"Placeholder option detected: {opt}"
            
            # Check for duplicates (case-insensitive, whitespace-normalized)
            normalized = [str(o).strip().lower() for o in options]
            if len(set(normalized)) != len(normalized):
                return False, "Duplicate options found"
            
            # Check correct answer exists in options
            correct = str(data.get('correct_answer')).strip().lower()
            if correct not in normalized:
                # Try partial match for numerical answers
                found = False
                for opt in normalized:
                    if correct in opt or opt in correct:
                        found = True
                        break
                if not found:
                    return False, f"Correct answer '{correct}' not in options"

        elif q_type == 'NUMERIC':
            # Validate numeric answer is actually a number
            try:
                answer = str(data.get('correct_answer', '')).strip()
                # Remove common units that might slip through
                answer = re.sub(r'[a-zA-Z°%]+$', '', answer).strip()
                float(answer)
            except ValueError:
                return False, f"Numerical answer is not a valid number: {data.get('correct_answer')}"

        # C. Image/SMILES Validation
        if image_type == "rdkit" and RDKIT_AVAILABLE:
            smiles = data.get('smiles')
            if smiles:
                try:
                    mol = Chem.MolFromSmiles(smiles)
                    if mol is None:
                        return False, f"Invalid SMILES string: {smiles}"
                except Exception as e:
                    return False, f"SMILES parsing error: {e}"

        # D. Content Quality Checks
        question_text = str(data.get('question_text', ''))
        
        # Check for incomplete sentences
        if question_text.endswith('...') or '[' in question_text:
            return False, "Question appears incomplete"
        
        # Check for placeholder text
        placeholder_patterns = ['INSERT', 'TODO', 'EXAMPLE', '[blank]', 'XXX']
        for pattern in placeholder_patterns:
            if pattern in question_text.upper():
                return False, f"Placeholder text found: {pattern}"

        return True, "Valid"

    def save_question(self, section, data, expected_type, image_type):
        """Save a validated question to the database"""
        q_type = data.get('type', expected_type).upper()
        
        # Clean text from any formatting artifacts
        q_text = self.clean_text(data.get('question_text', ''))
        explanation = data.get('explanation', '')
        difficulty = data.get('difficulty', 'MEDIUM').upper()
        
        # Ensure difficulty is valid
        if difficulty not in ['EASY', 'MEDIUM', 'HARD']:
            difficulty = 'MEDIUM'
        
        # Get correct answer (cleaned)
        correct_raw = str(data.get('correct_answer', '')).strip()
        if q_type == 'NUMERIC':
            # Clean numeric answer
            correct_raw = re.sub(r'[a-zA-Z°%]+$', '', correct_raw).strip()
        else:
            correct_raw = self.clean_text(correct_raw)

        # Create question
        question = TestQuestion.objects.create(
            section=section,
            question_text=q_text,
            question_type=q_type,
            difficulty=difficulty,
            correct_answer_value=correct_raw if q_type == 'NUMERIC' else None,
            explanation=explanation,
            marks=4,  # JEE marking scheme
            sort_order=section.questions.count() + 1
        )

        # Create options for MCQ
        if q_type == 'MCQ':
            options_raw = [self.clean_text(str(o)) for o in data.get('options', [])]
            for opt in options_raw:
                is_correct = (opt.lower().strip() == correct_raw.lower().strip())
                QuestionOption.objects.create(
                    question=question,
                    option_text=opt,
                    is_correct=is_correct
                )

        # Generate images if needed
        if image_type == "rdkit" and RDKIT_AVAILABLE and data.get('smiles'):
            self.generate_rdkit_image(question, data['smiles'])
        elif data.get('python_code'):
            self.generate_matplotlib_image(question, data['python_code'])

    def clean_text(self, text):
        """Clean text from formatting artifacts"""
        if not text:
            return ""
        text = str(text).strip()
        # Remove option prefixes
        text = re.sub(r'^(Option\s+)?[A-Da-d][\)\.\:]?\s*', '', text)
        text = re.sub(r'^\([A-Da-d]\)\s*', '', text)
        text = re.sub(r'^\d+[\)\.\:]?\s*', '', text)
        return text.strip()

    def generate_matplotlib_image(self, question, code_snippet):
        """Generate image using matplotlib"""
        try:
            plt.close('all')
            fig, ax = plt.subplots(figsize=(6, 5))
            plt.style.use('seaborn-v0_8-whitegrid')
            
            # Clean the code
            code_snippet = code_snippet.replace("plt.show()", "")
            code_snippet = code_snippet.replace("plt.savefig", "# plt.savefig")
            
            # Execute in isolated namespace
            exec_globals = {
                'plt': plt, 
                'np': np, 
                'fig': fig, 
                'ax': ax,
                'matplotlib': matplotlib
            }
            exec(code_snippet, exec_globals)
            
            # Save to buffer
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', bbox_inches='tight', dpi=150, 
                       facecolor='white', edgecolor='none')
            buffer.seek(0)
            
            # Save to model
            file_name = f"jee_q{question.id}_mpl.png"
            media = QuestionMedia(question=question, caption="Question Diagram")
            media.image.save(file_name, ContentFile(buffer.getvalue()), save=True)
            
            plt.close('all')
            
        except Exception as e:
            # Log but don't fail the question
            with self.lock:
                self.stdout.write(self.style.WARNING(f"      ⚠️ Matplotlib error: {str(e)[:50]}"))

    def generate_rdkit_image(self, question, smiles):
        """Generate molecular structure image using RDKit"""
        if not RDKIT_AVAILABLE:
            return
            
        try:
            mol = Chem.MolFromSmiles(smiles)
            if mol is None:
                return
            
            # Compute 2D coordinates
            AllChem.Compute2DCoords(mol)
            
            # Create high-quality image
            drawer = rdMolDraw2D.MolDraw2DCairo(400, 300)
            drawer.drawOptions().addStereoAnnotation = True
            drawer.drawOptions().addAtomIndices = False
            drawer.DrawMolecule(mol)
            drawer.FinishDrawing()
            
            # Get PNG data
            png_data = drawer.GetDrawingText()
            
            # Save to model
            file_name = f"jee_q{question.id}_mol.png"
            media = QuestionMedia(question=question, caption="Molecular Structure")
            media.image.save(file_name, ContentFile(png_data), save=True)
            
        except Exception as e:
            with self.lock:
                self.stdout.write(self.style.WARNING(f"      ⚠️ RDKit error: {str(e)[:50]}"))

    def print_summary(self, test_attr):
        """Print final summary of generated exam"""
        self.log(f"\n📊 GENERATION SUMMARY:")
        self.log(f"{'─'*40}")
        
        total_questions = 0
        for section in test_attr.sections.all():
            mcq_count = section.questions.filter(question_type='MCQ').count()
            num_count = section.questions.filter(question_type='NUMERIC').count()
            section_total = mcq_count + num_count
            total_questions += section_total
            
            self.log(f"   {section.title}:")
            self.log(f"      MCQ: {mcq_count} | Numerical: {num_count} | Total: {section_total}")
        
        self.log(f"{'─'*40}")
        self.log(f"   📝 Total Questions: {total_questions}")
        self.log(f"   ⏱️  Duration: {test_attr.duration_minutes} minutes")
        self.log(f"   ✏️  Marking: +4/-1 (MCQ), +4/0 (Numerical)")
