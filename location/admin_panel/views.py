from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import get_user_model
from django.http import JsonResponse, FileResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages as django_messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from accounts.models import Message
from django.db.models import Count, Sum, F
from django.db.models.functions import TruncMonth
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from io import BytesIO
from reservations.models import Reservation, Invoice
from .forms import PhotoboothForm
from photobooths.models import Photobooth
from .models import Payment
from datetime import datetime
import json
from django.conf import settings
import logging # Importer le module logging
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from reportlab.lib import colors
from blog.models import Article

# Configurez le logger pour cette application
logger = logging.getLogger(__name__) # 'admin_panel' par défaut si le nom de l'app est admin_panel

User = get_user_model()

def is_admin(user):
    return user.is_superuser or user.is_staff

@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    total_users = User.objects.count()
    total_reservations = Reservation.objects.count()
    total_confirmed = Reservation.objects.filter(status='confirmed').count()
    total_cancelled = Reservation.objects.filter(status='cancelled').count()
    total_revenue = Reservation.objects.filter(status='confirmed').aggregate(
        total=Sum(F('photobooth__price'))
    )['total'] or 0

    reservations_by_month = Reservation.objects.filter(status='confirmed') \
        .annotate(month=TruncMonth('start_date')) \
        .values('month') \
        .annotate(count=Count('id'), total=Sum('photobooth__price')) \
        .order_by('month')

    def format_month_data(queryset):
        return [
            {
                'month': item['month'].strftime('%Y-%m-%d'),
                'count': item.get('count', 0),
                'total': item.get('total', 0)
            }
            for item in queryset
        ]

    context = {
        'total_users': total_users,
        'total_reservations': total_reservations,
        'total_confirmed': total_confirmed,
        'total_cancelled': total_cancelled,
        'total_revenue': total_revenue,
        'reservations_by_month': format_month_data(reservations_by_month),
        'revenue_by_month': format_month_data(reservations_by_month),
    }
    return render(request, 'admin_panel/admin_dashboard.html', context)


@login_required
@user_passes_test(is_admin)
def manage_users(request):
    users = User.objects.all().order_by('id')

    return render(request, 'admin_panel/manage_users.html', {'users': users})

@login_required
@user_passes_test(is_admin)
def admin_user_detail(request, user_id):
    user_detail = get_object_or_404(User, id=user_id)
    return render(request, 'admin_panel/partials/user_detail.html', {'user_detail': user_detail})

@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_delete_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == "POST":
        user.is_active = False
        user.save()
        messages.success(request, "Utilisateur désactivé avec succès ✅")
    return redirect('manage_users')


@login_required
@user_passes_test(lambda u: u.is_superuser)
def reactivate_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == "POST":
        user.is_active = True
        user.save()
        messages.success(request, "Utilisateur réactivé avec succès ✅")
    return redirect('manage_users')


@login_required
@user_passes_test(is_admin)
def manage_photobooths(request):
    photobooths = Photobooth.objects.all()
    return render(request, 'admin_panel/manage_photobooths.html', {'photobooths': photobooths})

@login_required
@user_passes_test(is_admin)
def add_photobooth(request):
    if request.method == 'POST':
        form = PhotoboothForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Photobooth ajouté avec succès.")
            return redirect('admin_panel:manage_photobooths')
        else:
            messages.error(request, "Erreur lors de l'ajout du photobooth. Veuillez vérifier les informations.")
    else:
        form = PhotoboothForm()
    return render(request, 'admin_panel/photobooth_form.html', {'form': form, 'title': 'Ajouter un photobooth'})

@login_required
@user_passes_test(is_admin)
def edit_photobooth(request, pk):
    booth = get_object_or_404(Photobooth, pk=pk)
    if request.method == 'POST':
        form = PhotoboothForm(request.POST, request.FILES, instance=booth)
        if form.is_valid():
            form.save()
            messages.success(request, "Photobooth modifié avec succès.")
            return redirect('admin_panel:manage_photobooths')
        else:
            messages.error(request, "Erreur lors de la modification du photobooth. Veuillez vérifier les informations.")
    else:
        form = PhotoboothForm(instance=booth)
    return render(request, 'admin_panel/photobooth_form.html', {'form': form, 'title': 'Modifier le photobooth'})

