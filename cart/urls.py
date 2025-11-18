from django.urls import path
from .views import CartPageView, AddToCartFromDetailView, CartQuantityUpdateView, RemoveFromCartView, UserWalletView, AdminOverAllWalletView
from . import views



urlpatterns = [
    path('cart_page/', CartPageView.as_view(), name='cart_page'),
    path('add_to_cart/', AddToCartFromDetailView.as_view(), name='add_to_cart'),
    path('cart_update/', CartQuantityUpdateView.as_view(), name='cart_quantity_update'),
    path('remove_from_cart/', RemoveFromCartView.as_view(), name='remove_from_cart'),

    path('wallet/', UserWalletView.as_view(), name='wallet'),
    path('wallet/razorpay/callback/', views.razorpay_callback_wallet, name='razorpay_callback_wallet'),

    path('wallet/success/<int:trxct_id>/', views.WalletPaymentSuccessView.as_view(), name='wallet_payment_success'),
    path('wallet/cancel/<int:trxct_id>/', views.PaymentCancelReturnWalletView.as_view(), name='cancel_return_wallet'),
    path('wallet/payment/failed/<int:trxct_id>/', views.WalletPaymentFailedView.as_view(), name='wallet_payment_failed'),

    path('admin_wallet/', AdminOverAllWalletView.as_view(), name='admin_View_transactions'),

]