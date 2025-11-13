import json
import logging
from django.db import models
from django.shortcuts import render, redirect, get_object_or_404
from .models import Cart, CartItem
from django.db.models import Sum
from photobooths.models import Photobooth
from .forms import AddToCartForm  # S'assurer que ce formulaire existe
from django.contrib.auth.decorators import login_required
from datetime import datetime
from django.contrib import messages
from django.urls import reverse
from reservations.models import Reservation, Invoice  # Importe tes modèles mis à jour
from django.views.decorators.http import require_POST
from coupons.models import Coupon
from django.utils import timezone
from django.db import transaction
from decimal import Decimal, ROUND_HALF_UP

import stripe

from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.contrib.auth import get_user_model  # <-- Correction: Importe get_user_model
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from decimal import Decimal
from django.views.decorators.http import require_POST
from django.db import transaction  # <-- Ajoute cet import pour les transactions atomiques
from django.utils.timezone import now  # <-- Ajoute cet import pour now()
from django.views.decorators.csrf import csrf_exempt
from coupons.models import Coupon
from datetime import date


# Configurez un logger
import logging
logger = logging.getLogger(__name__)

# Initialise Stripe API key
stripe.api_key = settings.STRIPE_SECRET_KEY

# Récupère le modèle User une seule fois
User = get_user_model()  # <-- Correction de la NameError

# --- Vues de gestion du panier ---

@login_required
def add_to_cart(request, photobooth_id):
    photobooth = get_object_or_404(Photobooth, id=photobooth_id)

    if request.method == "POST":
        try:
            quantite = int(request.POST.get('quantite', 1))
            if quantite <= 0:
                messages.error(request, "La quantité doit être supérieure à zéro.")
                return redirect(request.META.get('HTTP_REFERER', '/'))
        except ValueError:
            messages.error(request, "Quantité invalide.")
            return redirect(request.META.get('HTTP_REFERER', '/'))

        try:
            start_date = datetime.strptime(request.POST.get('start_date'), '%Y-%m-%d').date()
            end_date = datetime.strptime(request.POST.get('end_date'), '%Y-%m-%d').date()
        except (ValueError, TypeError):
            messages.error(request, "Dates invalides ou manquantes.")
            return redirect(request.META.get('HTTP_REFERER', '/'))

        if end_date < start_date:
            messages.error(request, "La date de fin doit être après la date de début.")
            return redirect(request.META.get('HTTP_REFERER', '/'))

        if start_date < date.today():
            messages.error(request, "La date de début ne peut pas être dans le passé.")
            return redirect(request.META.get('HTTP_REFERER', '/'))

        # Vérification du stock disponible
        total_reserved = Reservation.objects.filter(
            photobooth=photobooth,
            start_date__lte=end_date,
            end_date__gte=start_date,
            status=Reservation.CONFIRMED
        ).aggregate(total=Sum('quantity'))['total'] or 0

        existing_item = CartItem.objects.filter(
            cart__user=request.user,
            photobooth=photobooth,
            start_date=start_date,
            end_date=end_date
        ).first()

        user_existing_qty = existing_item.quantite if existing_item else 0

        total_in_other_carts = CartItem.objects.filter(
            photobooth=photobooth,
            start_date__lte=end_date,
            end_date__gte=start_date
        ).exclude(cart__user=request.user).aggregate(total=Sum('quantite'))['total'] or 0

        disponible = photobooth.stock - total_reserved - total_in_other_carts

        if disponible <= 0:
            messages.error(request, "Ce photobooth est actuellement indisponible pour ces dates.")
            return redirect(request.META.get('HTTP_REFERER', '/'))

        max_possible = disponible - user_existing_qty
        if quantite > max_possible:
            if max_possible <= 0:
                messages.error(request, "La quantité demandée dépasse la disponibilité. Aucune unité supplémentaire ne peut être ajoutée.")
                return redirect(request.META.get('HTTP_REFERER', '/'))
            else:
                quantite = max_possible
                messages.warning(request, f"Seules {quantite} unité(s) ont été ajoutées en raison du stock limité.")

        cart, _ = Cart.objects.get_or_create(user=request.user)

        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            photobooth=photobooth,
            start_date=start_date,
            end_date=end_date,
            defaults={'quantite': quantite}
        )

        if not created:
            cart_item.quantite += quantite
            cart_item.save()
            messages.success(request, f"Quantité mise à jour à {cart_item.quantite} dans votre panier.")
        else:
            messages.success(request, "Article ajouté au panier avec succès !")

        return redirect(request.META.get('HTTP_REFERER', '/'))

    messages.error(request, "Requête invalide.")
    return redirect('photobooth_list')


