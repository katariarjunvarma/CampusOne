from __future__ import annotations

import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from datetime import date as _date

from .forms import CancelOrderForm, PreOrderForm
from .models import BreakSlot, BulkOrder, FoodItem, LoyaltyPoints, PreOrder


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

    def _award_points(user, points: int, stall_name: str = "") -> dict:
        """Award points with all bonus calculations. Returns dict with breakdown."""
        if not user or points <= 0:
            return {"total": 0, "breakdown": []}
        
        lp, _ = LoyaltyPoints.objects.get_or_create(user=user)
        today = timezone.localdate()
        breakdown = []
        total_bonus = 0
        
        # Base points for order
        base_points = points
        breakdown.append(f"Base order: +{base_points}")
        total_bonus += base_points
        
        # 1. First Order Bonus (+5 points for first ever order)
        if not lp.first_order_bonus:
            total_bonus += 5
            lp.first_order_bonus = True
            breakdown.append("First order bonus: +5")
        
        # 2. First Order of the Week (+2 points)
        week_start = today - timezone.timedelta(days=today.weekday())  # Monday
        if not lp.weekly_first_order_date or lp.weekly_first_order_date < week_start:
            # New week, reset weekly counter
            lp.weekly_first_order_date = today
            lp.weekly_orders_count = 1
            total_bonus += 2
            breakdown.append("First order of week: +2")
        else:
            lp.weekly_orders_count += 1
        
        # 3. Regular Customer Bonus (+10 for 6+ orders/week from same stall)
        if stall_name and lp.weekly_orders_count >= 6:
            if lp.favorite_stall == stall_name:
                # Already tracking this stall
                lp.favorite_stall_orders += 1
                if lp.favorite_stall_orders == 6:
                    total_bonus += 10
                    breakdown.append("Regular customer bonus (6+ orders): +10")
            else:
                # New favorite stall
                lp.favorite_stall = stall_name
                lp.favorite_stall_orders = 1
        
        # 4. 7-Day Streak Bonus (+15 for consecutive daily orders)
        if lp.last_order_date:
            days_diff = (today - lp.last_order_date).days
            if days_diff == 1:
                # Consecutive day
                lp.current_streak += 1
                if lp.current_streak == 7:
                    total_bonus += 15
                    breakdown.append("7-day streak bonus: +15")
            elif days_diff > 1:
                # Streak broken, reset
                lp.current_streak = 1
        else:
            lp.current_streak = 1
        
        lp.last_order_date = today
        lp.total_points = int(lp.total_points) + total_bonus
        lp.points_earned = int(lp.points_earned) + total_bonus
        lp.save()
        
        return {"total": total_bonus, "breakdown": breakdown}

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
            points_awarded = 0

            # Get packaging option from POST data
            packaging = request.POST.get("packaging", PreOrder.PACK_EAT)
            if packaging not in (PreOrder.PACK_EAT, PreOrder.PACK_PARCEL):
                packaging = PreOrder.PACK_EAT

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
                    defaults={"quantity": qty, "status": PreOrder.STATUS_PENDING, "packaging_option": packaging},
                )
                if created:
                    created_count += 1
                    points_awarded += 1
                else:
                    if obj.status != PreOrder.STATUS_PENDING:
                        continue
                    obj.quantity = int(obj.quantity) + qty
                    obj.save(update_fields=["quantity"])
                    updated_count += 1

            if created_count or updated_count:
                # Get the stall name for loyalty tracking
                cart_stall_name = list(stall_names)[0] if len(stall_names) == 1 else ""
                
                # Handle redeemed points
                redeemed_points = int(request.POST.get("redeemed_points") or 0)
                discount_amount = 0
                if redeemed_points > 0:
                    try:
                        lp = LoyaltyPoints.objects.get(user=request.user)
                        if lp.available_points >= redeemed_points and redeemed_points >= 20:
                            lp.points_redeemed += redeemed_points
                            lp.save(update_fields=["points_redeemed"])
                            discount_amount = redeemed_points * 0.25
                    except LoyaltyPoints.DoesNotExist:
                        pass
                
                points_result = _award_points(request.user, points_awarded, cart_stall_name)
                
                if discount_amount > 0:
                    messages.success(request, f"Order placed! ₹{discount_amount:.0f} discount applied. You earned {points_result['total']} points.")
                elif points_result["total"] > 0:
                    messages.success(request, f"Order placed! You earned {points_result['total']} points.")
                else:
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
            else:
                stall_name = food_item.stall_name if hasattr(food_item, 'stall_name') else ""
                points_result = _award_points(request.user, 1, stall_name)
                if points_result["total"] > 0:
                    messages.success(request, f"Order placed! You earned {points_result['total']} points.")

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
    locations = (
        FoodItem.objects.filter(is_active=True)
        .values_list("location", flat=True)
        .distinct()
        .order_by("location")
    )
    slots = BreakSlot.objects.all().order_by("start_time")

    stalls = (
        FoodItem.objects.filter(is_active=True)
        .values("stall_name", "location")
        .distinct()
        .order_by("stall_name")
    )

    loyalty = None
    try:
        loyalty = LoyaltyPoints.objects.get(user=request.user)
    except LoyaltyPoints.DoesNotExist:
        loyalty = None

    return render(
        request,
        "food/order.html",
        {
            "form": form,
            "today_str": timezone.localdate().strftime("%d/%m/%y"),
            "items": items,
            "categories": categories,
            "locations": locations,
            "slots": slots,
            "stalls": list(stalls),
            "loyalty": loyalty,
        },
    )


