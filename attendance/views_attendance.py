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
    CourseCreateForm,
    EnrollmentForm,
    FaceSampleMultiForm,
    FaceSampleForm,
    StudentForm,
    UserPermissionsForm,
)
from .models import AttendanceRecord, AttendanceSession, Course, Enrollment, FaceSample, Notification, Student

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
def home(request: HttpRequest) -> HttpResponse:
    # Check for stall owner first
    try:
        from food.models import StallOwner

        if StallOwner.objects.filter(user=request.user, is_active=True).exists() and not bool(
            getattr(request.user, "is_superuser", False)
        ):
            return redirect("food:vendor_dashboard")
    except Exception:
        pass
    
    # Role-based redirects
    if request.user.is_authenticated:
        # Admin -> Admin Dashboard
        if getattr(request.user, "is_superuser", False):
            return redirect("manage_dashboard")
        
        # Teacher -> Teacher Dashboard (staff but not superuser)
        if getattr(request.user, "is_staff", False) and not getattr(request.user, "is_superuser", False):
            return redirect("faculty_dashboard")
    
    # Default: Show food orders for regular users
    from food.models import PreOrder
    from django.utils import timezone

    today = timezone.localdate()

    # Show only orders that are ready for pickup today
    recent_food_orders = (
        PreOrder.objects.filter(
            ordered_by=request.user,
            order_date=today,
            status="ready"
        )
        .select_related("food_item", "slot")
        .order_by("-created_at")
    )
    return render(request, "attendance/dashboard.html", {"recent_food_orders": recent_food_orders})


@login_required
def attendance_home(request: HttpRequest) -> HttpResponse:
    try:
        from food.models import StallOwner

        if StallOwner.objects.filter(user=request.user, is_active=True).exists() and not bool(
            getattr(request.user, "is_superuser", False)
        ):
            return redirect("food:vendor_dashboard")
    except Exception:
        pass
    from django.utils import timezone
    from datetime import date
    
    sessions = AttendanceSession.objects.select_related("course").order_by("-created_at")[:20]
    
    # Statistics for the new UI
    today = date.today()
    sessions_today = AttendanceSession.objects.filter(session_date=today).count()
    total_students = Student.objects.count()
    
    # Get latest session info
    latest_session = AttendanceSession.objects.select_related("course").order_by("-created_at").first()
    latest_session_info = None
    if latest_session:
        latest_session_info = {
            "course_code": latest_session.course.code,
            "time_slot": latest_session.time_slot or "-"
        }
    
    return render(request, "attendance/attendance_home.html", {
        "sessions": sessions,
        "sessions_today": sessions_today,
        "total_students": total_students,
        "latest_session_info": latest_session_info,
    })