@login_required
def remove_from_cart(request, item_id):
    item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    item.delete()
    messages.info(request, "Article retiré du panier.")
    return redirect('cart_detail')


@login_required
def update_cart_item(request, item_id):
    item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)

    if request.method == 'POST':
        try:
            quantite = int(request.POST.get('quantite', 1))
            type_evenement = request.POST.get('type_evenement', 'mariage')  # Valeur par défaut

            start_date_str = request.POST.get('start_date')
            end_date_str = request.POST.get('end_date')

            option_id = request.POST.get('option_id')
            option = None
            if option_id:
                option = get_object_or_404(PhotoboothOption, id=option_id, photobooth=item.photobooth)

            if start_date_str and end_date_str:
                new_start_dt = datetime.strptime(start_date_str, "%Y-%m-%d")
                new_end_dt = datetime.strptime(end_date_str, "%Y-%m-%d")
                new_end_dt = new_end_dt.replace(hour=23, minute=59, second=59)

                if new_end_dt < new_start_dt:
                    messages.error(request, "La date de fin ne peut pas être antérieure à la date de début.")
                    return redirect('cart_detail')

                conflit_reservation = Reservation.objects.filter(
                    photobooth=item.photobooth,
                    start_date__lte=new_end_dt,
                    end_date__gte=new_start_dt
                ).exists()

                conflit_cartitem = CartItem.objects.filter(
                    cart=item.cart,
                    photobooth=item.photobooth,
                    start_date__lte=new_end_dt.date(),
                    end_date__gte=new_start_dt.date()
                ).exclude(id=item.id).exists()

                if conflit_reservation or conflit_cartitem:
                    messages.error(request, "Ce photobooth est déjà réservé sur cette période (panier ou confirmé).")
                    return redirect('cart_detail')

                item.start_date = new_start_dt.date()
                item.end_date = new_end_dt.date()

            item.quantite = quantite
            item.type_evenement = type_evenement
            item.option = option
            item.save()

            messages.success(request, "Article mis à jour avec succès.")
        except (ValueError, TypeError) as e:
            messages.error(request, f"Erreur lors de la mise à jour de l’article : {str(e)}")

    return redirect('cart_detail')

@login_required
def cart_detail(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)

    subtotal = cart.get_total_without_discount()
    discount = cart.get_discount()
    final_total = cart.get_total_price()
    coupon = cart.coupon

    return render(request, 'cart/cart_detail.html', {
        'cart': cart,
        'subtotal': subtotal,
        'discount': discount,
        'final_total': final_total,
        'coupon': coupon,
        'STRIPE_PUBLISHABLE_KEY': settings.STRIPE_PUBLISHABLE_KEY,
    })

# --- Vues de Paiement ---

@login_required
def checkout(request):
    messages.warning(request, "La page de checkout directe n'est plus utilisée. Veuillez passer par le panier.")
    return redirect('cart_detail')


@login_required
@require_POST
def create_checkout_session(request):
    user = request.user
    cart = Cart.objects.filter(user=user).first()

    if not cart or not cart.items.exists():
        return JsonResponse({'error': 'Votre panier est vide.'}, status=400)

    # Total après réduction
    total_after_discount = cart.get_total_price()
    unit_amount_cents = int((total_after_discount * Decimal('100')).to_integral_value(rounding=ROUND_HALF_UP))

    if unit_amount_cents <= 0:
        return JsonResponse({'error': 'Le montant du panier est invalide.'}, status=400)
        

    # Création d'un seul line_item pour tout le panier
    line_items = [{
        'price_data': {
            'currency': 'eur',
            'product_data': {
                'name': f'Panier de {cart.user.username}',
            },
            'unit_amount': unit_amount_cents,
        },
        'quantity': 1,
    }]

    # Création facture + réservations
    try:
        with transaction.atomic():
            invoice = Invoice.objects.create(
                user=user,
                total_amount=total_after_discount,
                payment_status='pending'
            )

            for item in cart.items.all():
                Reservation.objects.create(
                    user=user,
                    photobooth=item.photobooth,
                    start_date=datetime.combine(item.start_date, datetime.min.time()),
                    end_date=datetime.combine(item.end_date, datetime.max.time()),
                    status=Reservation.PENDING,
                    invoice=invoice,
                )

            # Création session Stripe
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                customer_email=user.email,
                line_items=line_items,
                mode='payment',
                success_url=request.build_absolute_uri(reverse('checkout_success')),
                cancel_url=request.build_absolute_uri('/panier/'),
                metadata={'invoice_id': str(invoice.id)},
            )

        return JsonResponse({'id': checkout_session.id})

    except Exception as e:
        return JsonResponse({'error': f'Erreur lors de la création de la session Stripe : {str(e)}'}, status=500)


