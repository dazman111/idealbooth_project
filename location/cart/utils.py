from .models import Cart
from django.template.loader import render_to_string
from weasyprint import HTML
import tempfile

def get_or_create_cart(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    return cart

def generate_invoice_pdf(invoice):
    html_string = render_to_string("pdf/invoice.html", {"invoice": invoice})
    result = tempfile.NamedTemporaryFile(delete=True, suffix='.pdf')

    HTML(string=html_string).write_pdf(target=result.name)

    return result

def format_price(amount):
    """
    Formate un montant float en chaîne en euros, ex: 49.0 => "49,00 €"
    """
    return f"{amount:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")

# utils/decorators.py
from django.http import JsonResponse
from django.contrib.auth.views import redirect_to_login

def json_login_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            if request.headers.get("Accept") == "application/json":
                return JsonResponse(
                    {"success": False, "message": "Authentification requise."},
                    status=401
                )
            return redirect_to_login(request.get_full_path())
        return view_func(request, *args, **kwargs)
    return wrapper

