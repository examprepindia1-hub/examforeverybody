from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.contrib import messages
from .forms import StudentSignUpForm, UserLoginForm

def student_signup(request):
    if request.method == 'POST':
        form = StudentSignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user) # Log them in immediately
            messages.success(request, f"Welcome to ExamForEverybody, {user.first_name}!")
            return redirect('home') # Redirect to homepage or dashboard
    else:
        form = StudentSignUpForm()
    return render(request, 'users/signup_student.html', {'form': form})

class CustomLoginView(LoginView):
    template_name = 'users/login.html'
    authentication_form = UserLoginForm
    redirect_authenticated_user = True
    
    def get_success_url(self):
        return reverse_lazy('home')