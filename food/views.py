from django.shortcuts import render
from django.http import HttpRequest, HttpResponse
from django.contrib.auth.decorators import login_required


@login_required
def food_home(request: HttpRequest) -> HttpResponse:
    return render(request, "food/home.html")


@login_required
def food_menu(request: HttpRequest) -> HttpResponse:
    return render(request, "food/menu.html")


@login_required
def create_order(request: HttpRequest) -> HttpResponse:
    return render(request, "food/order.html")


@login_required
def my_orders(request: HttpRequest) -> HttpResponse:
    return render(request, "food/my_orders.html")


@login_required
def food_dashboard(request: HttpRequest) -> HttpResponse:
    return render(request, "food/dashboard.html")
