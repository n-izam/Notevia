from allauth.account.signals import user_signed_up
from django.dispatch import receiver
from accounts.models import CustomUser
from cart.models import Wallet
from django.db.models.signals import post_save

@receiver(user_signed_up)
def populate_profile(sociallogin, user, **kwargs):
    if sociallogin.account.provider == 'google':
        data = sociallogin.account.extra_data
        user.full_name = data.get('name', '')
        user.is_active = True  # Make sure user is active
        user.save()


# Automatically Create a Wallet When User Registers

@receiver(post_save, sender=CustomUser)
def create_user_wallet(sender, instance, created, **kwargs):
    if created:
        Wallet.objects.create(user=instance)