@csrf_exempt
@require_POST
def stripe_webhook(request):
    """
    Webhook Stripe : met automatiquement à jour la facture après paiement réussi,
    confirme les réservations, vide le panier et envoie un e-mail.
    """
    import json

    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
        logger.info(f"Webhook Stripe reçu : {event['type']}")
    except (ValueError, stripe.error.SignatureVerificationError):
        # Mode fallback local (utile en dev)
        try:
            event = json.loads(payload)
            logger.warning("Webhook traité sans vérification de signature (mode debug).")
        except Exception as e:
            logger.error(f"Erreur de parsing JSON : {e}")
            return HttpResponse(status=400)

    # --- 1️⃣ Paiement complété ---
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        payment_intent_id = session.get("payment_intent")
        metadata = session.get("metadata") or {}
        invoice_id = metadata.get("invoice_id")

        if not invoice_id:
            logger.error("invoice_id manquant dans la session Stripe.")
            return HttpResponse(status=400)

        try:
            invoice = Invoice.objects.select_for_update().get(id=invoice_id)
        except Invoice.DoesNotExist:
            logger.error(f"Facture introuvable : ID={invoice_id}")
            return HttpResponse(status=404)

        # Évite un double traitement
        if invoice.payment_status == "paid":
            return HttpResponse(status=200)

        try:
            # --- Vérification du paiement Stripe ---
            payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)

            if payment_intent["status"] == "succeeded":
                with transaction.atomic():
                    invoice.payment_status = "paid"
                    invoice.stripe_checkout_session_id = session.get("id")
                    invoice.stripe_payment_intent_id = payment_intent_id
                    invoice.updated_at = now()
                    invoice.save()
                    logger.info(f"Facture {invoice.id} marquée comme PAYÉE automatiquement.")

                    # --- Gestion du coupon ---
                    user_cart = Cart.objects.filter(user=invoice.user).first()
                    if user_cart and user_cart.coupon:
                        coupon = user_cart.coupon
                        coupon.utilisations_effectuees += 1
                        if coupon.utilisations_effectuees >= coupon.utilisation_max:
                            coupon.actif = False
                        coupon.save()
                        logger.info(f"Coupon {coupon.code} utilisé ({coupon.utilisations_effectuees}/{coupon.utilisation_max})")

                    # --- 4️⃣ Confirmation des réservations ---
                    confirmed_reservations = []
                    for res in invoice.reservations_linked.all():
                        if res.photobooth.is_available_for_dates(res.start_date, res.end_date, res.quantity):
                            res.status = Reservation.CONFIRMED
                        else:
                            res.status = Reservation.CANCELED
                        res.save()
                        confirmed_reservations.append(res)

                    # --- 5️⃣ Vider le panier ---
                    if user_cart:
                        user_cart.items.all().delete()
                        logger.info(f"Panier vidé pour {invoice.user.email}")

                    # --- 6️⃣ Envoi email confirmation ---
                    if invoice.user and confirmed_reservations:
                        subject = "Confirmation de votre réservation IdealBooth"
                        html_message = render_to_string("emails/confirmation_reservation.html", {
                            "user": invoice.user,
                            "invoice": invoice,
                            "reservations": confirmed_reservations,
                        })
                        plain_message = strip_tags(html_message)
                        try:
                            send_mail(
                                subject, plain_message, settings.DEFAULT_FROM_EMAIL,
                                [invoice.user.email], html_message=html_message
                            )
                            logger.info(f"E-mail de confirmation envoyé à {invoice.user.email}.")
                        except Exception as mail_e:
                            logger.error(f"Erreur e-mail : {mail_e}")

            else:
                # Paiement non réussi
                invoice.payment_status = "failed"
                invoice.save()
                logger.warning(f"⚠️ Paiement échoué pour la facture {invoice.id}")

        except Exception as e:
            logger.error(f"❌ Erreur lors du traitement du webhook Stripe : {e}", exc_info=True)
            return HttpResponse(status=500)

    # --- 7️⃣ Paiement échoué ---
    elif event["type"] == "payment_intent.payment_failed":
        payment_intent = event["data"]["object"]
        try:
            invoice = Invoice.objects.get(stripe_payment_intent_id=payment_intent.get("id"))
            if invoice.payment_status != "paid":
                invoice.payment_status = "failed"
                invoice.save()
                for res in invoice.reservations_linked.all():
                    res.status = Reservation.CANCELED
                    res.save()
                logger.info(f"💀 Facture {invoice.id} et réservations annulées (échec paiement).")
        except Invoice.DoesNotExist:
            logger.warning(f"Aucune facture trouvée pour PaymentIntent {payment_intent.get('id')}.")

    return HttpResponse(status=200)

