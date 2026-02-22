from django.db import models
from django.core.validators import RegexValidator
from django.conf import settings
from django.core.exceptions import ValidationError

class Student(models.Model):
    registration_number = models.CharField(
        max_length=6, 
        unique=True,
        validators=[RegexValidator(r'^\d{6}$', 'Registration number must be 6 digits')]
    )
    full_name = models.CharField(max_length=128)
    year = models.PositiveSmallIntegerField(null=True, blank=True)
    semester = models.PositiveSmallIntegerField(null=True, blank=True)
    department = models.CharField(max_length=64, blank=True)
    email = models.EmailField(blank=True)
    parent_email = models.EmailField(blank=True)
    student_phone = models.CharField(max_length=32, blank=True)

    enrolled_courses = models.ManyToManyField(
        "Course",
        through="Enrollment",
        related_name="enrolled_students",
    )


    @property
    def section(self):
        mapping = getattr(self, "section_mapping", None)
        if mapping is None:
            return None
        return mapping.section

    def __str__(self) -> str:
        return f"{self.registration_number} - {self.full_name}"


class Course(models.Model):
    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=128)
    year = models.PositiveSmallIntegerField(null=True, blank=True)
    semester = models.PositiveSmallIntegerField(null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


class Section(models.Model):
    name = models.CharField(max_length=32, unique=True)
    courses = models.ManyToManyField(Course, related_name="sections", blank=True)
    year = models.PositiveSmallIntegerField(null=True, blank=True)
    semester = models.PositiveSmallIntegerField(null=True, blank=True)

    @property
    def students(self):
        return Student.objects.filter(section_mapping__section=self).order_by(
            "registration_number"
        )

    def __str__(self) -> str:
        return self.name


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
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if self.code:
            self.code = self.code.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.code} - {self.name}".strip(" -")


class Classroom(models.Model):
    TYPE_CLASSROOM = "classroom"
    TYPE_LAB = "lab"
    TYPE_SEMINAR = "seminar"
    TYPE_AUDITORIUM = "auditorium"

    ROOM_TYPE_CHOICES = [
        (TYPE_CLASSROOM, "Classroom"),
        (TYPE_LAB, "Lab"),
        (TYPE_SEMINAR, "Seminar"),
        (TYPE_AUDITORIUM, "Auditorium"),
    ]

    block = models.ForeignKey(Block, on_delete=models.PROTECT, related_name="classrooms")
    room_number = models.CharField(max_length=32)
    capacity = models.PositiveIntegerField(default=1)
    room_type = models.CharField(max_length=16, choices=ROOM_TYPE_CHOICES, default=TYPE_CLASSROOM)
    floor = models.IntegerField(null=True, blank=True)
    has_projector = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("block", "room_number")

    def __str__(self) -> str:
        return f"{self.block.code}-{self.room_number} ({self.capacity})"


class FacultyProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    employee_id = models.CharField(max_length=32, unique=True, blank=True)
    department = models.CharField(max_length=64, blank=True)
    designation = models.CharField(max_length=64, blank=True)
    max_weekly_load = models.PositiveIntegerField(default=20)
    phone = models.CharField(max_length=32, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        label = self.employee_id or "Faculty"
        return f"{self.user.username} ({label})"


class CourseOffering(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="offerings")
    faculty = models.ForeignKey(FacultyProfile, on_delete=models.PROTECT, related_name="offerings")
    section = models.ForeignKey(Section, on_delete=models.CASCADE, null=True, blank=True, related_name="offerings")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("course", "section")
        ordering = ["course__code", "section__name"]

    def __str__(self) -> str:
        section_name = self.section.name if self.section else 'No Section'
        return f"{self.course.code} - {section_name} - {self.faculty.user.username}"


class SectionCourseFaculty(models.Model):
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name="course_faculty_allocations")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="section_faculty_allocations")
    faculty = models.ForeignKey(FacultyProfile, on_delete=models.PROTECT, related_name="section_course_allocations")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("section", "course")
        ordering = ["section__name", "course__code"]

    def __str__(self) -> str:
        return f"{self.course.code} - {self.course.name} - {self.faculty.user.username} - {self.section.name}"


