from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from orders.models import Order, OrderItem, OrderAddress
from django.core.paginator import Paginator
from django.db.models import Sum
from datetime import datetime, timedelta
from django.utils import timezone
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from django.http import HttpResponse
from io import BytesIO
from django.template.loader import render_to_string
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.utils import get_column_letter
from accounts.utils import profile
from products.models import Referral, WishlistItem
from adminpanel.models import Product
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
# Create your views here.

@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class AdminSalesView(View):

    def get(self, request):
        filter_type = request.GET.get('filter')
        custom_start = request.GET.get('start_date')
        custom_end = request.GET.get('end_date')

        

        orders = Order.objects.exclude(status__in=['Cancelled', 'Payment Failed']).order_by('-created_at')

        if filter_type == 'daily':
            start_date = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = start_date + timedelta(days=1)
        elif filter_type == 'weekly':
            start_date = timezone.now() - timedelta(days=timezone.now().weekday())
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = start_date + timedelta(days=7)
            
        elif filter_type == 'monthly':
            today = timezone.now()
            start_date = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end_date = (start_date + timedelta(days=32)).replace(day=1)
            
        elif filter_type == 'yearly':
            today = timezone.now()
            start_date = today.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            end_date = start_date.replace(month=12, day=31, hour=23, minute=59, second=59)
        else:
            start_date = timezone.now() - timedelta(days=30)
            end_date = timezone.now()

        if custom_start and custom_end:
            start_date = datetime.strptime(custom_start, '%Y-%m-%d')
            end_date = datetime.strptime(custom_end, '%Y-%m-%d') + timedelta(days=1)
            start_date = timezone.make_aware(start_date)
            end_date = timezone.make_aware(end_date)

        orders = orders.filter(created_at__gte=start_date, created_at__lt=end_date)
        

        total_orders = orders.count()
        total_items = sum(item.quantity for order in orders for item in order.items.filter(is_cancel=False))
        total_revenue = sum(order.over_all_amount_all for order in orders if order.over_all_amount_all)
        avg_order_value = total_revenue / total_orders if total_orders else 0


        period_str = f"{start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')}"

        report_data = {
            'store_name': 'NoteVia',
            'period': period_str,
            'generated_at': timezone.now().strftime('%d/%m/%Y, %H:%M:%S'),
            'orders': orders,
            'total_orders': total_orders,
            'total_items': total_items,
            'total_revenue': round(total_revenue, 2),
            # 'total_commission': round(total_commission, 2),
            # 'vendor_payout': round(total_revenue - total_commission, 2),
            'avg_order': round(avg_order_value, 2),
        }
        
        if 'download_pdf' in request.GET:
            print('nisam hi ')
            
            return self.generate_pdf_reportlab(report_data)
        if 'download_excel' in request.GET:
            return self.generate_excel(report_data)

        delivered_orders = Order.objects.filter(status='Delivered')
        shippped_orders = Order.objects.filter(status='Shipped')
        processing_orders = Order.objects.filter(status='Processing')

        
        # print('shipped count',shippped_count)
        delivered_count = delivered_orders.count()
        shipped_count = shippped_orders.count()
        processing_count  = processing_orders.count()
        orders_count = orders.count()
        
        total_quantity_sold = OrderItem.objects.filter( order__status='Delivered',is_cancel=False
                                                       ).aggregate(total=Sum('quantity'))['total'] or 0
        

        total_sales = sum(order.over_all_amount_all for order in delivered_orders)
        print('deliverd total price,', total_sales)

        print('total quantity', total_quantity_sold)

        page_number = request.GET.get('page', 1)
        paginator = Paginator(orders, 6)
        page_obj = paginator.get_page(page_number)

        print('custom_start',custom_start)

        context = {
            **report_data,
            'filter_type': filter_type,
            "user_id": request.user.id,
            "orders": page_obj,
            "page_obj": page_obj,
            "delivered_count": delivered_count,
            "shipped_count": shipped_count,
            "processing_count": processing_count,
            "orders_count": orders_count,
            "total_quantity_sold": total_quantity_sold,
            "total_sales": total_sales,
            "custom_start" : custom_start,
            "custom_end": custom_end,


        }
        return render(request, 'products/admin_sales.html', context)
    
    def generate_pdf_reportlab(self, data):
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()

        # Title
        elements.append(Paragraph(f"<font size=16>ADMIN SALES REPORT - {data['store_name']}</font>", styles["Title"]))
        elements.append(Paragraph(f"Period: {data['period']}", styles["Normal"]))
        elements.append(Spacer(1, 12))

        # Table data
        table_data = [['Order ID', 'Date', 'Customer', 'Items', 'Payment', 'Total', 'Coupon', 'Status']]
        for order in data['orders']:
            table_data.append([
                order.order_id,
                order.created_at.strftime('%d/%m/%Y'),
                order.user.full_name or order.user.email,
                str(order.total_quantity_all()),
                order.get_payment_method_display(),
                f"Rs. {order.over_all_amount_all}",
                # f"₹{order.over_all_amount_all * 0.1:.2f}",
                order.coupon_code or '-',
                order.get_status_display()
            ])

        table = Table(table_data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#16213e')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ]))
        elements.append(table)

        # Footer
        elements.append(Spacer(1, 20))
        elements.append(Paragraph(f"Total Item: {data['total_items']} | Total Order: {data['total_orders']}", styles["Normal"]))
        elements.append(Spacer(1, 10))
        elements.append(Paragraph(f"Average Order: Rs.{data['avg_order']}", styles["Normal"]))
        elements.append(Spacer(1, 10))
        elements.append(Paragraph(f"TOTAL REVENUE: Rs.{data['total_revenue']}", styles["Normal"]))

        doc.build(elements)
        buffer.seek(0)
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="sales_report.pdf"'
        return response
    
    def generate_excel(self, data):
        wb = Workbook()
        ws = wb.active
        ws.title = "Admin Sales Report"

        # Headers
        headers = ['Order ID', 'Date', 'Customer Name', 'Customer Email', 'Items', 'Payment Method', 
                'Order Total (₹)', 'Coupon Code', 'Status']
        ws.append(headers)

        # Style header
        header_fill = PatternFill(start_color="16213e", end_color="16213e", fill_type="solid")
        header_font = Font(color="FFFFFF", bold=True)
        for cell in ws[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center")

        # Data
        for order in data['orders']:
            ws.append([
                order.order_id,
                order.created_at.strftime('%d/%m/%Y'),
                order.user.full_name or '',
                order.user.email,
                order.items.count(),
                order.get_payment_method_display(),
                float(order.over_all_amount_all),
                # float(order.over_all_amount_all * 0.1),
                order.coupon_code or 'N/A',
                order.get_status_display()
            ])

        # Summary
        ws.append([])
        ws.append(['SALES SUMMARY'])
        ws.append([f"Report Period", data['period']])
        ws.append([f"Total Orders", data['total_orders']])
        ws.append([f"Total Items Sold", data['total_items']])
        ws.append([f"Total Revenue", f"₹{data['total_revenue']}"])
        # ws.append([f"Total Commission", f"₹{data['total_commission']}"])
        ws.append([f"Average Order Value", f"₹{data['avg_order']}"])

        # Auto-adjust columns
        for col in ws.columns:
            max_length = 0
            column = col[0].column_letter
            for cell in col:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = (max_length + 2)
            ws.column_dimensions[column].width = adjusted_width

        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        response = HttpResponse(buffer, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="NoteVia_Sales_Report_{data["period"]}.xlsx"'
        return response
    
@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class ReferralView(View):

    def get(self, request):

        if Referral.objects.filter(user=request.user).exists():
            referral = get_object_or_404(Referral, user=request.user)


        context = {
            "user_id": request.user.id,
            "user_profile": profile(request),
            "referral": referral
        }
        return render(request, 'products/referral.html', context)
    

class WishListView(View):

    def get(self, request):
        
        wishlist = request.user.wishlist
        wishlist_items = WishlistItem.objects.filter(wishlist=wishlist)


        context = {
            "user_id": request.user.id,
            "wishlist_items": wishlist_items
        }

        return render(request, 'products/wishlist.html', context)
    
@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class AddToWishList(View):

    def get(self, request):

        if not request.GET.get('product_id'):

            return redirect('wishlist_view')

        product_id = request.GET.get('product_id')
        wishlist = request.user.wishlist
        print('wish list id', wishlist.id)
        product = Product.objects.get(id=product_id)
        WishlistItem.objects.get_or_create(
            wishlist=wishlist,
            product=product,
            )
        # variant = Variant.objects.get(id=variant_id)

        return redirect('wishlist_view')
    
@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class RemoveToWishlist(View):
    
    def get(self, request):

        if not request.GET.get('product_id'):
            return redirect('shop_products')
        
        product_id = request.GET.get('product_id')
        wishlist = request.user.wishlist
        product = Product.objects.get(id=product_id)
        WishlistItem.objects.filter(wishlist=wishlist, product=product).delete()

        return redirect('shop_products')
