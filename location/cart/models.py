from django.db import models
from django.conf import settings
from photobooths.models import Photobooth
from coupons.models import Coupon
from datetime import date
from decimal import Decimal

class Cart(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    coupon = models.ForeignKey(Coupon, null=True, blank=True, on_delete=models.SET_NULL)

    def get_discount(self):
        if self.coupon:
            return (self.coupon.discount / 100) * self.get_subtotal_price()
        return 0

    def get_total_price(self):
        return self.get_subtotal_price() - self.get_discount()
    
    def __str__(self):
        return f"Panier de {self.user.username} - créé le {self.created_at.date()}"
    
    def get_total_without_discount(self):
        total = Decimal('0.00')
        for item in self.items.all():
            total += item.subtotal
        return total


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
    option = models.CharField(max_length=100, blank=True, null=True)


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

    def get_total_price(self):
        """Renvoie un prix toujours positif pour Stripe (en float)."""
        total = self.subtotal
        if total <= 0:
            total = 0.01  # Stripe n'accepte pas 0€
        return total

    def __str__(self):
        return f"{self.quantite} × {self.photobooth.name} ({self.start_date} → {self.end_date})"
    
class Coupon(models.Model):
    code = models.CharField(max_length=50, unique=True)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    discount = models.IntegerField(help_text="Réduction en %")
    active = models.BooleanField()

    def __str__(self):
        return self.code
