from django.urls import path
from .views import AdminDashView, AdminProductView, AdminCustomersView, AdminCategoryView, AddCategoryView, ViewVariantView, AddVariantView, TogglCategoryStatusView, AddCategoryOffer, EditCategoryOffer
from .views import RemoveCategoryOfferView, CategoryDeleteView, CategoryUpdateView, AddBrandView, AddProductView, AddProductOfferView, EditProductOfferView,  RemoveProductOfferView, ToggleProductStatusView
from .views import EditProductView, ToggleVariatStatusView, EditVariantView, ToggleCustomerStatusView, AdminLoginView
from . import views


urlpatterns = [
    path('admindash/<int:user_id>/',AdminDashView.as_view() , name='admin-dash'),
    path('adminproduct/', AdminProductView.as_view(), name='admin-product'),
    path('admincustomers/', AdminCustomersView.as_view(), name='admin-customers'),
    path('toggles-status-customer/<int:pk>/', ToggleCustomerStatusView.as_view(), name='toggle_status_customer'),
    path('admincategory/', AdminCategoryView.as_view(), name='admin-category'),
    path('addcategory/',AddCategoryView.as_view(), name='add-category'),
    path('adminproduct/<int:product_id>/viewvariant/', ViewVariantView.as_view(), name='view-variant'),
    path('adminproduct/<int:product_id>/addvariant/', AddVariantView.as_view(), name='add-variant'),
    path('toggle-status/<int:pk>/', TogglCategoryStatusView.as_view(), name='toggle_status'),
    path('admincategory/<int:category_id>/addcategory-offer', AddCategoryOffer.as_view(), name='addcategory_offer'),
    path('admincategory/<int:category_id>/editcategory-offer', EditCategoryOffer.as_view(), name='editcategory_offer'),
    path('admincategory/<int:category_id>/remove-offer/', RemoveCategoryOfferView.as_view(), name='category_remove_offer'),
    path('admincategory/<int:pk>/delete/', CategoryDeleteView.as_view(), name='category_delete'),
    path('admincategory/<int:pk>/edit', CategoryUpdateView.as_view(), name='edit_category'),
    path('addproduct/', AddProductView.as_view(), name='add_product'),
    path('api/add-brand/', AddBrandView.as_view(), name='add_brand'),
    path('adminproduct/<int:product_id>/addproduct_offer/', AddProductOfferView.as_view(), name='addproduct_offer'),
    path('adminproduct/<int:product_id>/editproductoffer/', EditProductOfferView.as_view(), name='editproduct_offer'),
    path('adminproduct/<int:product_id>/removeproduct_offer/', RemoveProductOfferView.as_view(), name='remove_product_offer'),
    path('toggles-status/<int:pk>/', ToggleProductStatusView.as_view(), name='toggles_status'),
    path('adminproduct/<int:product_id>/edit', EditProductView.as_view(), name='edit_product'),
    path('toggles-status-variant/<int:pk>/', ToggleVariatStatusView.as_view(), name='toggles_status_variant'),
    path('edit_variant/<int:variant_id>/', EditVariantView.as_view(), name='edit_variant'),
    path('', AdminLoginView.as_view(), name='admin_login'),



    
    # path('api/add-brand', AddBrandView.as_view(), name='add_brand'),
    
]