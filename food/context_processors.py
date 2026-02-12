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

    return {"emergency_alerts": alerts}
