from django.urls import path
from .views import HomeView, ProductlistingView, ProductDetailsView, StaticHomeView, StaticProductListView, StaticProductDetailsView, StaticAboutView, StaticContactUsView
from .views import StaticTermsAndConditionsView, StaticPrivacyPolicyView


urlpatterns = [
    path('home/<int:user_id>/', HomeView.as_view(), name='cores-home'),
    path('shop_product_list/', ProductlistingView.as_view(), name='shop_products'),
    path('shopproductdetails/<int:product_id>/', ProductDetailsView.as_view(), name='shop_productdetail'),
    path('', StaticHomeView.as_view(), name='static_home'),
    path('static_product_list/', StaticProductListView.as_view(), name='static_product_list'),
    path('static_product_details/<int:product_id>/', StaticProductDetailsView.as_view(), name='static_product_detail'),
    path('static_about/', StaticAboutView.as_view(), name='static_about'),
    path('static_contact_us/', StaticContactUsView.as_view(), name='static_contact_us'),
    path('static_terms_and_conditions/', StaticTermsAndConditionsView.as_view(), name='static_terms_and_conditions'),
    path('static_privacy_policy/', StaticPrivacyPolicyView.as_view(), name='static_privacy_policy'),

]