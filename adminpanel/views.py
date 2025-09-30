from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.views import View
from accounts.models import CustomUser
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
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