class StudentSection(models.Model):
    student = models.OneToOneField(
        Student, on_delete=models.CASCADE, related_name="section_mapping"
    )
    section = models.ForeignKey(
        Section, on_delete=models.CASCADE, related_name="student_sections"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("student", "section")
        ordering = ["section__name", "student__registration_number"]

    def __str__(self) -> str:
        return f"{self.student.registration_number} -> {self.section.name}"


class Schedule(models.Model):
    """Academic schedule for course offerings - assigns classroom and time slots."""
    
    DAY_CHOICES = [
        ("Monday", "Monday"),
        ("Tuesday", "Tuesday"),
        ("Wednesday", "Wednesday"),
        ("Thursday", "Thursday"),
        ("Friday", "Friday"),
        ("Saturday", "Saturday"),
    ]
    
    TIME_SLOT_CHOICES = [
        ("8am-9am", "8 a.m. - 9 a.m."),
        ("9am-10am", "9 a.m. - 10 a.m."),
        ("10am-11am", "10 a.m. - 11 a.m."),
        ("11am-12pm", "11 a.m. - noon"),
        ("12pm-1pm", "noon - 1 p.m."),
        ("1pm-2pm", "1 p.m. - 2 p.m."),
        ("2pm-3pm", "2 p.m. - 3 p.m."),
        ("3pm-4pm", "3 p.m. - 4 p.m."),
        ("4pm-5pm", "4 p.m. - 5 p.m."),
        ("5pm-6pm", "5 p.m. - 6 p.m."),
        ("6pm-7pm", "6 p.m. - 7 p.m."),
        ("7pm-8pm", "7 p.m. - 8 p.m."),
        ("8pm-9pm", "8 p.m. - 9 p.m."),
        ("9pm-10pm", "9 p.m. - 10 p.m."),
    ]
    
    section_course_faculty = models.ForeignKey(
        SectionCourseFaculty, on_delete=models.CASCADE, related_name="schedules"
    )

    course_offering = models.ForeignKey(
        CourseOffering,
        on_delete=models.PROTECT,
        related_name="schedules",
        null=True,
        blank=True,
    )
    classroom = models.ForeignKey(
        Classroom, on_delete=models.PROTECT, related_name="schedules"
    )
    day_of_week = models.CharField(max_length=10, choices=DAY_CHOICES)
    time_slot = models.CharField(max_length=20, choices=TIME_SLOT_CHOICES, default="8am-9am")

    period_number = models.PositiveSmallIntegerField(null=True, blank=True)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_schedules",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ["day_of_week", "time_slot", "classroom__block__code", "classroom__room_number"]
        constraints = [
            # Prevent same classroom at same time
            models.UniqueConstraint(
                fields=["classroom", "day_of_week", "time_slot"],
                name="unique_room_slot",
                violation_error_message="This classroom is already booked for this time slot.",
            ),
        ]
    
    def __str__(self) -> str:
        return f"{self.section_course_faculty.course.code} - {self.day_of_week} {self.time_slot} - {self.classroom}"
    
    @property
    def faculty(self):
        return self.section_course_faculty.faculty
    
    @property
    def section(self):
        return self.section_course_faculty.section
    
    @property
    def course(self):
        return self.section_course_faculty.course
    
    @property
    def derived_period_number(self):
        """Derive period number from time slot for display purposes."""
        slot_map = {
            "8am-9am": 1, "9am-10am": 2, "10am-11am": 3, "11am-12pm": 4,
            "12pm-1pm": 5, "1pm-2pm": 6, "2pm-3pm": 7, "3pm-4pm": 8,
            "4pm-5pm": 9, "5pm-6pm": 10, "6pm-7pm": 11, "7pm-8pm": 12,
            "8pm-9pm": 13, "9pm-10pm": 14,
        }
        return slot_map.get(self.time_slot, 0)


class MakeUpClass(models.Model):
    """Make-up class sessions with remedial code for attendance."""
    
    STATUS_SCHEDULED = "scheduled"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_COMPLETED = "completed"
    STATUS_CANCELLED = "cancelled"
    
    STATUS_CHOICES = [
        (STATUS_SCHEDULED, "Scheduled"),
        (STATUS_IN_PROGRESS, "In Progress"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_CANCELLED, "Cancelled"),
    ]
    
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="makeup_classes")
    faculty = models.ForeignKey(FacultyProfile, on_delete=models.CASCADE, related_name="makeup_classes")
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name="makeup_classes")
    classroom = models.ForeignKey(Classroom, on_delete=models.PROTECT, related_name="makeup_classes")
    
    session_date = models.DateField()
    time_slot = models.CharField(max_length=20, choices=Schedule.TIME_SLOT_CHOICES)
    
    remedial_code = models.CharField(max_length=8, unique=True)
    reason = models.TextField(help_text="Reason for make-up class")
    
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_SCHEDULED)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ["-session_date", "time_slot"]
    
    def __str__(self) -> str:
        return f"Make-up: {self.course.code} - {self.session_date} - Code: {self.remedial_code}"
    
    def save(self, *args, **kwargs):
        if not self.remedial_code:
            self.remedial_code = self._generate_remedial_code()
        super().save(*args, **kwargs)
    
    def _generate_remedial_code(self) -> str:
        """Generate unique 6-character alphanumeric remedial code."""
        import random
        import string
        
        while True:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            if not MakeUpClass.objects.filter(remedial_code=code).exists():
                return code


class MakeUpAttendanceRecord(models.Model):
    """Separate attendance records for make-up classes."""
    
    VIA_FACULTY = "faculty"
    VIA_STUDENT = "student"
    VIA_AUTO = "auto"
    
    MARKED_VIA_CHOICES = [
        (VIA_FACULTY, "Faculty"),
        (VIA_STUDENT, "Student (Self)"),
        (VIA_AUTO, "Auto-marked"),
    ]
    
    makeup_class = models.ForeignKey(MakeUpClass, on_delete=models.CASCADE, related_name="attendance_records")
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    status = models.CharField(max_length=16, choices=AttendanceRecord.STATUS_CHOICES)
    marked_at = models.DateTimeField(auto_now_add=True)
    marked_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    marked_via = models.CharField(max_length=16, choices=MARKED_VIA_CHOICES, default=VIA_FACULTY)
    
    class Meta:
        unique_together = ("makeup_class", "student")
    
    def __str__(self) -> str:
        return f"{self.student.registration_number} - {self.makeup_class.course.code} - {self.status}"
