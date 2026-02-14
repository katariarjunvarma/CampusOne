from __future__ import annotations

from django.utils import timezone
from django.db.models import Q

from .models import EmergencyAlert


def emergency_alerts(request):
    now = timezone.now()
    qs = EmergencyAlert.objects.filter(is_active=True).filter(
        Q(expires_at__isnull=True) | Q(expires_at__gt=now)
    )

    # Show highest severity first, then latest
    severity_order = {
        "critical": 4,
        "high": 3,
        "medium": 2,
        "low": 1,
    }
    alerts = list(qs.order_by("-created_at")[:5])
    alerts.sort(key=lambda a: severity_order.get(a.severity, 0), reverse=True)

    is_stall_owner = False
    is_stall_owner_only = False
    stall_name = None
    user = getattr(request, "user", None)
    if user and getattr(user, "is_authenticated", False):
        try:
            from .models import StallOwner

            is_stall_owner_obj = StallOwner.objects.filter(user=user).first()
            is_stall_owner = bool(is_stall_owner_obj)
            is_stall_owner_only = bool(is_stall_owner and not getattr(user, "is_superuser", False))
            
            if is_stall_owner_obj:
                stall_name = is_stall_owner_obj.stall.name
            else:
                stall_name = None
        except Exception:
            is_stall_owner = False
            is_stall_owner_only = False
            stall_name = None

    return {
        "emergency_alerts": alerts,
        "is_stall_owner": is_stall_owner,
        "is_stall_owner_only": is_stall_owner_only,
        "stall_name": stall_name,
    }
