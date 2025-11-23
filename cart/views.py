from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.urls import reverse
from adminpanel.models import Product, Variant
from .models import Cart, CartItem, Wallet, WalletTransaction
from django.db import models
from accounts.utils import success_notify, info_notify, error_notify, profile
from decimal import Decimal

from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache

import razorpay
from django.conf import settings

import hmac, hashlib
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q

# Create your views here.

client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
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
                product__category__is_listed=True
                # is_active=True
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


@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
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
                info_notify(request, f"this product {product.name} with same variant  is already in cart")
                return redirect('shop_productdetail', product_id=product.id)
        else:
            if CartItem.objects.filter(cart=cart, product=product).exists():
                info_notify(request, f"this product {product.name} is already in cart")
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
            success_notify(request, f"product {product.name} {quantity} quantity is successfully add to cart")

        return redirect('shop_productdetail', product_id=product.id)
    
@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class CartQuantityUpdateView(View):

    def post(self, request):

        cart_item_id = request.POST.get('cart_product')
        quantity = request.POST.get('quantity')

        print('cart item id is :', cart_item_id, 'quantity is:', quantity)

        if not CartItem.objects.filter(id=cart_item_id ,is_active=True).exists():
            error_notify(request, "the item is not exists in cart")
            return redirect('cart_page')
        
        cart_item = get_object_or_404(CartItem, id=cart_item_id)

        # if not int(quantity) <= cart_item.variant.stock:
        #     error_notify(request, f"stock is only for {{quantity-1}}")
        #     return redirect('cart_page')
        
        if int(quantity) > cart_item.variant.stock:
            info_notify(request, f"maximum stock reached")
            return redirect('cart_page')
            
        
        cart_item.quantity = quantity
        cart_item.save()
        
        success_notify(request, "Cart stock quantity updated")
        return redirect('cart_page')
    
@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
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
    

#  wallet integration

@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class UserWalletView(View):

    def get(self, request):
        if request.session.get('wallet_payment_confirm'):
            transaction_id = request.session.get('session_transaction')
            session_transaction = get_object_or_404(WalletTransaction, id=transaction_id)
            session_transaction.delete()
            request.session.pop('wallet_payment_confirm', None)
            del request.session['session_transaction']
            error_notify(request, 'Try again, payment gateway failed..!')
            return redirect('wallet')

        page = request.GET.get('page', 1)
        wallet, create = Wallet.objects.get_or_create(user=request.user)
        transactions = wallet.transactions.all().order_by('-created_at')

        paginator = Paginator(transactions, 6)
        try:
            paginated_orders = paginator.page(page)
        except PageNotAnInteger:
            paginated_orders = paginator.page(1)
        except EmptyPage:
            paginated_orders = paginator.page(paginator.num_pages)

        user_profile = profile(request)
        context = {
            "user_id": request.user.id,
            "user_profile": user_profile,
            "wallet": wallet,
            "transactions": paginated_orders,
            "paginator" : paginator,
            "page_obj" : paginated_orders,



        }

        return render(request, 'cart/main_wallet.html', context)
    
    def post(self, request):
        amount = request.POST.get('money')
        print('amount need to add wallet:', amount)
        wallet = get_object_or_404(Wallet, user=request.user)
        if float(amount)<=0:
            error_notify(request, 'must enter the amount greater than zero')
            return redirect('wallet')
        transaction = wallet.credit(Decimal(amount), message="amount added to wallet")
        print('transaction', transaction.id)

        amount_in_paise = int(transaction.amount * 100)
        razorpay_transaction = client.order.create({
                "amount": amount_in_paise,
                "currency": "INR",
                "receipt": transaction.transaction_id,
            })
        transaction.razorpay_order_id = razorpay_transaction['id']
        transaction.save()

        request.session["wallet_payment_confirm"] = True
        request.session['session_transaction'] = transaction.id

        pay_url = f'{reverse("razorpay_callback_wallet")}?transaction={transaction.id}'
        return redirect(pay_url)



