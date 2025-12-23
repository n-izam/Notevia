from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.db import models
from accounts.models import Address, UserProfile, CustomUser
from adminpanel.models import Product, Variant
from cart.models import Cart, CartItem, Wallet, WalletTransaction
from orders.models import Order, OrderItem, OrderAddress, ReturnRequest, ReturnItemRequest
from django.urls import reverse
from accounts.utils import error_notify, info_notify, success_notify, warning_notify, profile, custom_page_range
from datetime import timedelta
from django.utils import timezone
from django.db.models import Q

import uuid
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import HttpResponse
from django.template.loader import render_to_string
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import inch
from io import BytesIO
from offers.models import Coupon, CouponUsage
import razorpay
from django.conf import settings

import hmac, hashlib
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
from decimal import Decimal

from django.core.mail import EmailMultiAlternatives
from accounts.forms import AddressForm

client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

# Create your views here.

@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class AddressSelectionView(View):

    def get(self, request):

        if request.session.get('selected_address'):
            request.session.pop('selected_address', None)

        if request.session.get('payment_confirm'):
            if request.session.get('session_order'):
                order_id = request.session.get('session_order')
                try:
                    session_order = Order.objects.get(id=order_id)
                except Order.DoesNotExist:
                    request.session.pop('payment_confirm', None)
                    del request.session['session_order']
                    return redirect('cart_page')
                # session_order = get_object_or_404(Order, id=order_id)
                if session_order.coupon_code:
                    used_coupon = get_object_or_404(Coupon, code=session_order.coupon_code)
                    update_usage = used_coupon.decrement_usage(request.user)
                for item in session_order.items.all():
                    item.variant.stock += item.quantity
                    item.variant.save()
                    
                session_order.items.all().delete()
                session_order.orders_address.delete()
                session_order.delete()
            request.session.pop('payment_confirm', None)
            del request.session['session_order']
            
            error_notify(request, 'Try again, payment gateway failed..!')
            return redirect('cart_page')

        addresses = Address.objects.filter(user=request.user).order_by('-is_default')
        cart = get_object_or_404(Cart, user=request.user)



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
        if not cart_items:
            return redirect('cart_page')
        
        for item in cart_items:
            if item.variant.stock < item.quantity:
                info_notify(request, f"cart item {item.product.name} haven't minmum stock for place the order")
                return redirect('cart_page')
        
        if cart_items.count() > 5:
            info_notify(request, f" A maximum of 5 item can be added to your one order. kindly remove item from cart or add to wishlist")
            return redirect('cart_page')

        cartitem_with_image = []
        for cart_item in cart_items:
            main_image = cart_item.product.images.filter(is_main=True).first()
            cartitem_with_image.append({
                "cart_item": cart_item,
                "main_image": main_image
            })

        context = {
            "user_id": request.user.id,
            "cart": cart,
            # "cart_items": cart_items,
            "cartitem_with_image": cartitem_with_image,
            "addresses": addresses,
            
        }

        return render(request, 'orders/address_select.html', context)
    
    def post(self, request):

        address_id = request.POST.get('address')
        
        request.session['selected_address'] = address_id

        return redirect('order_confirmation')
    
@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class ConfirmationCartView(View):

    def get(self, request):

        if request.session.get('payment_confirm'):
            if request.session.get('session_order'):
                order_id = request.session.get('session_order')
                
                try:
                    session_order = Order.objects.get(id=order_id)
                except Order.DoesNotExist:
                    request.session.pop('payment_confirm', None)
                    del request.session['session_order']
                    return redirect('cart_page')
                # session_order = get_object_or_404(Order, id=order_id)
                if session_order.coupon_code:
                    used_coupon = get_object_or_404(Coupon, code=session_order.coupon_code)
                    update_usage = used_coupon.decrement_usage(request.user)
                for item in session_order.items.all():
                    item.variant.stock += item.quantity
                    item.variant.save()
                    
                session_order.items.all().delete()
                session_order.orders_address.delete()
                session_order.delete()
            request.session.pop('payment_confirm', None)
            del request.session['session_order']
            
            error_notify(request, 'Try again, payment gateway failed..!')
            return redirect('cart_page')
        
        
        # if request.GET.get('applied_coupon'):
        applied_coupon = request.GET.get('applied_coupon','').strip()
        
        if not request.session.get('selected_address'):
            return redirect('address_selection')


        address_id = request.session.get('selected_address')
        
        

        if request.GET.get('payment'):
            payment_method = request.POST.get('payment')

        
        select_address = get_object_or_404(Address, id=address_id)
        
        cart = get_object_or_404(Cart, user=request.user)

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
        if not cart_items:
            return redirect('cart_page')
        
        for item in cart_items:
            if item.variant.stock < item.quantity:
                info_notify(request, f"cart item {item.product.name} haven't minmum stock for place the order")
                return redirect('cart_page')
        

        cartitem_with_image = []
        for cart_item in cart_items:
            main_image = cart_item.product.images.filter(is_main=True).first()
            cartitem_with_image.append({
                "cart_item": cart_item,
                "main_image": main_image
            })

        tax = 5
        is_coupon_apply = 0
        
        if Coupon.objects.filter(code=applied_coupon).exists():
            user_coupon = get_object_or_404(Coupon, code=applied_coupon)
            if cart.main_total_price < user_coupon.min_purchase_amount:
                info_notify(request, f"minimum puchase amount is {user_coupon.min_purchase_amount}")
                
                return redirect('order_confirmation')
            if not user_coupon.is_valid():
                info_notify(request, f"the Coupon is not valid")
                
                return redirect('order_confirmation')
            if CouponUsage.objects.filter(user=request.user, coupon=user_coupon).exists():
                coupon_usage = get_object_or_404(CouponUsage, user=request.user, coupon=user_coupon)
                if coupon_usage.usage_count >= user_coupon.usage_limit: 
                    info_notify(request, f"{user_coupon} coupon maximum usage is exceded")
                    
                    return redirect('order_confirmation')
            
            is_coupon_apply = user_coupon.apply_discount(cart.main_total_price)
            
        elif applied_coupon:
            info_notify(request, f"the applied coupon {applied_coupon} is not exists")
            
        
        final_over_all_amount = cart.over_all_amount_coupon(is_coupon_apply)
        

        final_tax_with_coupon = cart.final_tax_with_coupon(is_coupon_apply)
        
        
        coupons = Coupon.objects.filter(is_active=True)
        

        context = {
            "user_id": request.user.id,
            "cart": cart,
            "cartitem_with_image": cartitem_with_image,
            "select_address": select_address,
            "tax": tax,
            "coupons": coupons,
            "applied_coupon": is_coupon_apply,
            "final_over_all_amount": final_over_all_amount,
            "final_tax_with_coupon": final_tax_with_coupon,
            "valid_coupon": applied_coupon
        }
        
        return render(request, 'orders/final_confirmation.html', context)

    
    
