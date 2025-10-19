from django.urls import path
from . import views


urlpatterns = [
    path('', views.cart_detail, name='cart_detail'),
    path('panier/ajouter/<int:photobooth_id>/', views.add_to_cart, name='add_to_cart'),
    path('remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('update-item/<int:item_id>/', views.update_cart_item, name='update_cart_item'),
    path('api/cart/count/', views.get_cart_item_count, name='get_cart_item_count'),

    

    path("apply-coupon/", views.apply_coupon, name="apply_coupon"),
    path("remove-coupon/", views.remove_coupon, name="remove_coupon"),

    path('confirmation/', views.confirm_cart, name='confirm_cart'),

    # Paiement
    path('checkout/', views.checkout, name='checkout'),
    path('create-checkout-session/', views.create_checkout_session, name='create_checkout_session'),
    path('checkout/success/', views.checkout_success, name='checkout_success'),
    path('success/', views.payment_success, name='payment_success'),

    # Stripe webhook
    path('webhook/', views.stripe_webhook, name='stripe_webhook'),
]