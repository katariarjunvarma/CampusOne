from django.core.management.base import BaseCommand
from attendance.models import Course


class Command(BaseCommand):
    help = "Seed 7 courses into the centralized course state"

    def handle(self, *args, **options):
        courses = [
            {
                "code": "CSE101",
                "name": "Data Structures",
                "semester": 3,
                "year": 2,
            },
            {
                "code": "CSE202",
                "name": "Operating Systems",
                "semester": 4,
                "year": 2,
            },
            {
                "code": "AIML301",
                "name": "Machine Learning",
                "semester": 5,
                "year": 3,
            },
            {
                "code": "ICE201",
                "name": "Signals & Systems",
                "semester": 3,
                "year": 2,
            },
            {
                "code": "FASH101",
                "name": "Fashion Illustration",
                "semester": 2,
                "year": 1,
            },
            {
                "code": "MBA101",
                "name": "Principles of Management",
                "semester": 1,
                "year": 1,
            },
            {
                "code": "PHY102",
                "name": "Engineering Physics",
                "semester": 1,
                "year": 1,
            },
        ]

        created_count = 0
        skipped_count = 0

        for course_data in courses:
            obj, created = Course.objects.get_or_create(
                code=course_data["code"],
                defaults={
                    "name": course_data["name"],
                    "semester": course_data["semester"],
                    "year": course_data["year"],
                },
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f"Created course: {obj.code} - {obj.name}")
                )
            else:
                skipped_count += 1
                self.stdout.write(
                    self.style.WARNING(f"Skipped (exists): {obj.code} - {obj.name}")
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone. Created: {created_count}, Skipped: {skipped_count}"
            )
        )
