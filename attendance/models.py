from django.db import models

class Student(models.Model):
    roll_no = models.CharField(max_length=32, unique=True)
    full_name = models.CharField(max_length=128)
    email = models.EmailField(blank=True)
    parent_email = models.EmailField(blank=True)
    parent_phone = models.CharField(max_length=32, blank=True)

    def __str__(self) -> str:
        return f"{self.roll_no} - {self.full_name}"


class Course(models.Model):
    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=128)

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


class Enrollment(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="enrollments")
    course = models.ForeignKey(Course, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("student", "course")

    def __str__(self) -> str:
        return f"{self.student.roll_no} -> {self.course.code}"


class AttendanceSession(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    session_date = models.DateField()
    time_slot = models.CharField(max_length=32, blank=True)
    session_label = models.CharField(max_length=64, blank=True)

    def __str__(self) -> str:
        label = self.session_label or "Session"
        return f"{self.course.code} {label} {self.session_date} {self.time_slot}".strip()


class AttendanceRecord(models.Model):
    STATUS_PRESENT = "present"
    STATUS_ABSENT = "absent"

    STATUS_CHOICES = [
        (STATUS_PRESENT, "Present"),
        (STATUS_ABSENT, "Absent"),
    ]

    session = models.ForeignKey(AttendanceSession, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES)
    updated_at = models.DateTimeField(auto_now=True)
    source = models.CharField(max_length=32, default="manual")

    class Meta:
        unique_together = ("session", "student")

    def __str__(self) -> str:
        return f"{self.session_id} {self.student.roll_no} {self.status}"


class Notification(models.Model):
    recipient_student = models.ForeignKey(Student, on_delete=models.CASCADE)
    channel = models.CharField(max_length=32, default="simulated")
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.recipient_student.roll_no} {self.channel}"


def face_sample_upload_to(instance: "FaceSample", filename: str) -> str:
    return f"faces/{instance.student.roll_no}/{filename}"


class FaceSample(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    image = models.ImageField(upload_to=face_sample_upload_to)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.student.roll_no} sample"


# Food Pre-Ordering System
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

    student = models.ForeignKey(Student, on_delete=models.CASCADE)
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
