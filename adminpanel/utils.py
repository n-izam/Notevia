
from .models import Product, Variant, Category
from cart.models import Cart, CartItem


def cart_update(variant):

    if variant.is_listed:
        if Variant.objects.filter(id=variant.id).exists():

            CartItem.objects.filter(variant=variant, variant__product__is_listed=True, variant__product__category__is_listed=True, is_active=False).update(is_active=variant.is_listed)

        print(f"the variant is {variant} is listed {variant.is_listed}")
    else:
        if Variant.objects.filter(id=variant.id).exists():
            CartItem.objects.filter(variant=variant, variant__product__is_listed=True, variant__product__category__is_listed=True, is_active=True).update(is_active=variant.is_listed)
            print(f"the variant is {variant} is listed {variant.is_listed}")