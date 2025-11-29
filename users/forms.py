from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordResetForm, SetPasswordForm
from .models import CustomUser

class StudentSignUpForm(UserCreationForm):
    first_name = forms.CharField(max_length=30, required=True,label='First Name')
    last_name = forms.CharField(max_length=30, required=True,label='Last Name')
    email = forms.EmailField(required=True,label='Email Address')

    class Meta:
        model = CustomUser
        fields = ('first_name', 'last_name', 'email','country')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Loop through ALL fields (including the inherited password ones)
        for field_name, field in self.fields.items():
            # Add the Bootstrap class 'form-control' to every input
            field.widget.attrs['class'] = 'form-control'
            field.widget.attrs['placeholder'] = field.label  # Optional: Adds label as placeholder

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = CustomUser.Role.STUDENT
        user.username = user.email
        if commit:
            user.save()
        return user

class UserLoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Apply styling to Login fields too
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'

class CustomPasswordResetForm(PasswordResetForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'
            field.widget.attrs['placeholder'] = 'Enter your email address'

class CustomSetPasswordForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'