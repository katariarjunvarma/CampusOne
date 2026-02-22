from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.utils import timezone

from .models import (
    AttendanceSession,
    Block,
    Classroom,
    Course,
    CourseOffering,
    Enrollment,
    FaceSample,
    FacultyProfile,
    MakeUpAttendanceRecord,
    MakeUpClass,
    Schedule,
    Student,
    Section,
    SectionCourseFaculty,
)


User = get_user_model()


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        if not data:
            return []
        if not isinstance(data, (list, tuple)):
            data = [data]
        cleaned = [super().clean(d, initial) for d in data]
        return cleaned


class SectionForm(forms.ModelForm):
    class Meta:
        model = Section
        fields = ["name", "courses", "year", "semester"]
        labels = {
            "name": "Section Code",
            "courses": "Linked Courses",
        }
        help_texts = {
            "name": "This code will be used to identify the section everywhere (e.g., A, B, CSE-A, etc.)",
            "courses": "Optional: Link this section to one or more courses",
        }
        widgets = {
            "courses": forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["name"].widget.attrs.update({"placeholder": "Enter section code (e.g., A, B, CSE-A)", "class": "form-control"})
        self.fields["year"].widget.attrs.update({"class": "form-select"})
        self.fields["semester"].widget.attrs.update({"class": "form-select"})
        self.fields["courses"].required = False
        self.fields["courses"].queryset = Course.objects.order_by("code")


class SectionCourseFacultyForm(forms.ModelForm):
    class Meta:
        model = SectionCourseFaculty
        fields = [
            "section",
            "course",
            "faculty",
        ]
        widgets = {
            "section": forms.Select(attrs={"class": "form-select"}),
            "course": forms.Select(attrs={"class": "form-select"}),
            "faculty": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["section"].queryset = Section.objects.order_by("name")

        section = None
        if self.is_bound:
            section_id = (self.data.get("section") or "").strip()
            if section_id.isdigit():
                section = Section.objects.filter(id=int(section_id)).first()
        elif getattr(self.instance, "section_id", None):
            section = Section.objects.filter(id=int(self.instance.section_id)).first()

        if section is not None:
            self.fields["course"].queryset = section.courses.order_by("code")
        else:
            self.fields["course"].queryset = Course.objects.none()

    def clean(self):
        cleaned_data = super().clean()
        section = cleaned_data.get("section")
        course = cleaned_data.get("course")

        if section and course:
            # Ensure chosen course belongs to the section
            if not section.courses.filter(id=course.id).exists():
                raise forms.ValidationError("Selected course does not belong to this section.")

            existing = SectionCourseFaculty.objects.filter(section=section, course=course)
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)

            if existing.exists():
                raise forms.ValidationError(
                    "This course is already assigned to a faculty for this section."
                )

        return cleaned_data


class StudentSectionAllocationForm(forms.Form):
    section = forms.ModelChoiceField(queryset=Section.objects.order_by("name"))
    students = forms.ModelMultipleChoiceField(
        queryset=Student.objects.order_by("registration_number"),
        widget=forms.SelectMultiple(attrs={"class": "form-select", "size": "12"}),
    )


class AttendanceSessionCreateForm(forms.ModelForm):
    time_slot = forms.ChoiceField(required=False)

    class Meta:
        model = AttendanceSession
        fields = ["course", "session_date", "time_slot", "session_label"]
        widgets = {
            "session_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        def _label(hour: int) -> str:
            if hour == 0:
                return "12am"
            if hour < 12:
                return f"{hour}am"
            if hour == 12:
                return "12pm"
            return f"{hour - 12}pm"

        choices = [("", "---------")]
        for h in range(24):
            start = _label(h)
            end = _label((h + 1) % 24)
            value = f"{start}-{end}"
            choices.append((value, value))

        self.fields["time_slot"].choices = choices
        self.fields["time_slot"].widget.attrs.update({"class": "form-select"})
        if "session_label" in self.fields:
            self.fields["session_label"].widget.attrs.update({"class": "form-control"})
        if "course" in self.fields:
            self.fields["course"].widget.attrs.update({"class": "form-select"})


class CourseCreateForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ["code", "name", "year", "semester"]


class AttendancePhotoUploadForm(forms.Form):
    photo = forms.ImageField(
        widget=forms.ClearableFileInput(
            attrs={"class": "form-control form-control-sm", "style": "width:100%;"}
        )
    )


class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = [
            "registration_number",
            "full_name",
            "department",
            "year",
            "semester",
            "email",
            "student_phone",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Mandatory inputs when adding/updating students
        self.fields["department"].required = True
        self.fields["year"].required = True
        self.fields["semester"].required = True
        self.fields["student_phone"].required = True
        self.fields["student_phone"].label = "Student Phone Number"


class EnrollmentForm(forms.ModelForm):
    class Meta:
        model = Enrollment
        fields = ["student", "course"]

    def clean(self):
        cleaned = super().clean()
        student = cleaned.get("student")
        course = cleaned.get("course")
        if student and course:
            if Enrollment.objects.filter(student=student, course=course).exists():
                raise forms.ValidationError("This student is already enrolled in this course.")
        return cleaned


class FaceSampleForm(forms.ModelForm):
    class Meta:
        model = FaceSample
        fields = ["student", "image"]


class FaceSampleMultiForm(forms.Form):
    student = forms.ModelChoiceField(queryset=Student.objects.order_by("registration_number"))
    images = MultipleFileField(
        required=True,
        widget=MultipleFileInput(
            attrs={"multiple": True, "class": "form-control", "accept": "image/*"}
        ),
    )

    def clean_images(self):
        files = self.files.getlist("images")
        if len(files) < 5:
            raise forms.ValidationError("Please upload at least 5 photos.")
        if len(files) > 10:
            raise forms.ValidationError("Please upload at most 10 photos.")
        return files


class UserPermissionsForm(forms.ModelForm):
    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.order_by("name"),
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "form-select", "size": "10"}),
    )
    user_permissions = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.select_related("content_type").order_by(
            "content_type__app_label", "content_type__model", "codename"
        ),
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "form-select", "size": "10"}),
    )

    class Meta:
        model = User
        fields = ["is_active", "is_staff", "is_superuser", "groups", "user_permissions"]
        widgets = {
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_staff": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_superuser": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class BlockForm(forms.ModelForm):
    class Meta:
        model = Block
        fields = ["code", "name", "is_active"]


class ClassroomForm(forms.ModelForm):
    class Meta:
        model = Classroom
        fields = ["block", "room_number", "capacity", "is_active"]


class FacultyProfileForm(forms.ModelForm):
    class Meta:
        model = FacultyProfile
        fields = ["user", "employee_id", "is_active"]


class CourseOfferingForm(forms.ModelForm):
    class Meta:
        model = CourseOffering
        fields = [
            "course",
            "faculty",
            "section",
            "is_active",
        ]
        widgets = {
            "course": forms.Select(attrs={"class": "form-select"}),
            "faculty": forms.Select(attrs={"class": "form-select"}),
            "section": forms.Select(attrs={"class": "form-select"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Order sections by name for the dropdown
        self.fields["section"].queryset = Section.objects.order_by("name")
        self.fields["section"].required = False
        self.fields["section"].empty_label = "---------"

        # Filter course options by selected section -> courses
        if "section" in self.data:
            try:
                section_id = int(self.data.get("section") or 0)
                section = Section.objects.get(id=section_id)
                self.fields["course"].queryset = section.courses.order_by("code")
            except Exception:
                self.fields["course"].queryset = Course.objects.none()
        elif getattr(self.instance, "pk", None) and getattr(self.instance, "section_id", None):
            try:
                section = self.instance.section
                if section is not None:
                    self.fields["course"].queryset = section.courses.order_by("code")
                else:
                    self.fields["course"].queryset = Course.objects.none()
            except Exception:
                self.fields["course"].queryset = Course.objects.none()
        else:
            self.fields["course"].queryset = Course.objects.none()

    def clean(self):
        cleaned_data = super().clean()
        course = cleaned_data.get("course")
        faculty = cleaned_data.get("faculty")
        section = cleaned_data.get("section")

        if course and section:
            if not section.courses.filter(id=course.id).exists():
                raise forms.ValidationError("Selected course does not belong to this section.")

            # Check for duplicate (course + section) - only one faculty allowed per course+section
            existing = CourseOffering.objects.filter(
                course=course,
                section=section
            )
            # Exclude current instance when editing
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)

            if existing.exists():
                raise forms.ValidationError(
                    "Course already assigned to this section."
                )

        return cleaned_data


class ScheduleForm(forms.ModelForm):
    """Form for creating and editing academic schedules with clash prevention."""
    
    class Meta:
        model = Schedule
        fields = ["section_course_faculty", "classroom", "day_of_week", "time_slot"]
        widgets = {
            "section_course_faculty": forms.Select(attrs={"class": "form-select"}),
            "classroom": forms.Select(attrs={"class": "form-select"}),
            "day_of_week": forms.Select(attrs={"class": "form-select"}),
            "time_slot": forms.Select(attrs={"class": "form-select"}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Order section_course_faculty for dropdown
        self.fields["section_course_faculty"].queryset = SectionCourseFaculty.objects.select_related(
            "course", "faculty__user", "section"
        ).order_by("course__code", "section__name")
        
        # Order classrooms for dropdown
        self.fields["classroom"].queryset = Classroom.objects.select_related("block").order_by(
            "block__code", "room_number"
        )
    
    def clean(self):
        cleaned_data = super().clean()
        section_course_faculty = cleaned_data.get("section_course_faculty")
        classroom = cleaned_data.get("classroom")
        day_of_week = cleaned_data.get("day_of_week")
        time_slot = cleaned_data.get("time_slot")
        
        if not all([section_course_faculty, classroom, day_of_week, time_slot]):
            return cleaned_data
        
        faculty = section_course_faculty.faculty
        section = section_course_faculty.section
        
        # Check for room clash (excluding current instance when editing)
        room_clash = Schedule.objects.filter(
            classroom=classroom,
            day_of_week=day_of_week,
            time_slot=time_slot
        )
        if self.instance.pk:
            room_clash = room_clash.exclude(pk=self.instance.pk)
        if room_clash.exists():
            raise forms.ValidationError("Room already booked for this time slot.")
        
        # Check for faculty clash
        faculty_clash = Schedule.objects.filter(
            section_course_faculty__faculty=faculty,
            day_of_week=day_of_week,
            time_slot=time_slot
        )
        if self.instance.pk:
            faculty_clash = faculty_clash.exclude(pk=self.instance.pk)
        if faculty_clash.exists():
            raise forms.ValidationError("Faculty already assigned to another class at this time.")
        
        # Check for section clash (only if section exists)
        if section:
            section_clash = Schedule.objects.filter(
                section_course_faculty__section=section,
                day_of_week=day_of_week,
                time_slot=time_slot
            )
            if self.instance.pk:
                section_clash = section_clash.exclude(pk=self.instance.pk)
            if section_clash.exists():
                raise forms.ValidationError("Section already has another class at this time.")
        
        return cleaned_data


class MakeUpClassForm(forms.ModelForm):
    """Form for faculty to schedule make-up classes with smart scheduling."""
    
    class Meta:
        model = MakeUpClass
        fields = ["course", "section", "classroom", "session_date", "time_slot", "reason"]
        widgets = {
            "course": forms.Select(attrs={"class": "form-select"}),
            "section": forms.Select(attrs={"class": "form-select"}),
            "classroom": forms.Select(attrs={"class": "form-select"}),
            "session_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "time_slot": forms.Select(attrs={"class": "form-select"}),
            "reason": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }
    
    def __init__(self, *args, faculty=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.faculty = faculty
        
        # Filter sections by faculty's assigned courses
        if faculty:
            assigned_section_ids = SectionCourseFaculty.objects.filter(
                faculty=faculty
            ).values_list("section_id", flat=True).distinct()
            self.fields["section"].queryset = Section.objects.filter(
                id__in=assigned_section_ids
            ).order_by("name")
            
            assigned_course_ids = SectionCourseFaculty.objects.filter(
                faculty=faculty
            ).values_list("course_id", flat=True).distinct()
            self.fields["course"].queryset = Course.objects.filter(
                id__in=assigned_course_ids
            ).order_by("code")
        
        # Order classrooms
        self.fields["classroom"].queryset = Classroom.objects.select_related(
            "block"
        ).filter(is_active=True).order_by("block__code", "room_number")
        
        # Set minimum date to today
        self.fields["session_date"].widget.attrs["min"] = str(timezone.localdate())
    
    def clean(self):
        cleaned_data = super().clean()
        classroom = cleaned_data.get("classroom")
        session_date = cleaned_data.get("session_date")
        time_slot = cleaned_data.get("time_slot")
        course = cleaned_data.get("course")
        section = cleaned_data.get("section")
        
        if not all([classroom, session_date, time_slot, course, section]):
            return cleaned_data
        
        # Check classroom availability
        existing = MakeUpClass.objects.filter(
            classroom=classroom,
            session_date=session_date,
            time_slot=time_slot,
            status__in=[MakeUpClass.STATUS_SCHEDULED, MakeUpClass.STATUS_IN_PROGRESS]
        )
        if self.instance.pk:
            existing = existing.exclude(pk=self.instance.pk)
        if existing.exists():
            raise forms.ValidationError(
                f"Classroom {classroom} is already booked for this date and time slot."
            )
        
        # Check faculty availability
        if self.faculty:
            faculty_clash = MakeUpClass.objects.filter(
                faculty=self.faculty,
                session_date=session_date,
                time_slot=time_slot,
                status__in=[MakeUpClass.STATUS_SCHEDULED, MakeUpClass.STATUS_IN_PROGRESS]
            )
            if self.instance.pk:
                faculty_clash = faculty_clash.exclude(pk=self.instance.pk)
            if faculty_clash.exists():
                raise forms.ValidationError(
                    "You already have a make-up class scheduled at this time."
                )
            
            # Check regular schedule clash
            day_name = session_date.strftime("%A")
            if day_name in [choice[0] for choice in Schedule.DAY_CHOICES]:
                schedule_clash = Schedule.objects.filter(
                    section_course_faculty__faculty=self.faculty,
                    day_of_week=day_name,
                    time_slot=time_slot
                )
                if schedule_clash.exists():
                    raise forms.ValidationError(
                        "You have a regular class scheduled at this time."
                    )
        
        # Check section availability
        section_clash = MakeUpClass.objects.filter(
            section=section,
            session_date=session_date,
            time_slot=time_slot,
            status__in=[MakeUpClass.STATUS_SCHEDULED, MakeUpClass.STATUS_IN_PROGRESS]
        )
        if self.instance.pk:
            section_clash = section_clash.exclude(pk=self.instance.pk)
        if section_clash.exists():
            raise forms.ValidationError(
                "This section already has a make-up class at this time."
            )
        
        # Validate course belongs to section
        if course and section:
            if not section.courses.filter(id=course.id).exists():
                raise forms.ValidationError(
                    "Selected course is not assigned to this section."
                )
        
        return cleaned_data


class SmartSchedulingForm(forms.Form):
    """Form for AI-powered smart scheduling recommendations."""
    
    preferred_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        required=False,
        help_text="Leave blank for any date recommendation"
    )
    preferred_time_slot = forms.ChoiceField(
        choices=Schedule.TIME_SLOT_CHOICES,
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
        help_text="Leave blank for any time recommendation"
    )
    duration_hours = forms.IntegerField(
        min_value=1,
        max_value=3,
        initial=1,
        widget=forms.NumberInput(attrs={"class": "form-control"}),
        help_text="Estimated class duration in hours"
    )
    prioritize_low_traffic = forms.BooleanField(
        initial=True,
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        help_text="Recommend low-traffic time slots"
    )
