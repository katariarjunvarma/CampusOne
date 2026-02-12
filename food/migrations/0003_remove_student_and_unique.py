# Generated manually

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('food', '0002_add_ordered_by'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='preorder',
            unique_together={('ordered_by', 'food_item', 'slot', 'order_date')},
        ),
        migrations.RemoveField(
            model_name='preorder',
            name='student',
        ),
    ]
