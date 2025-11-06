from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.db import models
from accounts.models import Address, UserProfile, CustomUser
from adminpanel.models import Product, Variant
from cart.models import Cart, CartItem
from orders.models import Order, OrderItem, OrderAddress, ReturnRequest
from django.urls import reverse
from accounts.utils import error_notify, info_notify, success_notify, warning_notify
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

import razorpay
from django.conf import settings

import hmac, hashlib
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json

client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

# Create your views here.


class AddressSelectionView(View):

    def get(self, request):

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
    
@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class ConfirmationCartView(View):

    def get(self, request):

        address_id = request.GET.get('address')
        print("address id", address_id)

        if request.GET.get('payment'):
            payment_method = request.GET.get('payment')

            print('payment method is :', payment_method,"address id:", address_id)

        if not address_id:
            return redirect('address_selection')
        
        select_address = get_object_or_404(Address, id=address_id)
        print('address ', select_address)
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
        

        cartitem_with_image = []
        for cart_item in cart_items:
            main_image = cart_item.product.images.filter(is_main=True).first()
            cartitem_with_image.append({
                "cart_item": cart_item,
                "main_image": main_image
            })

        tax = 5
        tax_amount = cart.total_price*tax/100
        print("tax ",tax_amount)

        order_total_price = tax_amount + cart.main_total_price
        
        context = {
            "user_id": request.user.id,
            "cart": cart,
            "cartitem_with_image": cartitem_with_image,
            "select_address": select_address,
            "tax": tax,
            "tax_amount": tax_amount,
            "order_total_price": order_total_price,
            
        }
    
        return render(request, 'orders/final_confirmation.html', context)
    
    
@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class PlaceOrderView(View):

    def get(self, request):
        address_id = request.GET.get('address')
        payment_method = request.GET.get('payment')


        if not address_id:
            info_notify(request, "Select your delivery address please..")
            return redirect('address_selection')
        
        

        if not request.GET.get('payment'):
            info_notify(request, "select your payment method please.. ")
            # here is how pass query params in redirection
            url = f'{reverse("order_confirmation")}?address={address.id}'
            return redirect(url)
        
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
        
        #  creating order
        order = Order.objects.create(
            user=request.user,
            order_id = f"ORD{uuid.uuid4().hex[:10].upper()}",
            payment_method=payment_method,
            status='Pending'
        )

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

        print('payment method is :', payment_method,"address id:", address_id)

        if payment_method == 'COD':
            cart = get_object_or_404(Cart, user=request.user)
            cart.items.filter(is_active=True).delete()


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

@csrf_exempt
def razorpay_callback(request):
    if request.method != "POST":
        return redirect('cart_page')

    payment_id = request.POST.get('razorpay_payment_id')
    order_id   = request.POST.get('razorpay_order_id')
    signature  = request.POST.get('razorpay_signature')
    order_identity = request.POST.get('order_idetity')

    print('razorpay_payment_id', order_id," - ", order_identity)
    print('razorpay_payment_id', payment_id)

    cart = get_object_or_404(Cart, user=request.user)

    try:
        order = Order.objects.get(razorpay_order_id=order_id)
    except Order.DoesNotExist:
        return redirect('cart_page')

    # Verify signature
    generated_signature = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode(),
        f"{order_id}|{payment_id}".encode(),
        hashlib.sha256
    ).hexdigest()

    
    if generated_signature == signature:
        order.is_paid = True
        order.razorpay_payment_id = payment_id
        order.razorpay_signature = signature
        order.status = 'Pending'
        order.save()

        cart.items.filter(is_active=True).delete()
        return redirect('order_success', order_id=order.order_id)
    else:
        order.items.all().delete()
        order.orders_address.all().delete()
        order.delete()
        return redirect('order_cancel_return_cart', order_id=order.id)

@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class OrderSuccessView(View):
    def get(self, request, order_id):
        order = get_object_or_404(Order, order_id=order_id, user=request.user)
        success_notify(request, "Order placed successfully!")
        return render(request, 'orders/success_order.html', {'user_id': request.user.id ,'order': order})
    
@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class OrderCancelReturnCartView(View):
    def get(self, request, order_id):
        order = get_object_or_404(Order, id=order_id, user=request.user)
        order.items.all().delete()
        order.orders_address.delete()
        order.delete()
        return redirect('cart_page')
    
@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class PaymentFailedView(View):
    def get(self, request, order_id):
        order = get_object_or_404(Order, id=order_id, user=request.user)
        order.status='Payment Failed'
        order.save()
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
                order.save(update_fields=["status", "updated_at"])

        # continue to the original view
        return super().dispatch(request, *args, **kwargs)


@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class OrderListingView(OrderStatusUpdateByDateMixin, View):

    def get(self, request):

        user_profile = get_object_or_404(UserProfile, user=request.user)
        page = request.GET.get('page', 1)
        query = request.GET.get('q', '').strip()

        orders = Order.objects.filter(user=request.user).exclude(status='Payment Failed').order_by('-updated_at')

        if query:
            orders = orders.filter(Q(status__icontains=query))
        print("orders: ", orders)

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

        context = {
            "user_id": request.user.id,
            "user_profile": user_profile,
            "orders": paginated_orders,
            "breadcrumb": breadcrumb,
            "paginator" : paginator,
            "page_obj" : paginated_orders,
            "query": query,
        }

        return render(request, "orders/order_listing.html", context)
    
