from django.urls import path
from .views import AdminDashView

urlpatterns = [
    path('admindash/<int:user_id>/',AdminDashView.as_view() , name='admin-dash'),
]