@login_required
def create_session(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = AttendanceSessionCreateForm(request.POST)
        if form.is_valid():
            session = form.save()
            messages.success(request, "Session created.")
            return redirect("session_detail", session_id=session.id)
    else:
        form = AttendanceSessionCreateForm(initial={"session_date": timezone.localdate()})

    return render(request, "attendance/create_session.html", {"form": form})


@login_required
def edit_session(request: HttpRequest, session_id: int) -> HttpResponse:
    session = get_object_or_404(AttendanceSession.objects.select_related("course"), id=session_id)
    if request.method == "POST":
        form = AttendanceSessionCreateForm(request.POST, instance=session)
        if form.is_valid():
            form.save()
            messages.success(request, "Session updated.")
            return redirect("session_detail", session_id=session.id)
    else:
        form = AttendanceSessionCreateForm(instance=session)

    return render(request, "attendance/edit_session.html", {"form": form, "session": session})


@login_required
def delete_session(request: HttpRequest, session_id: int) -> HttpResponse:
    session = get_object_or_404(AttendanceSession.objects.select_related("course"), id=session_id)
    if request.method == "POST":
        session.delete()
        messages.success(request, "Session deleted.")
        return redirect("attendance_home")

    return render(request, "attendance/session_confirm_delete.html", {"session": session})


@login_required
def session_detail(request: HttpRequest, session_id: int) -> HttpResponse:
    session = get_object_or_404(AttendanceSession.objects.select_related("course"), id=session_id)
    students = (
        Student.objects.filter(enrollments__course=session.course)
        .order_by("registration_number")
        .distinct()
    )

    existing = {
        r.student_id: r
        for r in AttendanceRecord.objects.filter(session=session).select_related("student")
    }
    student_rows = []
    for s in students:
        rec = existing.get(s.id)
        student_rows.append(
            {
                "student": s,
                "status": rec.status if rec else "",
                "source": rec.source if rec else "",
            }
        )

    return render(
        request,
        "attendance/session_detail.html",
        {"session": session, "student_rows": student_rows, "photo_form": AttendancePhotoUploadForm()},
    )


@login_required
def session_view(request: HttpRequest, session_id: int) -> HttpResponse:
    session = get_object_or_404(AttendanceSession.objects.select_related("course"), id=session_id)
    students = (
        Student.objects.filter(enrollments__course=session.course)
        .order_by("registration_number")
        .distinct()
    )

    existing = {
        r.student_id: r
        for r in AttendanceRecord.objects.filter(session=session).select_related("student")
    }
    
    present_students = []
    absent_students = []
    
    for s in students:
        rec = existing.get(s.id)
        if rec and rec.status == AttendanceRecord.STATUS_PRESENT:
            present_students.append(s)
        else:
            absent_students.append(s)

    return render(
        request,
        "attendance/session_view.html",
        {
            "session": session,
            "present_students": present_students,
            "absent_students": absent_students,
            "total_count": len(students),
            "present_count": len(present_students),
            "absent_count": len(absent_students),
        },
    )


@login_required
@transaction.atomic
def mark_attendance_by_photo(request: HttpRequest, session_id: int) -> HttpResponse:
    session = get_object_or_404(AttendanceSession.objects.select_related("course"), id=session_id)
    students = (
        Student.objects.filter(enrollments__course=session.course)
        .order_by("registration_number")
        .distinct()
    )

    if request.method != "POST":
        return redirect("session_detail", session_id=session.id)

    form = AttendancePhotoUploadForm(request.POST, request.FILES)
    if not form.is_valid():
        messages.error(request, "Please upload a valid image.")
        return redirect("session_detail", session_id=session.id)

    # Build training set from stored FaceSample images
    images_by_label: dict[int, list[np.ndarray]] = {}
    usable_counts: dict[int, int] = {}
    for fs in (
        FaceSample.objects.select_related("student")
        .filter(student__enrollments__course=session.course)
        .distinct()
    ):
        try:
            img = cv2.imread(fs.image.path)
        except Exception:
            img = None
        if img is None:
            continue
        images_by_label.setdefault(fs.student_id, []).append(img)
        if detect_faces_count(img) > 0:
            usable_counts[fs.student_id] = usable_counts.get(fs.student_id, 0) + 1

    # Require more samples to reduce mis-labeling (important when two students look similar).
    min_samples_per_student = 5
    sample_counts = {sid: len(imgs) for (sid, imgs) in images_by_label.items()}

    # Filter out images where no face is detectable (training would be empty otherwise)
    filtered: dict[int, list[np.ndarray]] = {}
    for sid, imgs in images_by_label.items():
        keep = [im for im in imgs if detect_faces_count(im) > 0]
        if len(keep) >= min_samples_per_student:
            filtered[sid] = keep
    images_by_label = filtered

    present_ids: set[int] = set()
    used_method = ""

    # Prefer deep-learning embeddings (YuNet + SFace). If anything fails (no internet, model load error,
    # OpenCV build mismatch), fall back to existing LBPH pipeline.
    try:
        gallery = build_embedding_gallery(images_by_label, min_per_student=min_samples_per_student)
        if not gallery:
            raise ValueError("Embedding gallery empty")

        upload = form.cleaned_data["photo"]
        pil = Image.open(upload).convert("RGB")
        rgb = np.array(pil)
        bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

        recognized = recognize_embeddings_in_image(
            bgr,
            gallery,
            similarity_threshold=0.45,
            ambiguity_margin=0.04,
        )

        if len(recognized) == 0:
            messages.warning(
                request,
                "No confident face match found. Try better lighting/angle or upload clearer Face Data.",
            )
        else:
            present_ids = {r.label for r in recognized}

        used_method = "embedding"

    except Exception as e:
        messages.warning(
            request,
            f"Embedding face recognition unavailable, falling back to LBPH. Reason: {e}",
        )
        try:
            train_images, train_labels = build_training_set(images_by_label)
            recognizer = train_lbph(train_images, train_labels)
        except Exception:
            enrolled_ids = [s.id for s in students]
            parts = []
            for sid in enrolled_ids:
                parts.append(f"{sample_counts.get(sid, 0)}/{usable_counts.get(sid, 0)}")
            counts_str = ", ".join(parts)
            messages.error(
                request,
                "Face training data is missing/invalid. Upload Face Data in Manage Data (need at least 5 clear photos with a detectable face per enrolled student). "
                f"Samples found (total/usable) in course order: [{counts_str}]",
            )
            return redirect("session_detail", session_id=session.id)

        # Decode uploaded image
        upload = form.cleaned_data["photo"]
        pil = Image.open(upload).convert("RGB")
        rgb = np.array(pil)
        bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

        recognized = recognize_faces_in_image(recognizer, bgr)

        faces_detected_in_image = len(recognized)

        # If no faces detected in the uploaded image, show helpful error
        if faces_detected_in_image == 0:
            messages.error(
                request,
                "No face detected in the uploaded photo. Please ensure:\n"
                "1. Your face is clearly visible and well-lit\n"
                "2. You are facing the camera directly\n"
                "3. The photo is not blurry\n"
                "4. Only one person is in the frame\n"
                "Then try again or use Manual Attendance.",
            )
            return redirect("session_detail", session_id=session.id)

        # LBPH: lower confidence is better.
        # Strict mode (A1): use a tighter threshold to reduce false positives.
        threshold = 80.0
        allowed_ids = {s.id for s in students}

        # Choose best (lowest) confidence per predicted label
        best_by_id: dict[int, float] = {}
        for r in recognized:
            if r.label not in allowed_ids:
                continue
            conf = float(r.confidence)
            prev = best_by_id.get(r.label)
            if prev is None or conf < prev:
                best_by_id[r.label] = conf

        match_info = ", ".join([f"ID:{sid}={conf:.1f}" for sid, conf in best_by_id.items()])
        messages.info(
            request,
            f"Faces detected: {faces_detected_in_image}. Matches: {match_info if match_info else 'None'}",
        )

        sorted_matches = sorted(best_by_id.items(), key=lambda x: x[1])

        # Ambiguity guard: if the best match isn't clearly better than the second best,
        # treat the image as unknown to prevent look-alike false positives.
        if len(sorted_matches) >= 2:
            best_conf = float(sorted_matches[0][1])
            second_conf = float(sorted_matches[1][1])
            if (second_conf - best_conf) < 12.0:
                messages.error(
                    request,
                    "Face match is ambiguous (two students are too close). Please try again with better lighting/angle or improve Face Data.",
                )
                return redirect("session_detail", session_id=session.id)

        present_ids = {sid for (sid, conf) in sorted_matches if conf <= threshold}

        # If no students matched, explain why
        if len(present_ids) == 0 and len(best_by_id) > 0:
            best_match = sorted_matches[0]
            messages.warning(
                request,
                f"Face detected but confidence too low (best match: {best_match[1]:.1f}, threshold: {threshold}). "
                f"Try uploading clearer photos with better lighting, or use Manual Attendance.",
            )

        used_method = "lbph"

    # Only mark recognized students as present. Leave others unmarked so teacher can
    # manually verify or click "Absent Remaining" to mark unchecked students absent.
    marked_present_count = 0
    for s in students:
        if s.id in present_ids:
            AttendanceRecord.objects.update_or_create(
                session=session,
                student=s,
                defaults={"status": AttendanceRecord.STATUS_PRESENT, "source": "face"},
            )
            marked_present_count += 1

    # Get currently marked absent count for info message
    currently_absent = AttendanceRecord.objects.filter(
        session=session, status=AttendanceRecord.STATUS_ABSENT
    ).count()

    messages.success(
        request,
        f"Photo-based marking complete. Marked {marked_present_count} student(s) as present. "
        f"Review unchecked students, then click 'Absent Remaining' to mark others absent.",
    )
    if used_method:
        messages.info(request, f"Face matching method used: {used_method}.")
    return redirect("session_detail", session_id=session.id)


@login_required
@transaction.atomic
def mark_attendance(request: HttpRequest, session_id: int) -> HttpResponse:
    try:
        session = get_object_or_404(AttendanceSession.objects.select_related("course"), id=session_id)
        students = (
            Student.objects.filter(enrollments__course=session.course)
            .order_by("registration_number")
            .distinct()
        )

        if request.method != "POST":
            return redirect("session_detail", session_id=session.id)

        action = request.POST.get("action", "")

        if action == "mark_all_present":
            for s in students:
                AttendanceRecord.objects.update_or_create(
                    session=session,
                    student=s,
                    defaults={"status": AttendanceRecord.STATUS_PRESENT, "source": "manual"},
                )
            messages.success(request, "Marked all students present.")
            return redirect("session_detail", session_id=session.id)

        if action == "mark_all_absent":
            for s in students:
                AttendanceRecord.objects.update_or_create(
                    session=session,
                    student=s,
                    defaults={"status": AttendanceRecord.STATUS_ABSENT, "source": "manual"},
                )
            messages.success(request, "Marked all students absent.")
            return redirect("session_detail", session_id=session.id)

        if action == "mark_remaining_absent":
            present_ids_post = {
                int(x) for x in request.POST.getlist("present") if str(x).isdigit()
            }
            # Fall back to already-saved present records only if the form didn't send any.
            # This keeps the behavior safe even if JS submits without checkbox values.
            present_ids = present_ids_post or {
                r.student_id
                for r in AttendanceRecord.objects.filter(
                    session=session, status=AttendanceRecord.STATUS_PRESENT
                )
            }

            marked_count = 0
            for s in students:
                if s.id in present_ids:
                    AttendanceRecord.objects.update_or_create(
                        session=session,
                        student=s,
                        defaults={"status": AttendanceRecord.STATUS_PRESENT, "source": "manual"},
                    )
                else:
                    AttendanceRecord.objects.update_or_create(
                        session=session,
                        student=s,
                        defaults={"status": AttendanceRecord.STATUS_ABSENT, "source": "manual"},
                    )
                    marked_count += 1
            messages.success(request, f"Marked {marked_count} remaining students absent.")
            return redirect("session_detail", session_id=session.id)

        if action != "submit_manual":
            messages.error(request, "Invalid attendance action.")
            return redirect("session_detail", session_id=session.id)

        present_ids = {int(x) for x in request.POST.getlist("present") if x.isdigit()}

        emails_attempted = 0
        emails_sent = 0
        email_failures = 0

        # Save records
        for s in students:
            status = (
                AttendanceRecord.STATUS_PRESENT
                if s.id in present_ids
                else AttendanceRecord.STATUS_ABSENT
            )
            prev = (
                AttendanceRecord.objects.filter(session=session, student=s)
                .values_list("status", flat=True)
                .first()
            )
            AttendanceRecord.objects.update_or_create(
                session=session,
                student=s,
                defaults={"status": status, "source": "manual"},
            )

            became_absent = status == AttendanceRecord.STATUS_ABSENT and prev != AttendanceRecord.STATUS_ABSENT
            if became_absent and (s.email or s.parent_email):
                # Create notification record
                msg = (
                    f"Absent detected: {s.full_name} ({s.registration_number}) was marked ABSENT for "
                    f"{session.course.code} on {session.session_date}."
                )
                Notification.objects.create(recipient_student=s, channel="email", message=msg)
                
                # Send customized email with requested format
                try:
                    # Custom subject format: Absent marked for <course code> <date>
                    subject = f"Absent marked for {session.course.code} {session.session_date.strftime('%Y-%m-%d')}"
                    
                    # Prepare template context
                    context = {
                        'student_name': s.full_name,
                        'roll_number': s.registration_number,
                        'course_name': session.course.name,
                        'course_code': session.course.code,
                        'date': session.session_date.strftime('%d %B %Y'),
                        'time_slot': session.time_slot
                        or f"{session.session_date.strftime('%I:%M %p')} to {(session.session_date + timedelta(hours=1)).strftime('%I:%M %p')}",
                    }
                    
                    # Send separate emails for student and parent
                    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None)

                    if s.email:
                        html_message = render_to_string(
                            "attendance/email/absence_notification_student.html", context
                        )
                        text_message = render_to_string(
                            "attendance/email/absence_notification_student.txt", context
                        )
                        emails_attempted += 1
                        sent = send_mail(
                            subject=subject,
                            message=text_message,
                            html_message=html_message,
                            from_email=from_email,
                            recipient_list=[s.email],
                            fail_silently=False,
                        )
                        if sent:
                            emails_sent += 1
                        else:
                            email_failures += 1

                    if s.parent_email:
                        html_message = render_to_string(
                            "attendance/email/absence_notification_parent.html", context
                        )
                        text_message = render_to_string(
                            "attendance/email/absence_notification_parent.txt", context
                        )
                        emails_attempted += 1
                        sent = send_mail(
                            subject=subject,
                            message=text_message,
                            html_message=html_message,
                            from_email=from_email,
                            recipient_list=[s.parent_email],
                            fail_silently=False,
                        )
                        if sent:
                            emails_sent += 1
                        else:
                            email_failures += 1
                except Exception:
                    email_failures += 1

        absentees = [s for s in students if s.id not in present_ids]

        messages.success(
            request,
            f"Attendance saved. Absentees: {len(absentees)} | Emails sent: {emails_sent}/{emails_attempted}",
        )
        if email_failures or emails_sent < emails_attempted:
            messages.warning(
                request,
                f"Some absence emails failed to send ({email_failures}). Please check the server console for the exact error.",
            )
        return redirect("session_detail", session_id=session.id)
    
    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")
        return redirect("session_detail", session_id=session.id)


