from django.contrib import admin
from django.utils.html import format_html
from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import path

from .models import Reservation, Invoice

# Enregistrement simple pour Invoice
admin.site.register(Invoice)

@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ('user', 'photobooth', 'start_date', 'end_date', 'status', 'payment_status_display', 'confirm_button')
    list_filter = ('status', 'user', 'photobooth')

    # Affichage du statut de paiement en couleur
    def payment_status_display(self, obj):
        if obj.payment_status == 'paid':
            return format_html('<span style="color: green; font-weight: bold;">Payé</span>')
        return format_html('<span style="color: red;">Non payé</span>')
    payment_status_display.short_description = "Paiement"

    # Bouton "Confirmer" uniquement si payé ET en attente
    def confirm_button(self, obj):
        if obj.payment_status == 'paid' and obj.status == 'pending':
            return format_html(
                '<a class="button" href="{}">Confirmer</a>',
                f'confirm/{obj.id}/'
            )
        return "-"
    confirm_button.short_description = 'Action'

    # Ajout d'URL personnalisées pour la confirmation
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('confirm/<int:reservation_id>/', self.admin_site.admin_view(self.confirm_reservation), name='confirm-reservation'),
        ]
        return custom_urls + urls

    # Vue pour confirmer la réservation et changer le statut
    def confirm_reservation(self, request, reservation_id):
        reservation = self.get_object(request, reservation_id)
        if not reservation:
            self.message_user(request, "Réservation introuvable.", level=messages.ERROR)
        elif reservation.payment_status != 'paid':
            self.message_user(request, "La réservation n'a pas encore été payée.", level=messages.ERROR)
        elif reservation.status != 'pending':
            self.message_user(request, "La réservation est déjà confirmée ou annulée.", level=messages.WARNING)
        else:
            reservation.status = 'confirmed'
            reservation.save()
            self.message_user(request, "Réservation confirmée avec succès.", level=messages.SUCCESS)

        return redirect(request.META.get('HTTP_REFERER', '/admin/'))

# Si tu as besoin de ta vue personnalisée pour afficher toutes les réservations :
def admin_reservations(request):
    reservations = Reservation.objects.all()
    return render(request, 'reservations/admin_reservations.html', {'reservations': reservations})

