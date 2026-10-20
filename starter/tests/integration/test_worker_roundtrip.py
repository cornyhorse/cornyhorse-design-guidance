"""Integration: web side -> real broker -> a running worker container -> the real database.

Run with `make integration`. It needs the compose stack up (`worker`, `redis`, `db`) and migrated, and it
talks to the REAL database, not pytest-django's throwaway one, because the worker is a separate process.
The unit suite proves each piece; this proves the seams between them (queue names, task names, serialisation,
the worker's database settings), which is where a multi-container system actually breaks.
"""

import time
import uuid

import pytest

from apps.core.models import Heartbeat
from apps.core.tasks import record_heartbeat

pytestmark = pytest.mark.integration


@pytest.fixture
def real_database(django_db_blocker):
    with django_db_blocker.unblock():
        yield


def test_a_task_sent_by_name_is_run_by_the_worker_and_lands_in_the_database(real_database):
    from config.celery import app

    marker = f"integration-{uuid.uuid4()}"
    # Sent by NAME, exactly as a web container that does not import the task module would.
    app.send_task("core.record_heartbeat", args=[marker], queue="default")

    deadline = time.monotonic() + 30
    try:
        while time.monotonic() < deadline:
            if Heartbeat.objects.filter(source=marker).exists():
                return
            time.sleep(0.5)
        pytest.fail("no heartbeat from the worker within 30 s: is `docker compose up worker` running and migrated?")
    finally:
        Heartbeat.objects.filter(source=marker).delete()


def test_the_task_object_and_the_name_agree():
    assert record_heartbeat.name == "core.record_heartbeat"
