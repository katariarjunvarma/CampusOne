from django.db import migrations, models
import django.core.validators

class Migration(migrations.Migration):

    dependencies = [
        ('attendance', '0003_student_parent_email'),
    ]

    operations = [
        migrations.RenameField(
            model_name='student',
            old_name='roll_no',
            new_name='registration_number',
        ),
        migrations.AlterField(
            model_name='student',
            name='registration_number',
            field=models.CharField(
                max_length=6, 
                unique=True,
                validators=[django.core.validators.RegexValidator('^\\d{6}$', 'Registration number must be 6 digits')]
            ),
        ),
    ]
