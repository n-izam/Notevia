from django.urls import path, include
from .views import SigninView, SignupView, VerifyOTPView, ResendOTPView, SignOutView, ForgotPassView, VerifyForgotOTPView, ResetPasswordView, ResendPasswordOTPView
from .views import CustomerProfileView, ProfileEditView, AddressView, AddAddressView, SetDefaultView, RemoveAddressView, EditAddressView, VerifyProfileOTPView, ResendProfileOTPView, ChangeProfileView

urlpatterns = [
    path("signin/", SigninView.as_view(), name='signin'),
    path('signup/', SignupView.as_view(), name='signup'),
    path('verify-otp/<int:user_id>/', VerifyOTPView.as_view(), name='verify-otp'),
    path('resend-otp/<int:user_id>/', ResendOTPView.as_view(), name='resend-otp'),
    path('signout/<int:user_id>/',SignOutView.as_view(), name='signout'),
    path('forgotpass/', ForgotPassView.as_view(), name='forgot_pass'),
    path('verify-pass-otp/<int:user_id>/', VerifyForgotOTPView.as_view(), name='verify_forgot_otp'),
    path('resend-pass-otp/<int:user_id>/', ResendPasswordOTPView.as_view(), name='resend_forgot_otp'),
    path('new-password/<int:user_id>/', ResetPasswordView.as_view(), name='new_pass'),

    # customer profile
    path('profile/', CustomerProfileView.as_view(), name='profile'),
    path('change_profile/', ChangeProfileView.as_view(), name='change_profile'),
    path('profile_edit/', ProfileEditView.as_view(), name='profile_edit'),
    path('verify_profile_otp/', VerifyProfileOTPView.as_view(), name='verify_profile'),
    path('resend_profile_otp/', ResendProfileOTPView.as_view(), name='resend_profile'),
    path('user_address/', AddressView.as_view(), name='address'),
    path('add_address/', AddAddressView.as_view(), name='add_address'),
    path('set_main/<int:address_id>/', SetDefaultView.as_view(), name='set_default'),
    path('remove_address/<int:address_id>/', RemoveAddressView.as_view(), name='remove_address'),
    path('edit_address/<int:address_id>/', EditAddressView.as_view(), name='edit_address')
    
    # path('cores/',include('cores.url')),
    
]