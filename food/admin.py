from django.contrib import admin

from .models import BreakSlot, FoodItem, PreOrder


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
