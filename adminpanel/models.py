from django.db import models
from cloudinary.models import CloudinaryField
from django.db.models import Min
from django.db.models import UniqueConstraint

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

    # @property
    # def is_active(self):
    #     from django.utils import timezone
    #     today = timezone.now().date()
    #     return self.is_listed and self.start_date <= today <= self.end_date

    def __str__(self):
        return f"{self.title} ({self.offer_percent}%)"
    

# Category model

class Category(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    image = CloudinaryField(
        'image', folder='category/',
        blank=True,
        null=True
    )
    offer = models.ForeignKey(
        Offer, on_delete=models.SET_NULL, null=True, blank=True, related_name="categories"
    ) 
    is_listed = models.BooleanField(default=True)
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
    offer = models.ForeignKey(Offer, on_delete=models.SET_NULL, null=True, blank=True, related_name="products") 
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE)
    base_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    is_listed = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            UniqueConstraint(fields=['name', 'brand', 'category'], name='unique_product_per_brand_category')
        ]

    @property
    def calc_base_price(self):

        highest_stock_variant = self.variants.order_by('-stock').first()
        return highest_stock_variant.price if highest_stock_variant else None
    
    def save(self, *args, **kwargs):
        """
        Override save() to automatically update base_price.
        """
        if self.pk:
            self.base_price = self.calc_base_price  # 👈 updates before saving
        super().save(*args, **kwargs)
    
    @property
    def high_price(self):

        highest_price_variant = self.variants.order_by('-price').first()
        return highest_price_variant.price if highest_price_variant else None
    

    @property
    def main_image(self):
        return self.images.filter(is_main=True).first() or self.images.first()
    @property
    def max_stock_variant(self):
        return self.variants.all().order_by('-stock').first()

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
        price = self.price
        discounts = []

        if self.discount:
            discounts.append(self.discount)
        if self.product.offer:
            discounts.append(self.product.offer.offer_percent)
        if self.product.category and self.product.category.offer:
            discounts.append(self.product.category.offer.offer_percent)

        if discounts:
            max_discount = max(discounts)
            price -= price * (max_discount / 100)

        return round(price, 2)
    
    @property
    def discount_price(self):
        price = self.price
        discounts = []

        if self.discount:
            discounts.append(self.discount)
        if self.product.offer:
            discounts.append(self.product.offer.offer_percent)
        if self.product.category and self.product.category.offer:
            discounts.append(self.product.category.offer.offer_percent)

        if discounts:
            max_discount = max(discounts)
            price = price * (max_discount / 100)
        else:
            price = 0.00

        return round(price, 2) if price is not None else 0
    
    @property
    def discount_percent(self):
        
        discounts = []

        if self.discount:
            discounts.append(float(self.discount))
        if self.product.offer:
            discounts.append(float(self.product.offer.offer_percent))
        if self.product.category and self.product.category.offer:
            discounts.append(float(self.product.category.offer.offer_percent))

        if discounts:
            max_discount = max(discounts)
        else:
            max_discount = None
            

        return round(max_discount, 2) if max_discount is not None else 0
    
    @property
    def main_offer(self):
        # Determine the best offer (excluding the variant's own discount)
        best_offer = None
        best_percent = 0
        
        if self.product.offer:
            product_offer_percent = float(self.product.offer.offer_percent)
            if product_offer_percent > best_percent:
                best_percent = product_offer_percent
                best_offer = self.product.offer

        if self.product.category and self.product.category.offer:
            category_offer_percent = float(self.product.category.offer.offer_percent)
            if category_offer_percent > best_percent:
                best_percent = category_offer_percent
                best_offer = self.product.category.offer

        return best_offer
    
    def save(self, *args, **kwargs):
        """
        After saving a variant, update its product's base price.
        """
        super().save(*args, **kwargs)
        # Update product base price after variant change
        self.product.save()

    # @property
    # def final_price(self):
    #     """
    #     Calculates final price after discount and offer.
    #     Priority: variant.discount > product.offer > category.offer
    #     """
    #     price = float(self.price)
    #     discount = float(self.discount or 0)

    #     # Product level offer
    #     if self.product.offer:
    #         discount = max(discount, float(self.product.offer.offer_percent))

    #     # Category level offer
    #     if self.product.category and self.product.category.offer:
    #         discount = max(discount, float(self.product.category.offer.offer_percent))

    #     # Apply discount
    #     final_price = price - (price * discount / 100)
    #     return round(final_price, 2)
    
    

    def __str__(self):
        return self.name