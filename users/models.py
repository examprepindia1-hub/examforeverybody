from django.db import models
from django.contrib.auth.models import AbstractUser

# 1. Users Table (users)
class CustomUser(AbstractUser):
    # Django handles: username, password, email, first_name, last_name, is_staff, is_active

    class Role(models.TextChoices):
        STUDENT = 'STUDENT', 'Student'
        INSTRUCTOR = 'INSTRUCTOR', 'Instructor'
        ADMIN = 'ADMIN', 'Admin'
    
    # We use a default role for easy management
    role = models.CharField(
        max_length=15,
        choices=Role.choices,
        default=Role.STUDENT,
        verbose_name="User Role"
    )
    
    # Optional field for instructor bio or public profile description
    bio = models.TextField(
        blank=True, 
        null=True
    )
    
    # Required for custom user model setup
    REQUIRED_FIELDS = ['email', 'role']

    def __str__(self):
        return self.email