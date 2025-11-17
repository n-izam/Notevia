from django.shortcuts import render, redirect, get_object_or_404
# from django.contrib.auth import authenticate, login
from django.contrib.auth.mixins import LoginRequiredMixin
# from django.views.decorators.http import require_POST
from django.utils import timezone
import json
import re
from django.urls import reverse_lazy
from django.http import HttpResponse
from django.contrib import messages
from django.views.generic import View, DeleteView, UpdateView
from accounts.models import CustomUser
from .models import Category, Offer, Brand, Product, ProductImage, Variant
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from accounts.utils import warning_notify, info_notify,success_notify, error_notify
from django.http import JsonResponse
from datetime import datetime, timedelta
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q, Sum, F
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from cart.models import Cart, CartItem
from .forms import OfferForm, VariantForm
from orders.models import Order, OrderItem
from decimal import Decimal
from django.db.models.functions import Coalesce
from collections import defaultdict



# Create your views here.


@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
# dashboard view
class AdminDashView(View):

    
    def get(self, request, user_id):
        # user = CustomUser.objects.filter(id = user_id)
        total_customers = CustomUser.objects.count()
        total_orders = Order.objects.count()
        total_pending = Order.objects.filter(status='Pending').count()
        orders = Order.objects.exclude(status__in=['Cancelled', 'Payment Failed']).order_by('-created_at')
        delivered_orders = Order.objects.filter(status='Delivered')


        total_sales = sum(order.over_all_amount_all for order in delivered_orders if order.over_all_amount_all)

        now = timezone.now()

        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        hourly_data = defaultdict(Decimal)
        today_orders = OrderItem.objects.filter(
            order__status='Delivered',
            order__is_paid=True,
            order__created_at__gte=today_start
        )

        for item in today_orders:
            hour = item.order.created_at.hour
            hourly_data[hour] += item.quantity * (item.discount_price or item.price)
        
        day_labels = [f"{h % 12 if h % 12 != 0 else 12} {'AM' if h < 12 else 'PM'}" for h in range(24)]
        day_data = [float(hourly_data[h]) for h in range(24)]  # Convert to float for JSON

        # Week: Daily sales for last 7 days
        week_start = now - timedelta(days=6)
        daily_data = defaultdict(Decimal)
        week_orders = OrderItem.objects.filter(
            order__status='Delivered',
            order__is_paid=True,
            order__created_at__gte=week_start
        )
        for item in week_orders:
            day = item.order.created_at.date()
            daily_data[day] += item.quantity * (item.discount_price or item.price)
        
        week_labels = [(week_start + timedelta(days=i)).strftime('%A') for i in range(7)]
        week_data = [float(daily_data.get((week_start + timedelta(days=i)).date(), 0)) for i in range(7)]
        
        # Month: Monthly sales for last 12 months
        month_start = now.replace(day=1) - timedelta(days=365)  # Approx last 12 months
        monthly_data = defaultdict(Decimal)
        month_orders = OrderItem.objects.filter(
            order__status='Delivered',
            order__is_paid=True,
            order__created_at__gte=month_start
        )
        for item in month_orders:
            month_key = item.order.created_at.strftime('%b %Y')
            monthly_data[month_key] += item.quantity * (item.discount_price or item.price)
        
        # Generate labels for last 12 months
        month_labels = []
        month_data = []
        current = now.replace(day=1)
        for i in range(12):
            label = current.strftime('%b')
            month_labels.append(label)
            # Use the month key without year for matching (assuming current year dominance)
            full_key = f"{label} {current.year}"
            month_data.append(float(monthly_data.get(full_key, 0)))
            current -= timedelta(days=32)  # Rough month subtract
            current = current.replace(day=1)
        
        # Year: Yearly sales for last 6 years (matching static example)
        year_start = now.year - 5
        yearly_data = defaultdict(Decimal)
        year_orders = OrderItem.objects.filter(
            order__status='Delivered',
            order__is_paid=True,
        )
        for item in year_orders:
            year = item.order.created_at.year
            yearly_data[year] += item.quantity * (item.discount_price or item.price)
        
        year_labels = [str(y) for y in range(year_start, year_start + 6)]
        year_data = [float(yearly_data.get(int(y), 0)) for y in year_labels]

        chart_data_json = {
            'day': {'labels': day_labels, 'data': day_data},
            'week': {'labels': week_labels, 'data': week_data},
            'month': {'labels': month_labels, 'data': month_data},
            'year': {'labels': year_labels, 'data': year_data},
        }

        context = {
            "user_id": request.user.id,
            "total_customers": total_customers,
            "total_orders": total_orders,
            "total_sales": f"₹{total_sales:,.2f}",
            "total_pending": total_pending,
            "chart_data": json.dumps(chart_data_json),
            # For change percentages (static for now; make dynamic if needed with prev period queries)
            "customers_change": "↑ 16% this month",
            "orders_change": "↑ 8% this month",
            "sales_change": "↑ 12% this month",
            "pending_change": "↓ 3% this month",
        }

        print(total_sales)

        return render(request, 'adminpanel/admindash.html', context)