@login_required
@user_passes_test(is_admin)
@require_POST
def delete_photobooth(request, pk):
    booth = get_object_or_404(Photobooth, pk=pk)
    booth.delete()
    messages.success(request, "Photobooth supprimé avec succès.")
    return redirect('photobooth_list')  #

@login_required
@user_passes_test(is_admin)
def manage_payments(request):
    payments = Payment.objects.all().order_by('-date') 
    
    # --- DÉBUT DES LIGNES DE DÉBOGAGE ---
    logger.debug("\n--- DÉBOGAGE PAIEMENTS ---")
    logger.debug(f"Nombre de paiements récupérés : {payments.count()}")
    if payments.exists():
        logger.debug("Détails des paiements :")
        for p in payments:
            logger.debug(f"  ID: {p.id}, Utilisateur: {p.user.username}, Montant: {p.amount}, Date: {p.date}, Statut: {p.status}, Méthode: {getattr(p, 'method', 'N/A')}, Facture URL: {getattr(p, 'invoice_url', 'N/A')}")
    else:
        logger.debug("Aucun paiement dans le queryset.")
    logger.debug("--- FIN DÉBOGAGE ---")

    context = {'payments': payments}
    return render(request, 'admin_panel/manage_payments.html', context)

@login_required
@user_passes_test(is_admin)
def manage_reservations(request):
    status = request.GET.get('status')
    user_id = request.GET.get('user')

    # IMPORTANT: Ajouter 'invoice' à select_related pour que les infos de facture soient disponibles dans le template
    reservations = Reservation.objects.select_related('user', 'photobooth', 'invoice').all()
    if status:
        reservations = reservations.filter(status=status)
    if user_id:
        reservations = reservations.filter(user__id=user_id)
    
    reservations = reservations.order_by('-start_date')

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        html = render_to_string('admin_panel/partials/_reservation_table.html', {'reservations': reservations})
        return JsonResponse({'html': html})

    users = User.objects.all()
    return render(request, 'admin_panel/manage_reservations.html', {
        'reservations': reservations,
        'users': users
    })

