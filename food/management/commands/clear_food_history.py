from django.core.management.base import BaseCommand
from django.utils import timezone
from food.models import PreOrder
from datetime import timedelta

class Command(BaseCommand):
    help = 'Clears food order history based on specific rules.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--monthly',
            action='store_true',
            help='Run the monthly cleanup (resets missed orders)',
        )

    def handle(self, *args, **options):
        today = timezone.localdate()
        
        if options['monthly']:
            # Monthly Reset: Clear ALL missed orders from the previous month/period
            # Actually, user says "missed orders should reset once starting at every month automatically"
            # This implies deleting them or archiving them so they don't count towards penalty.
            # For simplicity, we'll delete them or mark them as processed/archived.
            # Since we just delete history here, we'll delete ALL missed orders.
            missed_deleted, _ = PreOrder.objects.filter(status=PreOrder.STATUS_MISSED).delete()
            self.stdout.write(self.style.SUCCESS(f'Monthly cleanup: Cleared {missed_deleted} missed orders.'))
            return

        # Weekly/Daily Cleanup (Default)
        # "history orders are restting everyweek i dont want to reset the missed order"
        # So we delete everything older than 7 days EXCEPT missed orders.
        cutoff_date = today - timedelta(days=7)
        
        # Delete non-missed orders older than 7 days
        orders_to_delete = PreOrder.objects.filter(
            order_date__lt=cutoff_date
        ).exclude(status=PreOrder.STATUS_MISSED)
        
        count, _ = orders_to_delete.delete()
        
        self.stdout.write(self.style.SUCCESS(f'Weekly cleanup: Cleared {count} old orders (kept missed orders).'))
