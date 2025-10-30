from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from adminpanel.models import Product, Variant
from .models import Cart, CartItem
from django.db import models
from accounts.utils import success_notify, info_notify, error_notify

# Create your views here.


class CartPageView(View):

    def get(self, request):

        cart, created = Cart.objects.get_or_create(user=request.user)
        
        # if not CartItem.objects.filter(cart=cart).exists():
        #     context = {
        #         "user_id": request.user.id
        #         }
        #     return render(request, 'cart/main_cart.html', context)
        
        cart_items = (
            cart.items.select_related('product', 'variant')
            .filter(
                product__is_listed=True,
                product__is_deleted=False,
                is_active=True
            )
            .filter(
                models.Q(variant__isnull=True) | models.Q(variant__is_listed=True)
            )
        )
        
        total_price = sum(item.subtotal() for item in cart_items)
        total_quantity = sum(item.quantity for item in cart_items)

        # print("cart items", cart_items)
        # print("total price", total_price)
        # print('total quantity', total_quantity)

        cartitem_with_image = []
        for cart_item in cart_items:
            main_image = cart_item.product.images.filter(is_main=True).first
            cartitem_with_image.append({
                "cart_item": cart_item,
                "main_image": main_image
            })
        
        # for item in cart_items:
        #     print("sub total", type(item.main_subtotal))
        #     print("variant final price", type(item.variant.final_price))
        
        print("cart total price", cart.total_price)

        
        
            





        context = {
            "user_id": request.user.id,
            "cart": cart,
            "cart_items": cart_items,
            "cartitem_with_image": cartitem_with_image,
            "total_price": total_price,
            "total_quantity": total_quantity,
        }

        return render(request, 'cart/main_cart.html', context)

class AddToCartFromDetailView(View):

    def post(self, request):

        main_get = request.POST.get('main')
        quantity = request.POST.get('quantity')
        product_id = request.POST.get('product')

        product = get_object_or_404(Product, id=product_id )
        variants = product.variants.filter(is_listed=True)

        if main_get:
            if Variant.objects.filter(product=product, name=main_get, is_listed=True).exists():
                main_variant = variants.get(name=main_get)
                # main_variant = Variant.objects.filter(product=product, name=main_get, is_listed=True) # when use this we can get queryset 


        print("main variant", main_get, "quantity", quantity, "product id", product_id, type(product_id))

        print("main product is:", product.name,"-", product.category, "product-", product, "main variant-", main_variant)

        cart, created = Cart.objects.get_or_create(user=request.user)

        if main_variant:
            if CartItem.objects.filter(cart=cart, product=product, variant=main_variant).exists():
                info_notify(request, "this product with same variant is already in cart")
                return redirect('shop_productdetail', product_id=product.id)
        else:
            if CartItem.objects.filter(cart=cart, product=product).exists():
                info_notify(request, "this product is already in cart")
                return redirect('shop_productdetail', product_id=product.id)


        if not created:
            if main_variant:
                cart_item = CartItem.objects.create(cart=cart, product=product, variant=main_variant, quantity=quantity)
            else:
                cart_item = CartItem.objects.create(cart=cart, product=product, quantity=quantity)
        else:
            if main_variant:
                cart_item = CartItem.objects.create(cart=cart, product=product, variant=main_variant, quantity=quantity)
            else:
                cart_item = CartItem.objects.create(cart=cart, product=product, quantity=quantity)

        
            
        if cart_item:
            success_notify(request, "successfully add to cart")

        return redirect('shop_productdetail', product_id=product.id)
    

class CartQuantityUpdateView(View):

    def post(self, request):

        cart_item_id = request.POST.get('cart_product')
        quantity = request.POST.get('quantity')

        print('cart item id is :', cart_item_id, 'quantity is:', quantity)

        if not CartItem.objects.filter(id=cart_item_id ,is_active=True).exists():
            error_notify(request, "the item is not exists in cart")
            return redirect('cart_page')
        
        cart_item = get_object_or_404(CartItem, id=cart_item_id)

        if not int(quantity) <= cart_item.variant.stock:
            error_notify(request, f"stock is only for {{quantity-1}}")
            return redirect('cart_page')
        
        if int(quantity) == cart_item.variant.stock:
            info_notify(request, f"maximum stock reached")
            
        
        cart_item.quantity = quantity
        cart_item.save()
        
        success_notify(request, "stock quantity updated")
        return redirect('cart_page')
    
class RemoveFromCartView(View):

    def get(self, request):
        cart_item_id = request.GET.get('remove_product')
        print("item is ", cart_item_id)

        if not CartItem.objects.filter(id=cart_item_id).exists():
            info_notify(request, "removing this item is not possible")
            return redirect('cart_page')
        
        caer_item = get_object_or_404(CartItem, id=cart_item_id).delete()

        success_notify(request, "Cart updated successfully")
        return redirect('cart_page')