@csrf_exempt
def razorpay_callback_wallet(request):

    if request.method == 'POST':

        payment_id = request.POST.get('razorpay_payment_id')
        order_id   = request.POST.get('razorpay_order_id')
        signature  = request.POST.get('razorpay_signature')
        transaction_identity = request.POST.get('order_idetity')

        print('razorpay_payment_id', order_id," - ", transaction_identity)
        print('razorpay_payment_id', payment_id)

        try:
            transaction = WalletTransaction.objects.get(razorpay_order_id=order_id)
        except WalletTransaction.DoesNotExist:
            return redirect('wallet')
        
        # Verify signature
        generated_signature = hmac.new(
            settings.RAZORPAY_KEY_SECRET.encode(),
            f"{order_id}|{payment_id}".encode(),
            hashlib.sha256
        ).hexdigest()

        if generated_signature == signature:
            transaction.razorpay_payment_id = payment_id
            transaction.razorpay_signature = signature
            transaction.save()

            return redirect('wallet_payment_success', trxct_id=transaction.id)
        else:
            transaction.delete()

            return redirect('cancel_return_wallet', trxct_id=transaction.id)
        

        pass
    else:
        if not request.session.get('wallet_payment_confirm'):
            return redirect('wallet')
        transaction_id = request.GET.get('transaction')
        print('transaction id:', transaction_id)
        transaction = get_object_or_404(WalletTransaction, id=transaction_id)
        amount_in_paise = int(transaction.amount * 100)
        print(amount_in_paise)
        context = {
            "transaction": transaction,
            "razorpay_key_id": settings.RAZORPAY_KEY_ID,
            "amount": amount_in_paise,
            'currency': 'INR',
            'real_amount': transaction.amount,
            'callback_url': request.build_absolute_uri(reverse('razorpay_callback_wallet')),
        }
        return render(request, 'cart/razorpay_checkout_wallet.html', context)
    


@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class WalletPaymentSuccessView(View):
    def get(self, request, trxct_id):

        if request.session.get('wallet_payment_confirm'):
            request.session.pop('wallet_payment_confirm', None)
            del request.session['session_transaction']

        transaction = get_object_or_404(WalletTransaction, id=trxct_id)
        success_notify(request, "payment success, added money to your wallet")
        return redirect('wallet')

@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class PaymentCancelReturnWalletView(View):
    def get(self, request, trxct_id):

        if request.session.get('wallet_payment_confirm'):
            request.session.pop('wallet_payment_confirm', None)
            del request.session['session_transaction']

        transaction = get_object_or_404(WalletTransaction, id=trxct_id)
        wallet = transaction.wallet
        wallet.balance -= transaction.amount
        wallet.save()
        transaction.delete()
        error_notify(request, "cancelled payment, try again")
        return redirect('wallet')

    
@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class WalletPaymentFailedView(View):
    def get(self, request, trxct_id):

        if request.session.get('wallet_payment_confirm'):
            request.session.pop('wallet_payment_confirm', None)
            del request.session['session_transaction']
            
        transaction = get_object_or_404(WalletTransaction, id=trxct_id)
        wallet = transaction.wallet
        wallet.balance -= transaction.amount
        wallet.save()
        transaction.delete()
        error_notify(request, "payment failed, try again")
        return redirect('wallet')


class AdminOverAllWalletView(View):

    def get(self, request):
        page = request.GET.get('page', 1)
        query = request.GET.get('q')
        types = request.GET.get('type')
        transactions = WalletTransaction.objects.all().order_by('-created_at')
        if query:
            transactions = transactions.filter(Q(transaction_id__icontains=query)|Q(wallet__user__full_name__icontains=query))
        if request.GET.get('type'):
            types = request.GET.get('type')
            transactions = transactions.filter(transaction_type=types)

        paginator = Paginator(transactions, 6)
        try:
            paginated_orders = paginator.page(page)
        except PageNotAnInteger:
            paginated_orders = paginator.page(1)
        except EmptyPage:
            paginated_orders = paginator.page(paginator.num_pages)

        context = {
            "user_id": request.user.id,
            "transaction_type": WalletTransaction.TRANSACTION_TYPES,
            "transactions": paginated_orders,
            "paginator" : paginator,
            "page_obj" : paginated_orders,
            "query": query,
            "types": types,


        }

        return render(request, 'cart/admin_wallet.html', context)