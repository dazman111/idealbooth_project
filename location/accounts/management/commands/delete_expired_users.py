from django.core.management.base import BaseCommand
from django.utils import timezone
from accounts.models import CustomUser

class Command(BaseCommand):
    help = "Supprime les comptes utilisateurs dont la date de suppression est dépassée"

    def handle(self, *args, **kwargs):
        now = timezone.now()
        users_to_delete = CustomUser.objects.filter(deleted_at__lte=now)
        count = users_to_delete.count()

        for user in users_to_delete:
            self.stdout.write(f"Suppression de l'utilisateur : {user.username} (ID: {user.id})")
            user.delete()

        self.stdout.write(self.style.SUCCESS(f"{count} comptes supprimés définitivement."))
