from django.urls import path

from . import views, views_manage

urlpatterns = [
    path("", views.home, name="home"),
    path("attendance/", views.attendance_home, name="attendance_home"),
    path("manage/", views.manage_dashboard, name="manage_dashboard"),
    path("manage/system/", views.manage_system, name="manage_system"),
    path("campus-resources/", views.manage_system, name="campus_resources_dashboard"),
    path("manage/blocks/", views.manage_blocks, name="manage_blocks"),
    path("manage/blocks/new/", views.manage_block_create, name="manage_block_create"),
    path("manage/blocks/<int:block_id>/edit/", views.manage_block_edit, name="manage_block_edit"),
    path("manage/blocks/<int:block_id>/delete/", views.manage_block_delete, name="manage_block_delete"),
    path("manage/classrooms/", views.manage_classrooms, name="manage_classrooms"),
    path("manage/classrooms/new/", views.manage_classroom_create, name="manage_classroom_create"),
    path(
        "manage/classrooms/<int:classroom_id>/edit/",
        views.manage_classroom_edit,
        name="manage_classroom_edit",
    ),
    path(
        "manage/classrooms/<int:classroom_id>/delete/",
        views.manage_classroom_delete,
        name="manage_classroom_delete",
    ),
    path("manage/faculty/", views.manage_faculty, name="manage_faculty"),
    path("manage/faculty/new/", views.manage_faculty_create, name="manage_faculty_create"),
    path("manage/faculty/<int:faculty_id>/edit/", views.manage_faculty_edit, name="manage_faculty_edit"),
    path(
        "manage/faculty/<int:faculty_id>/delete/",
        views.manage_faculty_delete,
        name="manage_faculty_delete",
    ),
    path("manage/course-offerings/", views.manage_course_offerings, name="manage_course_offerings"),
    path(
        "manage/course-offerings/new/",
        views.manage_course_offering_create,
        name="manage_course_offering_create",
    ),
    path(
        "manage/course-offerings/<int:offering_id>/edit/",
        views.manage_course_offering_edit,
        name="manage_course_offering_edit",
    ),
    path(
        "manage/course-offerings/<int:offering_id>/delete/",
        views.manage_course_offering_delete,
        name="manage_course_offering_delete",
    ),
    path(
        "manage/reports/block-utilization/",
        views_manage.report_block_utilization,
        name="report_block_utilization",
    ),
    path(
        "manage/reports/capacity-utilization/",
        views_manage.report_capacity_utilization,
        name="report_capacity_utilization",
    ),
    path(
        "manage/reports/workload-distribution/",
        views.report_workload_distribution,
        name="report_workload_distribution",
    ),
    path("manage/students/", views.manage_students, name="manage_students"),
    path("manage/students/new/", views.manage_student_create, name="manage_student_create"),
    path("manage/students/<int:student_id>/edit/", views.manage_student_edit, name="manage_student_edit"),
    path("manage/students/<int:student_id>/delete/", views.manage_student_delete, name="manage_student_delete"),
    path("manage/students/sections/", views_manage.manage_sections, name="manage_sections"),
    path("manage/students/sections/new/", views_manage.manage_section_create, name="manage_section_create"),
    path(
        "manage/students/sections/<int:section_id>/delete/",
        views_manage.manage_section_delete,
        name="manage_section_delete",
    ),
    path(
        "manage/students/sections/<int:section_id>/courses/",
        views_manage.section_courses_json,
        name="section_courses_json",
    ),
    path(
        "manage/students/sections/allocate/",
        views_manage.manage_section_allocate_students,
        name="manage_section_allocate_students",
    ),
    path("manage/courses/", views.manage_courses, name="manage_courses"),
    path("manage/courses/new/", views.manage_course_create, name="manage_course_create"),
    path("manage/courses/<int:course_id>/delete/", views.manage_course_delete, name="manage_course_delete"),
    path("manage/enrollments/", views.manage_enrollments, name="manage_enrollments"),
    path("manage/enrollments/new/", views.manage_enrollment_create, name="manage_enrollment_create"),
    path(
        "manage/enrollments/<int:enrollment_id>/delete/",
        views.manage_enrollment_delete,
        name="manage_enrollment_delete",
    ),
    path("manage/face-samples/", views.manage_face_samples, name="manage_face_samples"),
    path("manage/face-samples/new/", views.manage_face_sample_create, name="manage_face_sample_create"),
    path(
        "manage/face-samples/delete-all/",
        views.manage_face_samples_delete_all,
        name="manage_face_samples_delete_all",
    ),
    path(
        "manage/face-samples/<int:face_sample_id>/delete/",
        views.manage_face_sample_delete,
        name="manage_face_sample_delete",
    ),
    path("manage/notifications/", views.manage_notifications, name="manage_notifications"),
    path("manage/sessions/", views.manage_sessions, name="manage_sessions"),
    path("manage/sessions/new/", views.create_session, name="create_session"),
    path("manage/records/", views.manage_records, name="manage_records"),
    path("manage/view-attendance/", views.super_admin_view_attendance, name="super_admin_view_attendance"),
    # Users Management
    path("manage/users/", views.manage_users, name="manage_users"),
    path("manage/users/new/", views.manage_user_create, name="manage_user_create"),
    path("manage/users/<int:user_id>/edit/", views.manage_user_edit, name="manage_user_edit"),
    # Stalls Management
    path("manage/stalls/", views.manage_stalls, name="manage_stalls"),
    path("manage/stalls/new/", views.manage_stall_create, name="manage_stall_create"),
    path("manage/stalls/<int:stall_id>/edit/", views.manage_stall_edit, name="manage_stall_edit"),
    path("manage/stalls/<int:stall_id>/delete/", views.manage_stall_delete, name="manage_stall_delete"),
    # Break Slots Management
    path("manage/break-slots/", views.manage_break_slots, name="manage_break_slots"),
    path("manage/break-slots/new/", views.manage_break_slot_create, name="manage_break_slot_create"),
    path("manage/break-slots/<int:slot_id>/edit/", views.manage_break_slot_edit, name="manage_break_slot_edit"),
    path("manage/break-slots/<int:slot_id>/delete/", views.manage_break_slot_delete, name="manage_break_slot_delete"),
    # Food Items Management
    path("manage/food-items/", views.manage_food_items, name="manage_food_items"),
    path("manage/food-items/new/", views.manage_food_item_create, name="manage_food_item_create"),
    path("manage/food-items/<int:item_id>/edit/", views.manage_food_item_edit, name="manage_food_item_edit"),
    path("manage/food-items/<int:item_id>/delete/", views.manage_food_item_delete, name="manage_food_item_delete"),
    # PreOrders Management
    path("manage/preorders/", views.manage_preorders, name="manage_preorders"),
    # Bulk Orders Management
    path("manage/bulk-orders/", views.manage_bulk_orders, name="manage_bulk_orders"),
    # Loyalty Points Management
    path("manage/loyalty-points/", views.manage_loyalty_points, name="manage_loyalty_points"),
    # Emergency Alerts Management
    path("manage/emergency-alerts/", views.manage_emergency_alerts, name="manage_emergency_alerts"),
    path("manage/emergency-alerts/new/", views.manage_emergency_alert_create, name="manage_emergency_alert_create"),
    path("manage/emergency-alerts/<int:alert_id>/toggle/", views.manage_emergency_alert_toggle, name="manage_emergency_alert_toggle"),
    path("manage/emergency-alerts/<int:alert_id>/delete/", views.manage_emergency_alert_delete, name="manage_emergency_alert_delete"),
    path("faculty/dashboard/", views_manage.faculty_dashboard, name="faculty_dashboard"),
    path(
        "faculty/sessions/<int:session_id>/edit/",
        views.edit_session,
        name="edit_session",
    ),
    path(
        "faculty/sessions/<int:session_id>/delete/",
        views.delete_session,
        name="delete_session",
    ),
    path(
        "faculty/sessions/<int:session_id>/view/",
        views.session_view,
        name="session_view",
    ),
    path(
        "faculty/sessions/<int:session_id>/",
        views.session_detail,
        name="session_detail",
    ),
    path(
        "faculty/sessions/<int:session_id>/live/",
        views.live_attendance_frame,
        name="live_attendance_frame",
    ),
    path(
        "faculty/sessions/<int:session_id>/mark-by-photo/",
        views.mark_attendance_by_photo,
        name="mark_attendance_by_photo",
    ),
    path(
        "faculty/sessions/<int:session_id>/mark/",
        views.mark_attendance,
        name="mark_attendance",
    ),
    # Schedule Management
    path("schedule/", views_manage.schedule_list, name="schedule_list"),
    path("schedule/add/", views_manage.schedule_create, name="schedule_create"),
    path("schedule/delete/<int:schedule_id>/", views_manage.schedule_delete, name="schedule_delete"),
    # Faculty Timetable Views
    path("faculty/timetable/", views_manage.faculty_timetable, name="faculty_timetable"),
    path("faculty/today-classes/", views_manage.faculty_today_classes, name="faculty_today_classes"),
    path("faculty/section/<int:section_id>/timetable/", views_manage.section_timetable, name="section_timetable"),
    path("faculty/schedule/<int:schedule_id>/attendance/", views_manage.mark_attendance_quick, name="mark_attendance_quick"),
    path("faculty/book-room/", views_manage.faculty_book_room, name="faculty_book_room"),
    path("faculty/book-slot/", views_manage.book_room, name="book_room"),
    path("check-room/", views_manage.check_room_availability, name="check_room_availability"),
    path("book-room-ajax/", views_manage.book_room_ajax, name="book_room_ajax"),
    # Make-Up Class & Remedial Code Module
    path("faculty/makeup-classes/", views_manage.faculty_makeup_classes, name="faculty_makeup_classes"),
    path("faculty/makeup-classes/create/", views_manage.makeup_class_create, name="makeup_class_create"),
    path("faculty/makeup-classes/<int:makeup_class_id>/", views_manage.makeup_class_detail, name="makeup_class_detail"),
    path("faculty/makeup-classes/<int:makeup_class_id>/start/", views_manage.makeup_class_start, name="makeup_class_start"),
    path("faculty/makeup-classes/<int:makeup_class_id>/complete/", views_manage.makeup_class_complete, name="makeup_class_complete"),
    path("faculty/makeup-classes/<int:makeup_class_id>/cancel/", views_manage.makeup_class_cancel, name="makeup_class_cancel"),
    # Faculty Attendance Management
    path("faculty/makeup-classes/<int:makeup_class_id>/attendance/", views_manage.makeup_class_attendance, name="makeup_class_mark_attendance"),
    path("faculty/makeup-classes/<int:makeup_class_id>/attendance/records/", views_manage.makeup_class_attendance_records, name="makeup_class_attendance_records"),
    path("faculty/makeup-classes/<int:makeup_class_id>/attendance/export/", views_manage.makeup_class_export_report, name="makeup_class_export_report"),
    path("faculty/makeup-classes/<int:makeup_class_id>/reminder/", views_manage.makeup_class_send_reminder, name="makeup_class_send_reminder"),
    # Admin Make-Up Class Management
    path("admin/makeup-classes/", views_manage.admin_makeup_classes, name="admin_makeup_classes"),
    path("admin/makeup-classes/<int:makeup_class_id>/", views_manage.admin_makeup_class_detail, name="admin_makeup_class_detail"),
    path("admin/makeup-classes/<int:makeup_class_id>/cancel/", views_manage.admin_makeup_class_cancel, name="admin_makeup_class_cancel"),
    path("admin/makeup-classes/stats/", views_manage.admin_makeup_class_stats, name="admin_makeup_class_stats"),
    path("admin/makeup-classes/audit/", views_manage.admin_remedial_code_audit, name="admin_remedial_code_audit"),
    # AI Smart Scheduling & Rush Prediction
    path("faculty/smart-scheduling/", views_manage.smart_scheduling_recommendations, name="smart_scheduling"),
    path("faculty/class-rush-prediction/", views_manage.class_rush_prediction, name="class_rush_prediction"),
]