@login_required
@transaction.atomic
def submit_bulk_order(request: HttpRequest) -> HttpResponse:
    if not _require_staff(request):
        return JsonResponse({"ok": False, "error": "not_allowed"}, status=403)

    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "method_not_allowed"}, status=405)

    try:
        payload = json.loads((request.body or b"{}").decode("utf-8"))
    except Exception:
        payload = None

    if not isinstance(payload, dict):
        return JsonResponse({"ok": False, "error": "invalid_payload"}, status=400)

    event_name = (payload.get("event_name") or "").strip()
    contact_person = (payload.get("contact_person") or "").strip()
    contact_phone = (payload.get("contact_phone") or "").strip()
    special_instructions = (payload.get("special_instructions") or "").strip()
    stall_name = (payload.get("stall_name") or "").strip()
    requested_items = payload.get("requested_items")

    try:
        people_count = int(payload.get("people_count"))
    except Exception:
        people_count = 0

    try:
        delivery_date = _date.fromisoformat(str(payload.get("delivery_date")))
    except Exception:
        delivery_date = None

    try:
        slot = BreakSlot.objects.get(id=int(payload.get("slot_id")))
    except Exception:
        slot = None

    if not event_name or not contact_person or not stall_name or not delivery_date or not slot:
        return JsonResponse({"ok": False, "error": "missing_fields"}, status=400)
    if people_count < 5 or people_count > 200:
        return JsonResponse({"ok": False, "error": "invalid_people_count"}, status=400)

    min_day = timezone.localdate() + timezone.timedelta(days=2)
    if delivery_date < min_day:
        return JsonResponse({"ok": False, "error": "too_soon"}, status=400)

    bo = BulkOrder.objects.create(
        created_by=request.user,
        event_name=event_name,
        people_count=people_count,
        delivery_date=delivery_date,
        slot=slot,
        stall_name=stall_name,
        contact_person=contact_person,
        contact_phone=contact_phone,
        special_instructions=special_instructions,
        requested_items_json=json.dumps(requested_items) if requested_items else "",
        status=BulkOrder.STATUS_SUBMITTED,
    )

    return JsonResponse({"ok": True, "id": bo.id})


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

    # Get all orders for the day (not just user's orders - for dashboard)
    all_orders = PreOrder.objects.filter(order_date=day)
    
    # Summary metrics
    total_orders = all_orders.count()
    total_quantity = all_orders.aggregate(total=Sum("quantity"))["total"] or 0
    missed_orders = all_orders.filter(status=PreOrder.STATUS_MISSED).count()
    
    # Demand by item
    by_item = (
        all_orders
        .values("food_item__name")
        .annotate(total_qty=Sum("quantity"))
        .order_by("-total_qty", "food_item__name")
    )
    
    # Demand by slot
    by_slot = (
        all_orders
        .values("slot__name", "slot__start_time")
        .annotate(total_qty=Sum("quantity"))
        .order_by("-total_qty", "slot__start_time")
    )
    
    # Stall-wise breakdown
    by_stall = (
        all_orders
        .values("food_item__stall_name", "food_item__location")
        .annotate(total_qty=Sum("quantity"))
        .order_by("-total_qty", "food_item__stall_name")
    )

    peak_slot = by_slot[0] if by_slot else None

    loyalty = None
    try:
        loyalty = LoyaltyPoints.objects.get(user=request.user)
    except LoyaltyPoints.DoesNotExist:
        loyalty = None
    
    return render(
        request,
        "food/dashboard.html",
        {
            "day": day,
            "total_orders": total_orders,
            "total_quantity": total_quantity,
            "missed_orders": missed_orders,
            "by_item": list(by_item),
            "by_slot": list(by_slot),
            "by_stall": list(by_stall),
            "peak_slot": peak_slot,
            "loyalty": loyalty,
        },
    )
