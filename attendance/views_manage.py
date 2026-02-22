from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.views import LoginView
from django.db import transaction
from django.db.models import Sum
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
from django.template.loader import render_to_string

import cv2
import numpy as np
from PIL import Image
from django.http import JsonResponse
from django.core.mail import send_mail
from django.conf import settings
import base64
import time
from collections import deque
from datetime import timedelta

from .face_recognition import (
    build_embedding_gallery,
    build_training_set,
    detect_eyes_count,
    detect_faces_count,
    recognize_embeddings_in_image,
    recognize_faces_in_image,
    train_lbph,
)
from .forms import (
    AttendancePhotoUploadForm,
    AttendanceSessionCreateForm,
    BlockForm,
    CourseCreateForm,
    MakeUpClassForm,
    SectionCourseFacultyForm,
    EnrollmentForm,
    FaceSampleMultiForm,
    FaceSampleForm,
    FacultyProfileForm,
    ClassroomForm,
    ScheduleForm,
    SmartSchedulingForm,
    StudentForm,
    UserPermissionsForm,
    SectionForm,
    StudentSectionAllocationForm,
)
from .models import (
    AttendanceRecord,
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
    Notification,
    Schedule,
    Student,
    Section,
    SectionCourseFaculty,
    StudentSection,
)

from food.models import BulkOrder, BreakSlot, EmergencyAlert, FoodItem, LoyaltyPoints, PreOrder, Stall


User = get_user_model()


_live_state: dict[tuple[int, int], dict[str, object]] = {}


def _live_key(request: HttpRequest, session_id: int) -> tuple[int, int]:
    return (int(request.user.id or 0), int(session_id))


def _live_get_state(request: HttpRequest, session_id: int) -> dict[str, object]:
    key = _live_key(request, session_id)
    st = _live_state.get(key)
    if st is None:
        st = {
            "last_ts": 0.0,
            "eyes": deque(maxlen=8),
            "last_blink_ts": 0.0,
            "candidates": {},
        }
        _live_state[key] = st
    return st


