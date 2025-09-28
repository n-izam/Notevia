from django.urls import path
from .views import HomeView


urlpatterns = [
    path('home/<int:user_id>/', HomeView.as_view(), name='cores-home'),
]