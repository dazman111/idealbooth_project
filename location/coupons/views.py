import json
from decimal import Decimal

from datetime import date
from django.http import JsonResponse
from .models import Coupon
from cart.models import Cart

def apply_coupon(request):
    code = None

    # ✅ Si c'est une requête JSON (fetch)
    if request.content_type == 'application/json':
        try:
            data = json.loads(request.body)
            code = data.get('code', '').strip()
        except Exception:
            return JsonResponse({'success': False, 'message': "Format JSON invalide."})

    # ✅ Sinon (soumission HTML classique)
    if not code:
        code = request.POST.get('code', '').strip()

    if not code:
        return JsonResponse({'success': False, 'message': "Veuillez entrer un code."})

    try:
        today = date.today()
        coupon = Coupon.objects.get(
            code__iexact=code,
            actif=True,
            date_fin__gte=today
        )

        # Sauvegarde dans la session
        request.session['coupon_id'] = coupon.id

        # Récupération du panier
        cart, _ = Cart.objects.get_or_create(user=request.user)

        # Calcul du sous-total
        subtotal = cart.get_total_without_discount()

        # Calcul de la réduction
        if coupon.discount_type == 'percent':
            discount_amount = subtotal * (Decimal(coupon.discount_value) / Decimal(100))
        elif coupon.discount_type == 'fixed':
            discount_amount = Decimal(coupon.discount_value)
        else:
            discount_amount = Decimal(0)

        # Calcul du total
        total = max(subtotal - discount_amount, 0)

        # Sauvegarde dans le panier
        cart.coupon = coupon
        cart.save()

        return JsonResponse({
            'success': True,
            'message': f"Coupon « {coupon.code} » appliqué avec succès.",
            'coupon_code': coupon.code,
            'coupon_percent': float(coupon.discount), 
            'discount_type': coupon.discount_type,
            'discount_value': float(coupon.discount_value),
            'discount_amount': round(discount_amount, 2),  # clé utilisable directement
            'subtotal': round(subtotal, 2),               # clé utilisable directement
            'total': round(total, 2),                     # clé utilisable directement
        })

    except Coupon.DoesNotExist:
        return JsonResponse({'success': False, 'message': "Ce coupon est invalide ou expiré."})
