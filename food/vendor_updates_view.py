@login_required
def vendor_updates(request: HttpRequest) -> HttpResponse:
    """API Endpoint for Vendor Dashboard Realtime Updates"""
    stall_owner = _get_stall_owner(request)
    if not stall_owner or not stall_owner.is_active:
        return JsonResponse({"ok": False})

    today = timezone.localdate()
    all_orders = (
        PreOrder.objects.select_related("food_item", "slot", "ordered_by")
        .filter(food_item__stall=stall_owner.stall, order_date=today)
        .order_by("slot__start_time", "created_at")
    )

    pending_orders = all_orders.filter(status=PreOrder.STATUS_PENDING)
    cooking_orders = all_orders.filter(status=PreOrder.STATUS_COOKING)
    ready_orders = all_orders.filter(status=PreOrder.STATUS_READY)
    collected_orders = all_orders.filter(status=PreOrder.STATUS_COLLECTED)
    missed_orders = all_orders.filter(status=PreOrder.STATUS_MISSED)

    data = {
        "ok": True,
        "counts": {
            "pending": pending_orders.count(),
            "cooking": cooking_orders.count(),
            "ready": ready_orders.count(),
            "collected": collected_orders.count(),
            "missed": missed_orders.count(),
        },
        "sections": {
            "pending": render_to_string("food/partials/vendor_table.html", {"orders": pending_orders, "status": "pending"}),
            "cooking": render_to_string("food/partials/vendor_table.html", {"orders": cooking_orders, "status": "cooking"}),
            "ready": render_to_string("food/partials/vendor_table.html", {"orders": ready_orders, "status": "ready"}),
            "collected": render_to_string("food/partials/vendor_table.html", {"orders": collected_orders, "status": "completed"}),
            "missed": render_to_string("food/partials/vendor_table.html", {"orders": missed_orders, "status": "missed"}),
        }
    }
    return JsonResponse(data)
