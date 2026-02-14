from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import (
    BreakSlot,
    BulkOrder,
    EmergencyAlert,
    FoodItem,
    LoyaltyPoints,
    PreOrder,
    Stall,
    StallOwner,
)


User = get_user_model()


class StallOwnerInline(admin.StackedInline):
    model = StallOwner
    can_delete = True
    extra = 0


class UserAdmin(DjangoUserAdmin):
    inlines = [StallOwnerInline]

    def is_stall_owner(self, obj):
        return StallOwner.objects.filter(user=obj).exists()

    is_stall_owner.boolean = True
    is_stall_owner.short_description = "Stall owner"

    list_display = tuple(getattr(DjangoUserAdmin, "list_display", ())) + ("is_stall_owner",)


try:
    admin.site.unregister(User)
except Exception:
    pass

admin.site.register(User, UserAdmin)


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
    actions = ["clear_weekly_history", "clear_all_history"]

    @admin.action(description="Clear orders older than 7 days")
    def clear_weekly_history(self, request, queryset):
        from django.utils import timezone
        from datetime import timedelta
        cutoff = timezone.localdate() - timedelta(days=7)
        deleted_count, _ = PreOrder.objects.filter(order_date__lt=cutoff).delete()
        self.message_user(request, f"Cleared {deleted_count} orders older than 7 days.")

    @admin.action(description="Clear ALL orders (Warning: Clears everything)")
    def clear_all_history(self, request, queryset):
        # We use the queryset if selected, or all if we want a global button (but actions are usually selection-based).
        # To make it global-like, we can ignore queryset, but that's confusing.
        # Let's just make it delete the SELECTED ones, but rename it "Delete Selected History".
        # Actually, the user asked for a "clear food history button".
        # Best way is to delete ALL.
        count, _ = PreOrder.objects.all().delete()
        self.message_user(request, f"Cleared ALL {count} food orders history.")



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


@admin.register(Stall)
class StallAdmin(admin.ModelAdmin):
    list_display = ("name", "location", "is_active", "created_at")
    list_filter = ("is_active", "location")
    search_fields = ("name", "location")


@admin.register(StallOwner)
class StallOwnerAdmin(admin.ModelAdmin):
    list_display = ("user", "stall", "phone", "is_active", "created_at")
    list_filter = ("is_active", "stall")
    search_fields = ("user__username", "user__email", "stall__name", "phone")
