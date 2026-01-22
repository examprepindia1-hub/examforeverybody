from .models import UserAnswer

class BaseExamStrategy:
    """Base class with default logic for GENERAL exams"""
    
    def get_take_test_template(self):
        return 'mocktests/take_test_general.html'

    def get_result_template(self):
        return 'mocktests/result_general.html'

    def grade_answers(self, attempt):
        """
        Grades both MCQ and NUMERIC/INPUT answers.
        """
        answers = UserAnswer.objects.filter(attempt=attempt).select_related('question', 'selected_option')
        
        for answer in answers:
            # 1. Logic for MCQ
            if answer.question.question_type == 'MCQ':
                if answer.selected_option and answer.selected_option.is_correct:
                    answer.is_correct = True
                else:
                    answer.is_correct = False
            
            # 2. Logic for NUMERIC / INPUT (The Fix)
            elif answer.question.question_type == 'NUMERIC':
                # Get the user's text input and the stored correct value
                user_val = str(answer.text_answer).strip() if answer.text_answer else ""
                correct_val = str(answer.question.correct_answer_value).strip() if answer.question.correct_answer_value else ""
                
                # Compare them (Case-insensitive)
                if user_val and correct_val and user_val.lower() == correct_val.lower():
                    answer.is_correct = True
                else:
                    answer.is_correct = False

            # 3. Save the result
            answer.save()

    def calculate_score(self, attempt):
        """Standard simple scoring"""
        self.grade_answers(attempt)
        
        total_score = 0
        correct_count = 0
        
        # Re-fetch to ensure we have the latest is_correct status
        for answer in attempt.answers.all():
            if answer.is_correct:
                total_score += answer.question.marks
                correct_count += 1
        
        return {
            'score': total_score,
            'correct_count': correct_count,
            'passed': True 
        }

class SATExamStrategy(BaseExamStrategy):
    """Specific logic for Digital SAT"""
    
    def get_take_test_template(self):
        return 'mocktests/exams/sat/take_test.html'

    def get_result_template(self):
        return 'mocktests/exams/sat/result.html'

    def calculate_score(self, attempt):
        # 1. Grade the answers
        self.grade_answers(attempt)
        
        # 2. Get Raw Counts
        math_correct = attempt.answers.filter(is_correct=True, question__section__title__icontains="Math").count()
        rw_correct = attempt.answers.filter(is_correct=True, question__section__title__icontains="Reading").count()
        
        # 3. Simple Mock SAT Algorithm (Curve)
        math_score = 200 + (math_correct * 10)
        if math_score > 800: math_score = 800
        
        rw_score = 200 + (rw_correct * 10)
        if rw_score > 800: rw_score = 800
        
        total_sat_score = math_score + rw_score

        return {
            'score': total_sat_score,
            'details': {
                'math': math_score,
                'rw': rw_score
            }
        }

class IELTSExamStrategy(BaseExamStrategy):
    pass

class JEEMainExamStrategy(BaseExamStrategy):
    pass

def get_exam_strategy(exam_type):
    strategies = {
        'SAT_ADAPTIVE': SATExamStrategy(),
        'SAT_NON_ADAPTIVE': SATExamStrategy(),
        'SAT': SATExamStrategy(),
        'IELTS': IELTSExamStrategy(),
        'JEE_MAINS': JEEMainExamStrategy(), 
        'GENERAL': BaseExamStrategy(),
    }
    return strategies.get(exam_type, BaseExamStrategy())