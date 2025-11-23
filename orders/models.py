from django.db import models
from django.conf import settings
from adminpanel.models import Product, Variant
from accounts.models import Address
from datetime import timedelta
from django.utils import timezone
from offers.models import Coupon

# Create your models here.


class Order(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('COD', 'Cash on Delivery'),
        ('ONLINE', 'Online Payment'),
        ('Wallet', 'Wallet'),
    ]

    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Processing', 'Processing'),
        ('Shipped', 'Shipped'),
        ('Delivered', 'Delivered'),
        ('Cancelled', 'Cancelled'),
        ('Payment Failed', 'Payment Failed'),
        ('Returned', 'Returned'),
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

    coupon_code = models.CharField(max_length=50, blank=True, null=True)
    coupon_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    coupon_amount_static = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)


    def __str__(self):
        return f"Order {self.order_id} - {self.user.full_name}"
    @property
    def over_all_amount(self):
        tax = 5
        total_main_amount = self.total_amount()
        if self.coupon_amount:
            total_main_amount = self.total_amount() - self.coupon_amount
        total_main_amount = total_main_amount + self.tax_amount()
        return round(total_main_amount, 2)
    
    def tax_amount(self):

        tax = 5
        total_main_amount = self.total_amount()
        if self.coupon_amount:
            total_main_amount = self.total_amount() - self.coupon_amount
        total_tax_amount = total_main_amount*tax/100
        return round(total_tax_amount, 2)
    
    # the price with coupon without tax
    def total_amount_with_coupon(self):
        total_main_amount = self.total_amount()
        if self.coupon_amount:
            total_main_amount = self.total_amount() - self.coupon_amount
        return total_main_amount

    
    #  without discount and tax
    def total_items_amount(self):
        return self.total_amount() + self.total_discount()

    #  not applied tax but with discount if coupon is applied
    def total_amount(self):
        total = sum(item.total_price() for item in self.items.filter(is_cancel=False))
        
        return round(total, 2)
    
    def total_quantity(self):
        return sum(item.quantity for item in self.items.filter(is_cancel=False))
    
    def total_discount(self):
        return sum(item.sub_discount() for item in self.items.filter(is_cancel=False))


#  get order amount if it cancelld

    @property
    def over_all_amount_all(self):
        tax = 5
        total_main_amount = self.total_amount_all()
        if self.coupon_amount_static:
            total_main_amount = self.total_amount_all() - self.coupon_amount_static
        total_main_amount = total_main_amount + self.tax_amount_all()
        return round(total_main_amount, 2)

    def tax_amount_all(self):

        tax = 5
        total_main_amount = self.total_amount_all()
        if self.coupon_amount_static:
            total_main_amount = self.total_amount_all() - self.coupon_amount_static
        total_tax_amount = total_main_amount*tax/100
        return round(total_tax_amount, 2)
    
    # the price with coupon without tax
    def total_amount_with_coupon_all(self):
        total_main_amount = self.total_amount_all()
        if self.coupon_amount_static:
            total_main_amount = self.total_amount_all() - self.coupon_amount_static
        return total_main_amount


    #  without discount and tax
    def total_items_amount_all(self):
        return self.total_amount_all() + self.total_discount_all()
    
    #  not applied tax but with discount if coupon is applied
    def total_amount_all(self):
        total = sum(item.total_price() for item in self.items.all())
        
        return round(total, 2)
    
    def total_quantity_all(self):
        return sum(item.quantity for item in self.items.all())
    
    def total_discount_all(self):
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

    # price with discount and quantity
    def total_price(self):
        return self.price * self.quantity
    
    # deducted price from product
    def sub_discount(self):
        return self.discount_price * self.quantity
    
    def sub_offer(self):
        return self.discount_percent * self.quantity
    
    # real price for i tem without discount
    @property
    def real_price(self):
        return float(self.price + self.discount_price)
    
    # real price(without discount) * quantity = sub real price
    @property
    def sub_real_price(self):
        return float(self.real_price*self.quantity)
    
    
    # coupon discount deduct amount for this product
    def coupon_discount(self):
        coupon_price = self.order.coupon_amount_static
        discount_price = self.total_price() / self.order.total_amount_all() * coupon_price
        return round(discount_price, 2)
    
    
    
    #  return price with tax
    def return_with_tax_price(self):
        tax_price = round((self.total_price()/self.order.total_amount_with_coupon_all()) * self.order.tax_amount_all(), 2)
        total_return = self.total_price()
        if self.order.coupon_amount:
            
            # coupon_price = round((self.total_price()/self.order.total_amount()) * self.order.coupon_amount, 2)
            tax_price = round(((self.total_price()-self.coupon_discount())/self.order.total_amount_with_coupon_all()) * self.order.tax_amount_all(), 2)
            
            print(f"order item {self.product.name} - {self.variant.name} coupon amount", self.coupon_discount())
            
            total_return = self.total_price() - self.coupon_discount()
            self.order.coupon_amount -= self.coupon_discount()
            self.order.save()
            print(f"order item {self.product.name} - {self.variant.name} total amount after coupon", total_return)
            print(f"tax amount of item {self.product.name} - {self.variant.name} after coupon", tax_price)

        
        print("order coupon amount", self.order.coupon_amount)
        print(f"order item {self.product.name} - {self.variant.name} total amount", total_return)

        print(f"tax amount of item {self.product.name} - {self.variant.name}", tax_price)

        return round(total_return + tax_price, 2)
        
    
    
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