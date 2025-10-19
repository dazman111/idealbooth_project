from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from datetime import timedelta
from django.conf import settings

class CustomUser(AbstractUser):
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True) 
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)
    deleted_at = models.DateTimeField(null=True, blank=True)  # date prévue de suppression

    @property
    def is_pending_deletion(self):
        return self.deleted_at is not None and self.deleted_at > timezone.now()
    
    def schedule_deletion(self):
        """Programme la suppression dans 30 jours"""
        from django.utils import timezone
        self.deleted_at = timezone.now() + timedelta(days=30)
        self.save()

    def cancel_deletion(self):
        """Annule la suppression programmée"""
        self.deleted_at = None
        self.save()
    
    def __str__(self):
        return self.username

class Message(models.Model):
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="messages_sent"
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="messages_received"
    )
    subject = models.CharField(max_length=255)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    parent = models.ForeignKey('self', null=True, blank=True, related_name='replies', on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.subject} - {self.recipient.username}"

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.subject} - {self.sender}"