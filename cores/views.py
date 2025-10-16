from django.shortcuts import render, get_object_or_404
from django.views import View
from accounts.models import CustomUser
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from adminpanel.models import Category, Offer, Product, ProductImage, Variant

# Create your views here.

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
        
        products = Product.objects.filter(is_deleted=False, is_listed=True).order_by('-created_at')

        product_with_image = []
        for product in products:
            main_image = product.images.filter(is_main=True).first()
            product_with_image.append({
                "product": product,
                "main_image": main_image
            })

        # print(product_with_image)
        context = {
            "product_with_image": product_with_image,
            "user_id": request.user.id,
        }

        return render(request, 'cores/productlist1.html', context)
    
class ProductDetailsView(View):

    def get(self, request, product_id):




        main_product = get_object_or_404(Product, id=product_id)

        images = main_product.images.all()
        print("images are", images)

        context = {
            "main_product": main_product,
            "images": images,
            "user_id":request.user.id,
        }

        return render(request, 'cores/productdetail1.html', context)