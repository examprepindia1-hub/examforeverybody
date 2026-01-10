from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import UserUpdateForm

# Note: Authentication is now handled by django-allauth (Google Login)

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


@login_required
def delete_account(request):
    """
    Handle account deletion with confirmation.
    """
    if request.method == 'POST':
        # Verify the user typed 'DELETE' to confirm
        confirmation = request.POST.get('confirmation', '')
        if confirmation == 'DELETE':
            user = request.user
            # Log the user out first
            from django.contrib.auth import logout
            logout(request)
            # Delete the user account
            user.delete()
            messages.success(request, 'Your account has been permanently deleted.')
            return redirect('home')
        else:
            messages.error(request, 'Please type DELETE to confirm account deletion.')
            return redirect('profile')
    
    return render(request, 'users/delete_account.html')