@require_POST
@login_required
@user_passes_test(is_admin)
def update_reservation_status(request):
    logger.debug(f"Début de la fonction update_reservation_status. Méthode: {request.method}")
    try:
        data = json.loads(request.body)
        reservation_id = data.get('id')
        action = data.get('action')
        logger.debug(f"Requête reçue: ID={reservation_id}, Action={action}")

        if not reservation_id or not action:
            logger.warning(f"Données manquantes dans la requête: ID={reservation_id}, Action={action}. Corps reçu: {request.body.decode('utf-8')}")
            return JsonResponse({'success': False, 'error': "ID de réservation ou action manquant."}, status=400)

        reservation = get_object_or_404(Reservation.objects.select_related('invoice'), id=reservation_id)
        logger.debug(f"Réservation trouvée: ID={reservation.id}, Statut actuel={reservation.status}")

        message_success = ""
        error_message = ""

        if action == 'confirm':
            if reservation.status == 'pending':
                reservation.status = 'confirmed'
                reservation.save()
                message_success = "Réservation confirmée avec succès."
                logger.info(f"Réservation {reservation.id} confirmée.")
                envoyer_notification_email(
                    reservation.user,
                    'Votre réservation est confirmée',
                    f"Bonjour {reservation.user.username},\n\nVotre réservation du {reservation.start_date.strftime('%d/%m/%Y')} a bien été confirmée. Merci !"
                )
            else:
                error_message = "La réservation ne peut être confirmée que si son statut est 'En attente'."
                logger.warning(f"Tentative de confirmer la réservation {reservation.id} (statut actuel: {reservation.status}) qui n'est pas 'pending'.")
        elif action == 'cancel':
            # Assurez-vous que les constantes de statut sont correctement définies sur votre modèle Reservation.
            # Exemple: class Reservation(models.Model): PENDING='pending', CONFIRMED='confirmed', CANCELED='cancelled'
            if reservation.status in [Reservation.PENDING, Reservation.CONFIRMED]:
                reservation.status = Reservation.CANCELED
                reservation.save()
                message_success = "Réservation annulée avec succès."
                logger.info(f"Réservation {reservation.id} annulée.")
                envoyer_notification_email(
                    reservation.user,
                    'Votre réservation a été annulée',
                    f"Bonjour {reservation.user.username},\n\nNous vous informons que votre réservation du {reservation.start_date.strftime('%d/%m/%Y')} a été annulée."
                )
            else:
                error_message = "La réservation ne peut être annulée que si son statut est 'En attente' ou 'Confirmée'."
                logger.warning(f"Tentative d'annuler la réservation {reservation.id} (statut actuel: {reservation.status}) qui n'est ni 'pending' ni 'confirmed'.")
        elif action == 'mark_paid':
            if reservation.invoice:
                if reservation.invoice.payment_status != 'paid':
                    reservation.invoice.payment_status = 'paid'
                    reservation.invoice.save()
                    # Si la réservation est en attente, la confirmer aussi quand elle est marquée comme payée
                    if reservation.status == Reservation.PENDING:
                        reservation.status = Reservation.CONFIRMED
                        reservation.save()
                    message_success = "La réservation et la facture associée ont été marquées comme payées."
                    logger.info(f"Réservation {reservation.id} et facture {reservation.invoice.id} marquées comme payées.")
                    envoyer_notification_email(
                        reservation.user,
                        'Votre réservation a été marquée comme payée',
                        f"Bonjour {reservation.user.username},\n\nVotre réservation du {reservation.start_date.strftime('%d/%m/%Y')} a été marquée comme payée."
                    )
                else:
                    error_message = "La facture de cette réservation est déjà marquée comme payée."
                    logger.warning(f"Tentative de marquer la facture {reservation.invoice.id} de la réservation {reservation.id} comme payée, mais elle l'est déjà.")
            else:
                error_message = "Aucune facture associée à cette réservation pour marquer comme payée."
                logger.warning(f"Tentative de marquer la réservation {reservation.id} comme payée, mais aucune facture associée.")
        else:
            error_message = "Action invalide spécifiée."
            logger.warning(f"Action '{action}' invalide reçue pour la réservation {reservation.id}.")

        if error_message:
            logger.error(f"Erreur logique dans update_reservation_status pour ID={reservation_id}, Action={action}: {error_message}")
            return JsonResponse({'success': False, 'error': error_message}, status=400)

        # Récupérer les réservations à nouveau pour rafraîchir le tableau après la mise à jour
        status_filter_param = request.GET.get('status')
        user_id_filter_param = request.GET.get('user')
        
        reservations = Reservation.objects.select_related('user', 'photobooth', 'invoice').all() 
        if status_filter_param:
            reservations = reservations.filter(status=status_filter_param)
        if user_id_filter_param:
            reservations = reservations.filter(user__id=user_id_filter_param)
        
        reservations = reservations.order_by('-start_date')

        html = render_to_string('admin_panel/partials/_reservation_table.html', {'reservations': reservations})
        logger.info(f"Action {action} réussie pour réservation {reservation.id}. Renvoyé HTML mis à jour.")
        return JsonResponse({'success': True, 'html': html, 'message': message_success})

    except Reservation.DoesNotExist:
        logger.error(f"Reservation.DoesNotExist pour l'ID de réservation {reservation_id} fourni.")
        return JsonResponse({'success': False, 'error': 'Réservation introuvable.'}, status=404)
    except json.JSONDecodeError:
        logger.error(f"JSONDecodeError: Requête invalide (JSON mal formé). Corps: {request.body.decode('utf-8')}")
        return JsonResponse({'success': False, 'error': "Requête invalide : JSON mal formé."}, status=400)
    except Exception as e:
        logger.exception(f"Une erreur inattendue est survenue dans update_reservation_status pour ID={reservation_id}, Action={action}.")
        return JsonResponse({'success': False, 'error': f'Une erreur inattendue est survenue : {str(e)}'}, status=500)


