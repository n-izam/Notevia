from django.urls import path
from .views import AdminCouponListingView, AddCouponView, ToggleStatusCouponView, EditCouponView



urlpatterns = [
    path('coupons/', AdminCouponListingView.as_view(), name='admin_coupon_list'),
    path('coupon_add/', AddCouponView.as_view(), name='add_coupon'),
    path('toggles-status-coupon/<int:pk>/', ToggleStatusCouponView.as_view(), name='toggle_status_coupon'),
    path('coupon/edit/', EditCouponView.as_view(), name='edit_coupon'),
]