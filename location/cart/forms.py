from django import forms
from .models import CartItem
import datetime

class AddToCartForm(forms.Form):
    date_debut = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Date de début"
    )
    date_fin = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Date de fin"
    )
    quantite = forms.IntegerField(min_value=1, initial=1)
    type_evenement = forms.ChoiceField(choices=[
        ('mariage', 'Mariage'),
        ('bapteme', 'Baptême'),
        ('anniversaire', 'Anniversaire'),
        ('fete_entreprise', 'Fête entreprise'),
    ])

    class Meta:
        model = CartItem
        fields = ['date_debut', 'date_fin']

    def clean(self):
        cleaned_data = super().clean()
        date_debut = cleaned_data.get('date_debut')
        date_fin = cleaned_data.get('date_fin')

        if date_debut and date_fin:
            if date_debut < datetime.date.today():
                raise forms.ValidationError("La date de début ne peut pas être dans le passé.")
            if date_fin < date_debut:
                raise forms.ValidationError("La date de fin doit être postérieure à la date de début.")
        return cleaned_data