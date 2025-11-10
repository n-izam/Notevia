from django.urls import path
from .views import AdminSalesView


urlpatterns = [
    path('admin_sales/', AdminSalesView.as_view(), name='admin_sales'),
]