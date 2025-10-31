from django.urls import path
from .views import CartPageView, AddToCartFromDetailView, CartQuantityUpdateView, RemoveFromCartView




urlpatterns = [
    path('cart_page/', CartPageView.as_view(), name='cart_page'),
    path('add_to_cart/', AddToCartFromDetailView.as_view(), name='add_to_cart'),
    path('cart_update/', CartQuantityUpdateView.as_view(), name='cart_quantity_update'),
    path('remove_from_cart/', RemoveFromCartView.as_view(), name='remove_from_cart'),

]