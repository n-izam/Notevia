from allauth.account.signals import user_signed_up
from django.dispatch import receiver

@receiver(user_signed_up)
def populate_profile(sociallogin, user, **kwargs):
    if sociallogin.account.provider == 'google':
        data = sociallogin.account.extra_data
        user.full_name = data.get('name', '')
        user.is_active = True  # Make sure user is active
        user.save()
