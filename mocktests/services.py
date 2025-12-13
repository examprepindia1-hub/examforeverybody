# mocktests/services.py

from django.db.models import Sum

class BaseExamStrategy:
    """Base class with default logic for GENERAL exams"""
    
    def get_take_test_template(self):
        return 'mocktests/take_test_general.html'

    def get_result_template(self):
        return 'mocktests/result_general.html'

    def calculate_score(self, attempt):
        """Standard simple scoring: Sum of correct answers"""
        total_score = 0
        correct_count = 0
        
        # Simple loop (you can optimize this with aggregate queries)
        for answer in attempt.answers.all():
            if answer.is_correct:
                total_score += answer.question.marks
                correct_count += 1
        
        return {
            'score': total_score,
            'correct_count': correct_count,
            'passed': total_score >= (attempt.test.pass_percentage / 100) * total_score # Simplified logic
        }

class SATExamStrategy(BaseExamStrategy):
    """Specific logic for Digital SAT"""
    
    def get_take_test_template(self):
        return 'mocktests/exams/sat/take_test.html'  # Custom UI for SAT

    def get_result_template(self):
        return 'mocktests/exams/sat/result.html'     # 400-1600 Score Card

    def calculate_score(self, attempt):
        """
        SAT Scoring is complex (400-1600 scale). 
        You would implement the curve logic here.
        """
        raw_score = super().calculate_score(attempt)['score']
        
        # Dummy Logic: Convert raw score to 400-1600 scale
        # Real logic uses lookup tables based on difficulty.
        sat_score = 400 + (raw_score * 10) 
        sat_score = min(1600, sat_score) # Cap at 1600

        return {
            'score': sat_score,
            'details': "Your SAT Score is based on an adaptive curve."
        }

class IELTSExamStrategy(BaseExamStrategy):
    """Specific logic for IELTS"""
    
    def get_take_test_template(self):
        return 'mocktests/exams/ielts/take_test.html' # Split Screen UI

    def get_result_template(self):
        return 'mocktests/exams/ielts/result.html'    # Band 0-9 Report

    def calculate_score(self, attempt):
        raw_score = super().calculate_score(attempt)['score']
        
        # IELTS Band Conversion (approximate)
        # 30-40 -> Band 8-9, etc.
        band = 0
        if raw_score >= 39: band = 9.0
        elif raw_score >= 37: band = 8.5
        elif raw_score >= 35: band = 8.0
        # ... more logic ...
        else: band = 4.0

        return {
            'score': band,
            'details': "IELTS Band Score calculated."
        }

# --- FACTORY FUNCTION ---
def get_exam_strategy(exam_type):
    strategies = {
        'SAT': SATExamStrategy(),
        'IELTS': IELTSExamStrategy(),
        'GENERAL': BaseExamStrategy(),
    }
    return strategies.get(exam_type, BaseExamStrategy())