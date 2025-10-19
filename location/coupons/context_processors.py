from .models import PromotionBanner
from django.utils import timezone

def promo_message(request):
    now = timezone.now()
    banner = PromotionBanner.objects.filter(start_date__lte=now, end_date__gte=now).first()

    if request.user.is_authenticated and banner:
        return {
            'promo_banners': [banner]
        }
    return {}
