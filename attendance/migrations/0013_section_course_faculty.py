from django.db import migrations, models
import django.db.models.deletion


def forward_copy_course_offerings(apps, schema_editor):
    CourseOffering = apps.get_model("attendance", "CourseOffering")
    SectionCourseFaculty = apps.get_model("attendance", "SectionCourseFaculty")

    for o in CourseOffering.objects.exclude(section_id__isnull=True):
        # Enforce unique(section, course). If duplicates exist historically,
        # keep the first one we encounter.
        SectionCourseFaculty.objects.get_or_create(
            section_id=o.section_id,
            course_id=o.course_id,
            defaults={"faculty_id": o.faculty_id},
        )


class Migration(migrations.Migration):

    dependencies = [
        ("attendance", "0012_section_courses_m2m"),
    ]

    operations = [
        migrations.CreateModel(
            name="SectionCourseFaculty",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "course",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="section_faculty_allocations",
                        to="attendance.course",
                    ),
                ),
                (
                    "faculty",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="section_course_allocations",
                        to="attendance.facultyprofile",
                    ),
                ),
                (
                    "section",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="course_faculty_allocations",
                        to="attendance.section",
                    ),
                ),
            ],
            options={
                "ordering": ["section__name", "course__code"],
                "unique_together": {("section", "course")},
            },
        ),
        migrations.RunPython(forward_copy_course_offerings, reverse_code=migrations.RunPython.noop),
    ]
