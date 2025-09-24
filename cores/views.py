from django.shortcuts import render
from django.views import View
from accounts.models import CustomUser

# Create your views here.

class HouseView(View):

    def get(self, request, user_id):
        user = CustomUser.objects.get(id=user_id)
        
        return render(request, 'cores/house.html', {"user_id": user_id, "user":  user})