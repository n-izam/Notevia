from django.db import models
from django.utils import timezone
from django.conf import settings
from django.db.models import UniqueConstraint
from decimal import Decimal

# Create your models here.


class Coupon(models.Model):

    code = models.CharField(max_length=50, unique=True)
    usage_limit = models.PositiveIntegerField(default=0, help_text="Maximum usage count")
    max_redeemable_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="max discount amount")
    min_purchase_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Minimum purchase to apply coupon")
    discount_percentage = models.PositiveIntegerField(help_text="Discount percentage ")
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    usage_count = models.PositiveIntegerField(default=0, editable=False)

    def __str__(self):
        return self.code
    
    def is_valid(self):
        now = timezone.now()
        return self.is_active and self.valid_from <= now <= self.valid_to
    
    def increment_usage(self, user):
        """Call this when coupon is used successfully."""
        
        self.usage_count += 1
        self.save()

        usage, created = CouponUsage.objects.get_or_create(coupon=self, user=user)
        usage.increment_usage()

    def decrement_usage(self, user):
        """Call this when coupon is used successfully."""
        
        self.usage_count -= 1
        self.save()

        usage, created = CouponUsage.objects.get_or_create(coupon=self, user=user)
        usage.decrement_usage()

    # calculating discount amount
    def apply_discount(self, order_total):
        
        if order_total < self.min_purchase_amount:
            return 0  # Not eligible
        if not self.is_valid():
            return 0

        discount = (order_total * self.discount_percentage) / 100
        if self.max_redeemable_price > 0:
            discount = min(discount, self.max_redeemable_price)
        return discount
    
    #  this for normal use
    def apply_discount_access(self, order_total):
        
        if order_total < self.min_purchase_amount:
            return 0  # Not eligible
        # if not self.is_valid():
        #     return 0

        discount = (order_total * self.discount_percentage) / 100
        if self.max_redeemable_price > 0:
            discount = min(discount, self.max_redeemable_price)
        return discount
    
class CouponUsage(models.Model):
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name='usages')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='coupon_usages')
    usage_count = models.PositiveIntegerField(default=0)
    last_used = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            UniqueConstraint(fields=['coupon', 'user'], name='unique_coupon_per_user')
        ]

    def increment_usage(self):
        self.usage_count += 1
        self.last_used = timezone.now()
        self.save()

    def decrement_usage(self):
        self.usage_count -= 1
        self.last_used = timezone.now()
        self.save()

    def __str__(self):
        return f"{self.user} used {self.coupon.code} {self.usage_count} times"