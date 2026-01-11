from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordResetForm, SetPasswordForm
from .models import CustomUser

class StudentSignUpForm(UserCreationForm):
    first_name = forms.CharField(max_length=30, required=True, label='First Name')
    last_name = forms.CharField(max_length=30, required=True, label='Last Name')
    email = forms.EmailField(required=True, label='Email Address')

    class Meta:
        model = CustomUser
        fields = ('first_name', 'last_name', 'email', 'country')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Loop through ALL fields (including the inherited password ones)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
            field.widget.attrs['placeholder'] = field.label

    # --- NEW: VALIDATION TO PREVENT CRASH ---
    def clean_email(self):
        email = self.cleaned_data.get('email').lower()
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    # --- SPAM PROTECTION: HONEYPOT ---
    # This field is hidden from humans. Bots will fill it out.
    confirm_email = forms.CharField(
        required=False, 
        label='Confirm Email',
        widget=forms.TextInput(attrs={'style': 'display:none !important;', 'tabindex': '-1', 'autocomplete': 'off'})
    )

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('confirm_email'):
            # HoneyPot filled -> Bot detected!
            raise forms.ValidationError("Spam detected.")
        return cleaned_data

    def signup(self, request, user):
        """
        Required by django-allauth.
        """
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.country = self.cleaned_data['country']
        user.role = CustomUser.Role.STUDENT
        user.save()

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = CustomUser.Role.STUDENT
        # Ensure we use the cleaned (lowercased) email
        user.email = self.cleaned_data['email']
        user.username = user.email
        if commit:
            user.save()
        return user

class UserLoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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

class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'country']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}),
            'country': forms.Select(attrs={'class': 'form-select'}),
        }