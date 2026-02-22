"""
Email utility functions for CampusOne attendance system
"""
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.db.models import Count, Q
from datetime import datetime, timedelta
from .models import AttendanceRecord, Student


def send_absence_notification(student, session):
    """Send customized absence notification email"""
    if not student.email:
        return False
    
    try:
        subject = f"📅 Absence Notification - {session.course.name}"
        
        context = {
            'student_name': student.full_name,
            'roll_number': student.registration_number,
            'course_name': session.course.name,
            'course_code': session.course.code,
            'date': session.session_date.strftime('%d %B %Y'),
            'time': session.session_date.strftime('%I:%M %p'),
        }
        
        html_message = render_to_string('attendance/email/absence_notification.html', context)
        text_message = render_to_string('attendance/email/absence_notification.txt', context)
        
        send_mail(
            subject=subject,
            message=text_message,
            html_message=html_message,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
            recipient_list=[student.email],
            fail_silently=True,
        )
        return True
    except Exception:
        return False


def send_low_attendance_warning(student, course):
    """Send low attendance warning email"""
    if not student.email:
        return False
    
    try:
        # Calculate attendance statistics
        records = AttendanceRecord.objects.filter(
            student=student,
            session__course=course
        )
        
        total_classes = records.count()
        present_classes = records.filter(status='present').count()
        attendance_percentage = (present_classes / total_classes * 100) if total_classes > 0 else 0
        
        subject = f"⚠️ Low Attendance Warning - {course.name}"
        
        context = {
            'student_name': student.full_name,
            'roll_number': student.registration_number,
            'course_name': course.name,
            'course_code': course.code,
            'attendance_percentage': round(attendance_percentage, 1),
            'classes_attended': present_classes,
            'total_classes': total_classes,
        }
        
        html_message = render_to_string('attendance/email/low_attendance_warning.html', context)
        
        send_mail(
            subject=subject,
            message="Low attendance warning - please check HTML email for details.",
            html_message=html_message,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
            recipient_list=[student.email],
            fail_silently=True,
        )
        return True
    except Exception:
        return False


def send_monthly_attendance_summary(student, year, month):
    """Send monthly attendance summary email"""
    if not student.email:
        return False
    
    try:
        # Get attendance records for the month
        records = AttendanceRecord.objects.filter(
            student=student,
            session__session_date__year=year,
            session__session_date__month=month
        ).select_related('session', 'session__course').order_by('session__session_date')
        
        if not records.exists():
            return False
        
        # Calculate statistics
        total_classes = records.count()
        present_classes = records.filter(status='present').count()
        absent_classes = records.filter(status='absent').count()
        attendance_percentage = (present_classes / total_classes * 100) if total_classes > 0 else 0
        
        # Prepare attendance records for template
        attendance_records = []
        for record in records:
            attendance_records.append({
                'date': record.session.session_date.strftime('%d %B %Y'),
                'course': record.session.course.name,
                'time': record.session.session_date.strftime('%I:%M %p'),
                'status': record.status,
                'marked_by': record.source.capitalize(),
            })
        
        month_name = datetime(year, month, 1).strftime('%B')
        
        subject = f"📊 Monthly Attendance Summary - {month_name} {year}"
        
        context = {
            'student_name': student.full_name,
            'roll_number': student.registration_number,
            'month': month_name,
            'year': year,
            'attendance_percentage': round(attendance_percentage, 1),
            'total_classes': total_classes,
            'classes_present': present_classes,
            'classes_absent': absent_classes,
            'attendance_records': attendance_records,
        }
        
        html_message = render_to_string('attendance/email/attendance_summary.html', context)
        
        send_mail(
            subject=subject,
            message="Monthly attendance summary - please check HTML email for details.",
            html_message=html_message,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
            recipient_list=[student.email],
            fail_silently=True,
        )
        return True
    except Exception:
        return False


def check_and_send_low_attendance_warnings():
    """Check all students for low attendance and send warnings"""
    students = Student.objects.filter(email__isnull=False).exclude(email='')
    
    for student in students:
        # Get all courses for the student
        courses = student.courses.all()
        
        for course in courses:
            # Calculate attendance percentage
            records = AttendanceRecord.objects.filter(
                student=student,
                session__course=course
            )
            
            total_classes = records.count()
            if total_classes < 5:  # Only check after at least 5 classes
                continue
            
            present_classes = records.filter(status='present').count()
            attendance_percentage = (present_classes / total_classes * 100) if total_classes > 0 else 0
            
            # Send warning if attendance is below 75%
            if attendance_percentage < 75:
                send_low_attendance_warning(student, course)


def send_monthly_sumaries_to_all_students():
    """Send monthly attendance summaries to all students"""
    current_date = datetime.now()
    last_month = current_date - timedelta(days=30)
    
    students = Student.objects.filter(email__isnull=False).exclude(email='')
    
    for student in students:
        send_monthly_attendance_summary(
            student, 
            last_month.year, 
            last_month.month
        )
