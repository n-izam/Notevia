from django.urls import path
from .views import AdminDashView, AdminProductView

urlpatterns = [
    path('admindash/<int:user_id>/',AdminDashView.as_view() , name='admin-dash'),
    path('adminproduct/<int:user_id>/', AdminProductView.as_view(), name='admin-product'),
]