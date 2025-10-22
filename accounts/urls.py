from django.urls import path, include
from .views import SigninView, SignupView, VerifyOTPView, ResendOTPView, SignOutView, ForgotPassView, VerifyForgotOTPView, ResetPasswordView, ResendPasswordOTPView

urlpatterns = [
    path("signin/", SigninView.as_view(), name='signin'),
    path('signup/', SignupView.as_view(), name='signup'),
    path('verify-otp/<int:user_id>/', VerifyOTPView.as_view(), name='verify-otp'),
    path('resend-otp/<int:user_id>/', ResendOTPView.as_view(), name='resend-otp'),
    path('signout/<int:user_id>/',SignOutView.as_view(), name='signout'),
    path('forgotpass/', ForgotPassView.as_view(), name='forgot_pass'),
    path('verify-pass-otp/<int:user_id>/', VerifyForgotOTPView.as_view(), name='verify_forgot_otp'),
    path('resend-pass-otp/<int:user_id>/', ResendPasswordOTPView.as_view(), name='resend_forgot_otp'),
    path('new-password/<int:user_id>/', ResetPasswordView.as_view(), name='new_pass')
    
    # path('cores/',include('cores.url')),
    
]