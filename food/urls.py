from django.shortcuts import redirect
from django.urls import path

from . import views

app_name = "food"

urlpatterns = [
    path("", views.food_home, name="food_home"),
    path("menu/", lambda req: redirect("food:create_order"), name="food_menu"),
    path("order/", views.create_order, name="create_order"),
    path("bulk-orders/submit/", views.submit_bulk_order, name="submit_bulk_order"),
    path("my-orders/", views.my_orders, name="my_orders"),
    path("my-orders/updates/", views.my_orders_updates, name="my_orders_updates"),
    path("dashboard/", views.food_dashboard, name="food_dashboard"),
    path("vendor/", views.vendor_dashboard, name="vendor_dashboard"),
    path("vendor/updates/", views.vendor_updates, name="vendor_updates"),
    path("vendor/update/", views.vendor_update_order, name="vendor_update_order"),
    path("vendor/remind/", views.vendor_remind_order, name="vendor_remind_order"),
    path("vendor/menu/", views.vendor_menu, name="vendor_menu"),
    path("vendor/toggle-item/", views.vendor_toggle_item, name="vendor_toggle_item"),
    path("vendor/bulk-orders/", views.vendor_bulk_orders, name="vendor_bulk_orders"),
    path("vendor/bulk-orders/update/", views.vendor_update_bulk_status, name="vendor_update_bulk_status"),
    path("admin/", views.food_admin_dashboard, name="food_admin_dashboard"),
    path("admin/stall/<int:stall_id>/toggle/", views.food_admin_stall_toggle, name="food_admin_stall_toggle"),
    path("admin/item/create/", views.food_admin_item_create, name="food_admin_item_create"),
    path("admin/item/<int:item_id>/edit/", views.food_admin_item_edit, name="food_admin_item_edit"),
    path("admin/item/<int:item_id>/delete/", views.food_admin_item_delete, name="food_admin_item_delete"),
    path("admin/clear-history/", views.food_admin_clear_history, name="food_admin_clear_history"),
]
