from django.db import models


class FoodItem(models.Model):
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return f"{self.name} - ₹{self.price}"


class BreakSlot(models.Model):
    name = models.CharField(max_length=32, unique=True)  # e.g., "Morning Break", "Lunch", "Evening Snack"
    start_time = models.TimeField()
    end_time = models.TimeField()

    def __str__(self) -> str:
        return f"{self.name} ({self.start_time} - {self.end_time})"


class PreOrder(models.Model):
    STATUS_PENDING = "pending"
    STATUS_READY = "ready"
    STATUS_COLLECTED = "collected"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_READY, "Ready"),
        (STATUS_COLLECTED, "Collected"),
    ]

    student = models.ForeignKey("attendance.Student", on_delete=models.CASCADE)
    food_item = models.ForeignKey(FoodItem, on_delete=models.CASCADE)
    slot = models.ForeignKey(BreakSlot, on_delete=models.CASCADE)
    order_date = models.DateField()
    quantity = models.PositiveSmallIntegerField(default=1)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("student", "food_item", "slot", "order_date")

    def __str__(self) -> str:
        return f"{self.student.roll_no} - {self.food_item.name} ({self.slot.name})"

# Create your models here.
