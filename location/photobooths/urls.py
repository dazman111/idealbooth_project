from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from . import views
from django.urls import path, include
from .views import restock_photobooth

from rest_framework.routers import DefaultRouter
from .views import PhotoboothViewSet

router = DefaultRouter()
router.register(r'photobooths', PhotoboothViewSet)


urlpatterns = [
    path('cart/add/<int:photobooth_id>/', views.add_to_cart, name='add_to_cart'),
    path('', views.photobooth_list, name='photobooth_list'),
    path('<int:photobooth_id>/notify/', views.notify_me, name='notify_me'),
    path('admin/photobooth/<int:booth_id>/restock/', restock_photobooth, name='restock_photobooth'),
    path('favorite/add/<int:pk>/', views.add_favorite, name='add_favorite'),
    path('favorite/remove/<int:pk>/', views.remove_favorite, name='remove_favorite'),

    path('<int:pk>/', views.photobooth_detail, name='photobooth_detail'),
    path('add/', views.photobooth_create, name='photobooth_create'),
    path('<int:pk>/edit/', views.photobooth_update, name='photobooth_update'),
    path('<int:pk>/delete/', views.photobooth_delete, name='photobooth_delete'),
    path('dashboard/', views.dashboard, name='dashboard'), 
    path('photobooths/<int:booth_id>/restock/', views.restock_photobooth, name='restock_photobooth'),
    path('photobooths/<int:booth_id>/reduce/', views.reduce_stock_photobooth, name='reduce_stock_photobooth'),
    path('photobooths/reset-stock/', views.reset_stock_session, name='reset_stock_session'),


    path('', include(router.urls)),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
