from django.db import models
from django.core.validators import RegexValidator
from django.conf import settings

class Student(models.Model):
    registration_number = models.CharField(
        max_length=6, 
        unique=True,
        validators=[RegexValidator(r'^\d{6}$', 'Registration number must be 6 digits')]
    )
    full_name = models.CharField(max_length=128)
    email = models.EmailField(blank=True)
    parent_email = models.EmailField(blank=True)
    parent_phone = models.CharField(max_length=32, blank=True)

    def __str__(self) -> str:
        return f"{self.registration_number} - {self.full_name}"


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
        return f"{self.student.registration_number} -> {self.course.code}"


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
        return f"{self.session_id} {self.student.registration_number} {self.status}"


class Notification(models.Model):
    recipient_student = models.ForeignKey(Student, on_delete=models.CASCADE)
    channel = models.CharField(max_length=32, default="simulated")
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.recipient_student.registration_number} {self.channel}"


def face_sample_upload_to(instance: "FaceSample", filename: str) -> str:
    return f"faces/{instance.student.registration_number}/{filename}"


class FaceSample(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    image = models.ImageField(upload_to=face_sample_upload_to)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.student.registration_number} sample"


class Block(models.Model):
    code = models.CharField(max_length=16, unique=True)
    name = models.CharField(max_length=64)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return f"{self.code} - {self.name}".strip(" -")


class Classroom(models.Model):
    block = models.ForeignKey(Block, on_delete=models.PROTECT, related_name="classrooms")
    room_number = models.CharField(max_length=32)
    capacity = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("block", "room_number")

    def __str__(self) -> str:
        return f"{self.block.code}-{self.room_number} ({self.capacity})"


class FacultyProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    employee_id = models.CharField(max_length=32, unique=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        label = self.employee_id or "Faculty"
        return f"{self.user.username} ({label})"


class CourseOffering(models.Model):
    DOW_MON = 0
    DOW_TUE = 1
    DOW_WED = 2
    DOW_THU = 3
    DOW_FRI = 4
    DOW_SAT = 5
    DOW_SUN = 6

    DAY_OF_WEEK_CHOICES = [
        (DOW_MON, "Mon"),
        (DOW_TUE, "Tue"),
        (DOW_WED, "Wed"),
        (DOW_THU, "Thu"),
        (DOW_FRI, "Fri"),
        (DOW_SAT, "Sat"),
        (DOW_SUN, "Sun"),
    ]

    course = models.ForeignKey(Course, on_delete=models.PROTECT)
    faculty = models.ForeignKey(FacultyProfile, on_delete=models.PROTECT, related_name="offerings")
    classroom = models.ForeignKey(Classroom, on_delete=models.PROTECT, related_name="offerings")
    day_of_week = models.IntegerField(choices=DAY_OF_WEEK_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["day_of_week", "start_time"]

    def __str__(self) -> str:
        return f"{self.course.code} {self.get_day_of_week_display()} {self.start_time}-{self.end_time}"


