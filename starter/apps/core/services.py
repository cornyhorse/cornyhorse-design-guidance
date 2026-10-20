"""Business logic. Views stay thin and call these."""

from __future__ import annotations

from datetime import datetime

from django.utils import timezone

from .models import Heartbeat
from .tasks import record_heartbeat


def enqueue_heartbeat(source: str = "web") -> None:
    record_heartbeat.delay(source)


def last_heartbeat() -> Heartbeat | None:
    return Heartbeat.objects.first()


def age_phrase(then: datetime, now: datetime | None = None) -> str:
    """'11 s ago', '5 min ago', '3 h ago', '2 d ago'. A dashboard should say how stale it is."""
    seconds = max(0, int(((now or timezone.now()) - then).total_seconds()))
    for limit, unit, size in ((60, "s", 1), (3600, "min", 60), (86400, "h", 3600)):
        if seconds < limit:
            return f"{seconds // size} {unit} ago"
    return f"{seconds // 86400} d ago"
