from allauth.account.signals import user_signed_up
from django.dispatch import receiver
from accounts.models import CustomUser, UserProfile
from cart.models import Wallet
from django.db.models.signals import post_save
from products.models import Referral, Wishlist
from django.conf import settings

User = settings.AUTH_USER_MODEL

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
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def create_user_referral(sender, instance, created, **kwargs):
    if created:
        Referral.objects.create(user=instance)
        Wishlist.objects.create(user=instance)