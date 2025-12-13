from django.core.management.base import BaseCommand
from core.models import Category

class Command(BaseCommand):
    help = 'Populates the site with standard EdTech categories'

    def handle(self, *args, **kwargs):
        self.stdout.write("--- POPULATING CATEGORIES ---")
        
        # 1. Create Parent Categories
        academics = Category.objects.create(value='ACAD', display_name='Academics')
        languages = Category.objects.create(value='LANG', display_name='Languages')
        entrance = Category.objects.create(value='ENTR', display_name='Entrance Exams')
        
        # 2. Create Sub-Categories
        Category.objects.create(value='SAT', display_name='SAT Prep', parent_category=academics)
        Category.objects.create(value='JEE', display_name='JEE Mains/Advanced', parent_category=entrance)
        Category.objects.create(value='IELTS', display_name='IELTS Academic', parent_category=languages)
        
        # 3. SUCCESS MESSAGE (Return a string, not a dict)
        self.stdout.write(self.style.SUCCESS("Successfully populated categories"))