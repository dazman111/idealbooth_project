from django.shortcuts import redirect
from django.utils import timezone
from datetime import timedelta

def account_protection(view_func):
    def wrapper(request, *args, **kwargs):
        user = request.user
        if user.is_authenticated:
            # Vérifier la date de création
            if user.date_joined and timezone.now() - user.date_joined < timedelta(days=30):
                # Si compte < 30 jours → bloquer certaines actions
                return redirect("account_protection_notice")
        return view_func(request, *args, **kwargs)
    return wrapper
