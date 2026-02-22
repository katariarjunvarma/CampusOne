from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from attendance.models import FacultyProfile

User = get_user_model()


class Command(BaseCommand):
    help = "Sync FacultyProfile with Users who have staff status (is_staff=True)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--auto-id",
            action="store_true",
            help="Auto-generate employee_id if not provided",
        )
        parser.add_argument(
            "--department",
            default="Computer Science",
            help="Default department for new faculty (default: Computer Science)",
        )
        parser.add_argument(
            "--designation",
            default="Teacher",
            help="Default designation for new faculty (default: Teacher)",
        )

    def handle(self, *args, **options):
        auto_id = options["auto_id"]
        default_dept = options["department"]
        default_desig = options["designation"]

        # Get all staff users
        staff_users = User.objects.filter(is_staff=True)
        
        created_count = 0
        updated_count = 0
        skipped_count = 0

        for idx, user in enumerate(staff_users, start=1):
            # Generate employee_id if auto_id is enabled
            employee_id = f"EMP{idx:03d}" if auto_id else ""
            
            # Check if faculty profile exists
            faculty, created = FacultyProfile.objects.get_or_create(
                user=user,
                defaults={
                    "employee_id": employee_id or f"EMP{user.id:03d}",
                    "department": default_dept,
                    "designation": default_desig,
                    "max_weekly_load": 20,
                    "is_active": True,
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Created FacultyProfile: {user.username} (ID: {faculty.employee_id})"
                    )
                )
            else:
                skipped_count += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"FacultyProfile already exists: {user.username}"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone. Created: {created_count}, Skipped: {skipped_count}"
            )
        )
