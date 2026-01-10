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
            
            # --- GOOGLE TOKEN REVOCATION START ---
            try:
                from allauth.socialaccount.models import SocialToken, SocialAccount
                import requests

                # DEBUG: List all connected accounts and tokens
                accounts = SocialAccount.objects.filter(user=user)
                print(f"[DEBUG] Found {accounts.count()} social accounts for user {user.id}")
                for acc in accounts:
                    print(f"[DEBUG] Account: {acc.provider} (ID: {acc.uid})")
                    tokens = SocialToken.objects.filter(account=acc)
                    print(f"[DEBUG]   Tokens count: {tokens.count()}")
                    for t in tokens:
                        print(f"[DEBUG]    - Token: {t.token[:10]}... (Secret: {'YES' if t.token_secret else 'NO'})")

                # Find Google token
                google_token = SocialToken.objects.filter(
                    account__user=user, 
                    account__provider='google'
                ).last()

                if google_token:
                    print(f"[DEBUG] Found Google Token for user {user.id}. Access Token length: {len(google_token.token)}")
                    
                    # 1. Try Revoking Access Token
                    resp = requests.post(
                        'https://oauth2.googleapis.com/revoke',
                        params={'token': google_token.token},
                        headers={'Content-Type': 'application/x-www-form-urlencoded'},
                        timeout=5
                    )
                    
                    print(f"[DEBUG] Revoke Access Token Status: {resp.status_code}, Body: {resp.text}")

                    # 2. Try Revoking Refresh Token
                    if google_token.token_secret:
                        print(f"[DEBUG] Found Refresh Token. Revoking...")
                        resp_refresh = requests.post(
                            'https://oauth2.googleapis.com/revoke',
                            params={'token': google_token.token_secret},
                            headers={'Content-Type': 'application/x-www-form-urlencoded'},
                            timeout=5
                        )
                        print(f"[DEBUG] Revoke Refresh Token Status: {resp_refresh.status_code}, Body: {resp_refresh.text}")
                else:
                     print(f"[DEBUG] No Google Token found for user {user.id}")

            except Exception as e:
                # preventing crash on deletion
                print(f"[ERROR] Exception revoking Google token: {e}")
            # --- GOOGLE TOKEN REVOCATION END ---

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