from django.db import models
from django.conf import settings
from adminpanel.models import Product, Variant
from django.db.models import UniqueConstraint
import uuid
from django.utils import timezone
from decimal import Decimal
from orders.models import Order

# Create your models here.

class Cart(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='cart'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # without discount just product price sum with quantity
    @property
    def total_price(self):
        items_total_price = sum(item.subtotal() for item in self.items.filter(is_active=True, variant__is_listed=True)) # before here get all price from cart also calculating inactive products .all()
        return items_total_price
    @property
    def total_quantity(self):
        items_total_quantity = sum(item.quantity for item in self.items.filter(is_active=True, variant__is_listed=True))
        return float(items_total_quantity)
    
    # after add discount 
    @property
    def main_total_price(self):
        items_total_price = sum(item.after_subtotal() for item in self.items.filter(is_active=True, variant__is_listed=True))
        return items_total_price
    
    # over all product discount
    @property
    def deduct_amount(self):
        items_total_price = sum(item.discount_subtotal_amount() for item in self.items.filter(is_active=True, variant__is_listed=True))
        return items_total_price
    
    # over all amount need to implement coupen also
    @property
    def over_all_amount(self):
        final = self.main_total_price + self.tax_amount()
        return final
    
    def tax_amount(self):
        tax = 5
        total_tax_amount =self.main_total_price*tax/100
        return total_tax_amount
    
    def final_tax_with_coupon(self, coupon_discount):
        tax = 5
        final_coupon = self.main_total_price - coupon_discount
        toatal_tax = final_coupon*tax/100
        return round(toatal_tax, 2)
    
    def over_all_amount_coupon(self, coupon_discount):
        tax = 5
        final_coupon = self.main_total_price - coupon_discount
        toatal_with_tax = final_coupon + (final_coupon*tax/100)
        return round(toatal_with_tax, 2)

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

    #   price with quantity
    def subtotal(self):
        price = self.variant.price
        return price * self.quantity
    
    #  discount applied price with quantity
    def after_subtotal(self):
        price = self.variant.final_price
        return price * self.quantity
    
    # discount amount with quantity
    def discount_subtotal_amount(self):
        price = self.variant.discount_price
        return price * self.quantity


    
    @property
    def main_subtotal(self):
        price = self.variant.price
        return price * self.quantity
    
    @property
    def after_discount_subtotal(self):
        price = self.variant.final_price
        return price * self.quantity
    
    @property
    def discount_subtotal(self):
        price = self.variant.discount_price
        return price * self.quantity
    
    
    

    

    def __str__(self):
        if self.variant:
            return f"{self.product.name} ({self.variant.name}) x {self.quantity}"
        return f"{self.product.name} x {self.quantity}"
    

#  Wallet implementation in our project

class Wallet(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='wallets'
    )
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.user.full_name}'s Wallet - ₹{self.balance}"
    
    def credit(self, amount, message="Amount credited"):
        """Add money to wallet and record transaction."""
        self.balance += amount
        self.save()
        transaction = WalletTransaction.objects.create(
            wallet=self,
            amount=amount,
            transaction_type="Credit",
            message=message
        )
        return transaction

    def debit(self, amount, message="Amount debited"):
        """Deduct money from wallet and record transaction."""
        if self.balance < amount:
            raise ValueError("Insufficient balance")
        self.balance -= amount
        self.save()
        transaction = WalletTransaction.objects.create(
            wallet=self,
            amount=amount,
            transaction_type="Debit",
            message=message
        )
        return transaction
    
    def set_wallet_amount(self, amount):
        if self.balance < amount:
            raise ValueError("Insufficient balance")
        self.balance -= amount
        self.save()
        return self.balance

def generate_transaction_id():
    return f"TXN-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"
    
class WalletTransaction(models.Model):

    TRANSACTION_TYPES = (
        ('Credit', 'Credit'),
        ('Debit', 'Debit'),
    )

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    transaction_id = models.CharField(max_length=30, default=generate_transaction_id, unique=True, editable=False)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    message = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True, related_name='transaction_order')

    razorpay_order_id = models.CharField(max_length=255, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=255, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.transaction_type} ₹{self.amount} - {self.message} ({self.transaction_id})"