# admin product list view

@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class AdminProductView(View):
    def get(self, request):

        search_q = request.GET.get('q', '').strip()
        cat_option = request.GET.get('cat', '').strip()
        print("search query: ", search_q, "category query", cat_option)

        products = Product.objects.all().order_by('-updated_at')
        categories = Category.objects.filter(is_listed=True)

        if search_q:
            products = products.filter(Q(brand__name__icontains=search_q)| 
                                       Q(category__name__icontains=search_q))
            
        if cat_option and cat_option.lower() != 'clear':
            products = products.filter(category__name__iexact=cat_option)

        page_number = request.GET.get('page', 1)
        per_page = 5  # e.g., show 5 items per page
        paginator = Paginator(products, per_page)
        try:
            page_obj = paginator.page(page_number)
        except PageNotAnInteger:
            # If page is not an integer, deliver first page.
            page_obj = paginator.page(1)
        except EmptyPage:
            # If page is out of range (e.g., page_number too high), deliver last page.
            page_obj = paginator.page(paginator.num_pages)

        productimages = ProductImage.objects.all()

        contex = {
            "user_id": request.user.id,
            "products": page_obj.object_list,
            "page_obj": page_obj,
            "paginator": paginator,
            "categories": categories,
            "query": search_q,
            "cat_option" : cat_option,
            "per_page": per_page,
        }

        return render(request, 'adminpanel/product-main.html', contex)


