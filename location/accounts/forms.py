from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import CustomUser
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model

User = get_user_model()

# Formulaire d’inscription
class CustomUserCreationForm(UserCreationForm):
    accept_terms = forms.BooleanField(
        label="J'accepte les politiques de confidentialité et les mentions légales",
        error_messages={'required': "Vous devez accepter les politiques et mentions légales pour créer un compte."}
    )
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'first_name', 'last_name','profile_picture']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_active = False  # Compte inactif jusqu'à activation
        if commit:
            user.save()
        return user

# ✅ Formulaire de modification de profil
class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'first_name', 'last_name', 'phone_number', 'address', 'profile_picture']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'profile_picture': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            
        }

# Formulaire de contact
class ContactForm(forms.Form):
    subject = forms.CharField(max_length=200, label="Sujet")
    message = forms.CharField(widget=forms.Textarea, label="Message")

# Ajout pour changer le mot de passe sans ancien mot de passe
class PasswordResetWithoutOldForm(forms.Form):
    new_password1 = forms.CharField(
        label="Nouveau mot de passe",
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    new_password2 = forms.CharField(
        label="Confirmez le mot de passe",
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("new_password1")
        password2 = cleaned_data.get("new_password2")

        if password1 != password2:
            raise forms.ValidationError("Les mots de passe ne correspondent pas.")
        return cleaned_data

    def save(self, user):
        password = self.cleaned_data["new_password1"]
        user.set_password(password)
        user.save()
        return user