@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class PlaceOrderView(View):

    def post(self, request):
        
        address_id = request.POST.get('address')
        payment_method = request.POST.get('payment')
        applied_coupon = request.POST.get('apply_coupon','').strip()
        final_over_all_amount = request.POST.get('final_amount')

        if request.session.get('selected_address'):
            request.session.pop('selected_address', None)
        # if not request.session.get('payment_confirm'):
        #     return redirect('order_listing')

        if not address_id:
            info_notify(request, "Select your delivery address please..")
            return redirect('address_selection')
        
        address = get_object_or_404(Address, id=address_id)

        if not request.POST.get('payment'):
            info_notify(request, "select your payment method please.. ")
            # here is how pass query params in redirection
            # url = f'{reverse("order_confirmation")}?address={address.id}'
            return redirect('order_confirmation')
        
        if payment_method == 'COD':
            if Decimal(final_over_all_amount) > 1000:
                info_notify(request, "The order amount is geater than 1000, try an another payment method")
                # url = f'{reverse("order_confirmation")}?address={address.id}'
                return redirect('order_confirmation')
        
        address = get_object_or_404(Address, id=address_id)
        
        if not Cart.objects.filter(user=request.user).exists():

            return redirect('cart_page')
        

        cart = get_object_or_404(Cart, user=request.user)

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

        if not cart_items:
            return redirect('cart_page')
        
        for item in cart_items:
            if item.variant.stock < item.quantity:
                info_notify(request, f"cart item {item.product.name} haven't minmum stock for place the order")
                return redirect('cart_page')
        
        #  creating order
        order = Order.objects.create(
            user=request.user,
            order_id = f"ORD{uuid.uuid4().hex[:5].upper()}",
            payment_method=payment_method,
            status='Pending'
        )
        if applied_coupon and Coupon.objects.filter(code=applied_coupon).exists():
            
            user_coupon = get_object_or_404(Coupon, code=applied_coupon)
            coupon_amount = user_coupon.apply_discount(cart.main_total_price)
            order.coupon_code=applied_coupon
            order.coupon_amount=coupon_amount
            order.coupon_amount_static=coupon_amount
            order.save()
            update_usage = user_coupon.increment_usage(request.user)

        order_address = OrderAddress.objects.create(
            order=order, full_name=address.full_name, email=address.email,
            phone_no=address.phone_no, address=address.address,
            district=address.district, state=address.state, city=address.city,
            pin_code=address.pin_code, address_type=address.address_type

        )

        for item in cart_items:
            OrderItem.objects.create(
                order=order, product=item.product, variant=item.variant,
                quantity=item.quantity, price=item.variant.final_price,
                discount_price=item.variant.discount_price,
                discount_percent=item.variant.discount_percent

            )

            # Reduce stock respect to the order item
            item.variant.stock -= item.quantity
            item.variant.save()

            
        
        # cart.items.filter(is_active=True).delete()

        if order.razorpay_order_id:   # ← already paid once
            return redirect('razorpay_checkout', order_id=order.order_id)

        

        if payment_method == 'COD':
            cart = get_object_or_404(Cart, user=request.user)
            cart.items.filter(is_active=True).delete()


            context = {
            "user_id": request.user.id,
            "order": order,
            }
            success_notify(request, "Order placed successfully!")
            return render(request, 'orders/success_order.html', context)
        elif payment_method == 'Wallet':
            wallet, create = Wallet.objects.get_or_create(user=request.user)
            # wallet = get_object_or_404(Wallet, user=request.user)
            if wallet.balance < order.over_all_amount:
                order.items.all().delete()
                order.orders_address.delete()
                order.delete()

                error_notify(request, "Insufficient wallet balance, try an another method")
                # url = f'{reverse("order_confirmation")}?address={address.id}'
                return redirect('order_confirmation')
            
            order.is_paid=True
            order.save()

            cart = get_object_or_404(Cart, user=request.user)
            cart.items.filter(is_active=True).delete()

            transaction = wallet.debit(Decimal(order.over_all_amount), message=f"Order #{order.order_id} payment")
            transaction.order=order
            transaction.save()

            

            context = {
            "user_id": request.user.id,
            "order": order,
            }
            success_notify(request, "Order placed successfully!")
            return render(request, 'orders/success_order.html', context)
        
        elif payment_method == 'ONLINE':
            amount_in_paise = int(order.over_all_amount * 100)   # Razorpay uses paise
            razorpay_order = client.order.create({
                "amount": amount_in_paise,
                "currency": "INR",
                "receipt": order.order_id,
            })
            order.razorpay_order_id = razorpay_order['id']
            order.save()

            request.session["payment_confirm"] = True
            request.session['session_order'] = order.id

            if request.session.get('selected_address'):
                request.session.pop('selected_address', None)
            # pay_url = f'{reverse("razorpay_callback")}?order={order.id}'
            return redirect("razorpay_callback")

