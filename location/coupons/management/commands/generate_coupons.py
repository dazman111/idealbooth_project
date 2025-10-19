import os
import csv
from django.core.management.base import BaseCommand
from coupons.models import Coupon
from coupons.utils import generate_unique_coupon_code
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from django.conf import settings

class Command(BaseCommand):
    help = "Génère des coupons automatiquement et exporte en CSV"

    def add_arguments(self, parser):
        parser.add_argument('count', type=int, help='Nombre de coupons à générer')
        parser.add_argument('--discount', type=float, default=10, help='Montant ou pourcentage de réduction')
        parser.add_argument('--percent', action='store_true', help='Le rabais est-il en pourcentage ?')
        parser.add_argument('--days', type=int, default=30, help='Durée de validité en jours')
        parser.add_argument('--utilisation_max', type=int, default=1, help='Nombre max d\'utilisations par coupon')
        parser.add_argument('--description', type=str, default='Coupon généré automatiquement.')
        parser.add_argument('--prefix', type=str, default='', help='Préfixe du code coupon (ex: SUMMER)')

    def handle(self, *args, **options):
        count = options['count']
        discount = Decimal(options['discount'])
        is_percent = options['percent']
        days_valid = options['days']
        utilisation_max = options['utilisation_max']
        description = options['description']
        prefix = options['prefix'].upper()

        discount_type = 'percent' if is_percent else 'fixed'
        date_debut = timezone.now()
        date_fin = date_debut + timedelta(days=days_valid)

        coupons_crees = []

        for _ in range(count):
            unique_part = generate_unique_coupon_code(Coupon)
            code = f"{prefix}-{unique_part}" if prefix else unique_part

            coupon = Coupon.objects.create(
                code=code,
                description=description,
                discount_type=discount_type,
                discount_value=discount,
                date_debut=date_debut,
                date_fin=date_fin,
                actif=True,
                utilisation_max=utilisation_max,
                utilisations_effectuees=0
            )

            coupons_crees.append(coupon)
            self.stdout.write(self.style.SUCCESS(f'✅ Coupon créé : {coupon.code}'))

        # 📁 Export CSV
        export_dir = os.path.join(settings.BASE_DIR, 'exports')
        os.makedirs(export_dir, exist_ok=True)

        filename = f"coupons_{timezone.now().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = os.path.join(export_dir, filename)

        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Code', 'Type', 'Valeur', 'Début', 'Fin', 'Utilisations Max'])

            for coupon in coupons_crees:
                writer.writerow([
                    coupon.code,
                    coupon.discount_type,
                    str(coupon.discount_value),
                    coupon.date_debut.strftime('%Y-%m-%d %H:%M'),
                    coupon.date_fin.strftime('%Y-%m-%d %H:%M'),
                    coupon.utilisation_max
                ])

        self.stdout.write(self.style.SUCCESS(f"\n📁 Fichier CSV exporté : {filepath}"))
