from django.db import models
from django.conf import settings
import random
import string
from adminpanel.models import Product, Variant


User = settings.AUTH_USER_MODEL

# Create your models here.
#model for product

def generate_referral_code(name):
    """
    Generate a referral code using the username and random characters.
    Example: NISAM-7X9A@2
    """
    symbols = "@#$%&"
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits + symbols, k=5))
    base = name.upper()[:5]  # first 5 letters of username
    return f"{base}-{random_part}"

class Referral(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='referral')
    code = models.CharField(max_length=20, unique=True, blank=True)
    referred_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='referrals_made'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.full_name} - {self.code}"

    def save(self, *args, **kwargs):
        if not self.code:
            code = generate_referral_code(self.user.full_name)
            # ensure uniqueness
            while Referral.objects.filter(code=code).exists():
                code = generate_referral_code(self.user.full_name)
            self.code = code
        super().save(*args, **kwargs)



class Wishlist(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="wishlist"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Wishlist"


class WishlistItem(models.Model):
    wishlist = models.ForeignKey(
        Wishlist,
        on_delete=models.CASCADE,
        related_name="items"
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variant = models.ForeignKey(Variant, on_delete=models.SET_NULL, null=True, blank=True)

    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['wishlist', 'product'],
                name='unique_product_variant_per_wishlist'
            )
        ]

    def __str__(self):
        return f"{self.product.name} ({self.variant.name if self.variant else 'No variant'})"