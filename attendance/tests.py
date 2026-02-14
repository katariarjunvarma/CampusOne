from datetime import date

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse

from .models import AttendanceRecord, AttendanceSession, Course, Enrollment, Student


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class AttendanceActionsTests(TestCase):
    def setUp(self) -> None:
        User = get_user_model()
        self.user = User.objects.create_user(username="faculty", password="pass1234")

        self.course = Course.objects.create(code="CSE111", name="computer programming")
        self.s1 = Student.objects.create(
            registration_number="123456", full_name="satish", email="satish@example.com", parent_email="p1@example.com"
        )
        self.s2 = Student.objects.create(
            registration_number="654321",
            full_name="Katari Arjun Varma",
            email="arjun@example.com",
            parent_email="p2@example.com",
        )
        Enrollment.objects.create(student=self.s1, course=self.course)
        Enrollment.objects.create(student=self.s2, course=self.course)

        self.session = AttendanceSession.objects.create(
            course=self.course,
            session_date=date(2026, 2, 10),
            time_slot="11am-12pm",
        )

        self.client.login(username="faculty", password="pass1234")

    def test_submit_manual_saves_and_emails_only_on_transition_to_absent(self) -> None:
        url = reverse("mark_attendance", kwargs={"session_id": self.session.id})

        # First submit: s1 present, s2 absent => should send 2 emails (student+parent) for s2
        resp = self.client.post(url, {"action": "submit_manual", "present": [str(self.s1.id)]})
        self.assertEqual(resp.status_code, 302)

        r1 = AttendanceRecord.objects.get(session=self.session, student=self.s1)
        r2 = AttendanceRecord.objects.get(session=self.session, student=self.s2)
        self.assertEqual(r1.status, AttendanceRecord.STATUS_PRESENT)
        self.assertEqual(r2.status, AttendanceRecord.STATUS_ABSENT)

        self.assertEqual(len(mail.outbox), 2)

        # Second submit with same statuses: should not resend absence emails
        resp = self.client.post(url, {"action": "submit_manual", "present": [str(self.s1.id)]})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(len(mail.outbox), 2)

        # Now flip s1 to absent: should send 2 more emails for s1
        resp = self.client.post(url, {"action": "submit_manual"})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(len(mail.outbox), 4)

    def test_mark_remaining_absent_respects_checked_present(self) -> None:
        url = reverse("mark_attendance", kwargs={"session_id": self.session.id})

        resp = self.client.post(url, {"action": "mark_remaining_absent", "present": [str(self.s1.id)]})
        self.assertEqual(resp.status_code, 302)

        r1 = AttendanceRecord.objects.get(session=self.session, student=self.s1)
        r2 = AttendanceRecord.objects.get(session=self.session, student=self.s2)
        self.assertEqual(r1.status, AttendanceRecord.STATUS_PRESENT)
        self.assertEqual(r2.status, AttendanceRecord.STATUS_ABSENT)

    def test_mark_all_present_and_absent(self) -> None:
        url = reverse("mark_attendance", kwargs={"session_id": self.session.id})

        resp = self.client.post(url, {"action": "mark_all_present"})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(
            AttendanceRecord.objects.filter(
                session=self.session, status=AttendanceRecord.STATUS_PRESENT
            ).count(),
            2,
        )

        resp = self.client.post(url, {"action": "mark_all_absent"})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(
            AttendanceRecord.objects.filter(
                session=self.session, status=AttendanceRecord.STATUS_ABSENT
            ).count(),
            2,
        )
