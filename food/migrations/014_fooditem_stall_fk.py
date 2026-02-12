# Generated manually

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('food', '013_stall_and_update_stallowner'),
    ]

    operations = [
        migrations.AddField(
            model_name='fooditem',
            name='stall',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='food_items', to='food.stall'),
        ),
    ]