@csrf_exempt
def razorpay_callback(request):
    if request.method == "POST":

        try:
            payment_id = request.POST.get('razorpay_payment_id')
            order_id   = request.POST.get('razorpay_order_id')
            signature  = request.POST.get('razorpay_signature')
            order_identity = request.POST.get('order_idetity')

            

            cart = get_object_or_404(Cart, user=request.user)

            try:
                order = Order.objects.get(razorpay_order_id=order_id)
            except Order.DoesNotExist:
                info_notify(request, "the order is not confirmed. The amount has been added to your wallet. Please try again. ")
                return redirect('cart_page')
            
            

            # Verify signature
            generated_signature = hmac.new(
                settings.RAZORPAY_KEY_SECRET.encode(),
                f"{order_id}|{payment_id}".encode(),
                hashlib.sha256
            ).hexdigest()
            

            if generated_signature != signature:
                # FAILURE — Payment is not legitimate
                return redirect("order_cancel_return_cart", order_id=order.id)
            
            
            order.is_paid = True
            order.razorpay_payment_id = payment_id
            order.razorpay_signature = signature
            order.status = 'Pending'
            order.save()
            

            
            cart.items.filter(is_active=True).delete()
            return redirect('order_success', order_id=order.order_id)
        except Exception as e:

            info_notify(request, f"We couldn’t complete your order due to an {e}. The amount has been added to your wallet. Please try again.")

            return redirect("order_cancel_return_cart", order_id=order.id)
            # else:
            #     # order.items.all().delete()
            #     # order.orders_address.delete()
            #     # order.delete()

                
            #     return redirect('order_cancel_return_cart', order_id=order.id)
    else:
        if not request.session.get('payment_confirm'):
            return redirect('cart_page')
        
        order_id = request.session.get('session_order')
        if not Order.objects.filter(id=order_id).exists():
            return redirect('cart_page')
        order = get_object_or_404(Order, id=order_id)
        amount_in_paise = int(order.over_all_amount * 100)
        context = {
                'user_id': request.user.id,
                'order': order,
                'razorpay_key_id': settings.RAZORPAY_KEY_ID,
                'amount': amount_in_paise,
                'currency': 'INR',
                'real_amount': order.over_all_amount,
                'callback_url': request.build_absolute_uri(reverse('razorpay_callback')),
                # 'cancel_url': request.build_absolute_uri(reverse('order_cancel')),
            }
        return render(request, 'orders/razorpay_checkout.html', context)

@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class OrderSuccessView(View):
    def get(self, request, order_id):
        if request.session.get('selected_address'):
            request.session.pop('selected_address', None)

        if not request.session.get('payment_confirm'):
            return redirect('cart_page')
        
        if request.session.get('payment_confirm'):
            request.session.pop('payment_confirm', None)
            del request.session['session_order']

        order = get_object_or_404(Order, order_id=order_id, user=request.user)
        success_notify(request, "Order placed successfully!")
        return render(request, 'orders/success_order.html', {'user_id': request.user.id ,'order': order})
    
@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class OrderCancelReturnCartView(View):
    def get(self, request, order_id):
        if not request.session.get('payment_confirm'):
            return redirect('cart_page')
        if request.session.get('payment_confirm'):
            request.session.pop('payment_confirm', None)
            del request.session['session_order']
        order = get_object_or_404(Order, id=order_id, user=request.user)
        if order.coupon_code:
            used_coupon = get_object_or_404(Coupon, code=order.coupon_code)
            update_usage = used_coupon.decrement_usage(request.user)

        if order.is_paid:

            wallet= get_object_or_404(Wallet, user=request.user)
            transaction = wallet.credit(Decimal(order.over_all_amount), message=f"Order {order.order_id} payment failure")
        else:
            info_notify(request, "We couldn’t complete your order. Please try again.")

        for item in order.items.all():
            item.variant.stock += item.quantity
            item.variant.save()
            
        order.items.all().delete()
        order.orders_address.delete()
        order.delete()
        
        return redirect('cart_page')
    
@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class PaymentFailedView(View):
    def get(self, request, order_id):
        if not request.session.get('payment_confirm'):
            return redirect('cart_page')
        if request.session.get('payment_confirm'):
            request.session.pop('payment_confirm', None)
            del request.session['session_order']
            
        order = get_object_or_404(Order, id=order_id, user=request.user)
        if order.coupon_code:
                    used_coupon = get_object_or_404(Coupon, code=order.coupon_code)
                    update_usage = used_coupon.decrement_usage(request.user)
        order.status='Payment Failed'
        order.save()
        for item in order.items.all():
            item.variant.stock += item.quantity
            item.variant.save()
        error_notify(request, "Payment Failed..!")
        return render(request, 'orders/payment_failed.html', {'user_id': request.user.id ,'order': order})