@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class OrderDetailView(View):

    
    def get(self, request, order_id):

        user_profile = get_object_or_404(UserProfile, user=request.user)

        if not Order.objects.filter(user=request.user, id=order_id):
            return redirect('order_listing')
        
        order = get_object_or_404(Order, id=order_id)

        order_address = order.orders_address
        print('order address', order_address)

        order_items = order.items.select_related( 'product', 'variant' ).all()

        if not order_items:
            return redirect('order_listing')

        orderitem_with_image = []
        for order_item in order_items:
            main_image = order_item.product.images.filter(is_main=True).first()
            orderitem_with_image.append({
                "order_item": order_item,
                "main_image": main_image,
            })
        print("orders: ", order)

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
        }

        return render(request, "orders/order_detail.html", context)
    
class OrderTrackingView(View):

    def get(self, request, order_id):

        user_profile = get_object_or_404(UserProfile, user=request.user)

        if not Order.objects.filter(user=request.user, id=order_id):
            return redirect('order_listing')

        order = get_object_or_404(Order, id=order_id)
        print("orders: ", order)

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
            return redirect('order_details', order_id-order.id )
        
        order.cancel_reason = request.POST.get('reason', '')
        order.status = 'Cancelled'
        order.save()

        if order.items.filter(is_cancel=False).exists():
            for item in order.items.filter(is_cancel=False):
                if item.variant:
                    item.variant.stock += item.quantity
                    item.is_cancel = True
                    item.variant.save()
                    item.save() 

        

        return redirect('order_details', order_id=order.id)     


@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class CancelOrderItemView(View):

    def post(self, request, order_id, item_id):

        print("order_id", order_id)

        order = get_object_or_404(Order, id=order_id, user=request.user)
        if order.status not in ['Pending', 'Processing']:
            return redirect('order_details', order_id-order.id )
        
        item = get_object_or_404(OrderItem, id=item_id, order=order)

        print("hi")
        if item.variant:
            item.variant.stock += item.quantity
            item.is_cancel = True
            item.variant.save()
            item.save()

        if not order.items.filter(is_cancel=False).exists():
            order.status = 'Cancelled'
            order.save()

        return redirect('order_details', order_id=order.id )

        
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
            ['Your Company Name\n123 Your Street, Your City\nsupport@yourcompany.com', 
             f"INVOICE\nOrder ID: {order.order_id}\nDate: {order.created_at.strftime('%d %b %Y')}"]
        ]
        header_table = Table(header_data, colWidths=[4*inch, 2.5*inch])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
            ('FONTSIZE', (0,0), (-1,-1), 10),
            ('FONTSIZE', (1,0), (1,0), 16), # Larger 'INVOICE' text
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
            ['Product', 'Variant', 'Qty', 'Price', 'Discount', 'Subtotal']
        ]
        
        for item in order.items.all():
            row = [
                Paragraph(item.product.name, styles['Normal']),
                item.variant.name if item.variant else "—",
                item.quantity,
                f"Rs. {item.real_price:.2f}",
                f"Rs. {item.discount_price:.2f}" if item.discount_price else "Rs. 0.00",
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
            ['Subtotal:', f'Rs. {order.total_items_amount():.2f}'],
            ['Tax (5%):', f'Rs. {order.tax_amount():.2f}'],
            ['Grand Total:', f'Rs. {order.over_all_amount():.2f}']
        ]

        totals_table = Table(totals_data, colWidths=[1.5*inch, 1*inch])
        totals_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 2), (-1, 2), 'Helvetica-Bold'), # Bold Grand Total
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

        query = request.GET.get('q', '').strip()
        

        page = request.GET.get('page', 1)

        orders = Order.objects.all().order_by('-status')

        if query:
            orders = orders.filter(Q(status__icontains=query))

        paginator = Paginator(orders, 3)
        try:
            paginated_orders = paginator.page(page)
        except PageNotAnInteger:
            paginated_orders = paginator.page(1)
        except EmptyPage:
            paginated_orders = paginator.page(paginator.num_pages)

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
        print('order address', order_address)

        order_items = order.items.select_related( 'product', 'variant' ).all()

        if not order_items:
            return redirect('order_listing')

        orderitem_with_image = []
        for order_item in order_items:
            main_image = order_item.product.images.filter(is_main=True).first()
            orderitem_with_image.append({
                "order_item": order_item,
                "main_image": main_image,
            })
        print("orders: ", order)

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
        }

        return render(request, "orders/admin_order_detail.html", context)
    
    
@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')    
class OrderStatusUpdateView(View):

    def get(self, request, order_id, new_status):

        order = get_object_or_404(Order, id=order_id)
        order.status = new_status
        order.save()

        if order.status == 'Cancelled':
            for item in order.items.filter(is_cancel=False):
                item.variant.stock += item.quantity
                item.is_cancel = True
                item.save()

        return redirect('admin_order_detail', order_id=order.id)


class ReturnUpdateView(View):

    def post(self, request, order_id, user_id):

        user = get_object_or_404(CustomUser, id=user_id)

        order = get_object_or_404(Order, id=order_id, user=user)

        return redirect('admin_order_detail', order_id=order.id)
    

