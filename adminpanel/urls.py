from django.urls import path
from .views import AdminDashView, AdminProductView, AdminCustomersView, AdminCategoryView, AddCategoryView, ViewVariantView, AddVariantView

urlpatterns = [
    path('admindash/<int:user_id>/',AdminDashView.as_view() , name='admin-dash'),
    path('adminproduct/<int:user_id>/', AdminProductView.as_view(), name='admin-product'),
    path('admincustomers/<int:user_id>/', AdminCustomersView.as_view(), name='admin-customers'),
    path('admincategory/<int:user_id>/', AdminCategoryView.as_view(), name='admin-category'),
    path('addcategory/',AddCategoryView.as_view(), name='add-category'),
    path('viewvariant/', ViewVariantView.as_view(), name='view-variant'),
    path('addvariant/', AddVariantView.as_view(), name='add-variant'),
    
]