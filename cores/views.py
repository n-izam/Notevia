from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from accounts.models import CustomUser
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.db.models import Q, Min
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from adminpanel.models import Category, Offer, Product, ProductImage, Variant, Brand

# Create your views here.
@method_decorator(never_cache, name='dispatch')
class StaticHomeView(View):

    def get(self, request):

        if request.user.is_authenticated:
            if request.user.is_superuser:
                return redirect('admin-dash', user_id= request.user.id)
            else:
                return redirect("cores-home", user_id=request.user.id)

        latest_products = Product.objects.filter(is_deleted=False, is_listed=True).order_by('-created_at')[:4]

        product_with_image = []
        for product in latest_products:
            main_image = product.images.filter(is_main=True).first()
            product_with_image.append({
                "product": product,
                "main_image": main_image 
            })
        # user = CustomUser.objects.get(id=user_id)

        context = {
            "product_with_image":product_with_image,
        }
        
        return render(request, 'cores/static_home.html', context)

@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class HomeView(View):

    def get(self, request, user_id):
        latest_products = Product.objects.filter(is_deleted=False, is_listed=True).order_by('-created_at')[:4]

        product_with_image = []
        for product in latest_products:
            main_image = product.images.filter(is_main=True).first()
            product_with_image.append({
                "product": product,
                "main_image": main_image 
            })
        # user = CustomUser.objects.get(id=user_id)

        context = {
            "product_with_image":product_with_image,
            "user_id": user_id,
        }
        
        return render(request, 'cores/home1.html', context)
    
class ProductlistingView(View):

    def get(self, request):

        search_q = request.GET.get('q', '').strip()
        sort_option = request.GET.get('sort', '').strip()
        cat_option = request.GET.get('cat', '').strip()
        brand_option = request.GET.getlist('brand')
        page = request.GET.get('page', 1)

        print("search for ",search_q, "| sort by:", sort_option, "| category by :", cat_option, "| brand:", brand_option, "| page:", page)

        category = Category.objects.filter(is_listed=True)
        brand = Brand.objects.all()
        
        products = Product.objects.filter(is_deleted=False, is_listed=True)

        if search_q:
            products = products.filter(Q(brand__name__icontains=search_q)| 
                                       Q(category__name__icontains=search_q) | 
                                       Q(variants__name__icontains=search_q)).distinct()
            
        if brand_option:
            products = products.filter(brand__name__in=brand_option)

        # apply category selection
            
        if cat_option and cat_option.lower() != 'clear':
            products = products.filter(category__name__iexact=cat_option)
            

            
        # apply sorting
        if sort_option == "price_asc":

            # products = products.order_by('base_price')
            products = products.order_by('base_price')

            # print("products", products)
        
        elif sort_option == "price_desc":
            # products = products.order_by('-base_price')
            products = products.order_by('-base_price')

        elif sort_option == "name_asc":
            products = products.order_by('name')
        elif sort_option == "name_desc":
            products = products.order_by('-name')
        elif sort_option == "newest":
            products = products.order_by('-created_at')

            
        elif sort_option == "clear":
            products = products.order_by('-created_at')
            sort_option = ''
        else:
            products = products.order_by('-created_at')

        
        # prepare for display data
        product_with_image = []
        for product in products:
            main_image = product.images.filter(is_main=True).first()
            # main_variant = product.variants.filter(is_listed=True).order_by('-stock').first()
            # print(main_variant.price)
            product_with_image.append({
                "product": product,
                "main_image": main_image,
                # "main_variant":main_variant,
            })

        # Pagination — 6 items per page

        paginator = Paginator(product_with_image, 6)
        try:
            paginated_products = paginator.page(page)
        except PageNotAnInteger:
            paginated_products = paginator.page(1)
        except EmptyPage:
            paginated_products = paginator.page(paginator.num_pages)


        # print(product_with_image)
        context = {
            "product_with_image": paginated_products,
            "user_id": request.user.id,
            "categories": category,
            "brands": brand,
            "query": search_q,
            "sort_option": sort_option,
            "cat_option" : cat_option,
            "brand_option" : brand_option,
            "paginator" : paginator,
            "page_obj" : paginated_products,
        }

        return render(request, 'cores/productlist1.html', context)
    
class ProductDetailsView(View):

    def get(self, request, product_id):

        main_get = request.GET.get('main','').strip()
        print("main new ", main_get)


        main_product = get_object_or_404(Product, id=product_id)

        if not main_product.is_listed:
            return redirect('shop_products')

        

        images = main_product.images.all()
        print("images are", images)

        variants = main_product.variants.filter(is_listed=True)
        print(" variants", variants)
        variants = variants.order_by('-stock')
        print('variants based on stock', variants)

        if not main_get:
            main_variant = variants.first()
        else:
            main_variant = variants.get(name=main_get)
        print("main variant discount", main_variant.discount_percent)
        print("main variant main_offer", main_variant.main_offer)

        # for related products

        related_products = Product.objects.filter(is_deleted=False, is_listed=True).order_by('-created_at')[:4]

        product_with_image = []
        for product in related_products:
            main_image = product.images.filter(is_main=True).first()
            product_with_image.append({
                "product": product,
                "main_image": main_image,
            })

        # breadcrumb
        breadcrumb = [
            {"name": "Home", "url": "/"},
            {"name": main_product.category.name.capitalize(), "url": f"/shop_product_list/?cat={main_product.category.name}"},
            {"name": main_product.name.capitalize(), "url": ""},
        ]

        context = {
            "main_product": main_product,
            "images": images,
            "user_id":request.user.id,
            "variants" : variants,
            "main_variant": main_variant,
            "product_with_image":product_with_image,
            "breadcrumb": breadcrumb,
        }

        return render(request, 'cores/productdetail1.html', context)