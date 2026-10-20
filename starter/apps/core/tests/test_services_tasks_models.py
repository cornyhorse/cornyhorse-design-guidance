from datetime import timedelta

import pytest
from django.utils import timezone

from apps.core import services
from apps.core.models import Heartbeat
from apps.core.tasks import record_heartbeat

pytestmark = pytest.mark.django_db


def test_the_task_writes_one_row_and_returns_its_id():
    pk = record_heartbeat("unit")

    assert str(Heartbeat.objects.get(source="unit").pk) == pk


def test_delay_runs_inline_in_unit_tests():
    services.enqueue_heartbeat("queued")

    assert Heartbeat.objects.filter(source="queued").exists()


def test_the_task_has_a_stable_name_independent_of_its_module():
    assert record_heartbeat.name == "core.record_heartbeat"


def test_last_heartbeat_is_the_newest():
    assert services.last_heartbeat() is None
    Heartbeat.objects.create(source="old")
    newest = Heartbeat.objects.create(source="new")

    assert services.last_heartbeat() == newest


def test_heartbeat_str_names_source_and_time():
    assert str(Heartbeat.objects.create(source="s")).startswith("s @ ")


@pytest.mark.parametrize(
    ("seconds", "phrase"),
    [(0, "0 s ago"), (59, "59 s ago"), (60, "1 min ago"), (3599, "59 min ago"), (3600, "1 h ago"), (86399, "23 h ago"), (86400, "1 d ago"), (259200, "3 d ago")],
)
def test_age_phrase(seconds, phrase):
    now = timezone.now()

    assert services.age_phrase(now - timedelta(seconds=seconds), now) == phrase


def test_age_phrase_never_goes_negative_and_defaults_to_now():
    assert services.age_phrase(timezone.now() + timedelta(minutes=5)) == "0 s ago"


def test_the_user_model_is_the_custom_one_with_a_uuid_key(user):
    from django.contrib.auth import get_user_model

    assert get_user_model()._meta.label == "accounts.User"
    assert len(str(user.pk)) == 36
