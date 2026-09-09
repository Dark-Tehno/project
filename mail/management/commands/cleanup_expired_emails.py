from django.core.management.base import BaseCommand
from django.utils import timezone

from mail.models import TemporaryEmail


class Command(BaseCommand):
    help = 'Удаляет временные почтовые ящики с истёкшим сроком действия.'

    def handle(self, *args, **options):
        expired_emails = TemporaryEmail.objects.filter(
            expires_at__isnull=False,
            expires_at__lte=timezone.now(),
        )
        deleted_count = expired_emails.count()
        expired_emails.delete()

        self.stdout.write(
            self.style.SUCCESS(
                f'Удалено временных ящиков: {deleted_count}'
            )
        )