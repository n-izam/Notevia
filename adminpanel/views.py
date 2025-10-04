from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login
from django.http import HttpResponse
from django.contrib import messages
from django.views import View
from accounts.models import CustomUser
from .models import Category, Offer
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from accounts.utils import warning_notify, info_notify

# Create your views here.


@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class AdminDashView(View):

    
    def get(self, request, user_id):
        # user = CustomUser.objects.filter(id = user_id)

        return render(request, 'adminpanel/admindash.html', {"user_id": user_id})

class AdminProductView(View):
    def get(self, request, user_id):

        return render(request, 'adminpanel/product-main.html', {"user_id": user_id})
    
class AdminCustomersView(View):
    
    def get(self, request, user_id):

        return render(request, 'adminpanel/customers.html', {"user_id": user_id})
    
class AdminCategoryView(View):

    def get(self, request, user_id):

        category = Category.objects.all()

        return render(request, 'adminpanel/category.html', {"user_id": user_id, "category": category})
    
class AddCategoryView(View):

    def get(self, request):

        return render(request, 'adminpanel/add-category.html', {"user_id": request.user.id})
    
    def post(self, request):

        category_name = request.POST.get('category_name')
        description = request.POST.get('description')

        status = request.POST.get('categoryStatus')
        # return HttpResponse(f"the status is {status}")

        if status == 'listed':
            is_list = True
        else:
            is_list = False

        if not category_name:
            
            info_notify(request, "enter the category name")
            return redirect('add-category')
        elif not description:
            
            info_notify(request, "give any description")
            return redirect('add-category')
        
        else:
            category = Category.objects.create(name=category_name, description=description, is_list=is_list)
            category.save()
            print("category created")

            return redirect('admin-category', user_id=user_id)

class ViewVariantView(View):

    def get(self, request):# we see variants for specific product in product addinf time use (product id)

        return render(request, 'adminpanel/view-variant.html', {"user_id": request.user.id})
    
class AddVariantView(View):

    def get(self, request):# we add variants for specific product in product addinf time use (product id)

        return render(request, 'adminpanel/add-variant.html', {"user_id": request.user.id})