@login_required
def live_attendance_frame(request: HttpRequest, session_id: int) -> JsonResponse:
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "POST required"}, status=405)

    state = _live_get_state(request, session_id)
    now = time.time()
    last_ts = float(state.get("last_ts", 0.0))
    if now - last_ts < 0.35:
        return JsonResponse({"ok": False, "error": "Too many requests"}, status=429)
    state["last_ts"] = now

    session = get_object_or_404(AttendanceSession.objects.select_related("course"), id=session_id)
    students = (
        Student.objects.filter(enrollments__course=session.course)
        .order_by("registration_number")
        .distinct()
    )
    allowed_ids = {s.id for s in students}

    try:
        raw = request.body.decode("utf-8")
    except Exception:
        return JsonResponse({"ok": False, "error": "Invalid body"}, status=400)

    try:
        import json

        payload = json.loads(raw)
    except Exception:
        return JsonResponse({"ok": False, "error": "Invalid JSON"}, status=400)

    img_b64 = payload.get("image", "")
    require_blink = bool(payload.get("require_blink", False))
    if not isinstance(img_b64, str) or not img_b64:
        return JsonResponse({"ok": False, "error": "Missing image"}, status=400)

    if len(img_b64) > 2_500_000:
        return JsonResponse({"ok": False, "error": "Image too large"}, status=413)

    if img_b64.startswith("data:"):
        img_b64 = img_b64.split(",", 1)[-1]

    try:
        img_bytes = base64.b64decode(img_b64)
    except Exception:
        return JsonResponse({"ok": False, "error": "Bad base64"}, status=400)

    arr = np.frombuffer(img_bytes, dtype=np.uint8)
    bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if bgr is None:
        return JsonResponse({"ok": False, "error": "Could not decode image"}, status=400)

    # Update liveness state
    eyes_count = detect_eyes_count(bgr)
    eyes: deque[int] = state["eyes"]  # type: ignore[assignment]
    eyes.append(int(eyes_count))
    if _blink_seen(state):
        state["last_blink_ts"] = now

    if require_blink:
        last_blink_ts = float(state.get("last_blink_ts", 0.0))
        if now - last_blink_ts > 6.0:
            return JsonResponse(
                {
                    "ok": False,
                    "error": "Liveness check failed (blink not detected yet).",
                    "eyes": int(eyes_count),
                    "blink_recent": False,
                },
                status=200,
            )

    # Build training set from stored FaceSample images (only enrolled students)
    images_by_label: dict[int, list[np.ndarray]] = {}
    usable_counts: dict[int, int] = {}
    for fs in (
        FaceSample.objects.select_related("student")
        .filter(student__enrollments__course=session.course)
        .distinct()
    ):
        try:
            img = cv2.imread(fs.image.path)
        except Exception:
            img = None
        if img is None:
            continue
        images_by_label.setdefault(fs.student_id, []).append(img)
        if detect_faces_count(img) > 0:
            usable_counts[fs.student_id] = usable_counts.get(fs.student_id, 0) + 1

    # Only train on students with enough samples to reduce mis-labeling.
    min_samples_per_student = 4
    filtered: dict[int, list[np.ndarray]] = {}
    for sid, imgs in images_by_label.items():
        keep = [im for im in imgs if detect_faces_count(im) > 0]
        if len(keep) >= min_samples_per_student:
            filtered[sid] = keep
    images_by_label = filtered

    try:
        train_images, train_labels = build_training_set(images_by_label)
        recognizer = train_lbph(train_images, train_labels)
    except Exception:
        parts = []
        for sid in students.values_list("id", flat=True):
            total = FaceSample.objects.filter(student_id=sid).count()
            parts.append(f"{total}/{usable_counts.get(int(sid), 0)}")
        diag = ", ".join(parts)
        return JsonResponse(
            {
                "ok": False,
                "error": "Face data missing/invalid. Upload Face Data in Manage Data (need >= 4 clear photos with a detectable face per enrolled student).",
                "diag": f"total/usable in session course: [{diag}]",
                "eyes": int(eyes_count),
                "blink_recent": (now - float(state.get("last_blink_ts", 0.0)) <= 6.0),
            },
            status=200,
        )

    recognized = recognize_faces_in_image(recognizer, bgr)

    # Repeated-frame confirmation:
    # - Use strict threshold first (reduces false positives)
    # - If the same ID repeats across frames, allow a slightly looser threshold
    strict_threshold = 95.0
    loose_threshold = 120.0
    confirm_frames = 3
    confirm_window_s = 3.0

    candidates: dict[int, dict[str, float]] = state.get("candidates", {})  # type: ignore[assignment]

    # Decay old candidates
    for sid in list(candidates.keys()):
        last_seen = float(candidates[sid].get("last_seen", 0.0))
        if now - last_seen > confirm_window_s:
            candidates.pop(sid, None)

    # For each recognized face, choose best (lowest) confidence for that label
    best_by_id: dict[int, float] = {}
    for r in recognized:
        if r.label not in allowed_ids:
            continue
        conf = float(r.confidence)
        prev = best_by_id.get(r.label)
        if prev is None or conf < prev:
            best_by_id[r.label] = conf

    detected_ids: set[int] = set()
    pending_ids: set[int] = set()
    sorted_matches = sorted(best_by_id.items(), key=lambda x: x[1])
    top_matches = sorted_matches[:3]

    # Ambiguity guard: if the best match isn't clearly better than the second best,
    # do not mark anyone for this frame.
    if len(sorted_matches) >= 2:
        best_conf = float(sorted_matches[0][1])
        second_conf = float(sorted_matches[1][1])
        if (second_conf - best_conf) < 12.0:
            return JsonResponse(
                {
                    "ok": True,
                    "present_detected": 0,
                    "newly_marked": 0,
                    "pending": 0,
                    "faces_detected": len(recognized),
                    "trained_faces": len(train_images),
                    "trained_students": len(set(train_labels)),
                    "top_matches": [{"id": int(i), "conf": float(c)} for (i, c) in top_matches],
                    "eyes": int(eyes_count),
                    "blink_recent": (now - float(state.get("last_blink_ts", 0.0)) <= 6.0),
                }
            )

    for sid, conf in best_by_id.items():
        info = candidates.get(sid)
        prev_count = int(info.get("count", 0)) if info else 0

        # If already seen before, allow looser threshold; otherwise use strict.
        thr = loose_threshold if prev_count >= 1 else strict_threshold
        if conf > thr:
            continue

        new_count = prev_count + 1
        candidates[sid] = {"count": float(new_count), "last_seen": float(now), "best": float(conf)}
        if new_count >= confirm_frames:
            detected_ids.add(sid)
        else:
            pending_ids.add(sid)

    state["candidates"] = candidates

    newly_marked = 0
    for sid in detected_ids:
        obj, created = AttendanceRecord.objects.update_or_create(
            session=session,
            student_id=sid,
            defaults={"status": AttendanceRecord.STATUS_PRESENT, "source": "live_face"},
        )
        if created or obj.status != AttendanceRecord.STATUS_PRESENT:
            newly_marked += 1

    return JsonResponse(
        {
            "ok": True,
            "present_detected": len(detected_ids),
            "newly_marked": newly_marked,
            "pending": len(pending_ids),
            "faces_detected": len(recognized),
            "trained_faces": len(train_images),
            "trained_students": len(set(train_labels)),
            "top_matches": [{"id": int(i), "conf": float(c)} for (i, c) in top_matches],
            "eyes": int(eyes_count),
            "blink_recent": (now - float(state.get("last_blink_ts", 0.0)) <= 6.0),
        }
    )


