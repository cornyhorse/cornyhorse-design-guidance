from celery import shared_task

from .models import Heartbeat


# An explicit task name decouples the queue contract from the Python module path. A web container that
# does not even import this module can still enqueue it: current_app.send_task("core.record_heartbeat").
@shared_task(name="core.record_heartbeat")
def record_heartbeat(source: str = "web") -> str:
    """Write one Heartbeat row; the smallest task that crosses web, broker, worker and database."""
    return str(Heartbeat.objects.create(source=source).pk)