@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class OrderStatusUpdateByDateMixin:
    def dispatch(self, request, *args, **kwargs):
        # Update all orders for this user before view runs
        orders = Order.objects.filter(user=request.user)

        for order in orders:
            # check if the current time is greater than or equal to the processing time
            if timezone.now() >= order.processing_date and order.status == "Pending"  : 
                '''if not changing from admin side we can give timezone.now() >= order.processing_time and 
                (order.status == "Pending" or order.status == "Shipped" or order.status == "Processing")'''
                order.status = "Processing"
                order.save(update_fields=["status", "updated_at"])

            if timezone.now() >= order.shipped_date and order.status == "Processing" :
                order.status = "Shipped"
                order.save(update_fields=["status", "updated_at"])

            if timezone.now() >= order.delivery_date and order.status == "Shipped" :
                order.status = "Delivered"
                if order.payment_method in ['COD', 'Cash on Delivery']:
                    order.is_paid
                order.save()

        # continue to the original view
        return super().dispatch(request, *args, **kwargs)


@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class OrderListingView(OrderStatusUpdateByDateMixin, View):

    def get(self, request):
        if request.session.get('payment_confirm'):
            if request.session.get('session_order'):
                order_id = request.session.get('session_order')
                try:
                    session_order = Order.objects.get(id=order_id)
                except Order.DoesNotExist:
                    request.session.pop('payment_confirm', None)
                    del request.session['session_order']
                    return redirect('cart_page')
                # session_order = get_object_or_404(Order, id=order_id)
                if session_order.coupon_code:
                    used_coupon = get_object_or_404(Coupon, code=session_order.coupon_code)
                    update_usage = used_coupon.decrement_usage(request.user)
                for item in session_order.items.all():
                    item.variant.stock += item.quantity
                    item.variant.save()
                    
                session_order.items.all().delete()
                session_order.orders_address.delete()
                session_order.delete()
            request.session.pop('payment_confirm', None)
            del request.session['session_order']
            
            error_notify(request, 'payment gateway failed..!, try again')
            
            

        user_profile = profile(request)
        page = request.GET.get('page', 1)
        query = request.GET.get('q', '').strip()

        orders = Order.objects.filter(user=request.user).exclude(status='Payment Failed').order_by('-updated_at')

        if query:
            orders = orders.filter(Q(status__icontains=query))
        

        # paginator = Paginator(orders, 5) 

        # page_number = request.GET.get('page')

        # page_obj = paginator.get_page(page_number)
        breadcrumb = [
            {"name": "Profile", "url": "/accounts/profile/"},
            {"name": "My Orders", "url": ""},
        ]

        paginator = Paginator(orders, 3)
        try:
            paginated_orders = paginator.page(page)
        except PageNotAnInteger:
            paginated_orders = paginator.page(1)
        except EmptyPage:
            paginated_orders = paginator.page(paginator.num_pages)

        custom_range = custom_page_range(paginated_orders.number, paginator.num_pages)

        context = {
            "user_id": request.user.id,
            "user_profile": user_profile,
            "orders": paginated_orders,
            "breadcrumb": breadcrumb,
            "paginator" : paginator,
            "page_obj" : paginated_orders,
            "query": query,
            "custom_range": custom_range
        }

        return render(request, "orders/order_listing.html", context)
    
@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class OrderDetailView(View):

    
    def get(self, request, order_id):

        user_profile = profile(request)

        if not Order.objects.filter(user=request.user, id=order_id):
            return redirect('order_listing')
        
        order = get_object_or_404(Order, id=order_id)

        order_address = order.orders_address
        

        order_items = order.items.select_related( 'product', 'variant' ).all()

        if not order_items:
            return redirect('order_listing')
        
        return_item_requests = ReturnItemRequest.objects.filter(order=order)
        return_items = []
        for item_request in return_item_requests:
            if item_request.order_item in order_items:
                
                return_items.append(item_request.order_item)
        


        orderitem_with_image = []
        for order_item in order_items:
            main_image = order_item.product.images.filter(is_main=True).first()
            orderitem_with_image.append({
                "order_item": order_item,
                "main_image": main_image,
            })
        

        breadcrumb = [
            {"name": "Profile", "url": "/accounts/profile/"},
            {"name": "My Orders", "url": "/orders/order_listing/"},
            {"name": "Order Detail", "url": ""},
        ]

        context = {
            "user_id": request.user.id,
            "user_profile": user_profile,
            "order": order,
            "orderitem_with_image": orderitem_with_image,
            "breadcrumb": breadcrumb,
            "return_item_requests": return_item_requests,
            "return_items": return_items

        }

        return render(request, "orders/order_detail.html", context)
    
