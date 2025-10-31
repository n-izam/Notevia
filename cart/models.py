from django.db import models
from django.conf import settings
from adminpanel.models import Product, Variant
from django.db.models import UniqueConstraint

# Create your models here.

class Cart(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='cart'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def total_price(self):
        items_total_price = sum(item.subtotal() for item in self.items.all())
        return float(items_total_price)
    @property
    def total_quantity(self):
        items_total_quantity = sum(item.quantity for item in self.items.all())
        return float(items_total_quantity)

    def __str__(self):
        return f"Cart {{self.user}}"
    

class CartItem(models.Model):
    cart = models.ForeignKey(
        Cart, on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variant = models.ForeignKey(Variant, on_delete=models.SET_NULL, null=True, blank=True)

    quantity = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            UniqueConstraint(fields=['cart', 'product', 'variant'], name='unique_product_per_cart_variant')
        ]

    def subtotal(self):
        price = self.variant.price
        return price * self.quantity
    
    @property
    def main_subtotal(self):
        price = float(self.variant.price)
        return price * float(self.quantity)
    

    def __str__(self):
        if self.variant:
            return f"{self.product.name} ({self.variant.name}) x {self.quantity}"
        return f"{self.product.name} x {self.quantity}"