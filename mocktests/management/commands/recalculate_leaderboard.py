from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from mocktests.signals import recalculate_user_rank

User = get_user_model()

class Command(BaseCommand):
    help = 'Recalculates UserRankMetric for all users based on their test history'

    def handle(self, *args, **kwargs):
        self.stdout.write("Starting Leaderboard Recalculation...")
        
        users = User.objects.all()
        count = users.count()
        
        for i, user in enumerate(users):
            recalculate_user_rank(user)
            if i % 100 == 0:
                self.stdout.write(f"Processed {i}/{count} users...")
        
        self.stdout.write(self.style.SUCCESS('Successfully rebuilt Leaderboard Metrics!'))
