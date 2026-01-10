from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

class MySocialAccountAdapter(DefaultSocialAccountAdapter):
    def populate_user(self, request, sociallogin, data):
        """
        Hook that populates the user instance from the social login data.
        """
        user = super().populate_user(request, sociallogin, data)
        
        # Extract avatar URL from Google extra_data
        if sociallogin.account.provider == 'google':
            picture_url = sociallogin.account.extra_data.get('picture')
            if picture_url:
                user.avatar_url = picture_url
                
        return user

    def save_user(self, request, sociallogin, form=None):
        """
        Called after user is authenticated to ensure avatar is updated on every login.
        """
        user = super().save_user(request, sociallogin, form)
        
        if sociallogin.account.provider == 'google':
            picture_url = sociallogin.account.extra_data.get('picture')
            if picture_url and getattr(user, 'avatar_url', None) != picture_url:
                user.avatar_url = picture_url
                user.save(update_fields=['avatar_url'])
        
        return user
