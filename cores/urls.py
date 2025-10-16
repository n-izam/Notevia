from django.urls import path
from .views import HomeView, ProductlistingView, ProductDetailsView


urlpatterns = [
    path('home/<int:user_id>/', HomeView.as_view(), name='cores-home'),
    path('shop_product_list/', ProductlistingView.as_view(), name='shop_products'),
    path('shopproductdetails/<int:product_id>/', ProductDetailsView.as_view(), name='shop_productdetail')

]