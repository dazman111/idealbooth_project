from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.contrib import messages
from .models import Message
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode
from django.core.mail import send_mail
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils.timezone import now
from django.utils import timezone
from datetime import timedelta
from django.views import View
from django.urls import reverse, reverse_lazy
from django.contrib.auth.views import LoginView
from django.utils.decorators import method_decorator
from django.conf import settings

from .forms import CustomUserCreationForm, ProfileUpdateForm, PasswordResetWithoutOldForm
from .serializers import PhotoboothSerializer

from blog.models import Article
from reservations.models import Reservation, Invoice
from photobooths.models import Photobooth, Favorite

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticatedOrReadOnly

# ------------------------------------------------------
# AUTHENTIFICATION
# ------------------------------------------------------

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()

            # Génération du lien d'activation
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            activation_link = request.build_absolute_uri(
                reverse('activate_account', kwargs={'uidb64': uid, 'token': token})
            )

            # Envoi email
            send_mail(
                "Activation de votre compte",
                f"Bonjour {user.username},\n\nCliquez sur ce lien pour activer votre compte :\n{activation_link}",
                "noreply@monsite.com",
                [user.email],
                fail_silently=False,
            )

            messages.success(request, "📩 Compte créé ! Veuillez vérifier vos emails pour activer votre compte.")
            return redirect("login")
        
    else:
        form = CustomUserCreationForm()
    return render(request, 'accounts/register.html', {'form': form})

def activate_account(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        messages.success(request, "Votre compte a été activé avec succès. Vous pouvez maintenant vous connecter.")
        return redirect('login')
    else:
        messages.error(request, "Le lien d'activation est invalide ou expiré.")
        return redirect('register')


class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'

    def get_success_url(self):
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return reverse_lazy('admin_dashboard')
        return reverse_lazy('home')
    
    def form_invalid(self, form):
        from django.contrib import messages
        messages.error(self.request, "Identifiants invalides. Veuillez réessayer.")
        return super().form_invalid(form)


def logout_view(request):
    logout(request)
    return redirect('login')


# ------------------------------------------------------
# PROFIL UTILISATEUR
# ------------------------------------------------------

@login_required
def profile(request):
    return render(request, 'accounts/profile.html')


@login_required
def edit_profile(request):
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profil mis à jour avec succès.")
            return redirect('user_dashboard')
        else:
            messages.error(request, "Veuillez corriger les erreurs ci-dessous.")
    else:
        form = ProfileUpdateForm(instance=request.user)

    return render(request, 'accounts/edit_profile.html', {'form': form})


@method_decorator(login_required, name='dispatch')
class CustomPasswordResetView(View):
    template_name = 'accounts/change_password.html'

    def get(self, request):
        form = PasswordResetWithoutOldForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = PasswordResetWithoutOldForm(request.POST)
        if form.is_valid():
            form.save(request.user)
            messages.success(request, "Votre mot de passe a été mis à jour.")
            return redirect('password_change_done')
        return render(request, self.template_name, {'form': form})

@login_required
def request_account_deletion(request):
    user = request.user
    if user.deleted_at:
        messages.warning(request, "Votre compte est déjà en attente de suppression.")
    else:
        user.deleted_at = timezone.now() + timedelta(days=30)
        user.save()
        messages.success(request, "Votre compte sera supprimé définitivement dans 30 jours. Vous pouvez annuler avant cette date.")

    return redirect('user_dashboard')  # redirige vers le dashboard

@login_required
def cancel_account_deletion(request):
    user = request.user
    if user.deleted_at:
        user.deleted_at = None
        user.save()
        messages.success(request, "La suppression de votre compte a été annulée.")
    else:
        messages.info(request, "Votre compte n'était pas en suppression.")
    return redirect('user_dashboard')

def account_protection_notice(request):
    return render(request, "accounts/account_protection_notice.html")



# ------------------------------------------------------
# TABLEAU DE BORD UTILISATEUR
# ------------------------------------------------------

@login_required(login_url='home')
def user_dashboard(request):
    invoices = Invoice.objects.filter(user=request.user).prefetch_related('reservations_linked').order_by('-created_at')
    paginator = Paginator(invoices, 5)
    page_number = request.GET.get('page', 1)

    try:
        page_obj = paginator.page(page_number)
    except (PageNotAnInteger, EmptyPage):
        page_obj = paginator.page(1)

    return render(request, 'accounts/user_dashboard.html', {
        'page_obj': page_obj,
        'user': request.user,
        'today': now().date(),
    })


# ------------------------------------------------------
# CONTACT ADMIN
# ------------------------------------------------------
User = get_user_model()

@login_required
def user_messages(request):
    messages_list = Message.objects.filter(
        recipient=request.user
    ) | Message.objects.filter(sender=request.user)
    messages_list = messages_list.order_by('-created_at')

    # Compter les messages non lus
    unread_messages_count = Message.objects.filter(
        recipient=request.user,
        is_read=False
    ).count()

    if request.method == 'POST':
        subject = request.POST.get('subject')
        body = request.POST.get('body')
        admin = User.objects.filter(is_staff=True).first()

        if admin:
            Message.objects.create(
                sender=request.user,
                recipient=admin,
                subject=subject,
                body=body
            )
            messages.success(request, "Message envoyé à l’administrateur.")
            return redirect('user_messages')
        else:
            messages.error(request, "Aucun administrateur disponible.")

    return render(request, 'accounts/user_messages.html', {  # <--- changé ici
        'messages_list': messages_list,
        'unread_messages_count': unread_messages_count  # <-- ajouté
    })

@login_required
def contact_admin(request):
    if request.method == "POST":
        subject = request.POST.get("subject")
        message = request.POST.get("message")
        full_message = f"Message de {request.user.get_full_name()} ({request.user.email}) :\n\n{message}"

        send_mail(
            subject,
            full_message,
            settings.DEFAULT_FROM_EMAIL,
            [settings.ADMIN_EMAIL],
        )
        messages.success(request, "Votre message a bien été envoyé.")
        return redirect('user_dashboard')

    return redirect('user_dashboard')

@login_required
def user_favorites(request):
    favorites = Favorite.objects.filter(user=request.user).select_related("photobooth")
    return render(request, "accounts/user_favorites.html", {"favorites": favorites})


@login_required
def toggle_favorite(request, photobooth_id):
    photobooth = get_object_or_404(Photobooth, id=photobooth_id)
    favorite, created = Favorite.objects.get_or_create(user=request.user, photobooth=photobooth)
    if not created:
        favorite.delete()  # si déjà en favoris => retirer
    return redirect(request.META.get("HTTP_REFERER", "user_dashboard"))


# ------------------------------------------------------
# API : Photobooth
# ------------------------------------------------------

class PhotoboothViewSet(viewsets.ModelViewSet):
    queryset = Photobooth.objects.all()
    serializer_class = PhotoboothSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]  # ✅ Sécurité ajoutée


# ------------------------------------------------------
# REDIRECTIONS
# ------------------------------------------------------

def home(request):
    return render(request, 'home.html')

def profile_view(request):
    return render(request, 'accounts/profile.html')

def redirect_to_password_reset(request):
    return redirect(reverse('password_reset_custom'))