@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class OrderTrackingView(View):

    def get(self, request, order_id):

        user_profile = profile(request)

        if not Order.objects.filter(user=request.user, id=order_id):
            return redirect('order_listing')

        order = get_object_or_404(Order, id=order_id)
        

        breadcrumb = [
            {"name": "Profile", "url": "/accounts/profile/"},
            {"name": "My Orders", "url": "/orders/order_listing/"},
            {"name": "Order Details", "url": f"/orders/order_detail/{order.id}/"},
            {"name": "Track Order", "url": ""},
        ]

        context = {
            "user_id": request.user.id,
            "user_profile": user_profile,
            "order": order,
            "breadcrumb": breadcrumb,
        }
        return render(request, "orders/order_tracking.html", context)
    
    # cancellation 
    
@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class CancelOrderView(View):
    def get(self, request, order_id):

        order = get_object_or_404(Order, id=order_id, user=request.user)

        if order.status not in ['Pending', 'Processing']:
            return redirect('order_details', order_id-order.id )
        
        return render(request, 'order_confirm/order_cancel.html', {"order": order})
    
    def post(self, request, order_id):

        order = get_object_or_404(Order, id=order_id, user=request.user)

        if order.status not in ['Pending', 'Processing']:
            error_notify(request, "Order can't able to cancel after processing")
            return redirect('order_details', order_id-order.id )
        
        
        

        if order.items.filter(is_cancel=False).exists():
            if order.payment_method not in ['COD', 'Cash on Delivery']:
                refund_amount = order.over_all_amount
                

                wallet = get_object_or_404(Wallet, user=request.user)
                transaction = wallet.credit(Decimal(order.over_all_amount), message=f"Order {order.order_id} cancellation amount" )
                transaction.order=order
                transaction.save()
            for item in order.items.filter(is_cancel=False):
                if item.variant:
                    item.variant.stock += item.quantity
                    item.is_cancel = True
                    item.item_status = 'Cancelled'
                    item.variant.save()
                    item.save()
            
        order.cancel_reason = request.POST.get('reason', '')
        order.status = 'Cancelled'
        order.is_paid=False
        order.coupon_amount = 0.00
        order.save()

        
        success_notify(request, "order cancelled successfully")
        return redirect('order_details', order_id=order.id)     


@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class CancelOrderItemView(View):

    def post(self, request, order_id, item_id):

        

        order = get_object_or_404(Order, id=order_id, user=request.user)
        if order.status not in ['Pending', 'Processing']:
            error_notify(request, "Order can't able to cancel after processing")
            return redirect('order_details', order_id-order.id )
        
        item = get_object_or_404(OrderItem, id=item_id, order=order)
        
        
        if item.variant:
            if order.payment_method not in ['COD', 'Cash on Delivery']:
                refund_amount = item.return_with_tax_price()
                
                wallet = get_object_or_404(Wallet, user=request.user)
                transaction = wallet.credit(Decimal(refund_amount), message=f"Order #{order.order_id} refund for item:{item.product.name} ")
                transaction.order=order
                transaction.save()
            item.variant.stock += item.quantity
            item.is_cancel = True
            item.item_status = 'Cancelled'
            item.variant.save()
            item.save()
            

        if not order.items.filter(is_cancel=False).exists():
            order.status = 'Cancelled'
            order.is_paid=False
            order.coupon_amount = 0.00
            order.save()

        success_notify(request, "item removes successfully")
        return redirect('order_details', order_id=order.id )
    

@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class ReturnOrderView(View):

    def get(self, request, order_id):
        order = get_object_or_404(Order, id=order_id, user=request.user)
        if order.status != 'Delivered':
            return redirect('order_details', order_id=order.id)
        return render(request, 'order_confirm/return_confirmation.html', {"order": order})
    
    def post(self, request, order_id):
        order = get_object_or_404(Order, id=order_id, user=request.user)
        if order.status != 'Delivered':
            return redirect('order_details', order_id=order.id)
        reason = request.POST.get('reason')

        if not reason:
            error_notify(request, "reason required")
            return redirect('return_order', order_id=order.id)
        ReturnRequest.objects.create(order=order, reason=reason)
        return redirect('order_details', order_id=order.id)
    


class ReturnItemView(View):
    def get(self, request, order_id, item_id):
        order = get_object_or_404(Order, id=order_id, user=request.user)
        if order.status != 'Delivered':
            error_notify(request, "Order can only able to return after delivery")
            return redirect('order_details', order_id=order.id)
        
        if not OrderItem.objects.filter(id=item_id, order=order).exists():
            info_notify(request, "Order item can't able to return ")
            return redirect('order_details', order_id-order.id )
        
        item = get_object_or_404(OrderItem, id=item_id, order=order)
        if ReturnItemRequest.objects.filter(order=order, order_item=item).exists():
            info_notify(request, "Order item already in return request  list")
            return redirect('order_details', order_id=order.id )

        if item.is_cancel:
            info_notify(request, "Order item can't able to return ")
            return redirect('order_details', order_id-order.id )

        return render(request, 'order_confirm/return_confirmation.html', {"order": order, "item": item})
    def post(self, request, order_id, item_id):

        order = get_object_or_404(Order, id=order_id, user=request.user)

        if order.status not in ['Delivered']:
            error_notify(request, "Order item can only able to return after delivery")
            return redirect('order_details', order_id-order.id )

        if not OrderItem.objects.filter(id=item_id, order=order).exists():
            info_notify(request, "Order item can't able to return ")
            return redirect('order_details', order_id-order.id )
        
        item = get_object_or_404(OrderItem, id=item_id, order=order)
        if ReturnItemRequest.objects.filter(order=order, order_item=item).exists():
            info_notify(request, "Order item already in return request  list")
            return redirect('order_details', order_id=order.id )

        if item.is_cancel:
            info_notify(request, "Order item can't able to return ")
            return redirect('order_details', order_id-order.id )
        reason = request.POST.get('reason')
        if not reason:
            error_notify(request, "reason required")
            return redirect('return_order_item', order_id=order.id, item_id=item.id)
        
        ReturnItemRequest.objects.create(order=order, order_item=item, reason=reason)
        return redirect('order_details', order_id=order.id)

