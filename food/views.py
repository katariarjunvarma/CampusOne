from __future__ import annotations

import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from datetime import date as _date

from .forms import CancelOrderForm, PreOrderForm
from .models import BreakSlot, FoodItem, PreOrder


def _require_staff(request: HttpRequest) -> bool:
    if bool(getattr(request.user, "is_staff", False)):
        return True
    messages.error(request, "Food Pre-Order is available for staff users only.")
    return False


@login_required
def food_home(request: HttpRequest) -> HttpResponse:
    if not _require_staff(request):
        return redirect("home")
    today = timezone.localdate()
    items_count = FoodItem.objects.filter(is_active=True).count()
    slots_count = BreakSlot.objects.count()
    return render(
        request,
        "food/home.html",
        {
            "today": today,
            "items_count": items_count,
            "slots_count": slots_count,
        },
    )


@login_required
def food_menu(request: HttpRequest) -> HttpResponse:
    if not _require_staff(request):
        return redirect("home")
    items = FoodItem.objects.filter(is_active=True).order_by("stall_name", "name")
    slots = BreakSlot.objects.all().order_by("start_time")
    return render(
        request,
        "food/menu.html",
        {
            "items": items,
            "slots": slots,
        },
    )


@login_required
def create_order(request: HttpRequest) -> HttpResponse:
    if not _require_staff(request):
        return redirect("home")

    if request.method == "POST":
        cart_json = (request.POST.get("cart_json") or "").strip()
        if cart_json:
            try:
                cart = json.loads(cart_json)
            except Exception:
                cart = None

            slot_id = request.POST.get("slot")
            try:
                slot = BreakSlot.objects.get(id=int(slot_id))
            except Exception:
                slot = None

            if not isinstance(cart, list) or not slot:
                messages.error(request, "Please select a break slot and add at least one item.")
                return redirect("food:create_order")

            # Validate single-stall policy
            stall_names = set()
            for row in cart:
                if not isinstance(row, dict):
                    continue
                try:
                    food_id = int(row.get("id"))
                    food_item = FoodItem.objects.get(id=food_id, is_active=True)
                    stall_names.add(food_item.stall_name)
                except Exception:
                    continue
            
            if len(stall_names) > 1:
                messages.error(request, "Orders must be from a single stall only. Please order from one stall at a time.")
                return redirect("food:create_order")

            order_date = timezone.localdate()
            created_count = 0
            updated_count = 0

            for row in cart:
                if not isinstance(row, dict):
                    continue
                try:
                    food_id = int(row.get("id"))
                    qty = int(row.get("qty"))
                except Exception:
                    continue

                if qty < 1:
                    continue
                if qty > 6:
                    qty = 6

                try:
                    food_item = FoodItem.objects.get(id=food_id, is_active=True)
                except FoodItem.DoesNotExist:
                    continue

                obj, created = PreOrder.objects.get_or_create(
                    ordered_by=request.user,
                    food_item=food_item,
                    slot=slot,
                    order_date=order_date,
                    defaults={"quantity": qty, "status": PreOrder.STATUS_PENDING},
                )
                if created:
                    created_count += 1
                else:
                    if obj.status != PreOrder.STATUS_PENDING:
                        continue
                    obj.quantity = int(obj.quantity) + qty
                    obj.save(update_fields=["quantity"])
                    updated_count += 1

            if created_count or updated_count:
                messages.success(request, "Order placed successfully.")
                return redirect("food:my_orders")

            messages.error(request, "No valid items were found in your cart.")
            return redirect("food:create_order")

        form = PreOrderForm(request.POST)
        if form.is_valid():
            food_item: FoodItem = form.cleaned_data["food_item"]
            slot: BreakSlot = form.cleaned_data["slot"]
            order_date = timezone.localdate()
            quantity = int(form.cleaned_data["quantity"])

            obj, created = PreOrder.objects.get_or_create(
                ordered_by=request.user,
                food_item=food_item,
                slot=slot,
                order_date=order_date,
                defaults={"quantity": quantity, "status": PreOrder.STATUS_PENDING},
            )
            if not created:
                if obj.status != PreOrder.STATUS_PENDING:
                    messages.error(
                        request,
                        "This order is already processed and cannot be changed.",
                    )
                    return redirect("food:my_orders")
                obj.quantity = int(obj.quantity) + quantity
                obj.save(update_fields=["quantity"])

            messages.success(request, "Order placed successfully.")
            return redirect("food:my_orders")
    else:
        form = PreOrderForm()

    items = FoodItem.objects.filter(is_active=True).order_by("category", "name")
    categories = (
        FoodItem.objects.filter(is_active=True)
        .values_list("category", flat=True)
        .distinct()
        .order_by("category")
    )
    stalls = (
        FoodItem.objects.filter(is_active=True)
        .values_list("stall_name", flat=True)
        .distinct()
        .order_by("stall_name")
    )
    locations = (
        FoodItem.objects.filter(is_active=True)
        .values_list("location", flat=True)
        .distinct()
        .order_by("location")
    )
    slots = BreakSlot.objects.all().order_by("start_time")

    return render(
        request,
        "food/order.html",
        {
            "form": form,
            "today_str": timezone.localdate().strftime("%d/%m/%y"),
            "items": items,
            "categories": categories,
            "stalls": stalls,
            "locations": locations,
            "slots": slots,
        },
    )


