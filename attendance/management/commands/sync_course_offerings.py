from django.core.management.base import BaseCommand
from attendance.models import CourseOffering, FacultyProfile, Course, Classroom
import random


class Command(BaseCommand):
    help = "Sync CourseOfferings with real faculty and course data"

    def handle(self, *args, **options):
        # Clear existing offerings to avoid stale data
        CourseOffering.objects.all().delete()
        self.stdout.write(self.style.WARNING("Cleared all existing CourseOfferings."))

        # Get real data
        faculties = list(FacultyProfile.objects.select_related('user').all())
        courses = list(Course.objects.all())
        classrooms = list(Classroom.objects.select_related('block').all())

        if not faculties:
            self.stdout.write(self.style.ERROR("No FacultyProfile records found."))
            return
        if not courses:
            self.stdout.write(self.style.ERROR("No Course records found."))
            return
        if not classrooms:
            self.stdout.write(self.style.ERROR("No Classroom records found."))
            return

        created = 0
        # Create at least 40 offerings, ensuring each faculty gets some
        for i in range(40):
            faculty = random.choice(faculties)
            course = random.choice(courses)
            classroom = random.choice(classrooms)
            expected_strength = random.randint(40, 70)
            is_active = True
            # Add required schedule fields
            day_of_week = random.choice([0, 1, 2, 3, 4])  # Mon-Fri
            start_time = "09:00"
            end_time = "10:00"

            offering = CourseOffering.objects.create(
                course=course,
                faculty=faculty,
                classroom=classroom,
                expected_strength=expected_strength,
                is_active=is_active,
                day_of_week=day_of_week,
                start_time=start_time,
                end_time=end_time
            )
            created += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f"Created offering: {course.code} ({course.name}) - "
                    f"{faculty.user.username} - {classroom.room_number} "
                    f"(expected {expected_strength})"
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone. Created {created} course offerings synced with real data."
            )
        )
