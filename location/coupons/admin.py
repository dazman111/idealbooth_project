from django.contrib import admin
from .models import Coupon, PromotionBanner

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_type', 'discount_value', 'actif', 'date_debut', 'date_fin')
    search_fields = ('code',)
    readonly_fields = ('utilisations_effectuees',)

    # Autoriser code vide dans l'admin (facultatif selon ta config)
    def get_fields(self, request, obj=None):
        fields = super().get_fields(request, obj)
        return fields

admin.site.register(PromotionBanner)
class PromotionBannerAdmin(admin.ModelAdmin):
    list_display = ('message', 'coupon', 'start_date', 'end_date', 'is_active')

