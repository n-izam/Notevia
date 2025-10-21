from django.urls import path, include
from .views import SigninView, SignupView, VerifyOTPView, ResendOTPView, SignOutView

urlpatterns = [
    path("signin/", SigninView.as_view(), name='signin'),
    path('signup/', SignupView.as_view(), name='signup'),
    path('verify-otp/<int:user_id>/', VerifyOTPView.as_view(), name='verify-otp'),
    path('resend-otp/<int:user_id>/', ResendOTPView.as_view(), name='resend-otp'),
    path('signout/<int:user_id>/',SignOutView.as_view(), name='signout'),
    # path('cores/',include('cores.url')),
    
]