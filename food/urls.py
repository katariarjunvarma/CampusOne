from django.urls import path

from . import views

app_name = "food"

urlpatterns = [
    path("", views.food_home, name="food_home"),
    path("menu/", views.food_menu, name="food_menu"),
    path("order/", views.create_order, name="create_order"),
    path("my-orders/", views.my_orders, name="my_orders"),
    path("dashboard/", views.food_dashboard, name="food_dashboard"),
]
