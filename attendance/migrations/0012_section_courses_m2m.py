from django.db import migrations, models


def forward_copy_course_to_courses(apps, schema_editor):
    Section = apps.get_model("attendance", "Section")

    for section in Section.objects.exclude(course__isnull=True).exclude(course_id__isnull=True):
        section.courses.add(section.course_id)


class Migration(migrations.Migration):

    dependencies = [
        ("attendance", "0011_alter_courseoffering_unique_together"),
    ]

    operations = [
        migrations.AddField(
            model_name="section",
            name="courses",
            field=models.ManyToManyField(blank=True, related_name="sections", to="attendance.course"),
        ),
        migrations.RunPython(forward_copy_course_to_courses, reverse_code=migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="section",
            name="course",
        ),
    ]
