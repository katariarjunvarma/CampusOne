# Email Templates for CampusOne

This document describes the email templates available in the CampusOne attendance system.

## Available Templates

### 1. Absence Notification
- **HTML Template**: `attendance/templates/attendance/email/absence_notification.html`
- **Text Template**: `attendance/templates/attendance/email/absence_notification.txt`
- **Trigger**: When a student is marked absent (only on status change to absent)
- **Features**:
  - Professional design with CampusOne branding
  - Student information display
  - Course and session details
  - Contact information for parents
  - Responsive HTML design

### 2. Low Attendance Warning
- **HTML Template**: `attendance/templates/attendance/email/low_attendance_warning.html`
- **Trigger**: When student attendance falls below 75%
- **Features**:
  - Warning highlighting
  - Attendance statistics
  - Consequences and recommended actions
  - Color-coded attendance percentage

### 3. Monthly Attendance Summary
- **HTML Template**: `attendance/templates/attendance/email/attendance_summary.html`
- **Trigger**: Monthly automated reports
- **Features**:
  - Complete attendance statistics
  - Detailed attendance table
  - Visual stats cards
  - Color-coded status indicators

## Customization

### Template Variables
All templates use Django template variables. Common variables include:

- `{{ student_name }}` - Full name of the student
- `{{ roll_number }}` - Student's registration number (6 digits)
- `{{ course_name }}` - Course name
- `{{ course_code }}` - Course code
- `{{ date }}` - Formatted date (e.g., "09 February 2026")
- `{{ time }}` - Formatted time (e.g., "10:30 AM")
- `{{ attendance_percentage }}` - Attendance percentage
- `{{ classes_present }}` - Number of classes attended
- `{{ classes_absent }}` - Number of classes missed
- `{{ total_classes }}` - Total number of classes

### Customizing Colors and Styling
Each HTML template uses inline CSS for maximum email client compatibility. You can modify:

- **Primary Color**: Currently `#4CAF50` (green)
- **Warning Color**: Currently `#ff9800` (orange)
- **Danger Color**: Currently `#d32f2f` (red)
- **Font Family**: Currently `'Segoe UI', Tahoma, Geneva, Verdana, sans-serif`

### Adding New Templates
1. Create HTML template in `attendance/templates/attendance/email/`
2. Create corresponding text template for plain text fallback
3. Add email function in `attendance/email_utils.py`
4. Call the function from appropriate views or management commands

## Email Functions

### send_absence_notification(student, session)
Sends absence notification when a student is marked absent.

### send_low_attendance_warning(student, course)
Sends warning when attendance falls below 75%.

### send_monthly_attendance_summary(student, year, month)
Sends comprehensive monthly attendance report.

### check_and_send_low_attendance_warnings()
Checks all students and sends warnings where needed.

### send_monthly_sumaries_to_all_students()
Sends monthly summaries to all students.

## Usage Examples

### Manual Email Sending
```python
from attendance.email_utils import send_absence_notification

# Send absence notification
send_absence_notification(student, session)

# Send low attendance warning
send_low_attendance_warning(student, course)
```

### Automated Tasks
You can create Django management commands for automated emails:

```python
# management/commands/send_attendance_warnings.py
from django.core.management.base import BaseCommand
from attendance.email_utils import check_and_send_low_attendance_warnings

class Command(BaseCommand):
    def handle(self, *args, **options):
        check_and_send_low_attendance_warnings()
        self.stdout.write('Attendance warnings sent successfully')
```

## Email Configuration

Emails are sent using the configured SMTP settings in `settings.py`:
- Uses custom `NoVerifySMTPBackend` for SSL certificate issues
- Sends both HTML and text versions for maximum compatibility
- Fail-silently enabled to prevent application errors

## Testing

You can test email templates using Django shell:

```python
python manage.py shell
from attendance.email_utils import send_absence_notification
from attendance.models import Student, AttendanceSession

student = Student.objects.first()
session = AttendanceSession.objects.first()
send_absence_notification(student, session)
```

## Best Practices

1. **Always provide both HTML and text versions** for email client compatibility
2. **Use inline CSS** instead of external stylesheets
3. **Keep subject lines informative but concise**
4. **Include school branding and contact information**
5. **Test across different email clients** (Gmail, Outlook, etc.)
6. **Use responsive design** for mobile viewing
7. **Avoid JavaScript** in email templates
8. **Use absolute URLs** for any images or links
