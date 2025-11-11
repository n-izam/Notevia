from django.urls import path
from .views import AdminSalesView, ReferralView, WishListView, AddToWishList, RemoveToWishlist


urlpatterns = [
    path('admin_sales/', AdminSalesView.as_view(), name='admin_sales'),
    path('referral/', ReferralView.as_view(), name='referral_view'),
    path('wish_list/', WishListView.as_view(), name='wishlist_view'),
    path('add_wishlist/', AddToWishList.as_view(), name='add_to_wishlist'),
    path('wishlist/remove', RemoveToWishlist.as_view(), name='remove_from_wishlist'),

]