@login_required
@user_passes_test(is_admin)
def manage_reservations(request):
    status = request.GET.get('status')
    user_id = request.GET.get('user')

    reservations = Reservation.objects.select_related('user', 'photobooth', 'invoice').all()
    if status:
        reservations = reservations.filter(status=status)
    if user_id:
        reservations = reservations.filter(user__id=user_id)
    
    reservations = reservations.order_by('-start_date')

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        html = render_to_string('admin_panel/partials/_reservation_table.html', {'reservations': reservations})
        return JsonResponse({'html': html})

    users = User.objects.all()
    return render(request, 'admin_panel/manage_reservations.html', {
        'reservations': reservations,
        'users': users
    })


@login_required
def reservation_detail(request, reservation_id):
    try:
        reservation = Reservation.objects.select_related('user', 'photobooth').get(id=reservation_id)
        if not request.user.is_staff and not request.user.is_superuser and reservation.user != request.user:
            return JsonResponse({'success': False, 'error': 'Non autorisé à voir les détails de cette réservation.'}, status=403)

        html = render_to_string('admin_panel/partials/_reservation_detail.html', {'reservation': reservation})
        return JsonResponse({'success': True, 'html': html})
    except Reservation.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Réservation non trouvée'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Une erreur inattendue est survenue : {str(e)}'}, status=500)
    
@login_required
def generate_invoice(request, reservation_id):
    try:
        reservation = get_object_or_404(Reservation, id=reservation_id)

        if reservation.user != request.user:
            return HttpResponse("Non autorisé", status=403)

        if reservation.status != 'confirmed':
            return HttpResponse("La réservation doit être confirmée pour générer une facture.", status=400)

        user = reservation.user

        # --- Infos société (à insérer dans la facture) ---
        company_name = "Idealbooth SARL"
        company_vat_number = "N TVA 12345678900978"
        company_phone = "+32 465 45 67 89"
        company_email = "bpgloire@gmail.com"
        company_address = "123 Rue des Lumières, 6000 Charleroi, Belgique"

        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
# ...

        # En-tête stylisé
        p.setFillColor(colors.HexColor("#171029"))  # violet profond
        p.rect(0, height - 100, width, 100, fill=1, stroke=0)

        # Logo
        logo_path = "static/images/logo11.png"
        try:
            p.drawImage(logo_path, 40, height - 90, width=60, height=60, preserveAspectRatio=True, mask='auto')
        except Exception:
            pass
        p.setFont("Helvetica", 10)
        p.drawRightString(width - 50, height - 60, f"Facture n° {reservation.id}")

        # Numéro de facture horodaté
        now = datetime.now()
        invoice_number = f"{now.strftime('%Y%m%d%H%M%S')}-{reservation.id}"
        p.setFont("Helvetica", 10)
        p.setFillColor(colors.white)
        p.drawRightString(width - 50, height - 60, f"Facture n° {invoice_number}")
        p.drawRightString(width - 50, height - 75, f"Date : {now.strftime('%d/%m/%Y %H:%M')}")

        # Titre de la facture
        p.setFillColor(colors.HexColor("#FFD700"))  # doré
        p.setFont("Helvetica-Bold", 14)
        p.drawString(50, height - 20, "FACTURE DE RÉSERVATION")

        p.setStrokeColor(colors.HexColor("#581fc2"))  # ligne décorative
        p.setLineWidth(2)
        p.line(50, height - 110, width - 50, height - 110)

        # Infos société (à gauche)
        y = height - 140
        p.setFont("Helvetica-Bold", 12)
        p.setFillColor(colors.black)
        p.drawString(50, y, "Émetteur :")
        p.setFont("Helvetica", 11)
        y -= 18
        p.drawString(60, y, company_name)
        y -= 15
        p.drawString(60, y, f"N° TVA : {company_vat_number}")
        y -= 15
        p.drawString(60, y, f"Tél : {company_phone}")
        y -= 15
        p.drawString(60, y, f"Email : {company_email}")
        y -= 15
        p.drawString(60, y, company_address)

        # Infos client (à droite)
        y_client = height - 140
        p.setFont("Helvetica-Bold", 12)
        p.drawString(width / 2 + 20, y_client, "Destinataire :")
        p.setFont("Helvetica", 11)
        y_client -= 18
        p.drawString(width / 2 + 30, y_client, f"{user.get_full_name() or user.username}")
        y_client -= 15
        p.drawString(width / 2 + 30, y_client, f"Email : {user.email}")
        y_client -= 15
        p.drawString(width / 2 + 30, y_client, f"Tél : {getattr(user, 'phone_number', 'Non fourni')}")
        y_client -= 15
        p.drawString(width / 2 + 30, y_client, f"Adresse : {getattr(user, 'address', 'Non fournie')}")

        # Ligne séparatrice
        y = min(y, y_client) - 30
        p.setStrokeColor(colors.grey)
        p.setLineWidth(1)
        p.line(50, y, width - 50, y)
        y -= 30

        # Détails de la réservation
        p.setFont("Helvetica-Bold", 13)
        p.drawString(50, y, "Détails de la Réservation")
        p.setFont("Helvetica", 11)
        y -= 20
        p.drawString(60, y, f"Photobooth : {reservation.photobooth.name}")
        y -= 15
        p.drawString(60, y, f"Date de début : {reservation.start_date.strftime('%d/%m/%Y')}")
        y -= 15
        p.drawString(60, y, f"Date de fin : {reservation.end_date.strftime('%d/%m/%Y')}")
        y -= 30

        # Montant
        p.setFont("Helvetica-Bold", 13)
        p.drawString(50, y, "Montant total à payer")
        p.setFont("Helvetica", 11)
        y -= 20
        p.drawString(60, y, f"Prix TTC : {reservation.photobooth.price:.2f} €")
        y -= 30

        # Encadré Remerciement
        p.setFillColor(colors.HexColor("#8e44ad"))
        p.setFont("Helvetica-Oblique", 11)
        p.drawCentredString(width / 2, y, "Merci pour votre confiance et votre réservation !")


        p.showPage()
        p.save()
        buffer.seek(0)

        return FileResponse(buffer, as_attachment=True, filename=f"facture_{reservation.id}.pdf")

    except Reservation.DoesNotExist:
        return HttpResponse("Réservation introuvable.", status=404)
    except Exception as e:
        return HttpResponse(f"Une erreur est survenue : {str(e)}", status=500)


