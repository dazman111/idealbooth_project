from rest_framework import serializers
from .models import Reservation

class ReservationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reservation
        fields = ['id', 'user', 'photobooth', 'start_date', 'end_date', 'status', 'date_location', 'invoice']

    def update(self, instance, validated_data):
        # Si le status est mis à jour, on s'assure que la valeur est correcte
        if 'status' in validated_data:
            status = validated_data['status']
            if status not in dict(Reservation.STATUS_CHOICES).keys():
                raise serializers.ValidationError("Statut invalide")
        return super().update(instance, validated_data)
