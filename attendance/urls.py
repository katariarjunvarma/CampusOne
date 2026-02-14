from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("attendance/", views.attendance_home, name="attendance_home"),
    path("manage/", views.manage_dashboard, name="manage_dashboard"),
    path("manage/students/", views.manage_students, name="manage_students"),
    path("manage/students/new/", views.manage_student_create, name="manage_student_create"),
    path("manage/students/<int:student_id>/edit/", views.manage_student_edit, name="manage_student_edit"),
    path("manage/students/<int:student_id>/delete/", views.manage_student_delete, name="manage_student_delete"),
    path("manage/courses/", views.manage_courses, name="manage_courses"),
    path("manage/courses/new/", views.manage_course_create, name="manage_course_create"),
    path("manage/courses/<int:course_id>/delete/", views.manage_course_delete, name="manage_course_delete"),
    path("manage/enrollments/", views.manage_enrollments, name="manage_enrollments"),
    path("manage/enrollments/new/", views.manage_enrollment_create, name="manage_enrollment_create"),
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
    path("faculty/sessions/new/", views.create_session, name="create_session"),
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
]
