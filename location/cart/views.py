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
    total = cart.get_total_without_discount()
    discount = cart.get_discount()
    coupon = cart.coupon

    return render(request, 'cart/cart_detail.html', {
        'cart': cart,
        'total': cart.get_total_price(),
        'discount': discount,
        'coupon': coupon,
        'STRIPE_PUBLISHABLE_KEY': settings.STRIPE_PUBLISHABLE_KEY,
    })

# --- Vues de Paiement ---

@login_required
def checkout(request):
    messages.warning(request, "La page de checkout directe n'est plus utilisée. Veuillez passer par le panier.")
    return redirect('cart_detail')

from django.views.decorators.http import require_POST
from django.db import transaction
from django.http import JsonResponse
from django.urls import reverse
from django.utils import timezone
from datetime import datetime
from decimal import Decimal
import stripe

from django.contrib.auth.decorators import login_required
from .models import Cart, Reservation
from invoices.models import Invoice

stripe.api_key = settings.STRIPE_SECRET_KEY


@login_required
@require_POST
def create_checkout_session(request):
    user = request.user
    cart = Cart.objects.filter(user=user).first()

    if not cart or not cart.items.exists():
        return JsonResponse({'error': 'Votre panier est vide.'}, status=400)

    # --- Total après réduction ---
    total_amount = cart.get_total_price()
    line_items = []

    for item in cart.items.all():
        start_dt = datetime.combine(item.start_date, datetime.min.time())
        end_dt = datetime.combine(item.end_date, datetime.max.time())
        days = Decimal((end_dt - start_dt).days + 1)

        base_price = Decimal(str(item.photobooth.price))
        option_price = Decimal(str(item.option.price)) if item.option else Decimal('0.00')
        item_total = (base_price + option_price) * days * Decimal(item.quantite)

        unit_amount_cents = int(item_total.quantize(Decimal('0.01')) * 100)
        if unit_amount_cents <= 0:
            return JsonResponse({'error': 'Un des articles a un prix invalide.'}, status=400)

        line_items.append({
            'price_data': {
                'currency': 'eur',
                'unit_amount': unit_amount_cents,
                'product_data': {
                    'name': f'Photobooth: {item.photobooth.name} ({item.start_date} → {item.end_date})',
                },
            },
            'quantity': 1,
        })

    # --- Si un coupon est appliqué, ajouter la réduction ---
    discounts = None  # Stripe peut gérer un coupon natif
    if cart.coupon:
        try:
            # Création d’un coupon Stripe à usage unique
            stripe_coupon = stripe.Coupon.create(
                name=f"Réduction {cart.coupon.code}",
                percent_off=cart.coupon.discount,
                duration="once"
            )

            stripe_promo = stripe.PromotionCode.create(
                coupon=stripe_coupon.id,
                code=cart.coupon.code
            )

            discounts = [{"promotion_code": stripe_promo.id}]

        except Exception as e:
            # Si Stripe échoue à créer le coupon, on affiche juste la réduction manuellement
            discount_amount = cart.get_discount()
            if discount_amount > 0:
                line_items.append({
                    'price_data': {
                        'currency': 'eur',
                        'unit_amount': int(-discount_amount * 100),
                        'product_data': {
                            'name': f"Réduction ({cart.coupon.code})",
                        },
                    },
                    'quantity': 1,
                })

    # --- Création facture + réservations ---
    try:
        with transaction.atomic():
            invoice = Invoice.objects.create(
                user=user,
                total_amount=total_amount,
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

            # --- Création session Stripe ---
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                customer_email=user.email,
                line_items=line_items,
                mode='payment',
                discounts=discounts if discounts else None,
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
    Gère les événements webhook de Stripe pour mettre à jour les statuts de paiement,
    vider le panier, confirmer les réservations et vérifier la disponibilité du stock.
    """
    import json
   
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET
    
    logger.info("Stripe webhook brut reçu :")
    logger.info(request.body.decode())  # Affiche le JSON brut reçu


   
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
        logger.info(f"Stripe webhook reçu : {event['type']}")
    except (ValueError, stripe.error.SignatureVerificationError) as e:
        logger.warning(f"Signature Stripe invalide ou payload malformé : {e}")
        # --- DEBUG LOCAL UNIQUEMENT ---
        try:
            event = json.loads(payload)
            logger.info("Mode debug : payload analysé sans vérification de signature")
            logger.info(json.dumps(event, indent=2))
        except Exception as json_e:
            logger.error(f"Impossible de parser le JSON du webhook : {json_e}")
            return HttpResponse(status=400)
    except Exception as e:
        logger.error("Erreur inconnue dans le traitement du webhook", exc_info=True)
        return HttpResponse(status=400)

    # --- Paiement complété ---
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        payment_intent_id = session.get('payment_intent')
        metadata = session.get('metadata') or {}
        invoice_id = metadata.get('invoice_id')

        if not invoice_id:
            logger.error(f"Webhook: 'invoice_id' manquant dans la session {session.get('id')}.")
            return HttpResponse(status=400)

        with transaction.atomic():
            try:
                invoice = Invoice.objects.select_for_update().get(id=invoice_id)
            except Invoice.DoesNotExist:
                logger.error(f"Facture (ID: {invoice_id}) introuvable.")
                return HttpResponse(status=404)

            # Évite le double traitement
            if invoice.payment_status == 'paid':
                return HttpResponse(status=200)

            expected_total_cents = int(invoice.total_amount * 100)
            actual_total_cents = session.get('amount_total')

            if actual_total_cents != expected_total_cents:
                logger.error(f"Montant payé ({actual_total_cents}) ≠ attendu ({expected_total_cents}) pour la facture {invoice.id}.")
                invoice.payment_status = 'failed'
                invoice.save()
                return HttpResponse(status=400)

            if session.get('payment_status') == 'paid':
                # Mise à jour de la facture
                invoice.payment_status = 'paid'
                invoice.stripe_checkout_session_id = session.get('id')
                invoice.stripe_payment_intent_id = payment_intent_id
                invoice.updated_at = now()
                invoice.save()
                logger.info(f"Facture {invoice.id} mise à jour au statut 'paid'.")

                # Confirmer les réservations et vérifier le stock final
                confirmed_reservations = []
                for res in invoice.reservations_linked.all():
                    if res.photobooth.is_available_for_dates(res.start_date, res.end_date, res.quantity):
                        res.status = Reservation.CONFIRMED
                        res.save()
                        confirmed_reservations.append(res)
                        logger.info(f"Réservation {res.id} confirmée.")
                    else:
                        res.status = Reservation.CANCELED
                        res.save()
                        logger.warning(f"Réservation {res.id} annulée faute de stock suffisant.")

                # Vider le panier
                try:
                    cart = Cart.objects.get(user=invoice.user)
                    cart.items.all().delete()
                    logger.info(f"Panier vidé pour l'utilisateur {invoice.user.email}.")
                except Cart.DoesNotExist:
                    logger.warning(f"Aucun panier trouvé pour {invoice.user.email}.")

                # Envoi e-mail confirmation
                if invoice.user and confirmed_reservations:
                    subject = "Confirmation de votre réservation IdealBooth"
                    html_message = render_to_string('emails/confirmation_reservation.html', {
                        'user': invoice.user,
                        'invoice': invoice,
                        'reservations': confirmed_reservations,
                    })
                    plain_message = strip_tags(html_message)
                    try:
                        send_mail(
                            subject, plain_message, settings.DEFAULT_FROM_EMAIL,
                            [invoice.user.email], html_message=html_message
                        )
                        logger.info(f"E-mail de confirmation envoyé à {invoice.user.email}.")
                    except Exception as mail_e:
                        logger.error(f"Erreur lors de l'envoi e-mail à {invoice.user.email}: {mail_e}", exc_info=True)

            else:
                invoice.payment_status = 'failed'
                invoice.save()
                logger.warning(f"Paiement non confirmé pour facture {invoice.id}.")
                for res in invoice.reservations_linked.all():
                    res.status = Reservation.CANCELED
                    res.save()
                    logger.info(f"Réservation {res.id} annulée suite à paiement non confirmé.")

    # --- Paiement échoué ---
    elif event['type'] == 'payment_intent.payment_failed':
        payment_intent = event['data']['object']
        try:
            invoice = Invoice.objects.get(stripe_payment_intent_id=payment_intent.get('id'))
            if invoice.payment_status != 'paid':
                invoice.payment_status = 'failed'
                invoice.save()
                for res in invoice.reservations_linked.all():
                    if res.status != Reservation.CONFIRMED:
                        res.status = Reservation.CANCELED
                        res.save()
                logger.info(f"Facture {invoice.id} et réservations annulées suite à échec du Payment Intent.")
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

    total_price = cart.get_total_without_discount()

    return render(request, 'cart/confirm_cart.html', {
        'cart': cart,
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

@login_required
def apply_coupon(request):
    if request.method == "POST":
        code = request.POST.get("code", "").strip()
        now = timezone.now()

        if not code:
            return JsonResponse({"success": False, "message": "Veuillez entrer un code promo."})

        try:
            coupon = Coupon.objects.get(
                code__iexact=code,
                valid_from__lte=now,
                valid_to__gte=now,
                active=True
            )
        except Coupon.DoesNotExist:
            return JsonResponse({"success": False, "message": "❌ Ce code promo est invalide ou expiré."})

        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart.coupon = coupon
        cart.save()

        # Calcul du total avec la réduction
        total_after_discount = round(cart.get_total_price(), 2)
        discount_amount = round(cart.get_discount(), 2)

        return JsonResponse({
            "success": True,
            "message": f"✅ Coupon '{coupon.code}' appliqué avec succès !",
            "coupon_code": coupon.code,
            "coupon_percent": coupon.discount,
            "discount": str(discount_amount),
            "total_after_discount": str(total_after_discount),
        })

    return JsonResponse({"success": False, "message": "Requête invalide."})

@login_required
def remove_coupon(request):
    if request.method == "POST":
        cart = Cart.objects.get(user=request.user)
        cart.coupon = None
        cart.save()
        return JsonResponse({
            "success": True,
            "message": "🗑 Coupon retiré.",
            "discount": "0",
            "total_after_discount": str(round(cart.get_total_without_discount(), 2)),
        })
    return JsonResponse({"success": False, "message": "Requête invalide."})


def confirm_reservation(reservation):
    photobooth = reservation.photobooth
    photobooth.available -= reservation.quantity  # ou reservation.quantite selon ton champ
    if photobooth.available < 0:
        photobooth.available = 0
    photobooth.save()
    reservation.status = Reservation.CONFIRMED
    reservation.save()

@login_required
def get_cart_item_count(request):
    """
    Renvoie le nombre total d'articles dans le panier de l'utilisateur actuel.
    """
    if request.user.is_authenticated:
        try:
            cart = Cart.objects.get(user=request.user)
            return JsonResponse({'success': True, 'count': cart.cartitem_set.count()})
        except Cart.DoesNotExist:
            return JsonResponse({'success': True, 'count': 0})
    return JsonResponse({'success': False, 'message': 'Utilisateur non authentifié.'}, status=401)