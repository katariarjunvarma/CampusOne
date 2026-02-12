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
    path("dashboard/", views.food_dashboard, name="food_dashboard"),
    path("admin/", views.food_admin_dashboard, name="food_admin_dashboard"),
    path("admin/stall/<int:stall_id>/toggle/", views.food_admin_stall_toggle, name="food_admin_stall_toggle"),
    path("admin/item/create/", views.food_admin_item_create, name="food_admin_item_create"),
    path("admin/item/<int:item_id>/edit/", views.food_admin_item_edit, name="food_admin_item_edit"),
    path("admin/item/<int:item_id>/delete/", views.food_admin_item_delete, name="food_admin_item_delete"),
]