@login_required
def checkout_success(request):
    """
    Vue appelée après un paiement Stripe réussi (redirection).
    Vide le panier ici (comme avant).
    """
    try:
        cart = Cart.objects.filter(user=request.user).first()
        if cart:
            cart.items.all().delete()
            cart.save()
    except Exception as e:
        logger.error(f"Erreur lors du vidage du panier dans checkout_success : {e}")

    messages.success(request, "Paiement réussi ! Votre panier a été vidé.")
    return render(request, 'cart/checkout_success.html')

@login_required
def confirm_cart(request):
    """
    Affiche le résumé du panier avant le paiement.
    """
    cart = Cart.objects.filter(user=request.user).first()
    if not cart or cart.items.count() == 0:
        messages.warning(request, "Votre panier est vide. Veuillez ajouter des articles avant de confirmer.")
        return redirect('cart_detail') # Redirige vers la vue détaillée du panier

    total_without_discount = cart.get_subtotal_price()
    discount = cart.get_discount()
    total_price = cart.get_total_price()


    return render(request, 'cart/confirm_cart.html', {
        'cart': cart,
        'total_without_discount': total_without_discount,
        'discount': discount,
        'total_price': total_price,
        "STRIPE_PUBLISHABLE_KEY": settings.STRIPE_PUBLISHABLE_KEY,
    })


def payment_success(request):
    """
    Cette vue semble être un doublon de checkout_success ou une alternative.
    Considérez de n'en garder qu'une ou de les différencier clairement.
    """
    messages.success(request, "Paiement réussi ! Votre commande est en cours de traitement.")
    return render(request, 'cart/payment_success.html') # Assure-toi que ce template existe

# cart/views.py
@login_required
def apply_coupon(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            code = data.get('code', '').strip()
        except Exception:
            return JsonResponse({'success': False, 'message': "Requête invalide."})

        if not code:
            return JsonResponse({'success': False, 'message': "Veuillez entrer un code."})

        try:
            coupon = Coupon.objects.get(code__iexact=code, actif=True)
        except Coupon.DoesNotExist:
            return JsonResponse({'success': False, 'message': "Code promo invalide."})

        now = timezone.now()
        if coupon.date_debut > now or coupon.date_fin < now:
            return JsonResponse({'success': False, 'message': "Ce code n'est pas valable actuellement."})

        cart = Cart.objects.filter(user=request.user).first()
        if not cart or not cart.items.exists():
            return JsonResponse({'success': False, 'message': "Votre panier est vide."})

        subtotal = sum(item.subtotal for item in cart.items.all())

        # Calcul selon le type de réduction
        if coupon.discount_type == 'percent':
            discount_amount = subtotal * (float(coupon.discount_value) / 100)
        elif coupon.discount_type == 'fixed':
            discount_amount = float(coupon.discount_value)
        else:
            discount_amount = 0

        total = max(subtotal - discount_amount, 0)

        # Sauvegarde du coupon dans le panier
        cart.coupon = coupon
        cart.save()

        return JsonResponse({
            'success': True,
            'message': f"Le code {coupon.code} a été appliqué avec succès !",
            'coupon_code': coupon.code,
            'discount_type': coupon.discount_type,
            'discount_value': float(coupon.discount_value),
            'discount_amount': round(discount_amount, 2),
            'subtotal': round(subtotal, 2),
            'total': round(total, 2),
        })

    return JsonResponse({'success': False, 'message': "Méthode non autorisée."})


@login_required
def remove_coupon(request):
    """
    Supprime le coupon de la session et du panier.
    """
    if COUPON_SESSION_ID in request.session:
        del request.session[COUPON_SESSION_ID]
    cart, _ = Cart.objects.get_or_create(user=request.user)
    cart.coupon = None
    cart.save()
    messages.info(request, "Le code promo a été retiré.")
    return redirect('cart_detail')

def get_cart_item_count(request):
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
        count = cart.items.count()
    else:
        count = 0
    return JsonResponse({'count': count})