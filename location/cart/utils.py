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
