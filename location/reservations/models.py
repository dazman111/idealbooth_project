from django.db import models
from django.conf import settings
from coupons.models import Coupon
from datetime import date
from django.utils.translation import gettext_lazy as _
from django.utils import timezone  # Ajout nécessaire pour timezone.now()


class Reservation(models.Model):
    PENDING = 'pending'
    CONFIRMED = 'confirmed'
    CANCELED = 'canceled'
    
    STATUS_CHOICES = [
        (PENDING, _('En attente')),
        (CONFIRMED, _('Confirmée')),
        (CANCELED, _('Annulée')),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    photobooth = models.ForeignKey('photobooths.Photobooth', on_delete=models.CASCADE)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    date_location = models.DateField(default=date.today)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING)
    quantity = models.PositiveIntegerField(default=2)

    invoice = models.ForeignKey(
        'Invoice',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reservations_linked'
    )

    def __str__(self):
        return f"{self.photobooth.name} - {self.status} ({self.start_date.date()} → {self.end_date.date()})"

    def is_available(self):
        from .utils import is_photobooth_available
        return is_photobooth_available(self.photobooth, self.start_date, self.end_date)
    
    def est_active(self):
        now = timezone.now()
        return self.date_debut <= now <= self.date_fin and not self.retourne

    @classmethod
    def check_availability(cls, photobooth, start_date, end_date):
        from .utils import is_photobooth_available
        return is_photobooth_available(photobooth, start_date, end_date)

    # --- Ajout des méthodes save et delete pour mise à jour du stock ---
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.photobooth.update_available()

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        self.photobooth.update_available()


class Invoice(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ('pending', _('En attente de paiement')),
        ('paid', _('Payée')),
        ('failed', _('Échec du paiement')),
        ('refunded', _('Remboursée')),
        ('cancelled', _('Annulée par l\'utilisateur')),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text=_("Montant total de la facture (incluant les réductions).")
    )
    payment_status = models.CharField(
        max_length=50,
        choices=PAYMENT_STATUS_CHOICES,
        default='pending'
    )
    stripe_checkout_session_id = models.CharField(
        max_length=255, null=True, blank=True, unique=True,
        help_text=_("ID de la session Stripe Checkout.")
    )
    stripe_payment_intent_id = models.CharField(
        max_length=255, null=True, blank=True, unique=True,
        help_text=_("ID du Payment Intent Stripe après succès.")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Coupon information
    coupon_used = models.ForeignKey(
        Coupon,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Coupon appliqué à cette facture."
    )
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Montant de la réduction appliquée.")

    # --- Infos société ---
    company_name = models.CharField(max_length=255, blank=True, null=True, help_text=_("Nom de la société"))
    company_vat_number = models.CharField(max_length=50, blank=True, null=True, help_text=_("Numéro de TVA intracommunautaire"))
    company_phone = models.CharField(max_length=20, blank=True, null=True, help_text=_("Numéro de téléphone de la société"))
    company_email = models.EmailField(blank=True, null=True, help_text=_("Adresse email de la société"))
    company_address = models.TextField(blank=True, null=True, help_text=_("Adresse complète de la société"))

    def __str__(self):
        return f"Facture #{self.id} de {self.user.username} - {self.total_amount}€ ({self.get_payment_status_display()})"
    
    def apply_coupon(self, coupon: Coupon):
        """Applique un coupon à la facture et met à jour le montant final."""
        if coupon and coupon.est_valide():
            remise = coupon.apply_discount(self.total_amount)
            self.discount_amount = remise
            self.coupon_used = coupon
            self.total_amount -= remise
            self.save()
            return True
        return False
    
    def save(self, *args, **kwargs):
        if not self.company_name:
            self.company_name = "Idealbooth SARL"
            self.company_vat_number = "N TVA 12345678900978"
            self.company_phone = "+32 465 45 67 89"
            self.company_email = "bpgloire@gmail.com"
            self.company_address = " 123 Rue des Lumières, 6000 Charleroi, Belgique"
        super().save(*args, **kwargs)
