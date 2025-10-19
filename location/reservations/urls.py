from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ReservationViewSet  # ou AdminReservationViewSet si tu l'as créé
from .views import invoice_pdf

router = DefaultRouter()
router.register(r'reservations', ReservationViewSet)  # ou AdminReservationViewSet

urlpatterns = [
    path('', include(router.urls)),
    path('facture/<int:invoice_id>/', invoice_pdf, name='invoice_pdf'),
]
