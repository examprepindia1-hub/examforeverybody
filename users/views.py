from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, get_user_model
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth.decorators import login_required

# --- NEW IMPORTS FOR EMAIL VERIFICATION ---
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import EmailMessage
from django.contrib.auth.tokens import default_token_generator

from config import settings

from .forms import StudentSignUpForm, UserLoginForm, UserUpdateForm

def register(request):
    return redirect('student_signup')

def student_signup(request):
    if request.method == 'POST':
        form = StudentSignUpForm(request.POST)
        if form.is_valid():
            # 1. Save user but DO NOT activate yet
            user = form.save(commit=False)
            user.is_active = False 
            user.save()

            # 2. Generate Verification Data
            current_site = get_current_site(request)
            mail_subject = 'Activate your ExamForEverybody Account'
            
            # Prepare email content
            message = render_to_string('users/account_verification_email.html', {
                'user': user,
                'domain': current_site.domain,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': default_token_generator.make_token(user),
                'protocol': 'https' if request.is_secure() else 'http'
            })
            
            # 3. Send Email
            to_email = form.cleaned_data.get('email')
            email = EmailMessage(mail_subject, message, to=[to_email], from_email=settings.DEFAULT_FROM_EMAIL)
            email.content_subtype = "html"
            email.send()

            # 4. Redirect with Info Message
            messages.info(request, f"Dear {user.first_name}, a verification link has been sent to {to_email}. Please check your inbox.")
            return redirect('login') 
            
    else:
        form = StudentSignUpForm()
    return render(request, 'users/signup_student.html', {'form': form})

def activate(request, uidb64, token):
    """
    Handles the link click from the email.
    """
    User = get_user_model()
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except(TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        messages.success(request, 'Your account has been activated successfully! You can now log in.')
        return redirect('login')
    else:
        messages.error(request, 'Activation link is invalid or expired!')
        return redirect('login')

class CustomLoginView(LoginView):
    template_name = 'users/login.html'
    authentication_form = UserLoginForm
    redirect_authenticated_user = True
    
    def get_success_url(self):
        return reverse_lazy('home')
    
@login_required
def profile(request):
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated!')
            return redirect('profile')
    else:
        form = UserUpdateForm(instance=request.user)
    
    return render(request, 'users/profile.html', {'form': form})