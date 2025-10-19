from django.urls import path
from . import views
from .views import mentions_legales, politique_confidentialite

urlpatterns = [
    path('', views.home, name='home'),
    path('mentions-legales/', mentions_legales, name='mentions_legales'),
    path('politique-de-confidentialite/', politique_confidentialite, name='politique_confidentialite'),

]
