from django.core.management.base import BaseCommand
from attendance.models import FacultyProfile, CourseOffering
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = "Keep only arjunvarma as faculty and reassign offerings to him"

    def handle(self, *args, **options):
        # Get arjunvarma user
        try:
            arjun = User.objects.get(username='arjunvarma')
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR("User 'arjunvarma' not found."))
            return

        # Ensure arjunvarma has a FacultyProfile or create one
        fp, created = FacultyProfile.objects.get_or_create(
            user=arjun,
            defaults={
                'employee_id': 'ARJUN001',
                'department': 'Computer Science',
                'designation': 'Teacher',
                'max_weekly_load': 20,
                'is_active': True
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created FacultyProfile for {arjun.username}"))
        else:
            self.stdout.write(self.style.WARNING(f"FacultyProfile already exists for {arjun.username}"))

        # Reassign all course offerings to arjunvarma first
        updated = CourseOffering.objects.exclude(faculty=fp).update(faculty=fp)
        self.stdout.write(self.style.SUCCESS(f"Reassigned {updated} course offerings to {arjun.username}."))

        # Now delete other faculty profiles
        deleted_count = FacultyProfile.objects.exclude(user=arjun).delete()[0]
        self.stdout.write(self.style.WARNING(f"Deleted {deleted_count} other faculty profiles."))

        self.stdout.write(self.style.SUCCESS("Done. Only arjunvarma remains as faculty."))
