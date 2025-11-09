from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.utils import timezone
from datetime import datetime
from accounts.utils import error_notify, success_notify, info_notify
from .models import Coupon, CouponUsage
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.core.paginator import Paginator
# Create your views here.


class AdminCouponListingView(View):

    def get(self, request):

        coupons = Coupon.objects.all().order_by('-valid_from')

        paginator = Paginator(coupons, 6)
        page_number = request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)

        start_index = (page_obj.number - 1) * paginator.per_page + 1
        end_index = start_index + len(page_obj.object_list) - 1

        
        context = {
            "user_id": request.user.id,
            "coupons": page_obj, 
            "paginator": paginator,
            "page_obj": page_obj,
            "start_index": start_index,
            "end_index": end_index,
            
        }

        return render(request, 'offers/admin_coupon.html', context)
    
class AddCouponView(View):

    def post(self, request):

        coupon_code = request.POST.get('coupon_name', '').strip()
        limit = request.POST.get('limit')
        max_price = request.POST.get('max_price')
        min_price = request.POST.get('min_price')
        discount = request.POST.get('discount')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')

        if not coupon_code:
            error_notify(request, "Please enter the coupon code")
            return redirect('/offers/coupons/?open_modal=add')
        if Coupon.objects.filter(code=coupon_code).exists():
            error_notify(self.request, 'The coupon code is already exists' )
            return redirect('/offers/coupons/?open_modal=add')
        if not limit:
            error_notify(request, "limit is required")
            return redirect('/offers/coupons/?open_modal=add')
        if not max_price:
            error_notify(request, "maximum discoount price required")
            return redirect('/offers/coupons/?open_modal=add')
        if not min_price:
            error_notify(request, "minimum purchase price required")
            return redirect('/offers/coupons/?open_modal=add')
        if not max_price:
            error_notify(request, "maximum discoount price")
            return redirect('/offers/coupons/?open_modal=add')
        if not start_date or not end_date:
            error_notify(request, "Please select both start and end dates")
            return redirect('/offers/coupons/?open_modal=add')
        today = timezone.now().date()
        print(start_date)
        
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

        if not start_date >= today:
            error_notify(self.request, 'Start date must be greater than equal to today ' )
            return redirect('/offers/coupons/?open_modal=add')
        if not end_date > today:
            error_notify(self.request, 'End date must be greater than today' )
            return redirect('/offers/coupons/?open_modal=add')
        
        coupon = Coupon.objects.create(code=coupon_code, usage_limit=limit, max_redeemable_price=max_price, 
                                       min_purchase_amount=min_price, discount_percentage=discount, valid_from=start_date, valid_to=end_date)
        
        
        
        success_notify(request, 'Coupon added successfully')
        return redirect('admin_coupon_list')
    
@method_decorator(csrf_exempt, name='dispatch')
class ToggleStatusCouponView(View):

    def post(self, request, pk):

        coupon = get_object_or_404(Coupon, pk=pk)
        
        coupon.is_active = not coupon.is_active
        coupon.save()

        return redirect('admin_coupon_list')

class EditCouponView(View):

    def post(self, request):

        coupon_code = request.POST.get('coupon_name', '').strip()
        limit = request.POST.get('limit')
        max_price = request.POST.get('max_price')
        min_price = request.POST.get('min_price')
        discount = request.POST.get('discount')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')

        if not request.POST.get('coupon_id'):
            error_notify(request, "try again")
            return redirect('admin_coupon_list')
        coupon_id = request.POST.get('coupon_id')

        if not coupon_code:
            error_notify(request, "Please enter the coupon code")
            return redirect('/offers/coupons/?open_modal=edit')
        if Coupon.objects.all().exclude(code=coupon_code).exists():
            error_notify(self.request, 'The coupon code is already exists' )
            return redirect('/offers/coupons/?open_modal=edit')
        if not limit:
            error_notify(request, "limit is required")
            return redirect('/offers/coupons/?open_modal=edit')
        if not max_price:
            error_notify(request, "maximum discoount price required")
            return redirect('/offers/coupons/?open_modal=edit')
        if not min_price:
            error_notify(request, "minimum purchase price required")
            return redirect('/offers/coupons/?open_modal=edit')
        if not max_price:
            error_notify(request, "maximum discoount price")
            return redirect('/offers/coupons/?open_modal=edit')
        if not start_date or not end_date:
            error_notify(request, "Please select both start and end dates")
            return redirect('/offers/coupons/?open_modal=edit')

        today = timezone.now().date()
        print(start_date)
        
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

        if not start_date >= today:
            error_notify(self.request, 'Start date must be greater than equal to today ' )
            return redirect('/offers/coupons/?open_modal=edit')
        if not end_date > today:
            error_notify(self.request, 'End date must be greater than today' )
            return redirect('/offers/coupons/?open_modal=edit')
        
        coupon = get_object_or_404(Coupon, id=coupon_id)
        coupon.code=coupon_code
        coupon.min_purchase_amount=min_price
        coupon.max_redeemable_price=max_price
        coupon.usage_limit=limit
        coupon.valid_from=start_date
        coupon.valid_to=end_date
        coupon.discount_percentage=discount
        coupon.save()

        success_notify(request, 'coupon updated successfully')
        return redirect('admin_coupon_list')
        