def _blink_seen(state: dict[str, object]) -> bool:
    eyes: deque[int] = state["eyes"]  # type: ignore[assignment]
    if len(eyes) < 3:
        return False
    vals = list(eyes)
    hi1 = any(v >= 1 for v in vals[:2])
    low = any(v == 0 for v in vals[2:5])
    hi2 = any(v >= 1 for v in vals[5:]) if len(vals) >= 6 else any(v >= 1 for v in vals[4:])
    return bool(hi1 and low and hi2)


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def manage_dashboard(request: HttpRequest) -> HttpResponse:
    from django.utils import timezone
    from datetime import date
    
    today = date.today()
    sessions_today = AttendanceSession.objects.filter(session_date=today).count()
    
    stats = {
        "students": Student.objects.count(),
        "courses": Course.objects.count(),
        "enrollments": Enrollment.objects.count(),
        "face_samples": FaceSample.objects.count(),
        "notifications": Notification.objects.count(),
        "sessions": AttendanceSession.objects.count(),
        "sessions_today": sessions_today,
        "records": AttendanceRecord.objects.count(),
        "blocks": Block.objects.count(),
        "classrooms": Classroom.objects.count(),
        "faculty": FacultyProfile.objects.count(),
        "offerings": CourseOffering.objects.count(),
    }
    return render(request, "attendance/manage/admin_dashboard.html", {"stats": stats})


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def manage_system(request: HttpRequest) -> HttpResponse:
    from django.utils import timezone
    from datetime import date
    
    today = date.today()
    sessions_today = AttendanceSession.objects.filter(session_date=today).count()
    
    stats = {
        "students": Student.objects.count(),
        "courses": Course.objects.count(),
        "enrollments": Enrollment.objects.count(),
        "face_samples": FaceSample.objects.count(),
        "notifications": Notification.objects.count(),
        "sessions": AttendanceSession.objects.count(),
        "sessions_today": sessions_today,
        "records": AttendanceRecord.objects.count(),
        "blocks": Block.objects.count(),
        "classrooms": Classroom.objects.count(),
        "faculty": FacultyProfile.objects.count(),
        "offerings": CourseOffering.objects.count(),
    }
    return render(request, "attendance/manage/manage_system.html", {"stats": stats})


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def campus_resources_dashboard(request: HttpRequest) -> HttpResponse:
    """Redirect to manage_system since Campus Resources section is removed."""
    return redirect("manage_system")


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def manage_blocks(request: HttpRequest) -> HttpResponse:
    blocks = Block.objects.order_by("code")
    return render(request, "attendance/manage/blocks.html", {"blocks": blocks})


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def manage_block_create(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = BlockForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Block created.")
            return redirect("manage_blocks")
    else:
        form = BlockForm()
    return render(
        request,
        "attendance/manage/form.html",
        {
            "form": form,
            "title": "Add Block",
            "cancel_url": reverse("campus_resources_dashboard"),
        },
    )


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def manage_sections(request: HttpRequest) -> HttpResponse:
    sections = Section.objects.prefetch_related("courses").order_by("name")
    return render(request, "attendance/manage/sections.html", {"sections": sections})


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def manage_section_create(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = SectionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Section created.")
            return redirect("manage_sections")
    else:
        form = SectionForm()
    return render(
        request,
        "attendance/manage/form.html",
        {"form": form, "title": "Add Section", "cancel_url": reverse("manage_sections")},
    )


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def manage_section_delete(request: HttpRequest, section_id: int) -> HttpResponse:
    section = get_object_or_404(Section, id=section_id)
    if request.method == "POST":
        section.delete()
        messages.success(request, "Section deleted.")
        return redirect("manage_sections")
    return render(
        request,
        "attendance/manage/confirm_delete.html",
        {"object": section, "type": "Section", "cancel_url": "manage_sections"},
    )


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def manage_section_allocate_students(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = StudentSectionAllocationForm(request.POST)
        if form.is_valid():
            section = form.cleaned_data["section"]
            students = form.cleaned_data["students"]
            updated = 0
            for s in students:
                current_section = s.section
                if not current_section or current_section.id != section.id:
                    StudentSection.objects.update_or_create(
                        student=s, defaults={"section": section}
                    )
                    updated += 1
            messages.success(request, f"Allocated {updated} students to section {section.name}.")
            return redirect("manage_students")
    else:
        form = StudentSectionAllocationForm()
    return render(
        request,
        "attendance/manage/section_allocate.html",
        {"form": form, "cancel_url": reverse("manage_students")},
    )


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def manage_block_edit(request: HttpRequest, block_id: int) -> HttpResponse:
    block = get_object_or_404(Block, id=block_id)
    if request.method == "POST":
        form = BlockForm(request.POST, instance=block)
        if form.is_valid():
            form.save()
            messages.success(request, "Block updated.")
            return redirect("manage_blocks")
    else:
        form = BlockForm(instance=block)
    return render(
        request,
        "attendance/manage/form.html",
        {
            "form": form,
            "title": "Edit Block",
            "cancel_url": reverse("campus_resources_dashboard"),
        },
    )


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def manage_block_delete(request: HttpRequest, block_id: int) -> HttpResponse:
    block = get_object_or_404(Block, id=block_id)
    if request.method == "POST":
        block.delete()
        messages.success(request, "Block deleted.")
        return redirect("manage_blocks")
    return render(
        request,
        "attendance/manage/confirm_delete.html",
        {"object": block, "type": "Block", "cancel_url": "campus_resources_dashboard"},
    )


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def manage_classrooms(request: HttpRequest) -> HttpResponse:
    classrooms = Classroom.objects.select_related("block").order_by("block__code", "room_number")
    return render(
        request,
        "attendance/manage/classrooms.html",
        {"classrooms": classrooms},
    )


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def manage_classroom_create(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = ClassroomForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Classroom created.")
            return redirect("manage_classrooms")
    else:
        form = ClassroomForm()
    return render(
        request,
        "attendance/manage/form.html",
        {
            "form": form,
            "title": "Add Classroom",
            "cancel_url": reverse("campus_resources_dashboard"),
        },
    )


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def manage_classroom_edit(request: HttpRequest, classroom_id: int) -> HttpResponse:
    classroom = get_object_or_404(Classroom, id=classroom_id)
    if request.method == "POST":
        form = ClassroomForm(request.POST, instance=classroom)
        if form.is_valid():
            form.save()
            messages.success(request, "Classroom updated.")
            return redirect("manage_classrooms")
    else:
        form = ClassroomForm(instance=classroom)
    return render(
        request,
        "attendance/manage/form.html",
        {
            "form": form,
            "title": "Edit Classroom",
            "cancel_url": reverse("campus_resources_dashboard"),
        },
    )


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def manage_classroom_delete(request: HttpRequest, classroom_id: int) -> HttpResponse:
    classroom = get_object_or_404(Classroom, id=classroom_id)
    if request.method == "POST":
        classroom.delete()
        messages.success(request, "Classroom deleted.")
        return redirect("manage_classrooms")
    return render(
        request,
        "attendance/manage/confirm_delete.html",
        {
            "object": classroom,
            "type": "Classroom",
            "cancel_url": "campus_resources_dashboard",
        },
    )


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def manage_faculty(request: HttpRequest) -> HttpResponse:
    faculty = FacultyProfile.objects.select_related("user").order_by("user__username")
    return render(request, "attendance/manage/faculty.html", {"faculty": faculty})


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def manage_faculty_create(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = FacultyProfileForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Faculty profile created.")
            return redirect("manage_faculty")
    else:
        form = FacultyProfileForm()
    return render(
        request,
        "attendance/manage/form.html",
        {
            "form": form,
            "title": "Add Faculty",
            "cancel_url": reverse("campus_resources_dashboard"),
        },
    )


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def manage_faculty_edit(request: HttpRequest, faculty_id: int) -> HttpResponse:
    faculty = get_object_or_404(FacultyProfile, id=faculty_id)
    if request.method == "POST":
        form = FacultyProfileForm(request.POST, instance=faculty)
        if form.is_valid():
            form.save()
            messages.success(request, "Faculty profile updated.")
            return redirect("manage_faculty")
    else:
        form = FacultyProfileForm(instance=faculty)
    return render(
        request,
        "attendance/manage/form.html",
        {
            "form": form,
            "title": "Edit Faculty",
            "cancel_url": reverse("campus_resources_dashboard"),
        },
    )


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def manage_faculty_delete(request: HttpRequest, faculty_id: int) -> HttpResponse:
    faculty = get_object_or_404(FacultyProfile, id=faculty_id)
    if request.method == "POST":
        faculty.delete()
        messages.success(request, "Faculty profile deleted.")
        return redirect("manage_faculty")
    return render(
        request,
        "attendance/manage/confirm_delete.html",
        {"object": faculty, "type": "Faculty", "cancel_url": "campus_resources_dashboard"},
    )


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def manage_course_offerings(request: HttpRequest) -> HttpResponse:
    offerings = (
        SectionCourseFaculty.objects.select_related("course", "faculty__user", "section")
        .order_by("section__name", "course__code")
    )
    return render(request, "attendance/manage/course_offerings.html", {"offerings": offerings})


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def manage_course_offering_create(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = SectionCourseFacultyForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Course offering created.")
            return redirect("manage_course_offerings")
    else:
        form = SectionCourseFacultyForm()
    return render(
        request,
        "attendance/manage/form.html",
        {
            "form": form,
            "title": "Add Course Offering",
            "cancel_url": reverse("campus_resources_dashboard"),
        },
    )


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def manage_course_offering_edit(request: HttpRequest, offering_id: int) -> HttpResponse:
    offering = get_object_or_404(SectionCourseFaculty, id=offering_id)
    if request.method == "POST":
        form = SectionCourseFacultyForm(request.POST, instance=offering)
        if form.is_valid():
            form.save()
            messages.success(request, "Course offering updated.")
            return redirect("manage_course_offerings")
    else:
        form = SectionCourseFacultyForm(instance=offering)
    return render(
        request,
        "attendance/manage/form.html",
        {
            "form": form,
            "title": "Edit Course Offering",
            "cancel_url": reverse("campus_resources_dashboard"),
        },
    )


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def manage_course_offering_delete(request: HttpRequest, offering_id: int) -> HttpResponse:
    offering = get_object_or_404(SectionCourseFaculty, id=offering_id)
    if request.method == "POST":
        offering.delete()
        messages.success(request, "Course offering deleted.")
        return redirect("manage_course_offerings")
    return render(
        request,
        "attendance/manage/confirm_delete.html",
        {
            "object": offering,
            "type": "Course Offering",
            "cancel_url": "campus_resources_dashboard",
        },
    )


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def report_capacity_utilization(request: HttpRequest) -> HttpResponse:
    # Report on section+course combinations and their enrollment vs capacity
    # Use SectionCourseFaculty as the allocation model
    allocations = (
        SectionCourseFaculty.objects.select_related("course", "faculty__user", "section")
        .order_by("section__name", "course__code")
    )
    rows = []
    for a in allocations:
        # Count students in this section
        section_student_count = StudentSection.objects.filter(section=a.section).count()
        # Count total enrollments for this course
        enrolled = Enrollment.objects.filter(course=a.course).count()
        # Use section size as a proxy for "used" seats
        used_count = section_student_count if section_student_count > 0 else enrolled
        source = "Section Students" if section_student_count > 0 else "Course Enrollments"
        
        rows.append(
            {
                "allocation": a,
                "enrolled": enrolled,
                "used_count": used_count,
                "source": source,
            }
        )
    return render(request, "attendance/manage/report_capacity.html", {"rows": rows})


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def report_workload_distribution(request: HttpRequest) -> HttpResponse:
    faculty = FacultyProfile.objects.filter(is_active=True).select_related("user").order_by("user__username")
    rows = []
    for f in faculty:
        sessions_per_week = CourseOffering.objects.filter(faculty=f, is_active=True).count()
        max_load = f.max_weekly_load
        
        # Calculate load percentage
        load_pct = (sessions_per_week / max_load * 100.0) if max_load > 0 else 0.0
        
        is_overloaded = sessions_per_week > max_load
        
        rows.append({
            "faculty": f,
            "sessions_per_week": sessions_per_week,
            "max_load": max_load,
            "load_pct": round(load_pct, 1),
            "is_overloaded": is_overloaded
        })
    
    # Sort by sessions descending
    rows.sort(key=lambda r: r["sessions_per_week"], reverse=True)
    return render(request, "attendance/manage/report_workload.html", {"rows": rows})


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def manage_students(request: HttpRequest) -> HttpResponse:
    qs = Student.objects.order_by("registration_number")
    year = (request.GET.get("year") or "").strip()
    semester = (request.GET.get("semester") or "").strip()
    department = (request.GET.get("department") or "").strip()
    course_id = (request.GET.get("course_id") or "").strip()

    if year.isdigit():
        qs = qs.filter(year=int(year))
    if semester.isdigit():
        qs = qs.filter(semester=int(semester))
    if department:
        qs = qs.filter(department__icontains=department)
    if course_id.isdigit():
        qs = qs.filter(enrollments__course_id=int(course_id)).distinct()

    courses = Course.objects.order_by("code")
    return render(
        request,
        "attendance/manage/students.html",
        {
            "students": qs,
            "courses": courses,
            "filters": {
                "year": year,
                "semester": semester,
                "department": department,
                "course_id": course_id,
            },
        },
    )


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def manage_student_create(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = StudentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Student created.")
            return redirect("manage_students")
    else:
        form = StudentForm()
    return render(
        request,
        "attendance/manage/form.html",
        {"form": form, "title": "Add Student", "cancel_url": reverse("campus_resources_dashboard")},
    )


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def manage_student_edit(request: HttpRequest, student_id: int) -> HttpResponse:
    student = get_object_or_404(Student, id=student_id)
    if request.method == "POST":
        form = StudentForm(request.POST, instance=student)
        if form.is_valid():
            form.save()
            messages.success(request, "Student updated.")
            return redirect("manage_students")
    else:
        form = StudentForm(instance=student)
    return render(
        request,
        "attendance/manage/form.html",
        {"form": form, "title": "Edit Student", "cancel_url": reverse("campus_resources_dashboard")},
    )


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def manage_student_delete(request: HttpRequest, student_id: int) -> HttpResponse:
    student = get_object_or_404(Student, id=student_id)
    if request.method == "POST":
        student.delete()
        messages.success(request, "Student deleted.")
        return redirect("manage_students")
    return render(request, "attendance/manage/confirm_delete.html", {"object": student, "type": "Student"})


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def manage_courses(request: HttpRequest) -> HttpResponse:
    qs = Course.objects.order_by("code")
    year = (request.GET.get("year") or "").strip()
    semester = (request.GET.get("semester") or "").strip()
    teacher_id = (request.GET.get("teacher_id") or "").strip()

    if year.isdigit():
        qs = qs.filter(year=int(year))
    if semester.isdigit():
        qs = qs.filter(semester=int(semester))
    if teacher_id.isdigit():
        qs = qs.filter(section_faculty_allocations__faculty_id=int(teacher_id)).distinct()

    teachers = FacultyProfile.objects.select_related("user").order_by("user__username")
    return render(
        request,
        "attendance/manage/courses.html",
        {
            "courses": qs,
            "teachers": teachers,
            "filters": {"year": year, "semester": semester, "teacher_id": teacher_id},
        },
    )


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_staff", False)))
def section_courses_json(request: HttpRequest, section_id: int) -> JsonResponse:
    section = get_object_or_404(Section, id=section_id)
    courses = section.courses.order_by("code").values("id", "code", "name")
    return JsonResponse({"courses": list(courses)})


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def manage_course_create(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = CourseCreateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Course created.")
            return redirect("manage_courses")
    else:
        form = CourseCreateForm()
    return render(request, "attendance/manage/form.html", {"form": form, "title": "Add Course"})


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def manage_course_delete(request: HttpRequest, course_id: int) -> HttpResponse:
    course = get_object_or_404(Course, id=course_id)
    if request.method == "POST":
        course.delete()
        messages.success(request, "Course deleted.")
        return redirect("manage_courses")
    return render(request, "attendance/manage/confirm_delete.html", {"object": course, "type": "Course"})


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def manage_enrollments(request: HttpRequest) -> HttpResponse:
    enrollments = Enrollment.objects.select_related("student", "course").order_by("course__code", "student__registration_number")
    return render(request, "attendance/manage/enrollments.html", {"enrollments": enrollments})


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def manage_enrollment_create(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = EnrollmentForm(request.POST)
        if form.is_valid():
            student = form.cleaned_data["student"]
            course = form.cleaned_data["course"]
            obj, created = Enrollment.objects.get_or_create(student=student, course=course)
            if created:
                messages.success(request, "Enrollment created.")
            else:
                messages.info(request, "Student is already enrolled in this course.")
            return redirect("manage_enrollments")
    else:
        form = EnrollmentForm()
    return render(request, "attendance/manage/form.html", {"form": form, "title": "Add Enrollment"})


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def manage_enrollment_delete(request: HttpRequest, enrollment_id: int) -> HttpResponse:
    enrollment = get_object_or_404(Enrollment.objects.select_related("student", "course"), id=enrollment_id)
    if request.method == "POST":
        enrollment.delete()
        messages.success(request, "Enrollment removed.")
        return redirect("manage_enrollments")
    return render(
        request,
        "attendance/manage/confirm_delete.html",
        {"object": enrollment, "type": "Enrollment", "cancel_url": "manage_enrollments"},
    )


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def manage_face_samples(request: HttpRequest) -> HttpResponse:
    samples = FaceSample.objects.select_related("student").order_by("-created_at")
    return render(request, "attendance/manage/face_samples.html", {"samples": samples})


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def manage_face_sample_create(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = FaceSampleMultiForm(request.POST, request.FILES)
        if form.is_valid():
            student = form.cleaned_data["student"]
            images = form.cleaned_data["images"]
            for img in images:
                FaceSample.objects.create(student=student, image=img)
            messages.success(request, "Face data uploaded.")
            return redirect("manage_face_samples")
    else:
        form = FaceSampleMultiForm()
    return render(request, "attendance/manage/face_data_upload.html", {"form": form})


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def manage_face_sample_delete(request: HttpRequest, face_sample_id: int) -> HttpResponse:
    fs = get_object_or_404(FaceSample.objects.select_related("student"), id=face_sample_id)
    if request.method == "POST":
        if fs.image:
            fs.image.delete(save=False)
        fs.delete()
        messages.success(request, "Face data deleted.")
        return redirect("manage_face_samples")

    return render(request, "attendance/manage/confirm_delete.html", {"object": fs, "type": "Face Data"})


@login_required
@transaction.atomic
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def manage_face_samples_delete_all(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        samples = list(FaceSample.objects.all())
        deleted = 0
        for fs in samples:
            try:
                if fs.image:
                    fs.image.delete(save=False)
            except Exception:
                pass
            fs.delete()
            deleted += 1

        messages.success(request, f"Deleted {deleted} face data item(s).")
        return redirect("manage_face_samples")

    return render(
        request,
        "attendance/manage/confirm_delete.html",
        {"object": None, "type": "All Face Data", "cancel_url": "manage_face_samples"},
    )


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def manage_notifications(request: HttpRequest) -> HttpResponse:
    notifications = Notification.objects.select_related("recipient_student").order_by("-created_at")[:200]
    return render(request, "attendance/manage/notifications.html", {"notifications": notifications})


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def manage_sessions(request: HttpRequest) -> HttpResponse:
    sessions = AttendanceSession.objects.select_related("course").order_by("-created_at")[:200]
    return render(request, "attendance/manage/sessions.html", {"sessions": sessions})


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def manage_records(request: HttpRequest) -> HttpResponse:
    session_id = request.GET.get("session")
    qs = AttendanceRecord.objects.select_related("session", "session__course", "student").order_by(
        "-updated_at"
    )

    selected_session = None
    if session_id and session_id.isdigit():
        selected_session = AttendanceSession.objects.select_related("course").filter(id=int(session_id)).first()
        if selected_session:
            qs = qs.filter(session=selected_session)

    sessions = AttendanceSession.objects.select_related("course").order_by("-created_at")[:200]
    records = qs[:500]
    return render(
        request,
        "attendance/manage/records.html",
        {"records": records, "sessions": sessions, "selected_session": selected_session},
    )


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def report_block_utilization(request: HttpRequest) -> HttpResponse:
    # Aggregate students by block (via classrooms -> sections -> students)
    # Simplified report showing block capacity vs students assigned to sections in that block
    blocks = Block.objects.annotate(
        total_capacity=Sum("classrooms__capacity")
    ).prefetch_related("classrooms")
    
    block_data = []
    for block in blocks:
        # Get sections that have classrooms in this block (via section->classroom relation through courses)
        # Simplified: just count students allocated to sections
        total_capacity = block.total_capacity or 0
        
        # Count students whose section has courses allocated to classrooms in this block
        # This is an approximation - count all students in sections
        student_count = 0
        section_ids = set()
        
        # Get all sections that have allocations in this block's classrooms
        for classroom in block.classrooms.all():
            # Count students allocated to sections associated with this classroom
            # Since there's no direct link, we use a simplified approach
            pass
        
        # Simplified: count students in all sections as a proxy
        student_count = StudentSection.objects.count()
        
        utilization_pct = round((student_count / total_capacity * 100), 1) if total_capacity else 0
        
        block_data.append({
            "block": block,
            "total_capacity": total_capacity,
            "total_used": student_count,
            "utilization_pct": utilization_pct,
            "offering_count": 0,  # Simplified
            "offering_details": [],
        })
    
    # Sort by utilization descending
    block_data.sort(key=lambda x: x["utilization_pct"], reverse=True)
    
    return render(
        request,
        "attendance/manage/report_block_utilization.html",
        {"block_data": block_data},
    )


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def report_workload_distribution(request: HttpRequest) -> HttpResponse:
    faculty = FacultyProfile.objects.filter(is_active=True).select_related("user").order_by("user__username")
    rows = []
    for f in faculty:
        sessions_per_week = CourseOffering.objects.filter(faculty=f, is_active=True).count()
        max_load = f.max_weekly_load
        
        # Calculate load percentage
        load_pct = (sessions_per_week / max_load * 100.0) if max_load > 0 else 0.0
        
        is_overloaded = sessions_per_week > max_load
        
        rows.append({
            "faculty": f,
            "sessions_per_week": sessions_per_week,
            "max_load": max_load,
            "load_pct": round(load_pct, 1),
            "is_overloaded": is_overloaded
        })
    
    # Sort by sessions descending
    rows.sort(key=lambda r: r["sessions_per_week"], reverse=True)
    return render(request, "attendance/manage/report_workload.html", {"rows": rows})


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def super_admin_view_attendance(request: HttpRequest) -> HttpResponse:
    query = request.GET.get("q", "").strip()
    course_id = request.GET.get("course_id")
    student = None
    records = []
    stats = {}
    course_summaries = []
    selected_course = None

    if query:
        # Search for student by registration number or name
        student = Student.objects.filter(registration_number__iexact=query).first()
        if not student:
            # Try partial name match
            possible_students = Student.objects.filter(full_name__icontains=query)
            if possible_students.count() == 1:
                student = possible_students.first()
            elif possible_students.count() > 1:
                messages.warning(request, f"Multiple students found matching '{query}'. Please use the exact Registration Number.")
            else:
                pass # Just show not found message in template

    if student:
        # Get all regular attendance records
        all_records = AttendanceRecord.objects.select_related("session", "session__course").filter(student=student)
        
        # Get makeup class attendance records and convert to similar format
        makeup_records = MakeUpAttendanceRecord.objects.filter(
            student=student,
            makeup_class__status=MakeUpClass.STATUS_COMPLETED
        ).select_related("makeup_class", "makeup_class__course", "makeup_class__faculty")
        
        # Overall Stats (including makeup classes)
        total_regular_sessions = all_records.count()
        total_makeup_sessions = makeup_records.count()
        total_sessions = total_regular_sessions + total_makeup_sessions
        
        present_regular = all_records.filter(status=AttendanceRecord.STATUS_PRESENT).count()
        present_makeup = makeup_records.filter(status=AttendanceRecord.STATUS_PRESENT).count()
        present = present_regular + present_makeup
        
        absent_regular = all_records.filter(status=AttendanceRecord.STATUS_ABSENT).count()
        absent_makeup = makeup_records.filter(status=AttendanceRecord.STATUS_ABSENT).count()
        absent = absent_regular + absent_makeup
        
        percentage = (present / total_sessions * 100) if total_sessions > 0 else 0

        stats = {
            "total": total_sessions,
            "present": present,
            "absent": absent,
            "percentage": round(percentage, 1),
            "makeup_count": total_makeup_sessions,
        }

        if course_id:
            # Course Detail View - combine regular and makeup records
            regular_records = all_records.filter(session__course_id=course_id).order_by("-session__session_date", "-session__created_at")
            makeup_course_records = makeup_records.filter(makeup_class__course_id=course_id).order_by("-makeup_class__session_date")
            
            # Convert makeup records to display format
            records = list(regular_records)
            for mr in makeup_course_records:
                # Create a synthetic record-like object for template
                mr.session_date = mr.makeup_class.session_date
                mr.course_name = mr.makeup_class.course.name
                mr.course_code = mr.makeup_class.course.code
                mr.is_makeup = True
                mr.faculty_name = mr.makeup_class.faculty.user.get_full_name() or mr.makeup_class.faculty.user.username
                records.append(mr)
            
            # Sort by date
            records.sort(key=lambda x: x.session_date if hasattr(x, 'session_date') else x.session.session_date, reverse=True)
            
            if regular_records.exists():
                selected_course = regular_records.first().session.course
            elif makeup_course_records.exists():
                selected_course = makeup_course_records.first().makeup_class.course
            else:
                selected_course = Course.objects.filter(id=course_id).first()
        else:
            # Course Summary View - include makeup classes
            courses = {}
            # Process regular records
            for record in all_records:
                c = record.session.course
                if c.id not in courses:
                    courses[c.id] = {
                        "course": c,
                        "total": 0,
                        "present": 0,
                        "absent": 0,
                        "makeup_count": 0,
                    }
                courses[c.id]["total"] += 1
                if record.status == AttendanceRecord.STATUS_PRESENT:
                    courses[c.id]["present"] += 1
                else:
                    courses[c.id]["absent"] += 1
            
            # Process makeup records
            for mr in makeup_records:
                c = mr.makeup_class.course
                if c.id not in courses:
                    courses[c.id] = {
                        "course": c,
                        "total": 0,
                        "present": 0,
                        "absent": 0,
                        "makeup_count": 0,
                    }
                courses[c.id]["total"] += 1
                courses[c.id]["makeup_count"] += 1
                if mr.status == AttendanceRecord.STATUS_PRESENT:
                    courses[c.id]["present"] += 1
                else:
                    courses[c.id]["absent"] += 1
            
            for cid, data in courses.items():
                pct = (data["present"] / data["total"] * 100) if data["total"] > 0 else 0
                data["percentage"] = round(pct, 1)
                course_summaries.append(data)
            
            course_summaries.sort(key=lambda x: x["course"].code)

    return render(
        request,
        "attendance/super_admin_attendance.html",
        {
            "student": student, 
            "records": records, 
            "stats": stats, 
            "query": query, 
            "course_summaries": course_summaries, 
            "selected_course": selected_course
        },
    )


# ==================== ADMIN MANAGEMENT VIEWS ====================



@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def manage_users(request: HttpRequest) -> HttpResponse:
    users = User.objects.order_by("-date_joined")
    return render(request, "attendance/manage/users.html", {"users": users})


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def manage_user_create(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "User created.")
            return redirect("manage_users")
    else:
        form = UserCreationForm()
    return render(request, "attendance/manage/form.html", {"form": form, "title": "Add User"})


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def manage_user_edit(request: HttpRequest, user_id: int) -> HttpResponse:
    user_obj = get_object_or_404(User, id=user_id)
    if request.method == "POST":
        form = UserPermissionsForm(request.POST, instance=user_obj)
        if form.is_valid():
            form.save()
            messages.success(request, "User permissions updated.")
            return redirect("manage_users")
    else:
        form = UserPermissionsForm(instance=user_obj)
    return render(
        request,
        "attendance/manage/user_edit.html",
        {"form": form, "user_obj": user_obj, "title": f"Edit User: {user_obj.username}"},
    )


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def manage_stalls(request: HttpRequest) -> HttpResponse:
    stalls = Stall.objects.order_by("name")
    return render(request, "attendance/manage/stalls.html", {"stalls": stalls})


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def manage_stall_create(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        name = request.POST.get("name")
        location = request.POST.get("location")
        if name and location:
            Stall.objects.create(name=name, location=location)
            messages.success(request, "Stall created.")
            return redirect("manage_stalls")
        messages.error(request, "Name and location are required.")
    return render(request, "attendance/manage/stall_form.html", {"title": "Add Stall"})


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def manage_stall_edit(request: HttpRequest, stall_id: int) -> HttpResponse:
    stall = get_object_or_404(Stall, id=stall_id)
    if request.method == "POST":
        stall.name = request.POST.get("name", stall.name)
        stall.location = request.POST.get("location", stall.location)
        stall.is_active = request.POST.get("is_active") == "on"
        stall.save()
        messages.success(request, "Stall updated.")
        return redirect("manage_stalls")
    return render(request, "attendance/manage/stall_form.html", {"stall": stall, "title": "Edit Stall"})


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def manage_stall_delete(request: HttpRequest, stall_id: int) -> HttpResponse:
    stall = get_object_or_404(Stall, id=stall_id)
    if request.method == "POST":
        stall.delete()
        messages.success(request, "Stall deleted.")
        return redirect("manage_stalls")
    return render(request, "attendance/manage/confirm_delete.html", {"object": stall, "type": "Stall"})


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def manage_break_slots(request: HttpRequest) -> HttpResponse:
    slots = BreakSlot.objects.order_by("start_time")
    return render(request, "attendance/manage/break_slots.html", {"slots": slots})


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def manage_break_slot_create(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        name = request.POST.get("name")
        start_time = request.POST.get("start_time")
        end_time = request.POST.get("end_time")
        if name and start_time and end_time:
            BreakSlot.objects.create(name=name, start_time=start_time, end_time=end_time)
            messages.success(request, "Break slot created.")
            return redirect("manage_break_slots")
        messages.error(request, "All fields are required.")
    return render(request, "attendance/manage/break_slot_form.html", {"title": "Add Break Slot"})


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def manage_break_slot_edit(request: HttpRequest, slot_id: int) -> HttpResponse:
    slot = get_object_or_404(BreakSlot, id=slot_id)
    if request.method == "POST":
        slot.name = request.POST.get("name", slot.name)
        slot.start_time = request.POST.get("start_time", slot.start_time)
        slot.end_time = request.POST.get("end_time", slot.end_time)
        slot.save()
        messages.success(request, "Break slot updated.")
        return redirect("manage_break_slots")
    return render(request, "attendance/manage/break_slot_form.html", {"slot": slot, "title": "Edit Break Slot"})


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def manage_break_slot_delete(request: HttpRequest, slot_id: int) -> HttpResponse:
    slot = get_object_or_404(BreakSlot, id=slot_id)
    if request.method == "POST":
        slot.delete()
        messages.success(request, "Break slot deleted.")
        return redirect("manage_break_slots")
    return render(request, "attendance/manage/confirm_delete.html", {"object": slot, "type": "Break Slot"})


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def manage_food_items(request: HttpRequest) -> HttpResponse:
    items = FoodItem.objects.select_related("stall").order_by("name")
    return render(request, "attendance/manage/food_items.html", {"items": items})


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def manage_food_item_create(request: HttpRequest) -> HttpResponse:
    stalls = Stall.objects.filter(is_active=True)
    if request.method == "POST":
        name = request.POST.get("name")
        price = request.POST.get("price")
        category = request.POST.get("category")
        stall_id = request.POST.get("stall")
        if name and price and stall_id:
            stall = get_object_or_404(Stall, id=stall_id)
            FoodItem.objects.create(
                name=name,
                price=price,
                category=category or "",
                stall=stall,
                stall_name=stall.name,
                location=stall.location
            )
            messages.success(request, "Food item created.")
            return redirect("manage_food_items")
        messages.error(request, "Name, price, and stall are required.")
    return render(request, "attendance/manage/food_item_form.html", {"stalls": stalls, "title": "Add Food Item"})


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def manage_food_item_edit(request: HttpRequest, item_id: int) -> HttpResponse:
    item = get_object_or_404(FoodItem, id=item_id)
    stalls = Stall.objects.filter(is_active=True)
    if request.method == "POST":
        item.name = request.POST.get("name", item.name)
        item.price = request.POST.get("price", item.price)
        item.category = request.POST.get("category", item.category)
        stall_id = request.POST.get("stall")
        if stall_id:
            stall = get_object_or_404(Stall, id=stall_id)
            item.stall = stall
            item.stall_name = stall.name
            item.location = stall.location
        item.is_active = request.POST.get("is_active") == "on"
        item.save()
        messages.success(request, "Food item updated.")
        return redirect("manage_food_items")
    return render(request, "attendance/manage/food_item_form.html", {"item": item, "stalls": stalls, "title": "Edit Food Item"})


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def manage_food_item_delete(request: HttpRequest, item_id: int) -> HttpResponse:
    item = get_object_or_404(FoodItem, id=item_id)
    if request.method == "POST":
        item.delete()
        messages.success(request, "Food item deleted.")
        return redirect("manage_food_items")
    return render(request, "attendance/manage/confirm_delete.html", {"object": item, "type": "Food Item"})


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def manage_preorders(request: HttpRequest) -> HttpResponse:
    orders = PreOrder.objects.select_related("food_item", "slot", "ordered_by").order_by("-order_date", "-created_at")
    return render(request, "attendance/manage/preorders.html", {"orders": orders})


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def manage_bulk_orders(request: HttpRequest) -> HttpResponse:
    orders = BulkOrder.objects.select_related("slot").order_by("-created_at")
    return render(request, "attendance/manage/bulk_orders.html", {"orders": orders})


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def manage_loyalty_points(request: HttpRequest) -> HttpResponse:
    points = LoyaltyPoints.objects.select_related("user").order_by("-total_points")
    return render(request, "attendance/manage/loyalty_points.html", {"points": points})


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def manage_emergency_alerts(request: HttpRequest) -> HttpResponse:
    alerts = EmergencyAlert.objects.order_by("-created_at")
    return render(request, "attendance/manage/emergency_alerts.html", {"alerts": alerts})


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def manage_emergency_alert_create(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        title = request.POST.get("title")
        message = request.POST.get("message")
        severity = request.POST.get("severity", "medium")
        alert_type = request.POST.get("alert_type", "general")
        if title and message:
            EmergencyAlert.objects.create(
                title=title,
                message=message,
                severity=severity,
                alert_type=alert_type,
                is_active=True
            )
            messages.success(request, "Emergency alert created.")
            return redirect("manage_emergency_alerts")
        messages.error(request, "Title and message are required.")
    return render(request, "attendance/manage/emergency_alert_form.html", {"title": "Create Alert"})


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def manage_emergency_alert_toggle(request: HttpRequest, alert_id: int) -> HttpResponse:
    alert = get_object_or_404(EmergencyAlert, id=alert_id)
    alert.is_active = not alert.is_active
    alert.save()
    status = "activated" if alert.is_active else "deactivated"
    messages.success(request, f"Alert {status}.")
    return redirect("manage_emergency_alerts")


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def manage_emergency_alert_delete(request: HttpRequest, alert_id: int) -> HttpResponse:
    alert = get_object_or_404(EmergencyAlert, id=alert_id)
    if request.method == "POST":
        alert.delete()
        messages.success(request, "Alert deleted.")
        return redirect("manage_emergency_alerts")
@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_staff", False)))
def faculty_dashboard(request: HttpRequest) -> HttpResponse:
    """Faculty dashboard showing their assignments grouped by section."""
    # Get faculty profile for current user
    try:
        faculty = FacultyProfile.objects.get(user=request.user)
    except FacultyProfile.DoesNotExist:
        messages.error(request, "No faculty profile found. Please contact admin.")
        return redirect("home")
    
    # Get all offerings for this faculty
    offerings = (
        SectionCourseFaculty.objects.filter(faculty=faculty)
        .select_related("course", "section")
        .order_by("section__name", "course__code")
    )
    
    # Group by section
    sections_data = {}
    for offering in offerings:
        section_name = offering.section.name if offering.section else "No Section"
        if section_name not in sections_data:
            sections_data[section_name] = {
                "section": offering.section,
                "courses": []
            }
        sections_data[section_name]["courses"].append({
            "course": offering.course,
            "offering": offering
        })
    
    # Sort by section name
    sorted_sections = sorted(sections_data.items(), key=lambda x: x[0])
    
    return render(
        request,
        "attendance/faculty_dashboard.html",
        {
            "faculty": faculty,
            "sections": sorted_sections
        }
    )


# ==================== SCHEDULE VIEWS ====================

@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def schedule_list(request: HttpRequest) -> HttpResponse:
    """List all academic schedules with optional filters."""
    qs = Schedule.objects.select_related(
        "section_course_faculty__course",
        "section_course_faculty__faculty__user",
        "section_course_faculty__section",
        "classroom__block"
    ).order_by("day_of_week", "time_slot")
    
    # Get filter options
    sections = Section.objects.order_by("name")
    faculty_list = FacultyProfile.objects.filter(is_active=True).select_related("user").order_by("user__username")
    blocks = Block.objects.order_by("code")
    classrooms = Classroom.objects.select_related("block").order_by("block__code", "room_number")
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    
    # Apply filters
    section_filter = request.GET.get("section")
    faculty_filter = request.GET.get("faculty")
    day_filter = request.GET.get("day")
    block_filter = request.GET.get("block")
    classroom_filter = request.GET.get("classroom")
    
    if section_filter:
        qs = qs.filter(section_course_faculty__section_id=section_filter)
    if faculty_filter:
        qs = qs.filter(section_course_faculty__faculty_id=faculty_filter)
    if day_filter:
        qs = qs.filter(day_of_week=day_filter)
    if block_filter:
        qs = qs.filter(classroom__block_id=block_filter)
    if classroom_filter:
        qs = qs.filter(classroom_id=classroom_filter)
    
    return render(request, "attendance/manage/schedule_list.html", {
        "schedules": qs,
        "sections": sections,
        "faculty_list": faculty_list,
        "blocks": blocks,
        "classrooms": classrooms,
        "days": days,
        "filters": {
            "section": section_filter,
            "faculty": faculty_filter,
            "day": day_filter,
            "block": block_filter,
            "classroom": classroom_filter,
        }
    })


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def schedule_create(request: HttpRequest) -> HttpResponse:
    """Create a new schedule entry with clash prevention."""
    if request.method == "POST":
        form = ScheduleForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Schedule created successfully.")
            return redirect("schedule_list")
    else:
        form = ScheduleForm()
    
    return render(request, "attendance/manage/form.html", {
        "form": form,
        "title": "Add Schedule",
        "cancel_url": reverse("schedule_list"),
    })


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def schedule_delete(request: HttpRequest, schedule_id: int) -> HttpResponse:
    """Delete a schedule entry."""
    schedule = get_object_or_404(Schedule.objects.select_related(
        "section_course_faculty__course",
        "classroom__block"
    ), id=schedule_id)
    
    if request.method == "POST":
        schedule.delete()
        messages.success(request, "Schedule deleted successfully.")
        return redirect("schedule_list")
    
    return render(request, "attendance/manage/confirm_delete.html", {
        "object": schedule,
        "type": "Schedule",
        "cancel_url": "schedule_list",
    })


# ==================== FACULTY TIMETABLE VIEWS ====================

@login_required
def faculty_timetable(request: HttpRequest) -> HttpResponse:
    """Faculty views their weekly timetable with classroom allocation."""
    try:
        faculty = FacultyProfile.objects.get(user=request.user)
    except FacultyProfile.DoesNotExist:
        messages.error(request, "No faculty profile found.")
        return redirect("home")
    
    # Get all schedules for this faculty
    schedules = Schedule.objects.filter(
        section_course_faculty__faculty=faculty
    ).select_related(
        "section_course_faculty__course",
        "section_course_faculty__section",
        "classroom__block"
    ).order_by("day_of_week", "time_slot")
    
    # Group by day for timetable display
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    timetable = {day: [] for day in days}
    
    # Weekly load summary
    weekly_load = {
        "total_classes": schedules.count(),
        "classes_per_day": {day: 0 for day in days},
    }
    
    for s in schedules:
        timetable[s.day_of_week].append({
            "time_slot": s.get_time_slot_display(),
            "course_code": s.section_course_faculty.course.code,
            "course_name": s.section_course_faculty.course.name,
            "section": s.section_course_faculty.section.name if s.section_course_faculty.section else "-",
            "classroom": f"{s.classroom.block.code}-{s.classroom.room_number}",
            "schedule_id": s.id,
        })
        weekly_load["classes_per_day"][s.day_of_week] += 1
    
    # Get faculty's courses for booking dropdown
    faculty_courses = SectionCourseFaculty.objects.filter(
        faculty=faculty
    ).select_related("course", "section")

    classrooms = Classroom.objects.select_related("block").order_by("block__code", "room_number")

    # Ensure course offerings exist for assigned courses (so booking dropdown isn't empty)
    for scf in faculty_courses:
        existing_offering = CourseOffering.objects.filter(course=scf.course, section=scf.section).first()
        if existing_offering and existing_offering.faculty_id != faculty.id:
            continue
        CourseOffering.objects.get_or_create(
            course=scf.course,
            section=scf.section,
            defaults={"faculty": faculty, "is_active": True},
        )

    course_offerings = CourseOffering.objects.filter(
        faculty=faculty,
        is_active=True,
    ).select_related("course", "section").order_by("course__code", "section__name")

    booking_history = Schedule.objects.filter(
        created_by=request.user,
    ).select_related(
        "course_offering__course",
        "course_offering__section",
        "classroom__block",
        "section_course_faculty__course",
        "section_course_faculty__section",
    ).order_by("-created_at")
    
    return render(request, "attendance/faculty_timetable.html", {
        "timetable": timetable,
        "days": days,
        "faculty": faculty,
        "weekly_load": weekly_load,
        "time_slots": Schedule.TIME_SLOT_CHOICES,
        "faculty_courses": faculty_courses,
        "classrooms": classrooms,
        "booking_history": booking_history,
        "course_offerings": course_offerings,
    })


@login_required
def section_timetable(request: HttpRequest, section_id: int) -> HttpResponse:
    """View timetable for a specific section (faculty access)."""
    try:
        faculty = FacultyProfile.objects.get(user=request.user)
    except FacultyProfile.DoesNotExist:
        messages.error(request, "No faculty profile found.")
        return redirect("home")
    
    section = get_object_or_404(Section, id=section_id)
    
    # Check if faculty teaches this section
    teaches_section = SectionCourseFaculty.objects.filter(
        faculty=faculty, section=section
    ).exists()
    
    if not teaches_section and not request.user.is_superuser:
        messages.error(request, "You don't have access to this section's timetable.")
        return redirect("faculty_dashboard")
    
    schedules = Schedule.objects.filter(
        section_course_faculty__section=section
    ).select_related(
        "section_course_faculty__course",
        "section_course_faculty__faculty__user",
        "classroom__block"
    ).order_by("day_of_week", "time_slot")
    
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    timetable = {day: [] for day in days}
    
    for s in schedules:
        timetable[s.day_of_week].append({
            "time_slot": s.get_time_slot_display(),
            "course_code": s.section_course_faculty.course.code,
            "course_name": s.section_course_faculty.course.name,
            "faculty": s.section_course_faculty.faculty.user.get_full_name() or s.section_course_faculty.faculty.user.username,
            "classroom": f"{s.classroom.block.code}-{s.classroom.room_number}",
        })
    
    return render(request, "attendance/section_timetable.html", {
        "timetable": timetable,
        "days": days,
        "section": section,
    })


@login_required
def faculty_today_classes(request: HttpRequest) -> HttpResponse:
    """Quick view of today's classes for faculty with attendance links."""
    try:
        faculty = FacultyProfile.objects.get(user=request.user)
    except FacultyProfile.DoesNotExist:
        messages.error(request, "No faculty profile found.")
        return redirect("home")
    
    from datetime import datetime
    today = datetime.now().strftime("%A")
    
    # Get today's schedules
    today_schedules = Schedule.objects.filter(
        section_course_faculty__faculty=faculty,
        day_of_week=today
    ).select_related(
        "section_course_faculty__course",
        "section_course_faculty__section",
        "classroom__block"
    ).order_by("time_slot")
    
    classes = []
    for s in today_schedules:
        # Check if attendance session already exists
        existing_session = AttendanceSession.objects.filter(
            course_offering__course=s.section_course_faculty.course,
            section=s.section_course_faculty.section,
            faculty=faculty,
            created_at__date=datetime.now().date()
        ).first()
        
        classes.append({
            "time_slot": s.get_time_slot_display(),
            "course_code": s.section_course_faculty.course.code,
            "course_name": s.section_course_faculty.course.name,
            "section": s.section_course_faculty.section.name if s.section_course_faculty.section else "-",
            "classroom": f"{s.classroom.block.code}-{s.classroom.room_number}",
            "schedule_id": s.id,
            "attendance_session": existing_session,
            "can_take_attendance": existing_session is None,
        })
    
    return render(request, "attendance/faculty_today_classes.html", {
        "classes": classes,
        "today": today,
        "faculty": faculty,
    })


@login_required
@require_GET
def check_room_availability(request: HttpRequest) -> JsonResponse:
    selected_day = (request.GET.get("day") or "").strip()
    selected_slot = (request.GET.get("slot") or "").strip()
    selected_period = (request.GET.get("period") or "").strip()
    selected_start_time = (request.GET.get("start_time") or "").strip()
    classroom_id = (request.GET.get("room") or "").strip()

    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    allowed_days = set(days)
    allowed_slots = set(dict(Schedule.TIME_SLOT_CHOICES).keys())

    if not selected_day or not classroom_id or (not selected_slot and not selected_period and not selected_start_time):
        return JsonResponse({"ok": False, "error": "Missing parameters."}, status=400)

    if selected_day not in allowed_days:
        return JsonResponse({"ok": False, "error": "Invalid day."}, status=400)

    # Normalize to slot if period/start_time is provided
    if not selected_slot:
        if selected_period.isdigit():
            period_map = {
                1: "8am-9am", 2: "9am-10am", 3: "10am-11am", 4: "11am-12pm",
                5: "12pm-1pm", 6: "1pm-2pm", 7: "2pm-3pm", 8: "3pm-4pm",
                9: "4pm-5pm", 10: "5pm-6pm", 11: "6pm-7pm", 12: "7pm-8pm",
                13: "8pm-9pm", 14: "9pm-10pm",
            }
            selected_slot = period_map.get(int(selected_period), "")
        elif selected_start_time:
            start_map = {
                "08:00": "8am-9am", "09:00": "9am-10am", "10:00": "10am-11am", "11:00": "11am-12pm",
                "12:00": "12pm-1pm", "13:00": "1pm-2pm", "14:00": "2pm-3pm", "15:00": "3pm-4pm",
                "16:00": "4pm-5pm", "17:00": "5pm-6pm", "18:00": "6pm-7pm", "19:00": "7pm-8pm",
                "20:00": "8pm-9pm", "21:00": "9pm-10pm",
            }
            selected_slot = start_map.get(selected_start_time, "")

    if selected_slot not in allowed_slots:
        return JsonResponse({"ok": False, "error": "Invalid day or time slot."}, status=400)

    classroom = get_object_or_404(Classroom.objects.select_related("block"), id=classroom_id)

    booked = Schedule.objects.filter(
        classroom=classroom,
        day_of_week=selected_day,
        time_slot=selected_slot,
    ).select_related(
        "section_course_faculty__course",
        "section_course_faculty__section",
        "section_course_faculty__faculty__user",
        "classroom__block",
    ).first()

    if not booked:
        return JsonResponse({
            "ok": True,
            "available": True,
            "room": {
                "id": classroom.id,
                "label": f"{classroom.block.code}-{classroom.room_number}",
            },
            "day": selected_day,
            "slot": dict(Schedule.TIME_SLOT_CHOICES).get(selected_slot, selected_slot),
        })

    faculty_user = booked.section_course_faculty.faculty.user
    faculty_name = faculty_user.get_full_name() or faculty_user.username

    return JsonResponse({
        "ok": True,
        "available": False,
        "day": selected_day,
        "slot": booked.get_time_slot_display(),
        "booked": {
            "schedule_id": booked.id,
            "course_code": booked.section_course_faculty.course.code,
            "course_name": booked.section_course_faculty.course.name,
            "section": booked.section_course_faculty.section.name if booked.section_course_faculty.section else "-",
            "faculty": faculty_name,
            "room": f"{classroom.block.code}-{classroom.room_number}",
        },
    })


def _slot_to_times(slot: str):
    from datetime import time

    slot_map = {
        "8am-9am": (1, time(8, 0), time(9, 0)),
        "9am-10am": (2, time(9, 0), time(10, 0)),
        "10am-11am": (3, time(10, 0), time(11, 0)),
        "11am-12pm": (4, time(11, 0), time(12, 0)),
        "12pm-1pm": (5, time(12, 0), time(13, 0)),
        "1pm-2pm": (6, time(13, 0), time(14, 0)),
        "2pm-3pm": (7, time(14, 0), time(15, 0)),
        "3pm-4pm": (8, time(15, 0), time(16, 0)),
        "4pm-5pm": (9, time(16, 0), time(17, 0)),
        "5pm-6pm": (10, time(17, 0), time(18, 0)),
        "6pm-7pm": (11, time(18, 0), time(19, 0)),
        "7pm-8pm": (12, time(19, 0), time(20, 0)),
        "8pm-9pm": (13, time(20, 0), time(21, 0)),
        "9pm-10pm": (14, time(21, 0), time(22, 0)),
    }
    return slot_map.get(slot)


@login_required
@require_POST
def book_room(request: HttpRequest) -> HttpResponse:
    """Teacher books a classroom slot; persists Schedule with clash prevention."""
    try:
        faculty = FacultyProfile.objects.get(user=request.user)
    except FacultyProfile.DoesNotExist:
        messages.error(request, "No faculty profile found.")
        return redirect("home")

    day = (request.POST.get("day") or "").strip()
    slot = (request.POST.get("slot") or "").strip()
    room_id = (request.POST.get("room") or "").strip()
    offering_id = (request.POST.get("course_offering") or "").strip()

    if not all([day, slot, room_id, offering_id]):
        messages.error(request, "All fields are required.")
        return redirect("faculty_timetable")

    allowed_days = {"Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"}
    if day not in allowed_days:
        messages.error(request, "Invalid day.")
        return redirect("faculty_timetable")

    allowed_slots = set(dict(Schedule.TIME_SLOT_CHOICES).keys())
    if slot not in allowed_slots:
        messages.error(request, "Invalid time slot.")
        return redirect("faculty_timetable")

    # Teacher restriction
    try:
        offering = CourseOffering.objects.select_related("course", "section").get(id=offering_id, faculty=faculty)
    except CourseOffering.DoesNotExist:
        messages.error(request, "Invalid course offering.")
        return redirect("faculty_timetable")

    classroom = get_object_or_404(Classroom.objects.select_related("block"), id=room_id)

    # Keep existing timetable linkage
    try:
        scf = SectionCourseFaculty.objects.get(course=offering.course, section=offering.section, faculty=faculty)
    except SectionCourseFaculty.DoesNotExist:
        messages.error(request, "Course assignment missing. Contact admin to assign your course-section.")
        return redirect("faculty_timetable")

    # Clash prevention
    if Schedule.objects.filter(day_of_week=day, time_slot=slot, classroom=classroom).exists():
        messages.error(request, "Room already booked")
        return redirect("faculty_timetable")

    if Schedule.objects.filter(day_of_week=day, time_slot=slot, section_course_faculty__faculty=faculty).exists():
        messages.error(request, "You already have class at this time")
        return redirect("faculty_timetable")

    if offering.section and Schedule.objects.filter(day_of_week=day, time_slot=slot, section_course_faculty__section=offering.section).exists():
        messages.error(request, "This section already has a class at this time")
        return redirect("faculty_timetable")

    slot_info = _slot_to_times(slot)
    period_number = slot_info[0] if slot_info else None
    start_time = slot_info[1] if slot_info else None
    end_time = slot_info[2] if slot_info else None

    Schedule.objects.create(
        section_course_faculty=scf,
        course_offering=offering,
        classroom=classroom,
        day_of_week=day,
        time_slot=slot,
        period_number=period_number,
        start_time=start_time,
        end_time=end_time,
        created_by=request.user,
    )

    messages.success(request, "Slot booked successfully.")
    return redirect("faculty_timetable")


@login_required
@require_POST
def book_room_ajax(request: HttpRequest) -> JsonResponse:
    try:
        faculty = FacultyProfile.objects.get(user=request.user)
    except FacultyProfile.DoesNotExist:
        return JsonResponse({"ok": False, "error": "No faculty profile found."}, status=400)

    day_of_week = (request.POST.get("day") or "").strip()
    time_slot = (request.POST.get("slot") or "").strip()
    classroom_id = (request.POST.get("room") or "").strip()
    scf_id = (request.POST.get("section_course_faculty") or "").strip()

    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    allowed_days = set(days)
    allowed_slots = set(dict(Schedule.TIME_SLOT_CHOICES).keys())

    if not all([day_of_week, time_slot, classroom_id, scf_id]):
        return JsonResponse({"ok": False, "error": "All fields are required."}, status=400)

    if day_of_week not in allowed_days or time_slot not in allowed_slots:
        return JsonResponse({"ok": False, "error": "Invalid day or time slot."}, status=400)

    try:
        scf = SectionCourseFaculty.objects.select_related("course", "section").get(id=scf_id, faculty=faculty)
    except SectionCourseFaculty.DoesNotExist:
        return JsonResponse({"ok": False, "error": "Invalid course assignment."}, status=403)

    classroom = get_object_or_404(Classroom, id=classroom_id)

    if Schedule.objects.filter(day_of_week=day_of_week, time_slot=time_slot, classroom=classroom).exists():
        return JsonResponse({"ok": False, "error": "Room already booked"}, status=409)

    if Schedule.objects.filter(day_of_week=day_of_week, time_slot=time_slot, section_course_faculty__faculty=faculty).exists():
        return JsonResponse({"ok": False, "error": "You already have class at this time"}, status=409)

    if scf.section and Schedule.objects.filter(day_of_week=day_of_week, time_slot=time_slot, section_course_faculty__section=scf.section).exists():
        return JsonResponse({"ok": False, "error": "This section already has a class at this time"}, status=409)

    schedule = Schedule.objects.create(
        section_course_faculty=scf,
        classroom=classroom,
        day_of_week=day_of_week,
        time_slot=time_slot,
    )

    return JsonResponse({
        "ok": True,
        "created": True,
        "schedule_id": schedule.id,
    })


@login_required
def mark_attendance_quick(request: HttpRequest, schedule_id: int) -> HttpResponse:
    """Quick attendance marking from schedule - auto-creates session."""
    try:
        faculty = FacultyProfile.objects.get(user=request.user)
    except FacultyProfile.DoesNotExist:
        messages.error(request, "No faculty profile found.")
        return redirect("home")
    
    from datetime import datetime
    
    schedule = get_object_or_404(
        Schedule.objects.select_related(
            "section_course_faculty__course",
            "section_course_faculty__section"
        ),
        id=schedule_id,
        section_course_faculty__faculty=faculty
    )
    
    scf = schedule.section_course_faculty
    
    # Check if session already exists for today
    existing = AttendanceSession.objects.filter(
        course_offering__course=scf.course,
        section=scf.section,
        faculty=faculty,
        created_at__date=datetime.now().date()
    ).first()
    
    if existing:
        return redirect("mark_attendance", session_id=existing.id)
    
    # Find or create course offering
    offering, _ = CourseOffering.objects.get_or_create(
        course=scf.course,
        faculty=faculty,
        section=scf.section,
        defaults={"is_active": True}
    )
    
    # Create new attendance session
    session = AttendanceSession.objects.create(
        course_offering=offering,
        section=scf.section,
        faculty=faculty,
        scheduled_date=datetime.now().date()
    )
    
    messages.success(request, f"Attendance session created for {scf.course.code} - {schedule.get_time_slot_display()}")
    return redirect("mark_attendance", session_id=session.id)


@login_required
def faculty_book_room(request: HttpRequest) -> HttpResponse:
    """Faculty books a classroom for their course."""
    try:
        faculty = FacultyProfile.objects.get(user=request.user)
    except FacultyProfile.DoesNotExist:
        messages.error(request, "No faculty profile found.")
        return redirect("home")
    
    if request.method == "POST":
        classroom_id = request.POST.get("classroom")
        day_of_week = request.POST.get("day_of_week")
        time_slot = request.POST.get("time_slot")
        section_course_faculty_id = request.POST.get("section_course_faculty")
        
        if not all([classroom_id, day_of_week, time_slot, section_course_faculty_id]):
            messages.error(request, "All fields are required.")
            return redirect("faculty_timetable")
        
        # Verify the faculty owns this section_course_faculty
        try:
            scf = SectionCourseFaculty.objects.get(
                id=section_course_faculty_id,
                faculty=faculty
            )
        except SectionCourseFaculty.DoesNotExist:
            messages.error(request, "Invalid course assignment.")
            return redirect("faculty_timetable")
        
        # Check for room clash
        existing = Schedule.objects.filter(
            classroom_id=classroom_id,
            day_of_week=day_of_week,
            time_slot=time_slot
        ).first()
        
        if existing:
            messages.error(request, "This room is already booked for this time slot.")
            return redirect("faculty_timetable")
        
        # Check for faculty clash
        faculty_clash = Schedule.objects.filter(
            section_course_faculty__faculty=faculty,
            day_of_week=day_of_week,
            time_slot=time_slot
        ).first()
        
        if faculty_clash:
            messages.error(request, "You already have a class at this time.")
            return redirect("faculty_timetable")
        
        # Create the schedule
        Schedule.objects.create(
            section_course_faculty=scf,
            classroom_id=classroom_id,
            day_of_week=day_of_week,
            time_slot=time_slot
        )
        
        messages.success(request, f"Room booked successfully for {scf.course.code} on {day_of_week} at {dict(Schedule.TIME_SLOT_CHOICES).get(time_slot, time_slot)}")
        return redirect("faculty_timetable")
    
    # GET request - show booking form
    day = request.GET.get("day")
    slot = request.GET.get("slot")
    classroom_id = request.GET.get("classroom")
    
    # Get faculty's courses
    faculty_courses = SectionCourseFaculty.objects.filter(
        faculty=faculty
    ).select_related("course", "section")
    
    # Get available classrooms for the selected time
    available_classrooms = None
    if day and slot:
        busy_rooms = Schedule.objects.filter(
            day_of_week=day,
            time_slot=slot
        ).values_list("classroom_id", flat=True)
        
        available_classrooms = Classroom.objects.exclude(
            id__in=busy_rooms
        ).select_related("block").order_by("block__code", "room_number")
    
    return render(request, "attendance/faculty_book_room.html", {
        "faculty_courses": faculty_courses,
        "available_classrooms": available_classrooms,
        "day": day,
        "slot": slot,
        "classroom_id": classroom_id,
        "days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
        "time_slots": Schedule.TIME_SLOT_CHOICES,
    })
    
    if existing:
        return redirect("mark_attendance", session_id=existing.id)
    
    # Find or create course offering
    offering, _ = CourseOffering.objects.get_or_create(
        course=scf.course,
        faculty=faculty,
        section=scf.section,
        defaults={"is_active": True}
    )
    
    # Create new attendance session
    session = AttendanceSession.objects.create(
        course_offering=offering,
        section=scf.section,
        faculty=faculty,
        scheduled_date=datetime.now().date()
    )
    
    messages.success(request, f"Attendance session created for {scf.course.code} - {schedule.get_time_slot_display()}")
    return redirect("mark_attendance", session_id=session.id)


@login_required
def faculty_book_room(request: HttpRequest) -> HttpResponse:
    """Faculty books a classroom for their course."""
    try:
        faculty = FacultyProfile.objects.get(user=request.user)
    except FacultyProfile.DoesNotExist:
        messages.error(request, "No faculty profile found.")
        return redirect("home")
    
    if request.method == "POST":
        classroom_id = request.POST.get("classroom")
        day_of_week = request.POST.get("day_of_week")
        time_slot = request.POST.get("time_slot")
        section_course_faculty_id = request.POST.get("section_course_faculty")
        
        if not all([classroom_id, day_of_week, time_slot, section_course_faculty_id]):
            messages.error(request, "All fields are required.")
            return redirect("faculty_timetable")
        
        # Verify the faculty owns this section_course_faculty
        try:
            scf = SectionCourseFaculty.objects.get(
                id=section_course_faculty_id,
                faculty=faculty
            )
        except SectionCourseFaculty.DoesNotExist:
            messages.error(request, "Invalid course assignment.")
            return redirect("faculty_timetable")
        
        # Check for room clash
        existing = Schedule.objects.filter(
            classroom_id=classroom_id,
            day_of_week=day_of_week,
            time_slot=time_slot
        ).first()
        
        if existing:
            messages.error(request, "This room is already booked for this time slot.")
            return redirect("faculty_timetable")
        
        # Check for faculty clash
        faculty_clash = Schedule.objects.filter(
            section_course_faculty__faculty=faculty,
            day_of_week=day_of_week,
            time_slot=time_slot
        ).first()
        
        if faculty_clash:
            messages.error(request, "You already have a class at this time.")
            return redirect("faculty_timetable")
        
        # Create the schedule
        Schedule.objects.create(
            section_course_faculty=scf,
            classroom_id=classroom_id,
            day_of_week=day_of_week,
            time_slot=time_slot
        )
        
        messages.success(request, f"Room booked successfully for {scf.course.code} on {day_of_week} at {dict(Schedule.TIME_SLOT_CHOICES).get(time_slot, time_slot)}")
        return redirect("faculty_timetable")
    
    # GET request - show booking form
    day = request.GET.get("day")
    slot = request.GET.get("slot")
    classroom_id = request.GET.get("classroom")
    
    # Get faculty's courses
    faculty_courses = SectionCourseFaculty.objects.filter(
        faculty=faculty
    ).select_related("course", "section")
    
    # Get available classrooms for the selected time
    available_classrooms = None
    if day and slot:
        busy_rooms = Schedule.objects.filter(
            day_of_week=day,
            time_slot=slot
        ).values_list("classroom_id", flat=True)
        
        available_classrooms = Classroom.objects.exclude(
            id__in=busy_rooms
        ).select_related("block").order_by("block__code", "room_number")
    
    return render(request, "attendance/faculty_book_room.html", {
        "faculty_courses": faculty_courses,
        "available_classrooms": available_classrooms,
        "day": day,
        "slot": slot,
        "classroom_id": classroom_id,
        "days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
        "time_slots": Schedule.TIME_SLOT_CHOICES,
    })


# ==================== MAKE-UP CLASS & REMEDIAL CODE MODULE ====================


@login_required
def faculty_makeup_classes(request: HttpRequest) -> HttpResponse:
    """Faculty dashboard for managing make-up classes."""
    try:
        faculty = FacultyProfile.objects.get(user=request.user)
    except FacultyProfile.DoesNotExist:
        messages.error(request, "No faculty profile found.")
        return redirect("home")
    
    makeup_classes = MakeUpClass.objects.filter(
        faculty=faculty
    ).select_related("course", "section", "classroom", "classroom__block").order_by("-session_date", "time_slot")
    
    assigned_courses = SectionCourseFaculty.objects.filter(
        faculty=faculty
    ).select_related("course", "section")
    
    return render(request, "attendance/faculty_makeup_classes.html", {
        "makeup_classes": makeup_classes,
        "assigned_courses": assigned_courses,
    })


@login_required
def makeup_class_create(request: HttpRequest) -> HttpResponse:
    """Faculty schedules a new make-up class with remedial code generation."""
    try:
        faculty = FacultyProfile.objects.get(user=request.user)
    except FacultyProfile.DoesNotExist:
        messages.error(request, "No faculty profile found.")
        return redirect("home")
    
    if request.method == "POST":
        form = MakeUpClassForm(request.POST, faculty=faculty)
        if form.is_valid():
            makeup_class = form.save(commit=False)
            makeup_class.faculty = faculty
            makeup_class.save()
            messages.success(request, f"Make-up class scheduled! Remedial Code: {makeup_class.remedial_code}")
            return redirect("faculty_makeup_classes")
    else:
        form = MakeUpClassForm(faculty=faculty)
    
    return render(request, "attendance/makeup_class_form.html", {
        "form": form,
        "title": "Schedule Make-Up Class",
        "cancel_url": reverse("faculty_makeup_classes"),
    })


@login_required
def makeup_class_detail(request: HttpRequest, makeup_class_id: int) -> HttpResponse:
    """View make-up class details including remedial code."""
    try:
        faculty = FacultyProfile.objects.get(user=request.user)
    except FacultyProfile.DoesNotExist:
        messages.error(request, "No faculty profile found.")
        return redirect("home")
    
    makeup_class = get_object_or_404(
        MakeUpClass.objects.select_related("course", "section", "classroom", "classroom__block"),
        id=makeup_class_id, faculty=faculty
    )
    
    attendance_summary = {
        "total_present": MakeUpAttendanceRecord.objects.filter(
            makeup_class=makeup_class, status=AttendanceRecord.STATUS_PRESENT
        ).count(),
        "total_absent": MakeUpAttendanceRecord.objects.filter(
            makeup_class=makeup_class, status=AttendanceRecord.STATUS_ABSENT
        ).count(),
    }
    
    return render(request, "attendance/makeup_class_detail.html", {
        "makeup_class": makeup_class,
        "attendance_summary": attendance_summary,
    })


@login_required
def makeup_class_cancel(request: HttpRequest, makeup_class_id: int) -> HttpResponse:
    """Cancel a scheduled make-up class."""
    try:
        faculty = FacultyProfile.objects.get(user=request.user)
    except FacultyProfile.DoesNotExist:
        messages.error(request, "No faculty profile found.")
        return redirect("home")
    
    makeup_class = get_object_or_404(
        MakeUpClass, id=makeup_class_id, faculty=faculty,
        status__in=[MakeUpClass.STATUS_SCHEDULED, MakeUpClass.STATUS_IN_PROGRESS]
    )
    
    if request.method == "POST":
        makeup_class.status = MakeUpClass.STATUS_CANCELLED
        makeup_class.save()
        messages.success(request, "Make-up class cancelled.")
        return redirect("faculty_makeup_classes")
    
    return render(request, "attendance/makeup_class_cancel.html", {"makeup_class": makeup_class})


@login_required
def makeup_class_start(request: HttpRequest, makeup_class_id: int) -> HttpResponse:
    """Start a make-up class session."""
    try:
        faculty = FacultyProfile.objects.get(user=request.user)
    except FacultyProfile.DoesNotExist:
        messages.error(request, "No faculty profile found.")
        return redirect("home")
    
    makeup_class = get_object_or_404(
        MakeUpClass, id=makeup_class_id, faculty=faculty, status=MakeUpClass.STATUS_SCHEDULED
    )
    
    makeup_class.status = MakeUpClass.STATUS_IN_PROGRESS
    makeup_class.save()
    messages.success(request, f"Class started! Remedial Code: {makeup_class.remedial_code}")
    return redirect("makeup_class_detail", makeup_class_id=makeup_class.id)


@login_required
def makeup_class_complete(request: HttpRequest, makeup_class_id: int) -> HttpResponse:
    """Complete a make-up class session."""
    try:
        faculty = FacultyProfile.objects.get(user=request.user)
    except FacultyProfile.DoesNotExist:
        messages.error(request, "No faculty profile found.")
        return redirect("home")
    
    makeup_class = get_object_or_404(
        MakeUpClass, id=makeup_class_id, faculty=faculty,
        status__in=[MakeUpClass.STATUS_SCHEDULED, MakeUpClass.STATUS_IN_PROGRESS]
    )
    
    makeup_class.status = MakeUpClass.STATUS_COMPLETED
    makeup_class.save()
    messages.success(request, "Make-up class completed.")
    return redirect("faculty_makeup_classes")


# ==================== AI SMART SCHEDULING ====================


@login_required
def smart_scheduling_recommendations(request: HttpRequest) -> HttpResponse:
    """AI-powered scheduling recommendations for faculty."""
    try:
        faculty = FacultyProfile.objects.get(user=request.user)
    except FacultyProfile.DoesNotExist:
        messages.error(request, "No faculty profile found.")
        return redirect("home")
    
    recommendations = []
    if request.method == "POST":
        form = SmartSchedulingForm(request.POST)
        if form.is_valid():
            recommendations = _generate_smart_recommendations(
                faculty,
                form.cleaned_data.get("preferred_date"),
                form.cleaned_data.get("preferred_time_slot"),
                form.cleaned_data.get("prioritize_low_traffic", True)
            )
    else:
        form = SmartSchedulingForm()
    
    return render(request, "attendance/smart_scheduling.html", {
        "form": form,
        "recommendations": recommendations,
    })


def _generate_smart_recommendations(faculty, preferred_date=None, preferred_slot=None, prioritize_low_traffic=True):
    """Generate AI scheduling recommendations."""
    from datetime import timedelta
    
    recommendations = []
    base_date = timezone.localdate()
    days_to_check = [base_date + timedelta(days=i) for i in range(1, 8)]
    
    faculty_schedule = Schedule.objects.filter(
        section_course_faculty__faculty=faculty
    ).values_list("day_of_week", "time_slot")
    faculty_schedule_dict = {}
    for day, slot in faculty_schedule:
        faculty_schedule_dict.setdefault(day, set()).add(slot)
    
    traffic_analysis = _analyze_traffic_patterns()
    
    for day in days_to_check:
        day_name = day.strftime("%A")
        if day_name not in [c[0] for c in Schedule.DAY_CHOICES]:
            continue
        
        for slot_code, slot_display in Schedule.TIME_SLOT_CHOICES:
            if preferred_slot and slot_code != preferred_slot:
                continue
            if day_name in faculty_schedule_dict and slot_code in faculty_schedule_dict.get(day_name, set()):
                continue
            
            busy = Schedule.objects.filter(day_of_week=day_name, time_slot=slot_code).values_list("classroom_id", flat=True)
            makeup_busy = MakeUpClass.objects.filter(
                session_date=day, time_slot=slot_code,
                status__in=[MakeUpClass.STATUS_SCHEDULED, MakeUpClass.STATUS_IN_PROGRESS]
            ).values_list("classroom_id", flat=True)
            
            available = Classroom.objects.exclude(id__in=list(busy) + list(makeup_busy)).filter(is_active=True)
            if not available.exists():
                continue
            
            rush_score = traffic_analysis.get(slot_code, 50)
            score = (100 - rush_score) if prioritize_low_traffic else 50
            days_until = (day - base_date).days
            score += max(0, 10 - days_until)
            
            recommendations.append({
                "date": day,
                "day_name": day_name,
                "time_slot": slot_code,
                "time_display": slot_display,
                "rush_score": rush_score,
                "available_classrooms": list(available[:3]),
                "score": round(score, 1),
                "reason": f"In {days_until} days, {'low' if rush_score < 30 else 'moderate' if rush_score < 60 else 'high'} traffic",
            })
    
    recommendations.sort(key=lambda x: x["score"], reverse=True)
    return recommendations[:10]


def _analyze_traffic_patterns():
    """Analyze traffic patterns for rush prediction."""
    schedule_counts = Schedule.objects.values("time_slot").annotate(count=Count("id"))
    max_count = max([s["count"] for s in schedule_counts], default=1)
    
    traffic_scores = {}
    for slot in Schedule.TIME_SLOT_CHOICES:
        slot_code = slot[0]
        count = next((s["count"] for s in schedule_counts if s["time_slot"] == slot_code), 0)
        score = (count / max_count) * 60 if max_count > 0 else 0
        
        if slot_code in ["9am-10am", "10am-11am", "11am-12pm", "2pm-3pm"]:
            score += 20
        if slot_code in ["12pm-1pm", "1pm-2pm"]:
            score += 40
        
        traffic_scores[slot_code] = min(100, score)
    
    return traffic_scores


@login_required
def class_rush_prediction(request: HttpRequest) -> HttpResponse:
    """View class rush prediction and congestion analysis."""
    try:
        faculty = FacultyProfile.objects.get(user=request.user)
    except FacultyProfile.DoesNotExist:
        messages.error(request, "No faculty profile found.")
        return redirect("home")
    
    traffic_analysis = _analyze_traffic_patterns()
    today = timezone.localdate()
    today_name = today.strftime("%A")
    
    today_regular = Schedule.objects.filter(day_of_week=today_name).values("time_slot").annotate(count=Count("id"))
    today_makeup = MakeUpClass.objects.filter(
        session_date=today,
        status__in=[MakeUpClass.STATUS_SCHEDULED, MakeUpClass.STATUS_IN_PROGRESS]
    ).values("time_slot").annotate(count=Count("id"))
    
    today_rush = {}
    for slot in Schedule.TIME_SLOT_CHOICES:
        slot_code = slot[0]
        regular = next((s["count"] for s in today_regular if s["time_slot"] == slot_code), 0)
        makeup = next((s["count"] for s in today_makeup if s["time_slot"] == slot_code), 0)
        today_rush[slot_code] = {
            "predicted": traffic_analysis.get(slot_code, 0),
            "actual_regular": regular,
            "actual_makeup": makeup,
            "total_actual": regular + makeup,
        }
    
    sorted_slots = sorted(today_rush.items(), key=lambda x: x[1]["total_actual"], reverse=True)
    peak_slots = sorted_slots[:3]
    off_peak_slots = sorted_slots[-3:]
    
    return render(request, "attendance/class_rush_prediction.html", {
        "traffic_analysis": traffic_analysis,
        "today_rush": today_rush,
        "peak_slots": peak_slots,
        "off_peak_slots": off_peak_slots,
        "today": today,
        "time_slots": Schedule.TIME_SLOT_CHOICES,
    })


# ==================== ADMIN MAKE-UP CLASS MANAGEMENT ====================


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def admin_makeup_classes(request: HttpRequest) -> HttpResponse:
    """Admin monitor for all make-up classes across faculty."""
    status_filter = request.GET.get("status", "")
    faculty_id = request.GET.get("faculty_id", "")
    date_from = request.GET.get("date_from", "")
    date_to = request.GET.get("date_to", "")
    
    makeup_classes = MakeUpClass.objects.all().select_related(
        "faculty", "faculty__user", "course", "section", "classroom", "classroom__block"
    ).order_by("-session_date", "time_slot")
    
    if status_filter:
        makeup_classes = makeup_classes.filter(status=status_filter)
    if faculty_id and faculty_id.isdigit():
        makeup_classes = makeup_classes.filter(faculty_id=int(faculty_id))
    if date_from:
        makeup_classes = makeup_classes.filter(session_date__gte=date_from)
    if date_to:
        makeup_classes = makeup_classes.filter(session_date__lte=date_to)
    
    # Statistics
    total_classes = MakeUpClass.objects.count()
    scheduled_count = MakeUpClass.objects.filter(status=MakeUpClass.STATUS_SCHEDULED).count()
    in_progress_count = MakeUpClass.objects.filter(status=MakeUpClass.STATUS_IN_PROGRESS).count()
    completed_count = MakeUpClass.objects.filter(status=MakeUpClass.STATUS_COMPLETED).count()
    cancelled_count = MakeUpClass.objects.filter(status=MakeUpClass.STATUS_CANCELLED).count()
    
    # Today's classes
    today = timezone.localdate()
    today_classes = MakeUpClass.objects.filter(
        session_date=today
    ).select_related("faculty", "faculty__user", "course", "section").order_by("time_slot")
    
    faculty_list = FacultyProfile.objects.filter(is_active=True).select_related("user").order_by("user__username")
    
    return render(request, "attendance/manage/admin_makeup_classes.html", {
        "makeup_classes": makeup_classes,
        "faculty_list": faculty_list,
        "filters": {
            "status": status_filter,
            "faculty_id": faculty_id,
            "date_from": date_from,
            "date_to": date_to,
        },
        "stats": {
            "total": total_classes,
            "scheduled": scheduled_count,
            "in_progress": in_progress_count,
            "completed": completed_count,
            "cancelled": cancelled_count,
        },
        "today_classes": today_classes,
        "today": today,
    })


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def admin_makeup_class_detail(request: HttpRequest, makeup_class_id: int) -> HttpResponse:
    """Admin view for make-up class details."""
    makeup_class = get_object_or_404(
        MakeUpClass.objects.select_related(
            "faculty", "faculty__user", "course", "section", "classroom", "classroom__block"
        ),
        id=makeup_class_id
    )
    
    # Get attendance records
    attendance_records = MakeUpAttendanceRecord.objects.filter(
        makeup_class=makeup_class
    ).select_related("student").order_by("student__registration_number")
    
    attendance_summary = {
        "total_present": attendance_records.filter(status=AttendanceRecord.STATUS_PRESENT).count(),
        "total_absent": attendance_records.filter(status=AttendanceRecord.STATUS_ABSENT).count(),
        "total_excused": attendance_records.filter(status=AttendanceRecord.STATUS_EXCUSED).count(),
        "total": attendance_records.count(),
    }
    
    return render(request, "attendance/manage/admin_makeup_class_detail.html", {
        "makeup_class": makeup_class,
        "attendance_records": attendance_records,
        "attendance_summary": attendance_summary,
    })


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def admin_makeup_class_cancel(request: HttpRequest, makeup_class_id: int) -> HttpResponse:
    """Admin cancels a make-up class."""
    makeup_class = get_object_or_404(
        MakeUpClass,
        id=makeup_class_id,
        status__in=[MakeUpClass.STATUS_SCHEDULED, MakeUpClass.STATUS_IN_PROGRESS]
    )
    
    if request.method == "POST":
        reason = request.POST.get("reason", "")
        makeup_class.status = MakeUpClass.STATUS_CANCELLED
        makeup_class.save()
        
        # Send notification to faculty
        Notification.objects.create(
            recipient_faculty=makeup_class.faculty,
            title="Make-Up Class Cancelled by Admin",
            message=f"Your make-up class for {makeup_class.course.code} on {makeup_class.session_date} has been cancelled by admin. Reason: {reason}",
        )
        
        messages.success(request, f"Make-up class cancelled. Faculty notified.")
        return redirect("admin_makeup_classes")
    
    return render(request, "attendance/manage/admin_makeup_class_cancel.html", {
        "makeup_class": makeup_class,
    })


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def admin_makeup_class_stats(request: HttpRequest) -> HttpResponse:
    """Statistics report for make-up classes."""
    from django.db.models import Count, Q
    
    # Faculty-wise statistics
    faculty_stats = []
    for faculty in FacultyProfile.objects.filter(is_active=True).select_related("user"):
        classes = MakeUpClass.objects.filter(faculty=faculty)
        faculty_stats.append({
            "faculty": faculty,
            "total": classes.count(),
            "scheduled": classes.filter(status=MakeUpClass.STATUS_SCHEDULED).count(),
            "in_progress": classes.filter(status=MakeUpClass.STATUS_IN_PROGRESS).count(),
            "completed": classes.filter(status=MakeUpClass.STATUS_COMPLETED).count(),
            "cancelled": classes.filter(status=MakeUpClass.STATUS_CANCELLED).count(),
        })
    
    # Sort by total classes
    faculty_stats.sort(key=lambda x: x["total"], reverse=True)
    
    # Time slot popularity
    time_slot_stats = MakeUpClass.objects.values("time_slot").annotate(
        count=Count("id")
    ).order_by("-count")
    
    # Add display names
    for stat in time_slot_stats:
        stat["display"] = dict(Schedule.TIME_SLOT_CHOICES).get(stat["time_slot"], stat["time_slot"])
    
    # Course-wise statistics
    course_stats = MakeUpClass.objects.values("course__code", "course__name").annotate(
        count=Count("id")
    ).order_by("-count")[:10]
    
    # Monthly trend (last 6 months)
    from datetime import timedelta
    monthly_stats = []
    for i in range(5, -1, -1):
        month_start = (timezone.localdate() - timedelta(days=30*i)).replace(day=1)
        month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        count = MakeUpClass.objects.filter(
            created_at__date__gte=month_start,
            created_at__date__lte=month_end
        ).count()
        monthly_stats.append({
            "month": month_start.strftime("%b %Y"),
            "count": count,
        })
    
    return render(request, "attendance/manage/admin_makeup_stats.html", {
        "faculty_stats": faculty_stats,
        "time_slot_stats": time_slot_stats,
        "course_stats": course_stats,
        "monthly_stats": monthly_stats,
    })


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def admin_remedial_code_audit(request: HttpRequest) -> HttpResponse:
    """Audit view for remedial codes."""
    status_filter = request.GET.get("status", "active")
    
    if status_filter == "active":
        makeup_classes = MakeUpClass.objects.filter(
            status__in=[MakeUpClass.STATUS_SCHEDULED, MakeUpClass.STATUS_IN_PROGRESS]
        )
    elif status_filter == "expired":
        makeup_classes = MakeUpClass.objects.filter(
            status__in=[MakeUpClass.STATUS_COMPLETED, MakeUpClass.STATUS_CANCELLED]
        )
    else:
        makeup_classes = MakeUpClass.objects.all()
    
    makeup_classes = makeup_classes.select_related(
        "faculty", "faculty__user", "course", "section"
    ).order_by("-session_date")
    
    return render(request, "attendance/manage/admin_remedial_audit.html", {
        "makeup_classes": makeup_classes,
        "status_filter": status_filter,
    })


# ==================== FACULTY MAKE-UP CLASS ATTENDANCE ====================


@login_required
def makeup_class_attendance(request: HttpRequest, makeup_class_id: int) -> HttpResponse:
    """Faculty marks attendance for make-up class."""
    try:
        faculty = FacultyProfile.objects.get(user=request.user)
    except FacultyProfile.DoesNotExist:
        messages.error(request, "No faculty profile found.")
        return redirect("home")
    
    makeup_class = get_object_or_404(
        MakeUpClass.objects.select_related("section", "course"),
        id=makeup_class_id,
        faculty=faculty,
        status__in=[MakeUpClass.STATUS_SCHEDULED, MakeUpClass.STATUS_IN_PROGRESS]
    )
    
    # Get students in the section
    students = Student.objects.filter(
        section_mapping__section=makeup_class.section
    ).order_by("registration_number")
    
    if request.method == "POST":
        attendance_data = request.POST.getlist("attendance")
        absent_students = []  # Track absent students for email notification
        
        for student in students:
            status_key = f"status_{student.id}"
            status = request.POST.get(status_key, AttendanceRecord.STATUS_ABSENT)
            
            MakeUpAttendanceRecord.objects.update_or_create(
                makeup_class=makeup_class,
                student=student,
                defaults={
                    "status": status,
                    "marked_by": faculty.user,
                    "marked_via": MakeUpAttendanceRecord.VIA_FACULTY,
                }
            )
            
            # Track absent students for email notification
            if status == AttendanceRecord.STATUS_ABSENT:
                absent_students.append(student)
        
        # Send email notifications to absent students
        if absent_students:
            from django.core.mail import send_mass_mail
            from django.conf import settings
            
            email_messages = []
            for student in absent_students:
                if student.email:
                    subject = f"Attendance Alert: {makeup_class.course.code} Make-Up Class"
                    message = (
                        f"Dear {student.name},\n\n"
                        f"You were marked ABSENT for the make-up class on {makeup_class.session_date}.\n\n"
                        f"Course: {makeup_class.course.code} - {makeup_class.course.name}\n"
                        f"Date: {makeup_class.session_date}\n"
                        f"Time: {makeup_class.get_time_slot_display()}\n"
                        f"Faculty: {faculty.user.get_full_name() or faculty.user.username}\n\n"
                        f"Please contact your faculty if you believe this is an error.\n\n"
                        f"Best regards,\nCampusOne Team"
                    )
                    email_messages.append((subject, message, settings.DEFAULT_FROM_EMAIL, [student.email]))
            
            if email_messages:
                try:
                    send_mass_mail(email_messages, fail_silently=True)
                    messages.success(request, f"Attendance marked and {len(absent_students)} absentee notification emails sent.")
                except Exception as e:
                    messages.success(request, f"Attendance marked for {len(students)} students. (Email error: {str(e)})")
            else:
                messages.success(request, f"Attendance marked for {len(students)} students.")
        else:
            messages.success(request, f"Attendance marked for {len(students)} students.")
        
        return redirect("makeup_class_detail", makeup_class_id=makeup_class.id)
    
    # Get existing attendance records
    existing_records = {
        r.student_id: r.status
        for r in MakeUpAttendanceRecord.objects.filter(makeup_class=makeup_class)
    }
    
    # Add status to each student for template use
    students_with_status = []
    for student in students:
        status = existing_records.get(student.id, "absent")
        students_with_status.append({
            "student": student,
            "status": status,
            "is_present": status == "present",
            "is_absent": status == "absent",
            "is_excused": status == "excused",
        })
    
    return render(request, "attendance/makeup_class_attendance.html", {
        "makeup_class": makeup_class,
        "students_with_status": students_with_status,
    })


@login_required
def makeup_class_attendance_records(request: HttpRequest, makeup_class_id: int) -> HttpResponse:
    """View attendance records for a make-up class."""
    try:
        faculty = FacultyProfile.objects.get(user=request.user)
    except FacultyProfile.DoesNotExist:
        messages.error(request, "No faculty profile found.")
        return redirect("home")
    
    makeup_class = get_object_or_404(
        MakeUpClass.objects.select_related("section", "course", "classroom", "classroom__block"),
        id=makeup_class_id,
        faculty=faculty
    )
    
    attendance_records = MakeUpAttendanceRecord.objects.filter(
        makeup_class=makeup_class
    ).select_related("student").order_by("student__registration_number")
    
    summary = {
        "present": attendance_records.filter(status=AttendanceRecord.STATUS_PRESENT).count(),
        "absent": attendance_records.filter(status=AttendanceRecord.STATUS_ABSENT).count(),
        "excused": attendance_records.filter(status=AttendanceRecord.STATUS_EXCUSED).count(),
        "total": attendance_records.count(),
    }
    
    return render(request, "attendance/makeup_class_records.html", {
        "makeup_class": makeup_class,
        "attendance_records": attendance_records,
        "summary": summary,
    })


@login_required
def makeup_class_export_report(request: HttpRequest, makeup_class_id: int) -> HttpResponse:
    """Export attendance report as CSV."""
    import csv
    
    try:
        faculty = FacultyProfile.objects.get(user=request.user)
    except FacultyProfile.DoesNotExist:
        messages.error(request, "No faculty profile found.")
        return redirect("home")
    
    makeup_class = get_object_or_404(
        MakeUpClass.objects.select_related("section", "course"),
        id=makeup_class_id,
        faculty=faculty
    )
    
    attendance_records = MakeUpAttendanceRecord.objects.filter(
        makeup_class=makeup_class
    ).select_related("student").order_by("student__registration_number")
    
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="makeup_attendance_{makeup_class.id}.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        "Registration Number", "Student Name", "Status", 
        "Marked At", "Marked By", "Section", "Course"
    ])
    
    for record in attendance_records:
        writer.writerow([
            record.student.registration_number,
            record.student.name,
            record.get_status_display(),
            record.marked_at.strftime("%Y-%m-%d %H:%M") if record.marked_at else "",
            record.marked_by.user.username if record.marked_by else "",
            makeup_class.section.name,
            makeup_class.course.code,
        ])
    
    return response


@login_required
def makeup_class_send_reminder(request: HttpRequest, makeup_class_id: int) -> HttpResponse:
    """Send reminder notification to students about make-up class."""
    try:
        faculty = FacultyProfile.objects.get(user=request.user)
    except FacultyProfile.DoesNotExist:
        messages.error(request, "No faculty profile found.")
        return redirect("home")
    
    makeup_class = get_object_or_404(
        MakeUpClass.objects.select_related("section", "course", "classroom", "classroom__block"),
        id=makeup_class_id,
        faculty=faculty,
        status=MakeUpClass.STATUS_SCHEDULED
    )
    
    if request.method == "POST":
        # Get students in section
        students = Student.objects.filter(section_mapping__section=makeup_class.section)
        
        # Create notifications
        notification_count = 0
        for student in students:
            Notification.objects.create(
                recipient_student=student,
                title=f"Make-Up Class Reminder: {makeup_class.course.code}",
                message=(
                    f"Reminder: Make-up class for {makeup_class.course.name} "
                    f"scheduled on {makeup_class.session_date} at {makeup_class.get_time_slot_display()}. "
                    f"Location: {makeup_class.classroom.block.code}-{makeup_class.classroom.room_number}. "
                    f"Remedial Code: {makeup_class.remedial_code}"
                ),
            )
            notification_count += 1
        
        messages.success(request, f"Reminder sent to {notification_count} students.")
        return redirect("makeup_class_detail", makeup_class_id=makeup_class.id)
    
    return render(request, "attendance/makeup_class_reminder.html", {
        "makeup_class": makeup_class,
    })
