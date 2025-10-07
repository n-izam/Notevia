from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login
from django.urls import reverse_lazy
from django.http import HttpResponse
from django.contrib import messages
from django.views.generic import View, DeleteView, UpdateView
from accounts.models import CustomUser
from .models import Category, Offer
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from accounts.utils import warning_notify, info_notify
from django.http import JsonResponse
from datetime import datetime
from accounts.utils import success_notify

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

        return render(request, 'adminpanel/product-main.html', {"user_id": request.user.id})
    

# admin customers list view 

class AdminCustomersView(View):
    
    def get(self, request):

        return render(request, 'adminpanel/customers.html', {"user_id": request.user.id})
    
# admin category list view

class AdminCategoryView(View):

    def get(self, request):

        category = Category.objects.all()

        return render(request, 'adminpanel/category.html', {"category": category, "user_id":request.user.id})

# for category listing/unlisting

class TogglCategoryStatusView(View):
    def post(self, request, pk):
        category = get_object_or_404(Category, pk=pk)
        category.is_list = not category.is_list
        category.save()
        print("category is listed", category.is_list)
        return JsonResponse({'success': True, 'is_list': category.is_list})
    

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
        print("🔍 request.user =", self.request.user)
        print("🔍 type =", type(self.request.user))
        context['user_id'] = self.request.user.id
        return context
    
class AddCategoryOffer(View):
    def get(self, request, category_id):
        category = get_object_or_404(Category, id=category_id)
        
        print("category id", category.id)
        return render(request, 'adminpanel/addcategory-offer.html', {"user_id":request.user.id, "category": category})

    def post(self, request, category_id):
        category = get_object_or_404(Category, id=category_id)
        # offer = get_object_or_404(Offer, id=category.o)

        title = request.POST.get('offer-title')
        about = request.POST.get('about')
        discount = request.POST.get('discount')
        start_date = request.POST.get('start-date')
        end_date = request.POST.get('end-date')

        print("title",title)

        start_date = datetime.strptime(start_date, '%m/%d/%Y').date()
        end_date = datetime.strptime(end_date, '%m/%d/%Y').date()

        offer = Offer.objects.create(
            title=title, offer_percent=discount, about=about,
            start_date=start_date, end_date=end_date,
        )
        print("offer created")

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
        category.is_list = False  # Mark as unlisted
        category.save()
        return redirect(self.success_url)






        
# varient view of each products

class ViewVariantView(View):

    def get(self, request):# we see variants for specific product in product addinf time use (product id)

        return render(request, 'adminpanel/view-variant.html', {"user_id": request.user.id})
    
class AddVariantView(View):

    def get(self, request):# we add variants for specific product in product addinf time use (product id)

        return render(request, 'adminpanel/add-variant.html', {"user_id": request.user.id})
    




