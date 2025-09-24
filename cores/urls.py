from django.urls import path
from .views import HouseView


urlpatterns = [
    path('house/<int:user_id>/', HouseView.as_view(), name='cores-house'),
]