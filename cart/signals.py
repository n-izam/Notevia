from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from adminpanel.models import Product, Variant, Category
from .models import CartItem








@receiver(post_save, sender=Product)
def update_cart_items_on_product_list_change(sender, instance, **kwargs):
    """
    Automatically activate or deactivate cart items
    based on product listing status.
    """
    # Only proceed if product already exists (not newly created)
    if not instance.pk:
        return

    # Update all related cart items based on the product's listing status
    if instance.is_listed:

        CartItem.objects.filter(product=instance, product__category__is_listed=True, is_active=False).update(is_active=instance.is_listed)
    else:
        CartItem.objects.filter(product=instance, product__category__is_listed=True, is_active=True).update(is_active=instance.is_listed)




@receiver(post_save, sender=Category)
def update_cart_items_on_category_list_change(sender, instance, **kwargs):
    # Find products under this category
    products = instance.product_set.all()
    # Update cart items based on category listing
    if instance.is_listed:
        for item in CartItem.objects.filter(product__in=products, is_active=False):
            CartItem.objects.filter(product=item.product, product__is_listed=True, is_active=False).update(is_active=instance.is_listed)
    else:
        for item in CartItem.objects.filter(product__in=products, is_active=True):
            CartItem.objects.filter(product=item.product, product__is_listed=True, is_active=True).update(is_active=instance.is_listed)

    

