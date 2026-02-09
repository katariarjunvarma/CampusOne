"""
Django management command to send attendance reports
"""
from django.core.management.base import BaseCommand
from attendance.email_utils import (
    check_and_send_low_attendance_warnings,
    send_monthly_sumaries_to_all_students
)


class Command(BaseCommand):
    help = 'Send attendance reports (low attendance warnings, monthly summaries, etc.)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            type=str,
            choices=['warnings', 'monthly', 'all'],
            default='all',
            help='Type of report to send: warnings, monthly, or all'
        )
        parser.add_argument(
            '--month',
            type=int,
            help='Month for monthly summary (1-12)'
        )
        parser.add_argument(
            '--year',
            type=int,
            help='Year for monthly summary'
        )

    def handle(self, *args, **options):
        report_type = options['type']
        
        self.stdout.write(self.style.SUCCESS(f'Sending attendance reports...'))
        
        if report_type in ['warnings', 'all']:
            self.stdout.write('Checking for low attendance warnings...')
            check_and_send_low_attendance_warnings()
            self.stdout.write(self.style.SUCCESS('✓ Low attendance warnings sent'))
        
        if report_type in ['monthly', 'all']:
            self.stdout.write('Sending monthly attendance summaries...')
            send_monthly_sumaries_to_all_students()
            self.stdout.write(self.style.SUCCESS('✓ Monthly summaries sent'))
        
        self.stdout.write(self.style.SUCCESS('All attendance reports sent successfully!'))
