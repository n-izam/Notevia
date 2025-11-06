from django.db import models
from django.conf import settings
from adminpanel.models import Product, Variant
from accounts.models import Address
from datetime import timedelta
from django.utils import timezone

# Create your models here.


class Order(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('COD', 'Cash on Delivery'),
        ('ONLINE', 'Online Payment')
    ]

    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Processing', 'Processing'),
        ('Shipped', 'Shipped'),
        ('Delivered', 'Delivered'),
        ('Cancelled', 'Cancelled'),
        ('Payment Failed', 'Payment Failed'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    order_id = models.CharField(max_length=50, unique=True)
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHOD_CHOICES, default='CDO')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    cancel_reason = models.TextField(blank=True, null=True)
    is_paid = models.BooleanField(default=False)


    razorpay_order_id = models.CharField(max_length=255, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=255, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Order {self.order_id} - {self.user.full_name}"
    @property
    def over_all_amount(self):
        tax = 5
        total_main_amount = self.total_amount() + (self.total_items_amount()*tax/100)
        return total_main_amount
    
    def tax_amount(self):
        tax = 5
        total_tax_amount =self.total_items_amount()*tax/100
        return total_tax_amount
    
    #  without discount and tax
    def total_items_amount(self):
        return self.total_amount() + self.total_discount()

    #  not applied tax but with discount
    def total_amount(self):
        return sum(item.total_price() for item in self.items.all())
    
    def total_quantity(self):
        return sum(item.quantity for item in self.items.all())
    
    def total_discount(self):
        return sum(item.sub_discount() for item in self.items.all())
    
    
    @property
    def processing_date(self):
        return self.created_at + timedelta(days = 2)
    
    @property
    def shipped_date(self):
        return self.created_at + timedelta(days = 4)
    
    @property
    def delivery_date(self):
        return self.created_at + timedelta(days = 6)
    

    

    # 👇 Helper method to get first product image
    def get_first_product_image(self):
        first_item = self.items.first()
        if first_item and first_item.product:
            product = first_item.product

            image = product.images.filter(is_main=True).first() or product.images.first()
            if image:
                return image.image.url
            return None
    
    

class OrderAddress(models.Model):

    ADDRESS_TYPES = [
        ('home', 'Home'),
        ('work', 'Work'),
        ('other', 'Other'),
    ]
    order = models.OneToOneField(
        Order, 
        on_delete=models.CASCADE, 
        related_name='orders_address'
    )
    full_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone_no = models.CharField(max_length=10)
    address = models.TextField()
    district = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    pin_code = models.CharField(max_length=10)
    address_type = models.CharField(max_length=100, choices=ADDRESS_TYPES, default='home')
    

    def __str__(self):
        return f"{self.full_name} - {self.address_type}"
    
    
    

class OrderItem(models.Model):

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    variant = models.ForeignKey(Variant, on_delete=models.SET_NULL, null=True)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    is_cancel = models.BooleanField(default=False)

    def total_price(self):
        return self.price * self.quantity
    
    def sub_discount(self):
        return self.discount_price * self.quantity
    
    def sub_offer(self):
        return self.discount_percent * self.quantity
    
    @property
    def real_price(self):
        return float(self.price + self.discount_price)
    @property
    def sub_real_price(self):
        return float(self.real_price*self.quantity)
    
    
    
    def __str__(self):
        return f"{self.product.name} (x{self.quantity})"
    


class ReturnRequest(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    ]

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='return_requests')
    
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)