from django.db.models.signals import post_save
from django.dispatch import receiver

from adminpanel.models import Product, Variant, Category
from .models import CartItem






@receiver(post_save, sender=Product)
def remove_unlisted_or_deleted_products(sender, instance, **kwargs):
    """
    Automatically remove cart items for products
    that are unlisted or marked as deleted.
    """
    if not instance.is_deleted or instance.is_listed:
        CartItem.objects.filter(product=instance).update(is_active=True)

    if not instance.is_listed or instance.is_deleted:
        # CartItem.objects.filter(product=instance).delete()
        CartItem.objects.filter(product=instance).update(is_active=False)


# ----------------------------------------
# When a variant is unlisted
# ----------------------------------------
@receiver(post_save, sender=Variant)
def remove_unlisted_variants(sender, instance, **kwargs):
    """
    Automatically remove cart items for unlisted variants.
    """

    if instance.is_listed:
        CartItem.objects.filter(variant=instance).update(is_active=True)


    if not instance.is_listed:
        CartItem.objects.filter(variant=instance).update(is_active=False)



# ----------------------------------------
# When a category is unlisted
# ----------------------------------------
@receiver(post_save, sender=Category)
def remove_unlisted_variants(sender, instance, **kwargs):
    """
    Automatically remove cart items for unlisted category.
    """

    if instance.is_listed:
        CartItem.objects.filter(product__category=instance).update(is_active=True)


    if not instance.is_listed:
        CartItem.objects.filter(product__category=instance).update(is_active=False)


