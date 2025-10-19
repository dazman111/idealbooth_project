from django.db import models 
from django.conf import settings
from datetime import datetime
from django.core.validators import MinValueValidator, MaxValueValidator
from reservations.models import Reservation


class Photobooth(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='photobooths/')
    stock = models.PositiveIntegerField(
        default=3,
        validators=[MinValueValidator(1), MaxValueValidator(3)]
    )
    available = models.PositiveIntegerField(default=3)  # nombre dispo actuel

    def save(self, *args, **kwargs):
    # Lors de la création, initialiser available = stock si ce n’est pas défini
        if not self.pk:
            self.available = self.stock
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.name

    def update_available(self):
        """Met à jour le stock disponible en fonction des réservations confirmées uniquement"""
        confirmed = Reservation.objects.filter(
            photobooth=self,
            status=Reservation.CONFIRMED
        ).aggregate(total=models.Sum('quantity'))['total'] or 0

        self.available = max(0, self.stock - confirmed)
        self.save(update_fields=['available'])

    def available_stock(self, start_date, end_date):
        """Retourne le stock disponible pour les dates données"""
        from cart.models import CartItem
        
        # Réservations confirmées qui chevauchent les dates
        reserved = Reservation.objects.filter(
            photobooth=self,
            status=Reservation.CONFIRMED,
            start_date__lte=datetime.combine(end_date, datetime.max.time()),
            end_date__gte=datetime.combine(start_date, datetime.min.time())
        ).aggregate(total=models.Sum('quantity'))['total'] or 0

        # CartItems non payés qui chevauchent les dates
        in_carts = CartItem.objects.filter(
            photobooth=self,
            start_date=start_date,
            end_date=end_date
        ).aggregate(total=models.Sum('quantity'))['total'] or 0

        dispo = self.stock - reserved - in_carts
        return max(0, dispo)

    def is_available_for_dates(self, start_date, end_date, quantity=1):
        """Vérifie si le photobooth est disponible pour une quantité et des dates"""
        return self.available_stock(start_date, end_date) >= quantity
    
class Favorite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favorites")
    photobooth = models.ForeignKey(Photobooth, on_delete=models.CASCADE, related_name="favorited_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'photobooth')  # empêche les doublons

    def __str__(self):
        return f"{self.user} ❤️ {self.photobooth}"
