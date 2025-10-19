from django import forms
from .models import Photobooth

class PhotoboothForm(forms.ModelForm):
    class Meta:
        model = Photobooth
        fields = ['name', 'description', 'image', 'available']
