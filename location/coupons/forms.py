from django import forms

class GenerateCouponsForm(forms.Form):
    count = forms.IntegerField(label="Nombre de coupons", min_value=1, initial=5)
    discount = forms.DecimalField(label="Valeur de réduction", decimal_places=2, initial=10)
    percent = forms.BooleanField(label="En pourcentage ?", required=False)
    days = forms.IntegerField(label="Validité (jours)", initial=30)
    utilisation_max = forms.IntegerField(label="Utilisations max", min_value=1, initial=1)
    prefix = forms.CharField(label="Préfixe", required=False)
    description = forms.CharField(label="Description", required=False)
