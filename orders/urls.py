from django.urls import path
from .views import AddressSelectionView, ConfirmationCartView, PlaceOrderView, OrderListingView, OrderDetailView, OrderTrackingView, AdminSideOrderListingView, AddressAddFromSelectView, ReturnItemView
from .views import AdminOrderDetailView, OrderStatusUpdateView, CancelOrderView, CancelOrderItemView, ReturnOrderView, ReturnUpdateView, InvoiceDownloadView, OrderSuccessView, PaymentFailedView, ItemReturnUpdateView
from . import views




urlpatterns = [
    path('order_address/', AddressSelectionView.as_view(), name='address_selection'),
    path('order_confirmation/', ConfirmationCartView.as_view(), name='order_confirmation'),
    path('place_order/', PlaceOrderView.as_view(), name='place_order'),
    path('order/razorpay/callback/', views.razorpay_callback, name='razorpay_callback'),
    # path('order/success/<str:order_id>/', views.OrderSuccessView.as_view(), name='order_success'),
    path('order/success/<str:order_id>/', OrderSuccessView.as_view(), name='order_success'),
    path('order/cancel/<int:order_id>/', views.OrderCancelReturnCartView.as_view(), name='order_cancel_return_cart'),
    path('order/payment/failed/<int:order_id>/',PaymentFailedView.as_view(), name='payment_failed'),

    path('order_listing/', OrderListingView.as_view(), name='order_listing'),
    path('order_detail/<int:order_id>/', OrderDetailView.as_view(), name='order_details'),
    path('order_track/<int:order_id>/', OrderTrackingView.as_view(), name='order_tracking'),

    path('order/<int:order_id>/cancel', CancelOrderView.as_view(), name='cancel_order'),
    path('order/<int:order_id>/items/<int:item_id>/cancel/', CancelOrderItemView.as_view(), name='cancel_order_item'),
    path('order/<int:order_id>/return', ReturnOrderView.as_view(), name='return_order'),

    path('order/<int:order_id>/user/<int:user_id>/return_update/', ReturnUpdateView.as_view(), name='return_update'),
    path('order/<int:order_id>/item//<int:item_id>/return/', ReturnItemView.as_view(), name='return_order_item'),
    path('order/<int:order_id>/item/<int:item_id>/user/<int:user_id>/return-item-update/', ItemReturnUpdateView.as_view(), name='return_item_update'),

    path('order/<int:order_id>/invoice/', InvoiceDownloadView.as_view(), name='download_invoice'),



    path('admin_order/', AdminSideOrderListingView.as_view(), name='admin_order_list'),
    path('admin_order_detail/<int:order_id>/', AdminOrderDetailView.as_view(), name='admin_order_detail'),
    path('update_order_status/<int:order_id>/status/<str:new_status>/', OrderStatusUpdateView.as_view(), name='update_order_status'),
    path('address_add_from_select/', AddressAddFromSelectView.as_view(), name='address_add_from_select'),


]