@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class InvoiceDownloadView(View):

    def get(self, request, order_id):
        # Fetch the order object using the order_id
        order = get_object_or_404(Order, id=order_id)
        
        # --- Create PDF ---
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
        story = []
        styles = getSampleStyleSheet()

        # --- Header Section ---
        header_data = [
            ['NOTEVIA\nkakkenchery, Calicut\nsupport@notevia.com', 
             f"INVOICE\nOrder ID: {order.order_id}\nDate: {order.created_at.strftime('%d %b %Y')}"]
        ]
        header_table = Table(header_data, colWidths=[4*inch, 2.5*inch])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
            ('FONTSIZE', (0,0), (-1,-1), 10),
            ('FONTSIZE', (1,0), (1,0), 10), # Larger 'INVOICE' text
            ('BOTTOMPADDING', (0,0), (-1,-1), 12),
        ]))
        story.append(header_table)
        
        # --- Billing Address Section ---
        address = order.orders_address
        billing_address = f"""
            <b>Bill To:</b><br/>
            {address.full_name}<br/>
            {address.address}<br/>
            {address.city}, {address.state} {address.pin_code}<br/>
            {address.email}<br/>
            {address.phone_no}
        """
        story.append(Paragraph(billing_address, styles['Normal']))
        story.append(Spacer(1, 24))

        # --- Items Table Section ---
        items_data = [
            ['Product', 'Variant', 'Qty', 'Price', 'Discount\n per Qty', "Coupon\n Split", 'Subtotal']
        ]
        
        for item in order.items.filter(is_cancel=False).exclude(is_return=True):
            row = [
                Paragraph(item.product.name, styles['Normal']),
                item.variant.name if item.variant else "—",
                item.quantity,
                f"Rs. {item.real_price:.2f}",
                f"Rs. {item.discount_price:.2f}" if item.discount_price else "Rs. 0.00",
                f"Rs. {item.coupon_discount():.2f}" if item.coupon_discount() else "Rs. 0.00",
                f"Rs. {item.sub_real_price:.2f}"
            ]
            items_data.append(row)

        items_table = Table(items_data, colWidths=[2.5*inch, 1*inch, 0.5*inch, 0.8*inch, 0.8*inch, 0.9*inch])
        items_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'), # Align product names to the left
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(items_table)

        # --- Totals Section ---
        totals_data = [
            ['Total MRP:', f'Rs. {order.total_items_amount():.2f}'],
            ['Discount:', f'-Rs. {order.total_discount():.2f}'],
            ['Subtotal:', f'Rs. {order.total_amount():.2f}'],
            ['Coupon:', f'-Rs. {order.coupon_amount:.2f}'],
            ['Tax (5%):', f'Rs. {order.tax_amount():.2f}'],
            ['Grand Total:', f'Rs. {order.over_all_amount:.2f}']
        ]

        totals_table = Table(totals_data, colWidths=[1.5*inch, 1*inch])
        totals_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 5), (-1, 5), 'Helvetica-Bold'), # Bold Grand Total
            ('GRID', (0, 0), (-1, -1), 1, colors.lightgrey)
        ]))
        
        # Wrapper table to align the totals table to the right
        wrapper_table = Table([[totals_table]], colWidths=[6.5*inch], hAlign='RIGHT')
        story.append(Spacer(1, 24))
        story.append(wrapper_table)

        # --- Footer Section ---
        story.append(Spacer(1, 36))
        story.append(Paragraph(f"Payment Method: {order.get_payment_method_display()}", styles['Normal']))
        story.append(Paragraph("Thank you for your purchase!", styles['Normal']))

        # --- Build PDF ---
        doc.build(story)
        
        buffer.seek(0)
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="invoice_{order.order_id}.pdf"'
        return response

    # admin side order



@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class AdminSideOrderListingView(OrderStatusUpdateByDateMixin,View):

    def get(self, request):
        # user_profile = get_object_or_404(UserProfile, user=request.user)
        if request.session.get('payment_confirm'):
            if request.session.get('session_order'):
                order_id = request.session.get('session_order')
                try:
                    session_order = Order.objects.get(id=order_id)
                except Order.DoesNotExist:
                    request.session.pop('payment_confirm', None)
                    del request.session['session_order']
                    return redirect('cart_page')
                # session_order = get_object_or_404(Order, id=order_id)
                if session_order.coupon_code:
                    used_coupon = get_object_or_404(Coupon, code=session_order.coupon_code)
                    update_usage = used_coupon.decrement_usage(request.user)
                for item in session_order.items.all():
                    item.variant.stock += item.quantity
                    item.variant.save()
                    
                session_order.items.all().delete()
                session_order.orders_address.delete()
                session_order.delete()
            request.session.pop('payment_confirm', None)
            del request.session['session_order']
            
            error_notify(request, 'Try again, payment gateway failed..!')
            
            

        query = request.GET.get('q', '').strip()
        stat = request.GET.get('stat', '').strip()
        

        page = int(request.GET.get('page', 1))

        orders = Order.objects.all().order_by('-created_at')

        if query:
            orders = orders.filter(Q(status__icontains=query)|Q(user__full_name__icontains=query)|Q(order_id__icontains=query))

        if stat:
            orders = orders.filter(status=stat)

        paginator = Paginator(orders, 3)
        try:
            paginated_orders = paginator.page(page)
        except PageNotAnInteger:
            paginated_orders = paginator.page(1)
        except EmptyPage:
            paginated_orders = paginator.page(paginator.num_pages)

        custom_range = custom_page_range(paginated_orders.number, paginator.num_pages)

        breadcrumb = [
            {"name": "Dashboard", "url": f"/adminpanel/admindash/{request.user.id}/"},
            {"name": "Orders", "url": ""},
        ]

        context = {
            "user_id": request.user.id,
            "orders": paginated_orders,
            "paginator" : paginator,
            "page_obj" : paginated_orders,
            "breadcrumb": breadcrumb,
            "query":query,
            "stat": stat,
            'status_choices': Order.STATUS_CHOICES,
            "custom_range": custom_range
        }

        return render(request, 'orders/admin_order_listing.html', context)
    

