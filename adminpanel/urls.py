from django.urls import path
from .views import AdminDashView, AdminProductView, AdminCustomersView, AdminCategoryView, AddCategoryView, ViewVariantView, AddVariantView, TogglCategoryStatusView, AddCategoryOffer, EditCategoryOffer

urlpatterns = [
    path('admindash/<int:user_id>/',AdminDashView.as_view() , name='admin-dash'),
    path('adminproduct/', AdminProductView.as_view(), name='admin-product'),
    path('admincustomers/', AdminCustomersView.as_view(), name='admin-customers'),
    path('admincategory/', AdminCategoryView.as_view(), name='admin-category'),
    path('addcategory/',AddCategoryView.as_view(), name='add-category'),
    path('viewvariant/', ViewVariantView.as_view(), name='view-variant'),
    path('addvariant/', AddVariantView.as_view(), name='add-variant'),
    path('toggle-status/<int:pk>/', TogglCategoryStatusView.as_view(), name='toggle_status'),
    path('admincategory/<int:category_id>/addcategory-offer', AddCategoryOffer.as_view(), name='addcategory_offer'),
    path('admincategory/<int:category_id>/editcategory-offer', EditCategoryOffer.as_view(), name='editcategory_offer'),
    
]