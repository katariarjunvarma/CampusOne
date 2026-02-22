from django.contrib import admin

from .models import AttendanceRecord, AttendanceSession, Course, Enrollment, FaceSample, Notification, Student


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("registration_number", "full_name", "email", "student_phone")
    search_fields = ("registration_number", "full_name", "email")


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("code", "name")
    search_fields = ("code", "name")


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("student", "course")
    list_filter = ("course",)
    search_fields = ("student__registration_number", "student__full_name", "course__code")


@admin.register(AttendanceSession)
class AttendanceSessionAdmin(admin.ModelAdmin):
    list_display = ("course", "session_date", "session_label", "created_at")
    list_filter = ("course", "session_date")


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ("session", "student", "status", "source", "updated_at")
    list_filter = ("session__course", "session__session_date", "status", "source")
    search_fields = ("student__registration_number", "student__full_name")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("recipient_student", "channel", "created_at")
    search_fields = ("recipient_student__registration_number", "recipient_student__full_name", "message")


@admin.register(FaceSample)
class FaceSampleAdmin(admin.ModelAdmin):
    list_display = ("student", "created_at")
    search_fields = ("student__registration_number", "student__full_name")


from .models import Block, Classroom, FacultyProfile, CourseOffering, Section, SectionCourseFaculty, Schedule


@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ("section_course_faculty", "classroom", "day_of_week", "time_slot")
    list_filter = ("day_of_week", "classroom__block", "section_course_faculty__course")
    search_fields = ("section_course_faculty__course__code", "classroom__room_number", "classroom__block__code")
    autocomplete_fields = ["section_course_faculty", "classroom"]


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ("name", "courses_display", "year", "semester")
    search_fields = ("name", "courses__code", "courses__name")
    list_filter = ("year", "semester")

    @admin.display(description="Courses")
    def courses_display(self, obj: Section) -> str:
        return ", ".join(obj.courses.order_by("code").values_list("code", flat=True))


@admin.register(Block)
class BlockAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_active")
    search_fields = ("code", "name")
    list_filter = ("is_active",)


@admin.register(Classroom)
class ClassroomAdmin(admin.ModelAdmin):
    list_display = ("room_number", "block", "capacity", "room_type", "is_active")
    search_fields = ("room_number", "block__code", "block__name")
    list_filter = ("block", "room_type", "is_active", "has_projector")


@admin.register(FacultyProfile)
class FacultyProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "employee_id", "department", "designation", "is_active")
    search_fields = ("user__username", "user__email", "employee_id", "department")
    list_filter = ("department", "designation", "is_active")


@admin.register(CourseOffering)
class CourseOfferingAdmin(admin.ModelAdmin):
    list_display = ("course", "faculty", "section", "is_active")
    search_fields = ("course__code", "course__name", "faculty__user__username", "section__name")
    list_filter = ("is_active",)
    autocomplete_fields = ["course", "faculty", "section"]


@admin.register(SectionCourseFaculty)
class SectionCourseFacultyAdmin(admin.ModelAdmin):
    list_display = ("section", "course", "faculty", "created_at")
    search_fields = ("section__name", "course__code", "course__name", "faculty__user__username")
    list_filter = ("section", "course")
    autocomplete_fields = ["section", "course", "faculty"]