@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')    
class AdminOrderDetailView(View):

    def get(self, request, order_id):

        # user_profile = get_object_or_404(UserProfile, user=request.user)
        order = get_object_or_404(Order, id=order_id)

        if not Order.objects.filter(user=order.user.id, id=order_id):
            return redirect('order_listing')
        
        

        order_address = order.orders_address
        

        order_items = order.items.select_related( 'product', 'variant' ).all()

        if not order_items:
            return redirect('order_listing')
        
        return_item_requests = ReturnItemRequest.objects.filter(order=order).order_by('-status')

        orderitem_with_image = []
        for order_item in order_items:
            main_image = order_item.product.images.filter(is_main=True).first()
            orderitem_with_image.append({
                "order_item": order_item,
                "main_image": main_image,
            })
        

        breadcrumb = [
            {"name": "Dashboard", "url": f"/adminpanel/admindash/{request.user.id}/"},
            {"name": "Orders", "url": "/orders/admin_order/"},
            {"name": "Order Detail", "url": ""},
        ]

        context = {
            "user_id": request.user.id,
            "order": order,
            "orderitem_with_image": orderitem_with_image,
            'status_choices': Order.STATUS_CHOICES,
            "breadcrumb": breadcrumb,
            'return_status_choices': ReturnRequest.STATUS_CHOICES,
            "return_item_requests": return_item_requests,
            "return_item_status_choices": ReturnItemRequest.STATUS_CHOICES
        }

        return render(request, "orders/admin_order_detail.html", context)
    
    
@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')    
class OrderStatusUpdateView(View):

    def get(self, request, order_id, new_status):

        order = get_object_or_404(Order, id=order_id)
        if not order.status == new_status:
            order.status = new_status
            order.save()
            
            if order.status == 'Cancelled':
                if order.payment_method != 'COD':
                    for item in order.items.filter(is_cancel=False).exclude(is_return=True):
                        item.variant.stock += item.quantity
                        item.is_cancel = True
                        item.item_status = 'Cancelled'
                        item.save()
            if order.status == 'Returned':
                for item in order.items.filter(is_return=False).exclude(is_cancel=True):
                    item.variant.stock += item.quantity
                    item.is_return = True
                    item.item_status = 'Returned'
                    item.save()
            if order.status == 'Delivered':
                for item in order.items.filter(is_cancel=False).exclude(is_return=True):
                    item.item_status = 'Delivered'
                    item.save()
                order.is_paid=True
                order.save()

        return redirect('admin_order_detail', order_id=order.id)

@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class ReturnUpdateView(View):

    def post(self, request, order_id, user_id):
        if not CustomUser.objects.filter(id=user_id).exists():
            return redirect('admin_order_detail', order_id=order_id)
        return_status = request.POST.get('status')
        if not return_status:
            return redirect('admin_order_detail', order_id=order_id)


        user = get_object_or_404(CustomUser, id=user_id)

        order = get_object_or_404(Order, id=order_id, user=user)
        if return_status in ['Approved']:
            wallet = get_object_or_404(Wallet, user=user)
            transaction = wallet.credit(Decimal(order.over_all_amount), message=f"Order {order.order_id} Return Amount" )
            transaction.order=order
            transaction.save()
            for item in order.items.filter(is_cancel=False).exclude(is_return=True):
                
                item.variant.stock += item.quantity
                item.variant.save()
                # item.is_cancel = True # remove if not needed
                item.is_return = True
                item.item_status = 'Returned'
                item.save()

            order.return_requests.status = 'Approved'
            order.return_requests.save()
            order.status='Returned'
            order.is_paid=False
            order.save()
            # email for approval
            html_content = render_to_string("emails/approve_return.html", {"order": order})
            email = EmailMultiAlternatives(
                subject="Verify Your Account",
                body=f"Your OTP is ",
                from_email=settings.EMAIL_HOST_USER,
                to=[user.email],
            )

            email.attach_alternative(html_content, "text/html")
            email.send()

            return redirect('admin_order_detail', order_id=order.id)
        
        elif return_status in ['Rejected']:

            # email for rejection
            html_content = render_to_string("emails/return_reject.html", {"order": order})
            email = EmailMultiAlternatives(
                subject="Verify Your Account",
                body=f"Your OTP is ",
                from_email=settings.EMAIL_HOST_USER,
                to=[user.email],
            )

            email.attach_alternative(html_content, "text/html")
            email.send()

            order.return_requests.status = 'Rejected'
            order.return_requests.save()

            return redirect('admin_order_detail', order_id=order.id)
        return redirect('admin_order_detail', order_id=order.id)
    
