from django.urls import path
from .views import AdminSalesView, ReferralView, WishListView, AddToWishList


urlpatterns = [
    path('admin_sales/', AdminSalesView.as_view(), name='admin_sales'),
    path('referral/', ReferralView.as_view(), name='referral_view'),
    path('wish_list/', WishListView.as_view(), name='wishlist_view'),
    path('add_wishlist/', AddToWishList.as_view(), name='add_to_wishlist'),

]