def envoyer_notification_email(user, sujet, message):
    try:
        send_mail(
            sujet,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
    except Exception as e:
        print(f"Erreur lors de l'envoi de l'email à {user.email}: {e}")

def manage_blog(request):
    # On récupère uniquement les articles publiés (pas les brouillons)
    articles = Article.objects.all().order_by('-created_at')
    return render(request, 'admin_panel/manage_blog.html', {'articles': articles})


def cancelled_count_api(request):
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        count = Reservation.objects.filter(status="canceled").count()
        return JsonResponse({"cancelled_count": count})
    return JsonResponse({"error": "Invalid request"}, status=400)

class CustomLoginView(LoginView):
    def get_success_url(self):
        user = self.request.user
        if user.is_superuser or user.is_staff:
            return reverse_lazy('admin_panel:admin_dashboard')
        return reverse_lazy('accounts:user_dashboard')  # ou une autre vue utilisateur

@login_required
@user_passes_test(is_admin)    
def edit_user(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    if request.method == 'POST':
        user.username = request.POST.get('username')
        user.email = request.POST.get('email')
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        user.save()
        messages.success(request, "Utilisateur mis à jour avec succès.")
        return redirect('manage_users')
    return render(request, 'admin_panel/partials/edit_user.html', {'user': user})


@staff_member_required
def admin_messages(request):
    # Tous les messages reçus par l'admin
    messages_list = Message.objects.filter(recipient=request.user).order_by('-created_at')
    unread_count = messages_list.filter(is_read=False).count()

    # Réponse
    if request.method == 'POST':
        parent_id = request.POST.get('parent_id')
        body = request.POST.get('body')
        parent_msg = get_object_or_404(Message, id=parent_id)
        Message.objects.create(
            sender=request.user,
            recipient=parent_msg.sender,
            subject=f"Re: {parent_msg.subject}",
            body=body,
            parent=parent_msg
        )
        parent_msg.is_read = True
        parent_msg.save()
        messages.success(request, "Réponse envoyée avec succès.")
        return redirect('admin_panel:admin_messages')

    return render(request, 'admin_panel/messages.html', {
        'messages_list': messages_list,
        'unread_count': unread_count
    })