@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class ItemReturnUpdateView(View):

    def post(self, request, order_id, user_id, item_id):
        if not CustomUser.objects.filter(id=user_id).exists():
            return redirect('admin_order_detail', order_id=order_id)
        return_status = request.POST.get('status')
        if not return_status:
            return redirect('admin_order_detail', order_id=order_id)


        user = get_object_or_404(CustomUser, id=user_id)

        order = get_object_or_404(Order, id=order_id, user=user)
        if not OrderItem.objects.filter(order=order, id=item_id).exists():
            info_notify(request, "the item is not exists in this order")
            return redirect('admin_order_detail', order_id=order_id)
        item = get_object_or_404(OrderItem, order=order, id=item_id)
        if not ReturnItemRequest.objects.filter(order=order, order_item=item).exists():
            info_notify(request, "the item is not exists in the item request list")
            return redirect('admin_order_detail', order_id=order_id)
        return_item_request = get_object_or_404(ReturnItemRequest, order=order, order_item=item)

        if return_status in ['Approved']:
            refund_amount = item.return_with_tax_price()
            wallet = get_object_or_404(Wallet, user=user)
            transaction = wallet.credit(Decimal(refund_amount), message=f"Order {order.order_id} Return Amount for item {item.product.name}" )
            transaction.order=order
            transaction.save()
            
            item.variant.stock += item.quantity
            # item.is_cancel = True # remove if not needed
            item.is_return = True
            item.item_status = 'Returned'
            item.variant.save()
            item.save()
            
            
            return_item_request.status = 'Approved'
            return_item_request.save()
            if not order.items.filter(is_return=False).exclude(is_cancel=True).exists():
                order.status='Returned'
                order.is_paid=False
                order.save()
            # email for approval
            html_content = render_to_string("emails/approve_return.html", {"order": order, "item": item})
            email = EmailMultiAlternatives(
                subject="Verify Your Account",
                body=f"Your OTP is ",
                from_email=settings.EMAIL_HOST_USER,
                to=[user.email],
            )

            email.attach_alternative(html_content, "text/html")
            email.send()

            return redirect('admin_order_detail', order_id=order.id)
        
        elif return_status in ['Rejected']:

            # email for rejection
            html_content = render_to_string("emails/return_reject.html", {"order": order, "item": item})
            email = EmailMultiAlternatives(
                subject="Verify Your Account",
                body=f"Your OTP is ",
                from_email=settings.EMAIL_HOST_USER,
                to=[user.email],
            )

            email.attach_alternative(html_content, "text/html")
            email.send()

            return_item_request.status = 'Rejected'
            return_item_request.save()

            return redirect('admin_order_detail', order_id=order.id)
        return redirect('admin_order_detail', order_id=order.id)
    

class AddressAddFromSelectView(View):

    def get(self, request):

        user = get_object_or_404(CustomUser, id=request.user.id)

        # user_profile = get_object_or_404(UserProfile, user=user)

        # breadcrumb = [
        #     {"name": "Profile", "url": "/accounts/profile/"},
        #     {"name": "Address", "url": "/accounts/user_address/"},
        #     {"name": "Add Address", "url": "/accounts/user_address/"}
        # ]
        cart = get_object_or_404(Cart, user=request.user)

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
        if not cart_items:
            return redirect('cart_page')
        

        cartitem_with_image = []
        for cart_item in cart_items:
            main_image = cart_item.product.images.filter(is_main=True).first()
            cartitem_with_image.append({
                "cart_item": cart_item,
                "main_image": main_image
            })
        errors = request.session.pop("address_error", None)
        data = request.session.pop("address_data", None)

        form = AddressForm(data if data else None)

        if errors:
            form._errors = errors
        contex = {
            "user_id": request.user.id,
            "user": user,
            "cart": cart,
            # "cart_items": cart_items,
            "cartitem_with_image": cartitem_with_image,
            "form": form
        }


        return render(request, 'orders/address_add_from_select.html', contex)
    
    def post(self, request):
        form = AddressForm(request.POST)
        if form.is_valid():
            full_name = request.POST.get('full_name').strip()
            email = request.POST.get('email').strip()
            address = request.POST.get('address_field').strip()
            district = request.POST.get('district').strip()
            state = request.POST.get('state').strip()
            city = request.POST.get('city').strip()
            pincode = request.POST.get('pincode').strip()
            phone_no = request.POST.get('phone_no').strip()
            address_type = request.POST.get('addressType')

            # if city.isalpha():
            #     request.session["address_error"] = {"address_field": ["is alphabet"]}
            #     request.session["address_data"] = request.POST
            #     return redirect("address_add_from_select")
                

            address = Address.objects.create(user=request.user, full_name=full_name, email=email, address=address, 
                                         district=district, state=state, city=city, pin_code=pincode, phone_no=phone_no, address_type=address_type)

            success_notify(request, "new address add successfully")
            return redirect('address_selection')

        else:
            request.session["address_error"] = form.errors
            request.session["address_data"] = request.POST
            return redirect("address_add_from_select")
        



        


        
    

