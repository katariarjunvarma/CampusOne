from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission

from .models import (
    AttendanceSession,
    Block,
    Classroom,
    Course,
    CourseOffering,
    Enrollment,
    FaceSample,
    FacultyProfile,
    Student,
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
        fields = ["code", "name"]


class AttendancePhotoUploadForm(forms.Form):
    photo = forms.ImageField(
        widget=forms.ClearableFileInput(
            attrs={"class": "form-control form-control-sm", "style": "width:100%;"}
        )
    )


class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ["registration_number", "full_name", "email", "parent_email", "parent_phone"]


class EnrollmentForm(forms.ModelForm):
    class Meta:
        model = Enrollment
        fields = ["student", "course"]


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
            "classroom",
            "day_of_week",
            "start_time",
            "end_time",
            "is_active",
        ]
        widgets = {
            "start_time": forms.TimeInput(attrs={"type": "time"}),
            "end_time": forms.TimeInput(attrs={"type": "time"}),
        }
