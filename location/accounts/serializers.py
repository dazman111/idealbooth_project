from rest_framework import serializers
from photobooths.models import Photobooth

class PhotoboothSerializer(serializers.ModelSerializer):
    class Meta:
        model = Photobooth
        fields = '__all__'
