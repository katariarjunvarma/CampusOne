# Generated manually

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('food', '0011_loyaltypoints_current_streak_and_more'),
        ('food', '012_stallowner'),
    ]

    operations = [
        # Create Stall model
        migrations.CreateModel(
            name='Stall',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text="Stall name (e.g., '25 Block Canteen')", max_length=128, unique=True)),
                ('location', models.CharField(default='Campus Center', help_text='Location on campus', max_length=128)),
                ('owner_name', models.CharField(blank=True, help_text="Owner's full name", max_length=128)),
                ('phone_number', models.CharField(blank=True, help_text='Contact phone number', max_length=15)),
                ('is_active', models.BooleanField(default=True, help_text='Whether stall is operational')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        # Update StallOwner to use ForeignKey to Stall
        migrations.RemoveField(
            model_name='stallowner',
            name='stall_name',
        ),
        migrations.AddField(
            model_name='stallowner',
            name='stall',
            field=models.ForeignKey(help_text='Select the stall this user manages', on_delete=django.db.models.deletion.CASCADE, related_name='owners', to='food.stall'),
            preserve_default=False,
        ),
    ]
