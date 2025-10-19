from django.contrib import admin
from .models import Photobooth


@admin.register(Photobooth)
class PhotoboothAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'available')
    list_filter = ('available',)
    search_fields = ('name', 'description')

