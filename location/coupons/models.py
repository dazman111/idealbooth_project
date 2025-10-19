from django.db import models
from django.utils import timezone
from decimal import Decimal
from django.conf import settings
from .utils import generate_unique_coupon_code


class Coupon(models.Model):
    CODE_MAX_LENGTH = 20

    DISCOUNT_TYPE_CHOICES = [
        ('percent', 'Pourcentage'),
        ('fixed', 'Montant fixe'),
    ]

    code = models.CharField(max_length=CODE_MAX_LENGTH, unique=True)
    description = models.TextField(blank=True)
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPE_CHOICES)
    discount_value = models.DecimalField(max_digits=6, decimal_places=2, help_text="Pourcentage ou montant selon type")
    date_debut = models.DateTimeField()
    date_fin = models.DateTimeField()
    actif = models.BooleanField(default=True)
    utilisation_max = models.PositiveIntegerField(default=1, help_text="Nombre maximal d'utilisations")
    utilisations_effectuees = models.PositiveIntegerField(default=0)

    def est_valide(self):
        maintenant = timezone.now()
        return (
            self.actif and
            self.date_debut <= maintenant <= self.date_fin and
            self.utilisations_effectuees < self.utilisation_max
        )

    def apply_discount(self, amount):
        """Retourne le montant de la réduction à appliquer sur amount."""
        if not self.est_valide():
            return Decimal('0.00')

        if self.discount_type == 'percent':
            remise = amount * (self.discount_value / Decimal('100'))
            return remise.quantize(Decimal('0.01'))  # arrondi 2 décimales

        if self.discount_type == 'fixed':
            return min(self.discount_value, amount)

        return Decimal('0.00')

    def __str__(self):
        if self.discount_type == 'percent':
            return f"{self.code} - {self.discount_value}%"
        else:
            return f"{self.code} - {self.discount_value} €"

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = generate_unique_coupon_code(Coupon)
        super().save(*args, **kwargs)

class PromotionBanner(models.Model):
    message = models.CharField(max_length=255)  # Texte affiché
    promo_code = models.CharField(max_length=50, blank=True, null=True)  # Code promo cliquable
    start_date = models.DateTimeField()  # Début validité
    end_date = models.DateTimeField()    # Fin validité

    def is_active(self):
        now = timezone.now()
        return self.start_date <= now <= self.end_date

    def __str__(self):
        return f"Promo: {self.message} ({self.start_date} → {self.end_date})"

  