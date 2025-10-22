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
from datetime import datetime
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger



# Create your views here.


@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
# dashboard view
class AdminDashView(View):

    
    def get(self, request, user_id):
        # user = CustomUser.objects.filter(id = user_id)

        return render(request, 'adminpanel/admindash.html', {"user_id": request.user.id})

# admin product list view

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

            print("category:",category, "brand:",brand)
            product = Product.objects.create(name=product_name, description=product_description, category=category, brand=brand)
            print("product is added", product)

            variant = Variant.objects.create(product=product, name=variant_name, description=variant_description, price=variant_price, discount=variant_discount, stock=variant_stock, is_listed=variant_is_listed)
            print("variant is added", variant)

            # --- Save Images ---
            for index, image in enumerate(images):
                productimage = ProductImage.objects.create(
                    product=product,
                    image=image,
                    is_main=(index == 0)
                )
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
class EditProductView(View):

    def get(self, request, product_id):
        product = get_object_or_404(Product, id=product_id)
        brands = Brand.objects.all()
        categories = Category.objects.filter(is_listed=True)

        return render(request, 'adminpanel/edit_product.html', {"product": product, "user_id":request.user.id, "brands":brands, "categories":categories})
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

class AddProductOfferView(View):
    def get(self, request, product_id): # add product id
        product = get_object_or_404(Product, id=product_id)
        return render(request, 'adminpanel/product_offer.html', {"user_id": request.user.id, "product": product})
    
    def post(self, request, product_id):
        product = get_object_or_404(Product, id=product_id)

        title = request.POST.get('offer-title')
        about = request.POST.get('about')
        discount = request.POST.get('discount')
        start_date = request.POST.get('start-date')
        end_date = request.POST.get('end-date')



        print("title",title)

        start_date = datetime.strptime(start_date, '%m/%d/%Y').date()
        end_date = datetime.strptime(end_date, '%m/%d/%Y').date()

        today = timezone.now().date()

        print(start_date,"today",today)
        if not start_date >= today:
            error_notify(self.request, 'Start date must be greater than equal to today ' )
            return redirect('addproduct_offer', product_id=product_id)
        if not end_date > today:
            error_notify(self.request, 'End date must be greater than today' )
            return redirect('addproduct_offer', product_id=product_id)

        offer = Offer.objects.create(
            title=title, offer_percent=discount, about=about,
            start_date=start_date, end_date=end_date,
        )
        print("offer created", offer)

        product.offer = offer
        product.save()

        return redirect('admin-product')

class EditProductOfferView(View):
    def get(sel, request, product_id): #add product is also
        product = get_object_or_404(Product, id=product_id)
        return render(request, 'adminpanel/product_offer.html', {"user_id": request.user.id, "product": product})
    
    def post(self, request, product_id):
        product = get_object_or_404(Product, id=product_id)

        start_date = datetime.strptime(request.POST.get('start-date'), '%m/%d/%Y').date()

        end_date = datetime.strptime(request.POST.get('end-date'), '%m/%d/%Y').date()

        today = today = timezone.now().date()

        print(start_date,"today",today)
        if not start_date >= today:
            error_notify(self.request, 'Start date must be greater than equal to today ' )
            return redirect('editproduct_offer', product_id=product_id)
        if not end_date > today:
            error_notify(self.request, 'End date must be greater than today' )
            return redirect('editproduct_offer', product_id=product_id)

        offer = get_object_or_404(Offer, id=product.offer_id)

        offer.title = request.POST.get('offer-title')
        offer.about = request.POST.get('about')
        offer.offer_percent = request.POST.get('discount')
        offer.start_date = datetime.strptime(request.POST.get('start-date'), '%m/%d/%Y').date()
        offer.end_date = datetime.strptime(request.POST.get('end-date'), '%m/%d/%Y').date()

        offer.save()

        return redirect('admin-product')

class RemoveProductOfferView(View):

    def get(self, request, product_id):

        product = get_object_or_404(Product, id=product_id)
        product.offer = None
        product.save()
        return redirect('admin-product')

@method_decorator(csrf_exempt, name='dispatch')
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

class AdminCustomersView(View):
    
    def get(self, request):

        customers = CustomUser.objects.all().exclude(is_superuser=True)

        return render(request, 'adminpanel/customers.html', {"user_id": request.user.id, "customers": customers})
    
# admin category list view

class AdminCategoryView(View):

    def get(self, request):

        category = Category.objects.all()

        return render(request, 'adminpanel/category.html', {"category": category, "user_id":request.user.id})

# for category listing/unlisting

class TogglCategoryStatusView(View):
    def post(self, request, pk):
        category = get_object_or_404(Category, pk=pk)
        category.is_listed = not category.is_listed
        category.save()
        print("category is listed", category.is_listed)
        return JsonResponse({'success': True, 'is_list': category.is_listed})
    

