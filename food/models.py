from django.db import models
from django.conf import settings


class FoodItem(models.Model):
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    is_active = models.BooleanField(default=True)
    stall_name = models.CharField(max_length=128, default="Main Canteen")
    location = models.CharField(max_length=128, default="Campus Center")
    category = models.CharField(max_length=64, default="All Items")
    image_url = models.URLField(blank=True, default="")

    def __str__(self) -> str:
        return f"{self.name} - ₹{self.price} ({self.stall_name})"


class BreakSlot(models.Model):
    name = models.CharField(max_length=32, unique=True)  # e.g., "Morning Break", "Lunch", "Evening Snack"
    start_time = models.TimeField()
    end_time = models.TimeField()

    def __str__(self) -> str:
        return f"{self.name}"


class PreOrder(models.Model):
    STATUS_PENDING = "pending"
    STATUS_READY = "ready"
    STATUS_COLLECTED = "collected"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_READY, "Ready"),
        (STATUS_COLLECTED, "Collected"),
    ]

    ordered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True
    )
    food_item = models.ForeignKey(FoodItem, on_delete=models.CASCADE)
    slot = models.ForeignKey(BreakSlot, on_delete=models.CASCADE)
    order_date = models.DateField()
    quantity = models.PositiveSmallIntegerField(default=1)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("ordered_by", "food_item", "slot", "order_date")

    def __str__(self) -> str:
        return f"{self.ordered_by} - {self.food_item.name} ({self.slot.name})"
