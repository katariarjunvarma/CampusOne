"""
Django management command to send custom attendance reports
"""
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from attendance.models import Student, Course, AttendanceRecord, AttendanceSession
from datetime import datetime, timedelta
import csv
import io


class Command(BaseCommand):
    help = 'Send custom attendance reports to specific recipients'

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            type=str,
            required=True,
            help='Email address to send report to'
        )
        parser.add_argument(
            '--course',
            type=str,
            help='Course code to filter by (optional)'
        )
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days to include in report (default: 7)'
        )
        parser.add_argument(
            '--format',
            type=str,
            choices=['html', 'csv'],
            default='html',
            help='Report format: html or csv (default: html)'
        )

    def handle(self, *args, **options):
        email = options['email']
        course_code = options.get('course')
        days = options['days']
        report_format = options['format']
        
        self.stdout.write(f'Generating custom attendance report for {email}...')
        
        # Calculate date range
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        # Filter records
        records = AttendanceRecord.objects.filter(
            session__session_date__gte=start_date,
            session__session_date__lte=end_date
        ).select_related('student', 'session', 'session__course')
        
        if course_code:
            records = records.filter(session__course__code=course_code)
        
        if not records.exists():
            self.stdout.write(self.style.WARNING('No attendance records found for the specified criteria'))
            return
        
        if report_format == 'html':
            self._send_html_report(email, records, start_date, end_date, course_code)
        else:
            self._send_csv_report(email, records, start_date, end_date, course_code)
        
        self.stdout.write(self.style.SUCCESS('✓ Custom report sent successfully!'))

    def _send_html_report(self, email, records, start_date, end_date, course_code):
        """Send HTML formatted report"""
        
        # Prepare data for template
        report_data = []
        for record in records:
            report_data.append({
                'student_name': record.student.full_name,
                'roll_number': record.student.registration_number,
                'course_name': record.session.course.name,
                'course_code': record.session.course.code,
                'date': record.session.session_date.strftime('%d %B %Y'),
                'time': record.session.session_date.strftime('%I:%M %p'),
                'status': record.status.capitalize(),
                'marked_by': record.source.capitalize(),
            })
        
        context = {
            'report_data': report_data,
            'start_date': start_date.strftime('%d %B %Y'),
            'end_date': end_date.strftime('%d %B %Y'),
            'course_code': course_code or 'All Courses',
            'total_records': len(report_data),
            'present_count': len([r for r in report_data if r['status'] == 'Present']),
            'absent_count': len([r for r in report_data if r['status'] == 'Absent']),
        }
        
        html_message = render_to_string('attendance/email/custom_report.html', context)
        
        subject = f"📊 Custom Attendance Report - {course_code or 'All Courses'}"
        
        send_mail(
            subject=subject,
            message="Custom attendance report - please check HTML email for details.",
            html_message=html_message,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
            recipient_list=[email],
            fail_silently=False,
        )

    def _send_csv_report(self, email, records, start_date, end_date, course_code):
        """Send CSV formatted report"""
        
        # Create CSV content
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'Student Name', 'Registration Number', 'Course Code', 'Course Name',
            'Date', 'Time', 'Status', 'Marked By'
        ])
        
        # Write data
        for record in records:
            writer.writerow([
                record.student.full_name,
                record.student.registration_number,
                record.session.course.code,
                record.session.course.name,
                record.session.session_date.strftime('%d %B %Y'),
                record.session.session_date.strftime('%I:%M %p'),
                record.status.capitalize(),
                record.source.capitalize(),
            ])
        
        csv_content = output.getvalue()
        output.close()
        
        subject = f"📊 Custom Attendance Report (CSV) - {course_code or 'All Courses'}"
        
        message = f"""
Custom Attendance Report

Period: {start_date.strftime('%d %B %Y')} to {end_date.strftime('%d %B %Y')}
Course: {course_code or 'All Courses'}
Total Records: {records.count()}

CSV data is attached below.

{csv_content}
        """
        
        send_mail(
            subject=subject,
            message=message,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
            recipient_list=[email],
            fail_silently=False,
        )
