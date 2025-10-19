from django import forms
from photobooths.models import Photobooth  # ou le bon chemin vers le modèle

class PhotoboothForm(forms.ModelForm):
    class Meta:
        model = Photobooth
        fields = ['name', 'description', 'price', 'image']


