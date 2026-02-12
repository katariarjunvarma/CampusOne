from django.contrib import admin

from .models import BreakSlot, BulkOrder, EmergencyAlert, FoodItem, LoyaltyPoints, PreOrder


@admin.register(FoodItem)
class FoodItemAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)


@admin.register(BreakSlot)
class BreakSlotAdmin(admin.ModelAdmin):
    list_display = ("name", "start_time", "end_time")
    search_fields = ("name",)


@admin.register(PreOrder)
class PreOrderAdmin(admin.ModelAdmin):
    list_display = ("order_date", "slot", "ordered_by", "food_item", "quantity", "status", "created_at")
    list_filter = ("order_date", "slot", "status")
    search_fields = ("ordered_by__username", "food_item__name")


@admin.register(BulkOrder)
class BulkOrderAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "delivery_date",
        "slot",
        "event_name",
        "people_count",
        "stall_name",
        "created_by",
        "status",
    )
    list_filter = ("delivery_date", "slot", "status", "stall_name")
    search_fields = ("event_name", "stall_name", "created_by__username", "contact_person")


@admin.register(LoyaltyPoints)
class LoyaltyPointsAdmin(admin.ModelAdmin):
    list_display = ("user", "total_points", "points_earned", "points_redeemed", "updated_at")
    search_fields = ("user__username",)


@admin.register(EmergencyAlert)
class EmergencyAlertAdmin(admin.ModelAdmin):
    list_display = ("created_at", "severity", "alert_type", "title", "is_active", "expires_at")
    list_filter = ("is_active", "severity", "alert_type")
    search_fields = ("title", "message")
