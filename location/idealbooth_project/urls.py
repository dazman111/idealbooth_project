
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.i18n import set_language
from rest_framework.authtoken.views import obtain_auth_token

from rest_framework import routers
from reservations.views import ReservationViewSet

router = routers.DefaultRouter()
router.register(r'reservations', ReservationViewSet, basename='reservation')


urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),  # Fournit déjà /i18n/setlang/

    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    
    path('api/photobooths/', include('photobooths.urls')),
    path('api/reservations/', include('reservations.urls')),
    path('api/token/', obtain_auth_token),
    path('api-auth/', include('rest_framework.urls')),

    path('', include('home.urls')),  # Ajoute cette ligne si tu veux rediriger vers home
    path('accounts/', include('accounts.urls')),  # gestion comptes
    path('admin-panel/', include('admin_panel.urls')),
    path('admin-panel/', include(('admin_panel.urls','admin_panel'), namespace='admin_panel')),
    path('mon-compte/', include('accounts.urls')),
    
    path('photobooths/', include('photobooths.urls')),  # gestion photobooths
    path('reservations/', include(('reservations.urls', 'reservation'), namespace='reservation')), # gestion réservations
    path('blog/', include('blog.urls')),


    path('panier/', include('cart.urls')),
    path('coupon/', include('coupons.urls')),


 
]
if settings.DEBUG:
    from django.conf.urls.static import static
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