@login_required
def my_orders(request: HttpRequest) -> HttpResponse:
    if not _require_staff(request):
        return redirect("home")

    if request.method == "POST":
        cancel_form = CancelOrderForm(request.POST)
        if cancel_form.is_valid():
            order = get_object_or_404(PreOrder, id=cancel_form.cleaned_data["order_id"])
            if order.ordered_by_id != request.user.id:
                messages.error(request, "You cannot cancel someone else's order.")
                return redirect("food:my_orders")
            if order.status != PreOrder.STATUS_PENDING:
                messages.error(request, "Only pending orders can be cancelled.")
                return redirect("food:my_orders")
            order.delete()
            messages.success(request, "Order cancelled.")
            return redirect("food:my_orders")

    day_str = (request.GET.get("date") or "").strip()
    if day_str:
        try:
            day = _date.fromisoformat(day_str)
        except Exception:
            day = timezone.localdate()
    else:
        day = timezone.localdate()

    orders = (
        PreOrder.objects.select_related("food_item", "slot")
        .filter(order_date=day, ordered_by=request.user)
        .order_by("slot__start_time", "created_at")
    )
    return render(
        request,
        "food/my_orders.html",
        {
            "orders": orders,
            "day": day,
            "cancel_form": CancelOrderForm(),
        },
    )


@login_required
def food_dashboard(request: HttpRequest) -> HttpResponse:
    if not _require_staff(request):
        return redirect("home")

    day_str = (request.GET.get("date") or "").strip()
    if day_str:
        try:
            day = _date.fromisoformat(day_str)
        except Exception:
            day = timezone.localdate()
    else:
        day = timezone.localdate()

    by_item = (
        PreOrder.objects.filter(order_date=day, ordered_by=request.user)
        .values("food_item__name")
        .annotate(total_qty=Sum("quantity"))
        .order_by("-total_qty", "food_item__name")
    )
    by_slot = (
        PreOrder.objects.filter(order_date=day, ordered_by=request.user)
        .values("slot__name", "slot__start_time")
        .annotate(total_qty=Sum("quantity"))
        .order_by("-total_qty", "slot__start_time")
    )

    peak_slot = by_slot[0] if by_slot else None
    return render(
        request,
        "food/dashboard.html",
        {
            "day": day,
            "by_item": list(by_item),
            "by_slot": list(by_slot),
            "peak_slot": peak_slot,
        },
    )
