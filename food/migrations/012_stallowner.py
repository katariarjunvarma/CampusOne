# Generated manually

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('food', '0011_loyaltypoints_current_streak_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='StallOwner',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='stall_owner', to=settings.AUTH_USER_MODEL)),
                ('stall_name', models.CharField(help_text='Name of the stall this user owns', max_length=128, unique=True)),
                ('is_active', models.BooleanField(default=True, help_text='Whether this stall owner can manage orders')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
    ]
