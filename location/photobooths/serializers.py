from rest_framework import serializers
from .models import Photobooth

class PhotoboothSerializer(serializers.ModelSerializer):
    class Meta:
        model = Photobooth
        fields = '__all__'
