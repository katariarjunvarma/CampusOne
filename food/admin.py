from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import Group, Permission
from django.db.models import Q

from .models import (
    BreakSlot,
    BulkOrder,
    EmergencyAlert,
    FoodItem,
    LoyaltyPoints,
    PreOrder,
    Stall,
    StallOwner,
    UserProfile,
)


User = get_user_model()


def setup_groups():
    """
    Create Teacher and StallOwner groups with required permissions.
    Call this on startup or when needed.
    """
    # Teacher Group
    teacher_group, _ = Group.objects.get_or_create(name="Teacher")
    teacher_perms = Permission.objects.filter(
        Q(codename__in=[
            # Attendance permissions
            'view_student',
            'view_course',
            'view_section',
            'view_courseoffering',
            'add_attendancesession',
            'change_attendancesession',
            'view_attendancesession',
            'add_attendancerecord',
            'change_attendancerecord',
            'view_attendancerecord',
        ]) |
        Q(content_type__app_label='attendance', codename__startswith='view_')
    )
    teacher_group.permissions.set(teacher_perms)

    # StallOwner Group
    stallowner_group, _ = Group.objects.get_or_create(name="StallOwner")
    stallowner_perms = Permission.objects.filter(
        Q(codename__in=[
            # Food module permissions
            'view_stall',
            'add_fooditem',
            'change_fooditem',
            'view_fooditem',
            'view_preorder',
            'view_bulkorder',
            'view_breakslot',
        ])
    )
    stallowner_group.permissions.set(stallowner_perms)

    return teacher_group, stallowner_group


class StallOwnerInline(admin.StackedInline):
    model = StallOwner
    can_delete = True
    extra = 0


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    extra = 0
    fields = ('owner_status',)


class UserAdmin(DjangoUserAdmin):
    inlines = [UserProfileInline, StallOwnerInline]

    def is_stall_owner(self, obj):
        return StallOwner.objects.filter(user=obj).exists()

    is_stall_owner.boolean = True
    is_stall_owner.short_description = "Stall owner"

    def get_owner_status(self, obj):
        try:
            return obj.profile.owner_status
        except UserProfile.DoesNotExist:
            return False

    get_owner_status.boolean = True
    get_owner_status.short_description = "Owner Status"

    def get_role(self, obj):
        if obj.is_superuser:
            return "Admin"
        elif hasattr(obj, 'profile') and obj.profile.owner_status:
            return "Stall Owner"
        elif obj.is_staff:
            return "Teacher"
        return "Student"

    get_role.short_description = "Role"

    list_display = tuple(getattr(DjangoUserAdmin, "list_display", ())) + ("get_role", "is_stall_owner", "get_owner_status")

    # Hide manual permission selection, show only groups
    filter_horizontal = ()

    def save_model(self, request, obj, form, change):
        """
        Auto-assign groups based on user role:
        - Superuser: No group needed (all permissions)
        - Staff + Owner Status: StallOwner group
        - Staff only (no owner_status): Teacher group
        """
        # First save the user
        super().save_model(request, obj, form, change)

        # Ensure profile exists
        UserProfile.objects.get_or_create(user=obj)

        # Setup groups if they don't exist
        teacher_group, stallowner_group = setup_groups()

        # Clear existing groups (to prevent duplicate/conflicting assignments)
        obj.groups.clear()

        # Clear user-specific permissions (they should come from groups)
        obj.user_permissions.clear()

        # Assign group based on role
        if obj.is_superuser:
            # Superusers don't need any groups - they have all permissions
            pass
        elif obj.profile.owner_status:
            # Stall Owner role
            obj.groups.add(stallowner_group)
        elif obj.is_staff:
            # Teacher role (staff but not owner)
            obj.groups.add(teacher_group)

        # Save again to persist group changes
        obj.save()


try:
    admin.site.unregister(User)
except Exception:
    pass

admin.site.register(User, UserAdmin)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'owner_status', 'created_at')
    list_filter = ('owner_status',)
    search_fields = ('user__username', 'user__email')


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
