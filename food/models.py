from django.db import models
from django.conf import settings


class Stall(models.Model):
    name = models.CharField(max_length=128)
    location = models.CharField(max_length=128, default="Campus Center")
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.name} - {self.location}"


class StallOwner(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='stall_owner'
    )
    stall = models.ForeignKey(Stall, on_delete=models.CASCADE)
    phone = models.CharField(max_length=32, blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'stall')

    def __str__(self) -> str:
        return f"{self.user.username} - {self.stall.name}"


class FoodItem(models.Model):
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    is_active = models.BooleanField(default=True)
    stall = models.ForeignKey(Stall, on_delete=models.CASCADE, null=True, blank=True)
    stall_name = models.CharField(max_length=128, default="Main Canteen")
    location = models.CharField(max_length=128, default="Campus Center")
    category = models.CharField(max_length=64, default="All Items")
    image_url = models.URLField(blank=True, default="")

    def __str__(self) -> str:
        return f"{self.name} - ₹{self.price} ({self.stall_name})"


class BreakSlot(models.Model):
    name = models.CharField(max_length=32, unique=True)
    start_time = models.TimeField()
    end_time = models.TimeField()

    def __str__(self) -> str:
        return f"{self.name}"


class PreOrder(models.Model):
    PACK_EAT = "eat"
    PACK_PARCEL = "parcel"
    PACK_CHOICES = [
        (PACK_EAT, "Dine-in"),
        (PACK_PARCEL, "Pack for parcel"),
    ]

    STATUS_PENDING = "pending"
    STATUS_COOKING = "cooking"
    STATUS_READY = "ready"
    STATUS_COLLECTED = "collected"
    STATUS_MISSED = "missed"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_COOKING, "Cooking"),
        (STATUS_READY, "Ready"),
        (STATUS_COLLECTED, "Collected"),
        (STATUS_MISSED, "Missed"),
    ]

    ordered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True
    )
    food_item = models.ForeignKey(FoodItem, on_delete=models.CASCADE)
    slot = models.ForeignKey(BreakSlot, on_delete=models.CASCADE)
    order_date = models.DateField()
    quantity = models.PositiveSmallIntegerField(default=1)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDING)
    packaging_option = models.CharField(max_length=8, choices=PACK_CHOICES, default=PACK_EAT)
    order_number = models.CharField(max_length=5, blank=True)
    email_sent = models.BooleanField(default=False)
    penalty_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("ordered_by", "food_item", "slot", "order_date")

    def __str__(self) -> str:
        return f"Order #{self.order_number or self.id} - {self.food_item.name}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    @property
    def item_total(self):
        return self.quantity * self.food_item.price


class BulkOrder(models.Model):
    STATUS_SUBMITTED = "submitted"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    STATUS_CANCELLED = "cancelled"
    STATUS_COMPLETED = "completed"
    STATUS_CHOICES = [
        (STATUS_SUBMITTED, "Submitted"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_CANCELLED, "Cancelled"),
        (STATUS_COMPLETED, "Completed"),
    ]

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bulk_orders"
    )
    event_name = models.CharField(max_length=200)
    people_count = models.PositiveSmallIntegerField()
    delivery_date = models.DateField()
    slot = models.ForeignKey(BreakSlot, on_delete=models.PROTECT)
    stall_name = models.CharField(max_length=128)
    contact_person = models.CharField(max_length=128)
    contact_phone = models.CharField(max_length=32, blank=True, default="")
    special_instructions = models.TextField(blank=True, default="")
    requested_items_json = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=16, choices=STATUS_CHOICES, default=STATUS_SUBMITTED
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"BulkOrder #{self.id} - {self.event_name} ({self.people_count})"


class LoyaltyPoints(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='loyalty_points'
    )
    total_points = models.PositiveIntegerField(default=0)
    points_earned = models.PositiveIntegerField(default=0)
    points_redeemed = models.PositiveIntegerField(default=0)
    first_order_bonus = models.BooleanField(default=False)
    weekly_first_order_date = models.DateField(null=True, blank=True)
    weekly_orders_count = models.PositiveIntegerField(default=0)
    current_streak = models.PositiveIntegerField(default=0)
    last_order_date = models.DateField(null=True, blank=True)
    favorite_stall = models.CharField(max_length=128, blank=True, default="")
    favorite_stall_orders = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.total_points} points"
    
    @property
    def available_points(self):
        return self.total_points - self.points_redeemed
    
    @property
    def rupee_value(self):
        return self.available_points * 0.25


class EmergencyAlert(models.Model):
    ALERT_TYPES = [
        ('food_safety', 'Food Safety'),
        ('stall_closed', 'Stall Closed'),
        ('supply_issue', 'Supply Issue'),
        ('health_advisory', 'Health Advisory'),
        ('system_maintenance', 'System Maintenance'),
    ]
    
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    severity = models.CharField(max_length=10, choices=[
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ], default='medium')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.get_alert_type_display()}: {self.title}"
    
    @property
    def is_expired(self):
        from django.utils import timezone
        return self.expires_at and self.expires_at < timezone.now()


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile'
    )
    owner_status = models.BooleanField(default=False, help_text="Designates this user as a stall owner")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"

    def __str__(self):
        return f"{self.user.username} - Owner: {self.owner_status}"
