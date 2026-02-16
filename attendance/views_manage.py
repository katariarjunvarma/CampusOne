from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.views import LoginView
from django.db import transaction
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
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
    CourseOfferingForm,
    EnrollmentForm,
    FaceSampleMultiForm,
    FaceSampleForm,
    FacultyProfileForm,
    ClassroomForm,
    StudentForm,
    UserPermissionsForm,
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
    Notification,
    Student,
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
    return render(request, "attendance/manage/dashboard.html", {"stats": stats})


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
    return render(request, "attendance/manage/form.html", {"form": form, "title": "Add Block"})


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
    return render(request, "attendance/manage/form.html", {"form": form, "title": "Edit Block"})


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def manage_block_delete(request: HttpRequest, block_id: int) -> HttpResponse:
    block = get_object_or_404(Block, id=block_id)
    if request.method == "POST":
        block.delete()
        messages.success(request, "Block deleted.")
        return redirect("manage_blocks")
    return render(request, "attendance/manage/confirm_delete.html", {"object": block, "type": "Block"})


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
    return render(request, "attendance/manage/form.html", {"form": form, "title": "Add Classroom"})


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
    return render(request, "attendance/manage/form.html", {"form": form, "title": "Edit Classroom"})


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def manage_classroom_delete(request: HttpRequest, classroom_id: int) -> HttpResponse:
    classroom = get_object_or_404(Classroom, id=classroom_id)
    if request.method == "POST":
        classroom.delete()
        messages.success(request, "Classroom deleted.")
        return redirect("manage_classrooms")
    return render(request, "attendance/manage/confirm_delete.html", {"object": classroom, "type": "Classroom"})


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
    return render(request, "attendance/manage/form.html", {"form": form, "title": "Add Faculty"})


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
    return render(request, "attendance/manage/form.html", {"form": form, "title": "Edit Faculty"})


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def manage_faculty_delete(request: HttpRequest, faculty_id: int) -> HttpResponse:
    faculty = get_object_or_404(FacultyProfile, id=faculty_id)
    if request.method == "POST":
        faculty.delete()
        messages.success(request, "Faculty profile deleted.")
        return redirect("manage_faculty")
    return render(request, "attendance/manage/confirm_delete.html", {"object": faculty, "type": "Faculty"})


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def manage_course_offerings(request: HttpRequest) -> HttpResponse:
    offerings = (
        CourseOffering.objects.select_related("course", "faculty__user", "classroom__block")
        .order_by("day_of_week", "start_time")
    )
    return render(request, "attendance/manage/course_offerings.html", {"offerings": offerings})


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def manage_course_offering_create(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = CourseOfferingForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Course offering created.")
            return redirect("manage_course_offerings")
    else:
        form = CourseOfferingForm()
    return render(request, "attendance/manage/form.html", {"form": form, "title": "Add Course Offering"})


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def manage_course_offering_edit(request: HttpRequest, offering_id: int) -> HttpResponse:
    offering = get_object_or_404(CourseOffering, id=offering_id)
    if request.method == "POST":
        form = CourseOfferingForm(request.POST, instance=offering)
        if form.is_valid():
            form.save()
            messages.success(request, "Course offering updated.")
            return redirect("manage_course_offerings")
    else:
        form = CourseOfferingForm(instance=offering)
    return render(request, "attendance/manage/form.html", {"form": form, "title": "Edit Course Offering"})


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def manage_course_offering_delete(request: HttpRequest, offering_id: int) -> HttpResponse:
    offering = get_object_or_404(CourseOffering, id=offering_id)
    if request.method == "POST":
        offering.delete()
        messages.success(request, "Course offering deleted.")
        return redirect("manage_course_offerings")
    return render(request, "attendance/manage/confirm_delete.html", {"object": offering, "type": "Course Offering"})


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def report_capacity_utilization(request: HttpRequest) -> HttpResponse:
    offerings = (
        CourseOffering.objects.filter(is_active=True)
        .select_related("course", "faculty__user", "classroom__block")
        .order_by("day_of_week", "start_time")
    )
    rows = []
    for o in offerings:
        enrolled = Enrollment.objects.filter(course=o.course).count()
        capacity = int(o.classroom.capacity or 0)
        utilization = (enrolled / capacity * 100.0) if capacity > 0 else 0.0
        rows.append(
            {
                "offering": o,
                "enrolled": enrolled,
                "capacity": capacity,
                "utilization": round(utilization, 1),
            }
        )
    rows.sort(key=lambda r: r["utilization"], reverse=True)
    return render(request, "attendance/manage/report_capacity.html", {"rows": rows})


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def report_workload_distribution(request: HttpRequest) -> HttpResponse:
    faculty = FacultyProfile.objects.select_related("user").order_by("user__username")
    rows = []
    for f in faculty:
        sessions_per_week = CourseOffering.objects.filter(faculty=f, is_active=True).count()
        rows.append({"faculty": f, "sessions_per_week": sessions_per_week})
    rows.sort(key=lambda r: r["sessions_per_week"], reverse=True)
    return render(request, "attendance/manage/report_workload.html", {"rows": rows})


@login_required
@user_passes_test(lambda u: bool(getattr(u, "is_superuser", False)))
def manage_students(request: HttpRequest) -> HttpResponse:
    students = Student.objects.order_by("registration_number")
    return render(request, "attendance/manage/students.html", {"students": students})


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
    return render(request, "attendance/manage/form.html", {"form": form, "title": "Add Student"})


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
    return render(request, "attendance/manage/form.html", {"form": form, "title": "Edit Student"})


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
    courses = Course.objects.order_by("code")
    return render(request, "attendance/manage/courses.html", {"courses": courses})


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
            form.save()
            messages.success(request, "Enrollment created.")
            return redirect("manage_enrollments")
    else:
        form = EnrollmentForm()
    return render(request, "attendance/manage/form.html", {"form": form, "title": "Add Enrollment"})


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
        # Get all records for calculating overall stats
        all_records = AttendanceRecord.objects.select_related("session", "session__course").filter(student=student)
        
        # Overall Stats
        total_sessions = all_records.count()
        present = all_records.filter(status=AttendanceRecord.STATUS_PRESENT).count()
        absent = all_records.filter(status=AttendanceRecord.STATUS_ABSENT).count()
        percentage = (present / total_sessions * 100) if total_sessions > 0 else 0

        stats = {
            "total": total_sessions,
            "present": present,
            "absent": absent,
            "percentage": round(percentage, 1),
        }

        if course_id:
            # Course Detail View
            records = all_records.filter(session__course_id=course_id).order_by("-session__session_date", "-session__created_at")
            if records.exists():
                selected_course = records.first().session.course
            else:
                # Handle case where ID is valid but no records exist (e.g. wiped)
                selected_course = Course.objects.filter(id=course_id).first()
        else:
            # Course Summary View
            # Group by course
            courses = {}
            for record in all_records:
                c = record.session.course
                if c.id not in courses:
                    courses[c.id] = {
                        "course": c,
                        "total": 0,
                        "present": 0,
                        "absent": 0,
                    }
                courses[c.id]["total"] += 1
                if record.status == AttendanceRecord.STATUS_PRESENT:
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
    return render(request, "attendance/manage/confirm_delete.html", {"object": alert, "type": "Emergency Alert"})
