from unittest.mock import patch

import pytest
from django.db.utils import OperationalError

from apps.core.models import Heartbeat

pytestmark = pytest.mark.django_db


def test_home_requires_sign_in(client):
    response = client.get("/")

    assert response.status_code == 302
    assert response["Location"] == "/login/?next=/"


def test_home_without_a_heartbeat_says_so(signed_in):
    response = signed_in.get("/")

    assert response.status_code == 200
    assert b"No heartbeat yet" in response.content
    assert b"Needs attention" in response.content


def test_home_shows_the_latest_heartbeat_and_how_old_it_is(signed_in):
    Heartbeat.objects.create(source="worker-a")

    response = signed_in.get("/")

    assert b"worker-a" in response.content
    assert b"0 s ago" in response.content


def test_queueing_a_heartbeat_writes_a_row_and_confirms(signed_in):
    response = signed_in.post("/heartbeat/", follow=True)

    assert Heartbeat.objects.filter(source="web").count() == 1
    assert b"Heartbeat queued" in response.content


def test_heartbeat_is_post_only(signed_in):
    assert signed_in.get("/heartbeat/").status_code == 405


def test_heartbeat_requires_sign_in(client):
    assert client.post("/heartbeat/").status_code == 302
    assert Heartbeat.objects.count() == 0


def test_design_reference_is_public_and_shows_every_state(client):
    response = client.get("/design/")

    assert response.status_code == 200
    for label in (b"Up", b"Degraded", b"Down", b"Stale", b"Expected offline", b"Site unreachable", b"Unknown", b"Overcommitted"):
        assert label in response.content


def test_sign_in_and_out(client, user):
    assert client.post("/login/", {"username": "alice", "password": "correct horse battery staple"}).status_code == 302
    assert client.get("/").status_code == 200

    assert client.post("/logout/").status_code == 302
    assert client.get("/").status_code == 302


def test_healthz_is_ok_when_the_database_answers(client):
    response = client.get("/healthz/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_healthz_is_503_when_the_database_does_not():
    from django.test import Client

    with patch("apps.core.views.connection") as connection:
        connection.cursor.side_effect = OperationalError("connection refused")
        response = Client().get("/healthz/")

    assert response.status_code == 503
    assert response.json() == {"status": "database unavailable"}


def test_the_product_name_comes_from_settings(client, settings):
    settings.SITE_NAME = "Renamed"

    assert b"Renamed" in client.get("/design/").content


def test_the_login_page_shows_our_name_not_the_host(client, settings):
    """Django's LoginView injects its own `site_name` (the request host) into the context; ours must not collide."""
    settings.SITE_NAME = "Renamed"

    html = client.get("/login/", HTTP_HOST="example.test").content.decode()

    assert "<span>Renamed</span>" in html
    assert "example.test" not in html
