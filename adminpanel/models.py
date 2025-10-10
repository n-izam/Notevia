from django.db import models
from cloudinary.models import CloudinaryField

# Create your models here.

# Offer model

class Offer(models.Model):
    title = models.CharField(max_length=255)
    offer_percent = models.DecimalField(max_digits=5, decimal_places=2) 
    about = models.TextField(blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    is_listed = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({self.offer_percent}%)"
    

# Category model

class Category(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    offer = models.ForeignKey(
        Offer, on_delete=models.SET_NULL, null=True, blank=True, related_name="categories"
    ) 
    is_list = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    
class Brand(models.Model):
    name = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Product(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    offer = models.ForeignKey(
        Offer, on_delete=models.SET_NULL, null=True, blank=True, related_name="products"
    ) 
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE)
    is_deleted = models.BooleanField(default=False)
    is_listed = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"product name is : {self.name}"

class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = CloudinaryField('image', folder='products/')
    is_main = models.BooleanField(default=False)

    def __str__(self):
        return f"the product image: {self.product}"

class Variant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    stock = models.PositiveIntegerField()
    is_listed = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def final_price(self):
        """
        Calculates final price after discount and offer.
        Priority: variant.discount > product.offer > category.offer
        """
        price = float(self.price)
        discount = float(self.discount or 0)

        # Product level offer
        if self.product.offer:
            discount = max(discount, float(self.product.offer.offer_percent))

        # Category level offer
        if self.product.category and self.product.category.offer:
            discount = max(discount, float(self.product.category.offer.offer_percent))

        # Apply discount
        final_price = price - (price * discount / 100)
        return round(final_price, 2)

    def __str__(self):
        return self.name