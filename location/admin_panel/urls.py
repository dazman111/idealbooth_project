from django.urls import path
from . import views
from .views import CustomLoginView


urlpatterns = [


    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/users/<int:user_id>/edit/', views.edit_user, name='edit_user'),
   
    path('reservations/', views.manage_reservations, name='manage_reservations'),

    # Gestion utilisateurs

    path('users/', views.manage_users, name='manage_users'),
    path('users/<int:user_id>/', views.admin_user_detail, name='admin_user_detail'),
    path("users/<int:user_id>/delete/", views.admin_delete_user, name="admin_delete_user"),
    path('admin/user/reactivate/<int:user_id>/', views.reactivate_user, name='admin_reactivate_user'),
    
    # Gestion photobooth
    path('photobooths/', views.manage_photobooths, name='manage_photobooths'),
    path('photobooths/add/', views.add_photobooth, name='add_photobooth'),
    path('photobooths/edit/<int:pk>/', views.edit_photobooth, name='edit_photobooth'),
    path('photobooths/delete/<int:pk>/', views.delete_photobooth, name='delete_photobooth'),

    path('login/', CustomLoginView.as_view(), name='login'),

    path('blog/', views.manage_blog, name='manage_blog'),

    path('payments/', views.manage_payments, name='manage_payments'),
    
    path('reservations/update/', views.update_reservation_status, name='update_reservation_status'),
    path('reservations/<int:reservation_id>/detail/', views.reservation_detail, name='reservation_detail'),
    path('reservations/<int:reservation_id>/facture/', views.generate_invoice, name='generate_invoice'),

    path('api/cancelled-count/', views.cancelled_count_api, name='cancelled_count_api'),

   path('messages/', views.admin_messages, name='admin_messages'),
   path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),


]
