from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from adminpanel.models import Product, Variant, Category
from .models import CartItem






# @receiver(post_save, sender=Product)
# def remove_unlisted_or_deleted_products(sender, instance, **kwargs):
#     """
#     Automatically remove cart items for products
#     that are unlisted or marked as deleted.
#     """
#     if not instance.is_deleted or instance.is_listed:
#         CartItem.objects.filter(product=instance).update(is_active=True)

#     if not instance.is_listed or instance.is_deleted:
#         # CartItem.objects.filter(product=instance).delete()
#         CartItem.objects.filter(product=instance).update(is_active=False)


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
    CartItem.objects.filter(product=instance).update(is_active=instance.is_listed)

# ----------------------------------------
# When a variant is unlisted
# ----------------------------------------
# @receiver(post_save, sender=Variant)
# def remove_unlisted_variants(sender, instance, **kwargs):
#     """
#     Automatically remove cart items for unlisted variants.
#     """
#     
#     if instance.is_listed:
#         CartItem.objects.filter(product=instance.product, variant=instance, is_active=False).update(is_active=instance.is_listed)


#     else:
        
#         CartItem.objects.filter(product=instance.product, variant=instance, is_active=True).update(is_active=instance.is_listed)


# @receiver(pre_save, sender=Variant)
# def handle_variant_unlisting(sender, instance, **kwargs):
#     if instance.pk:  # Only for existing variants (updates, not creates)
#         try:
#             old_variant = Variant.objects.get(pk=instance.pk)
#             if old_variant.is_listed and not instance.is_listed:
#                 # Variant was listed but is now unlisted: inactivate related cart items
#                 CartItem.objects.filter(variant=instance).update(is_active=False)
#         except Variant.DoesNotExist:
#             pass  # Shouldn't happen, but safe fallback

# ----------------------------------------
# When a category is unlisted
# ----------------------------------------
# @receiver(post_save, sender=Category)
# def remove_unlisted_variants(sender, instance, **kwargs):
#     """
#     Automatically remove cart items for unlisted category.
#     """

#     if instance.is_listed:
#         CartItem.objects.filter(product__category=instance).update(is_active=True)


#     if not instance.is_listed:
#         CartItem.objects.filter(product__category=instance).update(is_active=False)

# @receiver(post_save, sender=Variant)
# def sync_variant_listing_to_cart_items(sender, instance, **kwargs):
#     """
#     Keep CartItem.is_active in sync with Variant.is_listed
#     - Variant listed  → activate all its cart items
#     - Variant unlisted → deactivate all its cart items
#     """
#     if instance.is_listed:
#         # Activate any that were inactive (e.g. previously unlisted or manually toggled)
#         CartItem.objects.filter(
#             variant=instance, product=instance.product,
#             is_active=False
#         ).update(is_active=instance.is_listed)
#     else:
#         # Deactivate any that are still active
#         CartItem.objects.filter(
#             variant=instance, product=instance.product,
#             is_active=True
#         ).update(is_active=instance.is_listed)

@receiver(post_save, sender=Category)
def update_cart_items_on_category_list_change(sender, instance, **kwargs):
    # Find products under this category
    products = instance.product_set.all()
    # Update cart items based on category listing
    if instance.is_listed:
        CartItem.objects.filter(product__in=products, is_active=False).update(is_active=instance.is_listed)
    else:
        CartItem.objects.filter(product__in=products, is_active=True).update(is_active=instance.is_listed)


# @receiver(post_save, sender=Variant)
# def remove_unlisted_variants(sender, instance, **kwargs):
#     """
#     Automatically enable/disable cart items when variant is listed/unlisted.
#     """
#     def update_cart_items():
#         if instance.is_listed:
#             CartItem.objects.filter(variant=instance).update(is_active=True)
#         else:
#             CartItem.objects.filter(variant=instance).update(is_active=False)

#     transaction.on_commit(update_cart_items)

# @receiver(post_save, sender=Variant)
# def update_cart_items_on_variant_change(sender, instance, **kwargs):
#     """
#     When a variant under a product is unlisted, or listed again,
#     only affect that exact variant under that specific product.
#     """
#     # Variant active only if listed, product listed, category listed, and has stock
#     variant_active = (
#         instance.is_listed
#         and instance.product.is_listed
#         and instance.product.category.is_listed
#         and instance.stock > 0
#     )

#     # Update matching cart items for this exact variant under this product
#     CartItem.objects.filter(
#         product=instance.product,
#         variant=instance
#     ).update(is_active=variant_active)