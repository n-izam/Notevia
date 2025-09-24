from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
# Create your views here.

def admin_login(request):
    

    return render(request, 'adminpanel/login.html')