@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class AddProductView(LoginRequiredMixin, View):
    def get(self, request):
        brands = Brand.objects.all()
        categories = Category.objects.filter(is_listed=True)
        return render(request, 'adminpanel/product_add.html', {
            'brands': brands,
            'categories': categories, "user_id": request.user.id
        })
    
    def post(self, request):
        try:
            errors = {}

            # --- Product Fields ---
            product_name = request.POST.get('product_name', '').strip()
            product_description = request.POST.get('product_description', '').strip()
            category_id = request.POST.get('category')
            brand_id = request.POST.get('brand')

            print("brand is ",brand_id, "product name is ", product_name, "product description:", product_description, "category_id", category_id)

            if not product_name:
                errors['product_name'] = 'Product name is required.'
            if not product_description:
                errors['product_description'] = 'Product description is required.'
            if not category_id or not Category.objects.filter(id=category_id, is_listed=True).exists():
                errors['category'] = 'Valid category is required.'
            if not brand_id or not Brand.objects.filter(id=brand_id).exists():
                errors['brand'] = 'Valid brand is required.'

            # --- Images ---
            for i in range(1, 4):
                print(f"image {i} are:",request.FILES.get(f'cropped_image_{i}'))
            
            images = [request.FILES.get(f'cropped_image_{i}') for i in range(1, 4)]
            images = [img for img in images if img]
            
            if len(images) < 3:
                errors['images'] = 'At least 3 images are required.'

            print("the viariant is listed :",request.POST.get('variant_is_listed') )
            # --- Variant ---
            variant_name = request.POST.get('variant_name', '').strip()
            variant_description = request.POST.get('variant_description', '').strip()
            variant_price = request.POST.get('variant_price', '').strip()
            variant_discount = request.POST.get('variant_discount', '0').strip()
            variant_stock = request.POST.get('variant_stock', '').strip()
            variant_is_listed = request.POST.get('variant_is_listed') == 'on'

            print("variant name :", variant_name,"variant description :", variant_description, "variant_price :", variant_price, "variant_discount :", variant_discount, "variant stock :", variant_stock, "variant is listed :", variant_is_listed)

            if not variant_name:
                errors['variant_name'] = 'Variant name is required.'
            if not variant_price or not re.match(r'^\d+(\.\d{1,2})?$', variant_price):
                errors['variant_price'] = 'Variant price must be a valid number (e.g., 99.99).'
            if not variant_stock.isdigit() or int(variant_stock) < 0:
                errors['variant_stock'] = 'Variant stock must be a non-negative integer.'
            if not re.match(r'^\d+(\.\d{1,2})?$|^0$', variant_discount):
                errors['variant_discount'] = 'Variant discount must be a valid number (e.g., 10.00) or 0.'

            if errors:
                return JsonResponse({'success': False, 'errors': errors}, status=400)

            # --- Save Product ---
            # product = Product.objects.create(
            #     name=product_name,
            #     description=product_description,
            #     category=category_id,
            #     brand=brand_id
            # )
            category = get_object_or_404(Category, id=category_id)
            brand = get_object_or_404(Brand, id=brand_id)

            if Product.objects.filter(name__iexact=product_name, brand=brand, category=category).exists():
                
                errors['product_name'] = 'Another product with this name, brand, and category already exists.'
            
            
            if errors:
                return JsonResponse({'success': False, 'errors': errors}, status=400)

            print("category:",category, "brand:",brand)
            product = Product.objects.create(name=product_name, description=product_description, category=category, brand=brand)
            print("product is added", product)

            variant = Variant.objects.create(product=product, name=variant_name, description=variant_description, price=variant_price, discount=variant_discount, stock=variant_stock, is_listed=variant_is_listed)
            print("variant is added", variant)

            # --- Save Images ---
            for index, image in enumerate(images):
                productimage = ProductImage.objects.create( product=product, image=image, is_main=(index == 0) )
                
                print("product image is added", productimage)

            

            # --- Save Variant ---
            # Variant.objects.create(
            #     product=product,
            #     name=variant_name,
            #     description=variant_description,
            #     price=float(variant_price),
            #     discount=float(variant_discount),
            #     stock=int(variant_stock),
            #     is_listed=variant_is_listed
            # )

            return JsonResponse({'success': True, 'message': 'Product added successfully!'})

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
        