# category add view 

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
    
class AddCategoryOffer(View):
    def get(self, request, category_id):
        category = get_object_or_404(Category, id=category_id)
        today = timezone.now().date()
        print(today)
        
        print("category id", category.id)
        return render(request, 'adminpanel/addcategory-offer.html', {"user_id":request.user.id, "category": category})

    def post(self, request, category_id):
        category = get_object_or_404(Category, id=category_id)
        print(category)
        # offer = get_object_or_404(Offer, id=category.o)

        title = request.POST.get('offer-title')
        about = request.POST.get('about')
        discount = request.POST.get('discount')
        start_date = request.POST.get('start-date')
        end_date = request.POST.get('end-date')

        print("title",title)
        today = timezone.now().date()

        start_date = datetime.strptime(start_date, '%m/%d/%Y').date()
        end_date = datetime.strptime(end_date, '%m/%d/%Y').date()

        print(start_date,"today",today)
        if not start_date >= today:
            error_notify(self.request, 'Start date must be greater than equal to today ' )
            return redirect('addcategory_offer', category_id=category_id)
        if not end_date > today:
            error_notify(self.request, 'End date must be greater than today' )
            return redirect('addcategory_offer', category_id=category_id)

        offer = Offer.objects.create(
            title=title, offer_percent=discount, about=about,
            start_date=start_date, end_date=end_date,
        )
        print("offer created", offer)

        category.offer = offer
        category.save()

        return redirect('admin-category')

class EditCategoryOffer(View):

    def get(self, request, category_id):

        category = get_object_or_404(Category, id=category_id)
        

        return render(request, 'adminpanel/addcategory-offer.html', {"user_id":request.user.id, "category": category})
    
    def post(self, request, category_id):

        category = get_object_or_404(Category, id=category_id)

        # find offer using foreign key
        offer = get_object_or_404(Offer, id=category.offer_id)
        print("the offer title is :", offer.title)


        start_date = datetime.strptime(request.POST.get('start-date'), '%m/%d/%Y').date()

        end_date = datetime.strptime(request.POST.get('end-date'), '%m/%d/%Y').date()

        today = today = timezone.now().date()

        print(start_date,"today",today)
        if not start_date >= today:
            error_notify(self.request, 'Start date must be greater than equal to today ' )
            return redirect('editcategory_offer', category_id=category_id)
        if not end_date > today:
            error_notify(self.request, 'End date must be greater than today' )
            return redirect('editcategory_offer', category_id=category_id)


        offer.title = request.POST.get('offer-title')
        offer.about = request.POST.get('about')
        offer.offer_percent = request.POST.get('discount')
        offer.start_date = datetime.strptime(request.POST.get('start-date'), '%m/%d/%Y').date()
        offer.end_date = datetime.strptime(request.POST.get('end-date'), '%m/%d/%Y').date()
        offer.save()

        # title = request.POST.get('offer-title')
        # about = request.POST.get('about')
        # discount = request.POST.get('discount')
        # start_date = request.POST.get('start-date')
        # end_date = request.POST.get('end-date')

        # start_date = datetime.strptime(start_date, '%m/%d/%Y').date()
        # end_date = datetime.strptime(end_date, '%m/%d/%Y').date()
        print("the offer title is :", offer.title)
        print("offer updated")
        return redirect('admin-category')


class RemoveCategoryOfferView(View):

    def get(self, request, category_id):
        category = get_object_or_404(Category, id=category_id)
        category.offer = None
        category.save()
        return redirect('admin-category')

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

class ViewVariantView(View):

    def get(self, request, product_id):# we see variants for specific product in product addinf time use (product id)

        product = get_object_or_404(Product, id=product_id)
        variants = Variant.objects.filter(product_id=product_id)

        return render(request, 'adminpanel/view-variant.html', {"user_id": request.user.id, "product": product, "variants": variants})
    
