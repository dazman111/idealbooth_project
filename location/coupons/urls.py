from django.urls import path
from . import views

urlpatterns = [
    path('appliquer/', views.apply_coupon, name='apply_coupon'),
]