# edit product
@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class EditProductView(View):

    def get(self, request, product_id):
        product = get_object_or_404(Product, id=product_id)
        brands = Brand.objects.all()
        images = product.images.all()

        categories = Category.objects.filter(is_listed=True)

        return render(request, 'adminpanel/edit_product.html', {"product": product, "user_id":request.user.id, "brands":brands, "categories":categories, "images": images})
    def post(self, request, product_id):
        try:
            errors = {}

            # --- Product Fields ---
            product_name = request.POST.get('product_name', '').strip()
            product_description = request.POST.get('product_description', '').strip()
            category_id = request.POST.get('category')
            brand_id = request.POST.get('brand')

            print("brand is ",brand_id, "product name is ", product_name, "product description:", product_description, "category_id", category_id)

            if not product_name:
                errors['product_name'] = 'Product name is required.'
            if not product_description:
                errors['product_description'] = 'Product description is required.'
            if not category_id or not Category.objects.filter(id=category_id, is_listed=True).exists():
                errors['category'] = 'Valid category is required.'
            if not brand_id or not Brand.objects.filter(id=brand_id).exists():
                errors['brand'] = 'Valid brand is required.'

            # --- Images ---
            for i in range(1, 4):
                print(f"image {i} are:",request.FILES.get(f'cropped_image_{i}'))
            
            images = [request.FILES.get(f'cropped_image_{i}') for i in range(1, 4)]
            images = [img for img in images if img]
            
            if len(images) < 3:
                errors['images'] = 'At least 3 images are required.'

            if errors:
                return JsonResponse({'success': False, 'errors': errors}, status=400)
            
            category = get_object_or_404(Category, id=category_id)
            brand = get_object_or_404(Brand, id=brand_id)

            product = get_object_or_404(Product, id=product_id)
            if Product.objects.filter(name__iexact=product_name, brand=brand, category=category).exclude(id=product.id).exists():
                
                errors['product_name'] = 'Another product with this name, brand, and category already exists.'


            if errors:
                return JsonResponse({'success': False, 'errors': errors}, status=400)


            product.name = product_name
            product.description = product_description
            product.category = category
            product.brand = brand
            product.save()
            
            if images:
                ProductImage.objects.filter(product_id=product_id).delete()

                for index, image in enumerate(images):
                    ProductImage.objects.create(
                        product=product, image=image, is_main=(index == 0)
                        )

            
            print("product update successfully")

            return JsonResponse({'success': True, 'message': 'Product added successfully!'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class AddProductOfferView(View):
    def get(self, request, product_id): # add product id
        product = get_object_or_404(Product, id=product_id)

        errors = request.session.pop("add_offer_error", None)
        data = request.session.pop("add_offer_data", None)

        form = OfferForm(data if data else None)

        if errors:
            form._errors = errors
        
        context = {
            "user_id": request.user.id,
              "product": product,
              "form": form
              }
        return render(request, 'adminpanel/product_offer.html', context)
    
    def post(self, request, product_id):
        product = get_object_or_404(Product, id=product_id)

        form = OfferForm(request.POST)
        if form.is_valid():

            title = request.POST.get('offer_title')
            about = request.POST.get('about')
            discount = request.POST.get('discount')
            start_date = request.POST.get('start_date')
            end_date = request.POST.get('end_date')

            # if not title:
            #     error_notify(self.request, 'Leave offer title ' )
            #     return redirect('addproduct_offer', product_id=product_id)
            # if not about:
            #     error_notify(self.request, 'Leave offer discription ' )
            #     return redirect('addproduct_offer', product_id=product_id)
            # if not discount:
            #     error_notify(self.request, 'Leave product offer discount ' )
            #     return redirect('addproduct_offer', product_id=product_id)
            # if not start_date:
            #     error_notify(self.request, 'Set product offer start date ' )
            #     return redirect('addproduct_offer', product_id=product_id)
            # if not end_date:
            #     error_notify(self.request, 'Set product offer End date ' )
            #     return redirect('addproduct_offer', product_id=product_id)


            # print("title",title)

            start_date = datetime.strptime(start_date, '%m/%d/%Y').date()
            end_date = datetime.strptime(end_date, '%m/%d/%Y').date()

            # today = timezone.now().date()

            # print(start_date,"today",today)
            # if not start_date >= today:
            #     error_notify(self.request, 'Start date must be greater than equal to today ' )
            #     return redirect('addproduct_offer', product_id=product_id)
            # if not end_date > today:
            #     error_notify(self.request, 'End date must be greater than today' )
            #     return redirect('addproduct_offer', product_id=product_id)

            offer = Offer.objects.create(
                title=title, offer_percent=discount, about=about,
                start_date=start_date, end_date=end_date,
            )
            print("offer created", offer)

            product.offer = offer
            product.save()
            success_notify(request, f"successfully add offer is add for product")
            return redirect('admin-product')
        else:
            request.session["add_offer_error"] = form.errors
            request.session["add_offer_data"] = request.POST
            return redirect('addproduct_offer', product_id=product_id)


@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class EditProductOfferView(View):
    def get(sel, request, product_id): #add product is also
        product = get_object_or_404(Product, id=product_id)

        errors = request.session.pop("edit_product_offer_error", None)
        data = request.session.pop("edit_product_offer_data", None)

        form = OfferForm(data if data else None)

        if errors:
            form._errors = errors

        context = {
            "user_id": request.user.id,
              "product": product,
              "form": form
              }
        return render(request, 'adminpanel/product_offer.html', context)
    
    def post(self, request, product_id):
        product = get_object_or_404(Product, id=product_id)

        form = OfferForm(request.POST)
        if form.is_valid():


            title = request.POST.get('offer_title', '').strip()

            description = request.POST.get('about', '').strip()

            offer_discount = request.POST.get('discount')

            start_date = request.POST.get('start_date')

            end_date = request.POST.get('end_date')
            print(title, description, offer_discount, start_date, end_date)

            
            start_date = datetime.strptime(start_date, '%m/%d/%Y').date()

            end_date = datetime.strptime(end_date, '%m/%d/%Y').date()

            offer = get_object_or_404(Offer, id=product.offer_id)

            offer.title = title
            offer.about = description
            offer.offer_percent = offer_discount
            offer.start_date = start_date
            offer.end_date = end_date

            offer.save()
            success_notify(request, f"successfully updated offer{offer.title} is add for product{product.name}")
            return redirect('admin-product')
        else:
            request.session["edit_product_offer_error"] = form.errors
            request.session["edit_product_offer_data"] = request.POST
            return redirect('editproduct_offer', product_id=product_id)


@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class RemoveProductOfferView(View):

    def get(self, request, product_id):

        product = get_object_or_404(Product, id=product_id)
        product.offer = None
        product.save()
        return redirect('admin-product')

@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class ToggleProductStatusView(View):

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        
        # print("the variants are ", variants)
        product.is_listed = not product.is_listed
        product.save()

        Variant.objects.filter(product=product).update(is_listed=product.is_listed)
        # variants = get_object_or_404(Variant, product_id=product.id)
        # print("the variants are ", variants)

        print("product is listed :", product.is_listed)
        return JsonResponse({'success': True, 'is_listed': product.is_listed})

        

@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class AddBrandView(LoginRequiredMixin, View):
    def post(self, request):
        try:
            data = json.loads(request.body)
            brand_name = data.get('brand_name', '').strip()
            if not brand_name:
                return JsonResponse({'success': False, 'error': 'Brand name is required.'}, status=400)
            if Brand.objects.filter(name__iexact=brand_name).exists():
                return JsonResponse({'success': False, 'error': 'Brand already exists.'}, status=400)
            brand = Brand.objects.create(name=brand_name)
            return JsonResponse({'success': True, 'brand': {'id': brand.id, 'name': brand.name}})
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON payload.'}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

# admin customers list view 

@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class AdminCustomersView(View):
    
    def get(self, request):

        search_q = request.GET.get('q', '').strip()

        customers = CustomUser.objects.all().exclude(is_superuser=True).order_by('-id')

        if search_q:
            customers = customers.filter(Q(full_name__icontains=search_q)| 
                                       Q(email__icontains=search_q))



        return render(request, 'adminpanel/customers.html', {"user_id": request.user.id, "customers": customers})
    

@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class ToggleCustomerStatusView(View):

    def post(self, request, pk):
        user = get_object_or_404(CustomUser, pk=pk)
        
        # print("the variants are ", variants)
        user.is_active = not user.is_active
        user.save()

        # Variant.objects.filter(product=product).update(is_listed=product.is_listed)
        # variants = get_object_or_404(Variant, product_id=product.id)
        # print("the variants are ", variants)

        print("customer is active :", user.is_active)
        return JsonResponse({'success': True, 'is_active': user.is_active})
    

    
# admin category list view
@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class AdminCategoryView(View):

    def get(self, request):

        search_q = request.GET.get('q', '').strip()

        category = Category.objects.all()

        if search_q:
            category = category.filter(Q(name__icontains=search_q))

        return render(request, 'adminpanel/category.html', {"category": category, "user_id":request.user.id})

# for category listing/unlisting
@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class TogglCategoryStatusView(View):
    def post(self, request, pk):
        category = get_object_or_404(Category, pk=pk)
        category.is_listed = not category.is_listed
        category.save()
        print("category is listed", category.is_listed)
        return JsonResponse({'success': True, 'is_list': category.is_listed})
    

# category add view 
@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class AddCategoryView(View):

    def get(self, request):

        return render(request, 'adminpanel/add-category.html', {"user_id": request.user.id})
    
    def post(self, request):

        category_name = request.POST.get('category_name')
        description = request.POST.get('description')

        status = request.POST.get('categoryStatus')
        # return HttpResponse(f"the status is {status}")

        if status == 'listed':
            is_listed = True
        else:
            is_listed = False

        if not category_name:
            
            info_notify(request, "enter the category name")
            return redirect('add-category')
        elif not description:
            
            info_notify(request, "give any description")
            return redirect('add-category')
        
        else:
            category = Category.objects.create(name=category_name, description=description, is_listed=is_listed)
            category.save()
            print("category created")

            return redirect('admin-category')

# edit categkory
@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class CategoryUpdateView(UpdateView):
    model = Category
    fields = ['name', 'description']
    template_name = 'adminpanel/add-category.html'
    success_url = reverse_lazy('admin-category')

    def form_valid(self, form):

        name = form.cleaned_data['name']
        category_id = self.get_object().id

        if Category.objects.filter(name__iexact=name).exclude(id=category_id).exists():
            form.add_error('name',"Category with this name already exists.")
            return self.form_invalid(form)
        success_notify(self.request, "Category update successfully")
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)
        print("request.user =", self.request.user)
        print("type =", type(self.request.user))
        context['user_id'] = self.request.user.id
        return context
    

@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class AddCategoryOffer(View):
    def get(self, request, category_id):
        category = get_object_or_404(Category, id=category_id)
        today = timezone.now().date()
        print(today)
        
        print("category id", category.id)
        errors = request.session.pop("add_category_offer_error", None)
        data = request.session.pop("add_category_offer_data", None)

        form = OfferForm(data if data else None)

        if errors:
            form._errors = errors

        context = {
            "user_id":request.user.id,
              "category": category,
              "form": form
              }

        return render(request, 'adminpanel/addcategory-offer.html', context)

    def post(self, request, category_id):
        category = get_object_or_404(Category, id=category_id)
        print(category)
        # offer = get_object_or_404(Offer, id=category.o)

        form = OfferForm(request.POST)
        if form.is_valid():

            title = request.POST.get('offer_title')
            about = request.POST.get('about')
            discount = request.POST.get('discount')
            start_date = request.POST.get('start_date')
            end_date = request.POST.get('end_date')

            # print("title",title)
            # today = timezone.now().date()

            start_date = datetime.strptime(start_date, '%m/%d/%Y').date()
            end_date = datetime.strptime(end_date, '%m/%d/%Y').date()

            # print(start_date,"today",today)
            # if not start_date >= today:
            #     error_notify(self.request, 'Start date must be greater than equal to today ' )
            #     return redirect('addcategory_offer', category_id=category_id)
            # if not end_date > today:
            #     error_notify(self.request, 'End date must be greater than today' )
            #     return redirect('addcategory_offer', category_id=category_id)

            offer = Offer.objects.create(
                title=title, offer_percent=discount, about=about,
                start_date=start_date, end_date=end_date,
            )
            print("offer created", offer)

            category.offer = offer
            category.save()
            success_notify(request, f"successfully add the offer for category")
            return redirect('admin-category')
        else:
            request.session["add_category_offer_error"] = form.errors
            request.session["add_category_offer_data"] = request.POST
            return redirect('addcategory_offer', category_id=category_id)


@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class EditCategoryOffer(View):

    def get(self, request, category_id):

        category = get_object_or_404(Category, id=category_id)
        errors = request.session.pop("edit_category_offer_error", None)
        data = request.session.pop("edit_category_offer_data", None)

        form = OfferForm(data if data else None)

        if errors:
            form._errors = errors
        context = {
            "user_id":request.user.id,
              "category": category,
              "form": form
              }

        return render(request, 'adminpanel/addcategory-offer.html', context)
    
    def post(self, request, category_id):

        category = get_object_or_404(Category, id=category_id)

        # find offer using foreign key
        offer = get_object_or_404(Offer, id=category.offer_id)
        print("the offer title is :", offer.title)

        form = OfferForm(request.POST)
        if form.is_valid():
            title = request.POST.get('offer_title')
            about = request.POST.get('about')
            discount = request.POST.get('discount')
            start_date = request.POST.get('start_date')
            end_date = request.POST.get('end_date')


            start_date = datetime.strptime(start_date, '%m/%d/%Y').date()

            end_date = datetime.strptime(end_date, '%m/%d/%Y').date()


            offer.title = title
            offer.about = about
            offer.offer_percent = discount
            offer.start_date = start_date
            offer.end_date = end_date
            offer.save()

            
            success_notify(request, f"successfully updated the offer for category")
            return redirect('admin-category')
        else:
            request.session["edit_category_offer_error"] = form.errors
            request.session["edit_category_offer_data"] = request.POST
            return redirect('editcategory_offer', category_id=category_id)

@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class RemoveCategoryOfferView(View):

    def get(self, request, category_id):
        category = get_object_or_404(Category, id=category_id)
        category.offer = None
        category.save()
        return redirect('admin-category')

@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class CategoryDeleteView(DeleteView):

    model = Category
    template_name = "adminpanel/category_confirm_delete.html"
    success_url = reverse_lazy('admin-category')

    def post(self, request, *args, **kwargs):
        category = self.get_object()
        category.is_listed = False  # Mark as unlisted
        category.save()
        return redirect(self.success_url)







        
# varient view of each products
@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class ViewVariantView(View):

    def get(self, request, product_id):# we see variants for specific product in product addinf time use (product id)

        product = get_object_or_404(Product, id=product_id)
        variants = Variant.objects.filter(product_id=product_id)

        return render(request, 'adminpanel/view-variant.html', {"user_id": request.user.id, "product": product, "variants": variants})
    
@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class AddVariantView(View):

    def get(self, request, product_id):# we add variants for specific product in product addinf time use (product id)

        product = get_object_or_404(Product, id=product_id)

        errors = request.session.pop("add_variant_error", None)
        data = request.session.pop("add_variant_data", None)

        form = VariantForm(data if data else None)

        if errors:
            form._errors = errors

        context = {
            "user_id": request.user.id,
              "product": product,
              "form": form
              }

        return render(request, 'adminpanel/add-variant.html', context)
    
    def post(self, request, product_id):


        form = VariantForm(request.POST)
        if form.is_valid():
            variant_name = request.POST.get('name', '').strip()
            variant_description = request.POST.get('description', '').strip()
            variant_price = request.POST.get('price', '').strip()
            variant_discount = request.POST.get('discount_percent', '0').strip()
            variant_stock = request.POST.get('stock', '').strip()
            variant_is_listed = request.POST.get('variant_is_listed') == 'on'

            print("variant name :", variant_name,"variant description :", variant_description, "variant_price :", variant_price, "variant_discount :", variant_discount, "variant stock :", variant_stock, "variant is listed :", variant_is_listed)

            # if not variant_name:
                
            #     error_notify(self.request, 'Variant name is required.')
            #     return redirect('add-variant', product_id=product_id)
            # elif not variant_price or not re.match(r'^\d+(\.\d{1,2})?$', variant_price):

            #     # errors['variant_price'] = 'Variant price must be a valid number (e.g., 99.99).'
            #     error_notify(self.request, 'Variant price must be a valid number (e.g., 99.99).')
            #     return redirect('add-variant', product_id=product_id)
            # elif not variant_stock.isdigit() or int(variant_stock) < 0:
            #     # errors['variant_stock'] = 'Variant stock must be a non-negative integer.'
            #     error_notify(self.request, 'Variant stock must be a non-negative integer.')
            #     return redirect('add-variant', product_id=product_id)
            # elif not re.match(r'^\d+(\.\d{1,2})?$|^0$', variant_discount):
            #     # errors['variant_discount'] = 'Variant discount must be a valid number (e.g., 10.00) or 0.'
            #     error_notify(self.request, 'Variant discount must be a valid number (e.g., 10.00) or 0.')
            #     return redirect('add-variant', product_id=product_id)
            if Variant.objects.filter(product_id=product_id, name__iexact=variant_name).exists():
                # error_notify(self.request, 'Variant name already exists for this product.')
                request.session["add_variant_error"] = {"name": ["Variant name already exists for this product."]}
                request.session["add_variant_data"] = request.POST
                return redirect('add-variant', product_id=product_id)
            
            product = get_object_or_404(Product, id=product_id)

            variant = Variant.objects.create(product=product, name=variant_name, description=variant_description, price=variant_price, discount=variant_discount, stock=variant_stock, is_listed=variant_is_listed)
            success_notify(request, "new variant added successfully")
            return redirect('view-variant', product_id=product_id)
        else:
            request.session["add_variant_error"] = form.errors
            request.session["add_variant_data"] = request.POST
            return redirect('add-variant', product_id=product_id)


@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class EditVariantView(View):

    def get(self, request, variant_id):
        
        variant = get_object_or_404(Variant, id=variant_id)
        product = get_object_or_404(Product, id=variant.product.id)

        errors = request.session.pop("edit_variant_error", None)
        data = request.session.pop("edit_variant_data", None)

        form = VariantForm(data if data else None)

        if errors:
            form._errors = errors

        context = {
            "variant":variant, 
            "user_id": request.user.id,
            "product": product,
            "form":form
            }
    
        # the offer final price test
        # print("main discount:", variant.final_price)
        # print("variant price:", variant.price, "variant discount", variant.discount)
        # print("product category offer", variant.product.category.offer.offer_percent)

        return render(request, 'adminpanel/add-variant.html', context)

    def post(self, request, variant_id):

        variant = get_object_or_404(Variant, id=variant_id)
        product = get_object_or_404(Product, id=variant.product.id)

        form = VariantForm(request.POST)
        if form.is_valid():

            variant_name = request.POST.get('name', '').strip()
            variant_description = request.POST.get('description', '').strip()
            variant_price = request.POST.get('price', '').strip()
            variant_discount = request.POST.get('discount_percent', '0').strip()
            variant_stock = request.POST.get('stock', '').strip()


            
            if Variant.objects.filter(product_id=product.id, name__iexact=variant_name).exclude(id=variant_id).exists():
                
                request.session["edit_variant_error"] = {"name": ["Variant name already exists for this product."]}
                request.session["edit_variant_data"] = request.POST
                return redirect('edit_variant', variant_id=variant_id)

            print("variant name :", variant_name,"variant description :", variant_description, "variant_price :", variant_price, "variant_discount :", variant_discount, "variant stock :", variant_stock)

            variant.name = variant_name
            variant.description = variant_description
            variant.price = variant_price
            variant.discount = variant_discount
            variant.stock = variant_stock
            variant.save()

            success_notify(request, "new variant Updated successfully")
            return redirect('view-variant', product_id=product.id)
        else:
            request.session["edit_variant_error"] = form.errors
            request.session["edit_variant_data"] = request.POST
            return redirect('edit_variant', variant_id=variant_id)


@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class ToggleVariatStatusView(View):

    def post(self, request, pk):
        variant = get_object_or_404(Variant, pk=pk)
        
        # print("the variants are ", variants)
        variant.is_listed = not variant.is_listed
        variant.save()
        # if (variant.is_listed and variant.product.is_listed and variant.product.category.is_listed):
        #     print('nisam')

        #     CartItem.objects.filter(product=variant.product, variant=variant, is_active=False).update(is_active=True)
        # elif not (variant.is_listed and variant.product.is_listed and variant.product.category.is_listed):
        #     print('variant', variant.is_listed)
        #     cart_items = CartItem.objects.filter(product=variant.product, variant=variant, is_active=True).update(is_active=False)

        # Variant.objects.filter(product=product).update(is_listed=product.is_listed)
        # variants = get_object_or_404(Variant, product_id=product.id)
        # print("the variants are ", variants)

        
        return JsonResponse({'success': True, 'is_listed': variant.is_listed})
