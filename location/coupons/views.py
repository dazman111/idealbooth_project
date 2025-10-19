from django.shortcuts import render

# Create your views here.
from datetime import date
from django.shortcuts import redirect
from django.http import JsonResponse
from .models import Coupon
from cart.models import Cart  # adapte selon ton projet

def apply_coupon(request):
    code = request.POST.get('code', '').strip()

    if not code:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': "Veuillez entrer un code."})
        return redirect('cart_detail')

    try:
        today = date.today()  # ✅ définition ici
        coupon = Coupon.objects.get(
            code__iexact=code,
            actif=True,
            date_fin__gte=today  # ✅ utilisation ici
        )

        request.session['coupon_id'] = coupon.id

        cart, _ = Cart.objects.get_or_create(user=request.user)

        discount = cart.get_discount_amount()
        total = cart.get_total_without_discount()


        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': f"Coupon « {coupon.code} » appliqué avec succès.",
                'discount': f"{discount:.2f}",
                'coupon_code': coupon.code,
                'coupon_percent': coupon.discount_value,
                'total': f"{total:.2f}"
            })

        return redirect('cart_detail')

    except Coupon.DoesNotExist:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': "Ce coupon est invalide ou expiré."})
        return redirect('cart_detail')
