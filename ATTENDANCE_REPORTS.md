# Attendance Reports Management Commands

This document describes the Django management commands for sending attendance reports in Smart LPU.

## Available Commands

### 1. Send Attendance Reports
Send automated attendance reports (warnings, monthly summaries, etc.)

```bash
python manage.py send_attendance_reports --type all
```

**Options:**
- `--type`: Type of report to send
  - `warnings`: Send low attendance warnings only
  - `monthly`: Send monthly summaries only
  - `all`: Send both (default)

**Examples:**
```bash
# Send all types of reports
python manage.py send_attendance_reports

# Send only low attendance warnings
python manage.py send_attendance_reports --type warnings

# Send only monthly summaries
python manage.py send_attendance_reports --type monthly
```

### 2. Send Custom Report
Generate and send custom attendance reports to specific recipients.

```bash
python manage.py send_custom_report --email admin@example.com --days 7 --format html
```

**Required Options:**
- `--email`: Email address to send report to

**Optional Options:**
- `--course`: Course code to filter by (e.g., `CS101`)
- `--days`: Number of days to include (default: 7)
- `--format`: Report format - `html` or `csv` (default: `html`)

**Examples:**
```bash
# Send last 7 days report for all courses
python manage.py send_custom_report --email admin@smartlpu.edu

# Send last 30 days report for specific course
python manage.py send_custom_report --email admin@smartlpu.edu --course CS101 --days 30

# Send CSV format report
python manage.py send_custom_report --email admin@smartlpu.edu --format csv

# Send report for specific course and time period
python manage.py send_custom_report --email hod@smartlpu.edu --course CS101 --days 14 --format html
```

## Automated Scheduling

You can set up cron jobs to automate report sending:

### Daily Low Attendance Warnings
```bash
# Run every day at 6 PM
0 18 * * * /path/to/venv/bin/python /path/to/smartLPU/manage.py send_attendance_reports --type warnings
```

### Monthly Attendance Summaries
```bash
# Run on 1st of every month at 9 AM
0 9 1 * * /path/to/venv/bin/python /path/to/smartLPU/manage.py send_attendance_reports --type monthly
```

### Weekly Reports for Administrators
```bash
# Run every Friday at 5 PM
0 17 * * 5 /path/to/venv/bin/python /path/to/smartLPU/manage.py send_custom_report --email admin@smartlpu.edu --days 7
```

## Report Features

### Low Attendance Warnings
- Automatically detects students with attendance below 75%
- Sends professional warning emails with statistics
- Includes consequences and recommended actions
- Only triggers after minimum 5 classes attended

### Monthly Summaries
- Comprehensive attendance reports for each student
- Detailed attendance tables with dates and times
- Visual statistics and attendance percentages
- Color-coded status indicators

### Custom Reports
- Flexible date range filtering
- Course-specific filtering
- HTML and CSV format options
- Real-time statistics and summaries
- Professional email templates

## Email Templates

### Custom Message Format
Absence emails now use your requested format:

**Subject:** `Absent marked for {course_code}{date}{time}`
- Example: `Absent marked for CS101202602091030AM`

**Message:** `You have been marked absent for {course code} - {course name} from time {time} on {date}`

### Template Features
- Professional HTML design with Smart LPU branding
- Responsive layout for mobile devices
- Detailed student and course information
- Contact information and next steps
- Both HTML and text versions for compatibility

## Testing Commands

### Test Email Configuration
```bash
python manage.py shell
>>> from attendance.email_utils import send_absence_notification
>>> from attendance.models import Student, AttendanceSession
>>> student = Student.objects.first()
>>> session = AttendanceSession.objects.first()
>>> send_absence_notification(student, session)
```

### Test Custom Report
```bash
# Send test report to your email
python manage.py send_custom_report --email your-email@example.com --days 1
```

## Troubleshooting

### Common Issues

1. **Email not sending:**
   - Check `.env` file configuration
   - Verify SMTP settings in `settings.py`
   - Check email recipient addresses in student records

2. **Command not found:**
   - Ensure you're in the project directory
   - Activate virtual environment
   - Run `python manage.py help` to verify commands

3. **No attendance records:**
   - Check if attendance sessions exist
   - Verify date range includes actual sessions
   - Ensure course codes are correct

### Debug Mode
Add `--verbosity 2` to commands for detailed output:

```bash
python manage.py send_attendance_reports --type all --verbosity 2
```

## Best Practices

1. **Schedule reports during off-peak hours**
2. **Test with small date ranges first**
3. **Monitor email delivery rates**
4. **Keep email templates updated**
5. **Regular backup of attendance data**
6. **Use appropriate email addresses for different report types**

## Security Notes

- Email addresses are pulled from student records
- Reports contain sensitive attendance data
- Use secure email transmission (TLS/SSL)
- Consider access controls for custom reports
- Log report generation for audit purposes
