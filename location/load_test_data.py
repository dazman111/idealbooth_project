# Fichier : load_test_data.py
# À placer à la racine du projet (même niveau que manage.py)

# Fichier : load_test_data.py
# À placer à la racine du projet (même niveau que manage.py)

import os
import django
import random
from datetime import datetime, timedelta
from faker import Faker

# --- Configuration Django ---
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'idealbooth_project.settings')
django.setup()

from django.contrib.auth import get_user_model
from photobooths.models import Photobooth, Favorite
from reservations.models import Reservation, Invoice
from blog.models import Article, Comment, ArticleLikes, ArticleImage
from cart.models import Cart, CartItem, Coupon

User = get_user_model()
fake = Faker("fr_FR")  # Générateur de données réalistes en français

# --- Suppression des anciennes données ---
print("Suppression des anciennes données...")
CartItem.objects.all().delete()
Cart.objects.all().delete()
ArticleImage.objects.all().delete()
ArticleLikes.objects.all().delete()
Comment.objects.all().delete()
Article.objects.all().delete()
Reservation.objects.all().delete()
Invoice.objects.all().delete()
Favorite.objects.all().delete()
User.objects.all().delete()

# --- Utilisateurs ---
print("Création des utilisateurs...")
users = []
for i in range(1, 101):
    username = f"user{i}"
    user = User.objects.create_user(
        username=username,
        first_name=fake.first_name(),
        last_name=fake.last_name(),
        email=fake.unique.email(),
        phone_number=fake.phone_number(),
        address=fake.address(),
        password="Test1234!",
        is_active=True
    )
    users.append(user)

# --- Photobooths ---
print("Création des photobooths...")
photobooths = []
for i in range(1, 21):
    booth = Photobooth.objects.create(
        name=f"Photobooth {i}",
        description=f"Description réaliste du photobooth numéro {i}",
        price=100 + i * 10,
        image="photobooth_default.jpg",
        stock=5,
        available=5
    )
    photobooths.append(booth)

# --- Réservations et Factures ---
print("Création des réservations et factures...")
for _ in range(100):
    user = random.choice(users)
    photobooth = random.choice(photobooths)
    start_date = datetime(2025, 9, random.randint(1, 28), random.randint(8, 18), 0)
    end_date = start_date + timedelta(hours=8)

    invoice = Invoice.objects.create(
        total_amount=photobooth.price,
        payment_status=random.choice(["paid", "pending"]),
        stripe_checkout_session_id=None,
        stripe_payment_intent_id=None,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        discount_amount=0,
        user=user,
        company_address=fake.address(),
        company_email=fake.company_email(),
        company_name=fake.company(),
        company_phone=fake.phone_number(),
        company_vat_number=fake.siren()
    )

    Reservation.objects.create(
        user=user,
        photobooth=photobooth,
        start_date=start_date,
        end_date=end_date,
        date_location=start_date.date(),
        created_at=datetime.now(),
        status=random.choice(["pending", "confirmed"]),
        quantity=random.randint(1, 3),
        invoice=invoice
    )

# --- Favoris ---
print("Création des favoris...")
for user in users:
    fav_count = random.randint(1, 5)
    favs = random.sample(photobooths, fav_count)
    for booth in favs:
        Favorite.objects.get_or_create(user=user, photobooth=booth)

# --- Articles de blog ---
print("Création des articles de blog...")
articles = []
for i in range(1, 21):
    article = Article.objects.create(
        title=f"Article {i}",
        content=fake.text(500),
        author=random.choice(users).username
    )
    articles.append(article)

# --- Commentaires ---
print("Création des commentaires...")
for _ in range(200):
    Comment.objects.create(
        content=fake.text(200),
        created_at=datetime.now(),
        updated_at=datetime.now(),
        rating=random.randint(0, 5),
        article=random.choice(articles),
        user=random.choice(users)
    )

# --- Likes d'articles ---
print("Création des likes...")
for user in users:
    liked_articles = random.sample(articles, random.randint(1, 5))
    for article in liked_articles:
        ArticleLikes.objects.get_or_create(article=article, customuser=user)

# --- Images pour articles ---
print("Création des images pour articles...")
for article in articles:
    for _ in range(random.randint(1, 3)):
        ArticleImage.objects.create(
            article=article,
            image="default_article_image.jpg",
            uploaded_at=datetime.now()
        )

# --- Paniers et CartItems ---
print("Création des paniers et items...")
for user in users:
    cart, _ = Cart.objects.get_or_create(
        user=user,
        defaults={"created_at": datetime.now(), "coupon": None}
    )
    for _ in range(random.randint(1, 3)):
        photobooth = random.choice(photobooths)
        CartItem.objects.create(
            start_date=datetime.now().date(),
            end_date=(datetime.now() + timedelta(days=1)).date(),
            quantite=random.randint(1, 3),
            type_evenement=random.choice(["mariage", "anniversaire", "corporate"]),
            option=random.choice(["Pack VIP", "Pack Standard", "Sans option"]),
            cart=cart,
            photobooth=photobooth
        )

print("✅ Toutes les données de test ont été créées avec succès !")
