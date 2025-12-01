from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.utils import timezone
from datetime import datetime
from accounts.utils import error_notify, success_notify, info_notify
from .models import Coupon, CouponUsage
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.core.paginator import Paginator
from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import login_required
from .forms import CouponForm
# Create your views here.

@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class AdminCouponListingView(View):

    def get(self, request):

        coupons = Coupon.objects.all().order_by('-valid_from')

        paginator = Paginator(coupons, 8)
        page_number = request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)

        start_index = (page_obj.number - 1) * paginator.per_page + 1
        end_index = start_index + len(page_obj.object_list) - 1

        if request.session.get("add_coupon_error"):
            errors = request.session.pop("add_coupon_error", None)
            data = request.session.pop("add_coupon_data", None)

            form = CouponForm(data if data else None)

            if errors:
                form._errors = errors
    
        elif request.session.get("edit_coupon_error"):
            errors = request.session.pop("edit_coupon_error", None)
            data = request.session.pop("edit_coupon_data", None)
            form = CouponForm(data if data else None)

            if errors:
                form._errors = errors
        else:
            form = CouponForm()

        # form = CouponForm(data if data else None)

        
        
        context = {
            "user_id": request.user.id,
            "coupons": page_obj, 
            "paginator": paginator,
            "page_obj": page_obj,
            "start_index": start_index,
            "end_index": end_index,
            "form": form
            
        }

        return render(request, 'offers/admin_coupon.html', context)
    
@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class AddCouponView(View):
    

    def post(self, request):
        form = CouponForm(request.POST)

        if form.is_valid():

            coupon_code = request.POST.get('coupon_name', '').strip()
            limit = request.POST.get('limit')
            max_price = request.POST.get('max_price')
            min_price = request.POST.get('minpurchase')
            discount = request.POST.get('discount')
            start_date = request.POST.get('start_date')
            end_date = request.POST.get('end_date')

            
            if Coupon.objects.filter(code__iexact=coupon_code).exists():
                request.session["add_coupon_error"] = {"coupon_name": ["this coupon is alreary exists."]}
                request.session["add_coupon_data"] = request.POST
                return redirect('/offers/coupons/?open_modal=add')
            
            
            
            coupon = Coupon.objects.create(code=coupon_code, usage_limit=limit, max_redeemable_price=max_price, 
                                        min_purchase_amount=min_price, discount_percentage=discount, valid_from=start_date, valid_to=end_date)
            
            
            
            success_notify(request, 'Coupon added successfully')
            return redirect('admin_coupon_list')
        else:
            request.session["add_coupon_error"] = form.errors
            request.session["add_coupon_data"] = request.POST
            return redirect('/offers/coupons/?open_modal=add')

    
@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(csrf_exempt, name='dispatch')
class ToggleStatusCouponView(View):

    def post(self, request, pk):

        coupon = get_object_or_404(Coupon, pk=pk)
        
        coupon.is_active = not coupon.is_active
        coupon.save()

        return redirect('admin_coupon_list')


@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class EditCouponView(View):

    def post(self, request):
        form = CouponForm(request.POST)
        if not request.POST.get('coupon_id'):
                error_notify(request, "try again")
                return redirect('admin_coupon_list')
        coupon_id = request.POST.get('coupon_id')
        
        if Coupon.objects.filter(id=coupon_id):
            coupon = get_object_or_404(Coupon, id=coupon_id)

        if form.is_valid():
            coupon_code = request.POST.get('coupon_name', '').strip()
            limit = request.POST.get('limit')
            max_price = request.POST.get('max_price')
            min_price = request.POST.get('minpurchase')
            discount = request.POST.get('discount')
            start_date = request.POST.get('start_date')
            end_date = request.POST.get('end_date')

            

            
            if Coupon.objects.filter(code__iexact=coupon_code).exclude(id=coupon_id).exists():
                request.session["edit_coupon_error"] = {"coupon_name": ["this coupon is alreary exists."]}
                request.session["edit_coupon_data"] = request.POST
                return redirect(f'/offers/coupons/?open_modal=edit&coupon_id={coupon.id}')

            
            
            
            
            # coupon = get_object_or_404(Coupon, id=coupon_id)
            
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
        else:
            request.session["edit_coupon_error"] = form.errors
            request.session["edit_coupon_data"] = request.POST
            return redirect(f'/offers/coupons/?open_modal=edit&coupon_id={coupon.id}')
        