class AddVariantView(View):

    def get(self, request, product_id):# we add variants for specific product in product addinf time use (product id)

        product = get_object_or_404(Product, id=product_id)

        return render(request, 'adminpanel/add-variant.html', {"user_id": request.user.id, "product": product})
    
    def post(self, request, product_id):

        


        variant_name = request.POST.get('name', '').strip()
        variant_description = request.POST.get('description', '').strip()
        variant_price = request.POST.get('price', '').strip()
        variant_discount = request.POST.get('discount_percent', '0').strip()
        variant_stock = request.POST.get('stock', '').strip()
        variant_is_listed = request.POST.get('variant_is_listed') == 'on'

        print("variant name :", variant_name,"variant description :", variant_description, "variant_price :", variant_price, "variant_discount :", variant_discount, "variant stock :", variant_stock, "variant is listed :", variant_is_listed)

        if not variant_name:
            
            error_notify(self.request, 'Variant name is required.')
            return redirect('add-variant', product_id=product_id)
        elif not variant_price or not re.match(r'^\d+(\.\d{1,2})?$', variant_price):

            # errors['variant_price'] = 'Variant price must be a valid number (e.g., 99.99).'
            error_notify(self.request, 'Variant price must be a valid number (e.g., 99.99).')
            return redirect('add-variant', product_id=product_id)
        elif not variant_stock.isdigit() or int(variant_stock) < 0:
            # errors['variant_stock'] = 'Variant stock must be a non-negative integer.'
            error_notify(self.request, 'Variant stock must be a non-negative integer.')
            return redirect('add-variant', product_id=product_id)
        elif not re.match(r'^\d+(\.\d{1,2})?$|^0$', variant_discount):
            # errors['variant_discount'] = 'Variant discount must be a valid number (e.g., 10.00) or 0.'
            error_notify(self.request, 'Variant discount must be a valid number (e.g., 10.00) or 0.')
            return redirect('add-variant', product_id=product_id)
        elif Variant.objects.filter(product_id=product_id, name__iexact=variant_name).exists():
            error_notify(self.request, 'Variant name already exists for this product.')
            return redirect('add-variant', product_id=product_id)
        
        product = get_object_or_404(Product, id=product_id)

        variant = Variant.objects.create(product=product, name=variant_name, description=variant_description, price=variant_price, discount=variant_discount, stock=variant_stock, is_listed=variant_is_listed)

        return redirect('view-variant', product_id=product_id)

class EditVariantView(View):

    def get(self, request, variant_id):
        
        variant = get_object_or_404(Variant, id=variant_id)
        product = get_object_or_404(Product, id=variant.product.id)
    
        # the offer final price test
        # print("main discount:", variant.final_price)
        # print("variant price:", variant.price, "variant discount", variant.discount)
        # print("product category offer", variant.product.category.offer.offer_percent)

        return render(request, 'adminpanel/add-variant.html', {"variant":variant, "user_id": request.user.id, "product": product})

    def post(self, request, variant_id):

        variant = get_object_or_404(Variant, id=variant_id)
        product = get_object_or_404(Product, id=variant.product.id)

        variant_name = request.POST.get('name', '').strip()
        variant_description = request.POST.get('description', '').strip()
        variant_price = request.POST.get('price', '').strip()
        variant_discount = request.POST.get('discount_percent', '0').strip()
        variant_stock = request.POST.get('stock', '').strip()


        if not variant_name:
            
            error_notify(self.request, 'Variant name is required.')
            return redirect('edit_variant', variant_id=variant_id)
        elif not variant_price or not re.match(r'^\d+(\.\d{1,2})?$', variant_price):

            # errors['variant_price'] = 'Variant price must be a valid number (e.g., 99.99).'
            error_notify(self.request, 'Variant price must be a valid number (e.g., 99.99).')
            return redirect('edit_variant', variant_id=variant_id)
        elif not variant_stock.isdigit() or int(variant_stock) < 0:
            # errors['variant_stock'] = 'Variant stock must be a non-negative integer.'
            error_notify(self.request, 'Variant stock must be a non-negative integer.')
            return redirect('edit_variant', variant_id=variant_id)
        elif not re.match(r'^\d+(\.\d{1,2})?$|^0$', variant_discount):
            # errors['variant_discount'] = 'Variant discount must be a valid number (e.g., 10.00) or 0.'
            error_notify(self.request, 'Variant discount must be a valid number (e.g., 10.00) or 0.')
            return redirect('edit_variant', variant_id=variant_id)
        elif Variant.objects.filter(product_id=product.id, name__iexact=variant_name).exclude(id=variant_id).exists():
            error_notify(self.request, 'Variant name already exists for this product.')
            return redirect('edit_variant', variant_id=variant_id)

        print("variant name :", variant_name,"variant description :", variant_description, "variant_price :", variant_price, "variant_discount :", variant_discount, "variant stock :", variant_stock)

        variant.name = variant_name
        variant.description = variant_description
        variant.price = variant_price
        variant.discount = variant_discount
        variant.stock = variant_stock
        variant.save()

        return redirect('view-variant', product_id=product.id)

@method_decorator(csrf_exempt, name='dispatch')
class ToggleVariatStatusView(View):

    def post(self, request, pk):
        variant = get_object_or_404(Variant, pk=pk)
        
        # print("the variants are ", variants)
        variant.is_listed = not variant.is_listed
        variant.save()

        # Variant.objects.filter(product=product).update(is_listed=product.is_listed)
        # variants = get_object_or_404(Variant, product_id=product.id)
        # print("the variants are ", variants)

        print("variant is listed :", variant.is_listed)
        return JsonResponse({'success': True, 'is_listed': variant.is_listed})
