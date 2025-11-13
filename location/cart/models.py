from django.db import models
from django.conf import settings
from decimal import Decimal
from photobooths.models import Photobooth
from coupons.models import Coupon

class Cart(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    coupon = models.ForeignKey('coupons.Coupon', null=True, blank=True, on_delete=models.SET_NULL)

    def get_subtotal_price(self):
        """Total sans réduction."""
        total = Decimal('0.00')
        for item in self.items.all():
            total += item.subtotal
        return total
    
    def get_total_without_discount(self):
        """Total sans réduction (même que get_subtotal_price mais peut être utilisé différemment)."""
        return self.get_subtotal_price()

    def get_discount(self):
        """Montant de la réduction appliquée par le coupon."""
        if self.coupon:
            subtotal = self.get_subtotal_price()
            if self.coupon.discount_type == 'percent':
                return subtotal * (Decimal(self.coupon.discount_value) / Decimal('100'))
            elif self.coupon.discount_type == 'fixed':
                return Decimal(self.coupon.discount_value)
        return Decimal('0.00')

    def get_total_price(self):
        """Total après réduction."""
        return self.get_subtotal_price() - self.get_discount()

    def __str__(self):
        return f"Panier de {self.user.username} - créé le {self.created_at.date()}"


class CartItem(models.Model):
    EVENEMENT_CHOICES = [
        ('mariage', 'Mariage'),
        ('bapteme', 'Baptême'),
        ('anniversaire', 'Anniversaire'),
        ('entreprise', 'Événement d’entreprise'),
    ]

    cart = models.ForeignKey(Cart, related_name='items', on_delete=models.CASCADE)
    photobooth = models.ForeignKey(Photobooth, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    quantite = models.PositiveIntegerField(default=1)
    type_evenement = models.CharField(max_length=50, choices=EVENEMENT_CHOICES, default='mariage')

    @property
    def duration(self):
        """Durée en jours (minimum 1 jour)."""
        if self.start_date and self.end_date and self.end_date >= self.start_date:
            return (self.end_date - self.start_date).days + 1
        return 1

    @property
    def subtotal(self):
        """Prix total = prix/jour × quantité × durée."""
        return self.photobooth.price * self.quantite * self.duration

    def __str__(self):
        return f"{self.quantite} × {self.photobooth.name} ({self.start_date} → {self.end_date})"
