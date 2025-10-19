import random
import string

def generate_coupon_code(length=8):
    """Génère un code aléatoire de lettres majuscules et chiffres."""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def generate_unique_coupon_code(model, length=8):
    """Génère un code unique qui n'existe pas encore dans la base de données."""
    code = generate_coupon_code(length)
    while model.objects.filter(code=code).exists():
        code = generate_coupon_code(length)
    return code
