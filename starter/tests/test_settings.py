"""Configuration plumbing: the environment reader, DATABASE_URL, the production settings, and the entry points."""

import importlib
import sys
from contextlib import contextmanager

import pytest
from django.core.exceptions import ImproperlyConfigured

from config.env import env, env_bool, env_list
from config.settings.base import db_from_url

LONG_KEY = "k" * 64


@contextmanager
def fresh_settings_modules():
    """Import settings modules anew without disturbing the ones Django is already running with."""
    names = ("config.settings.base", "config.settings.prod")
    saved = {name: sys.modules.pop(name, None) for name in names}
    try:
        yield
    finally:
        for name, module in saved.items():
            sys.modules.pop(name, None)
            if module is not None:
                sys.modules[name] = module


def load_prod_settings(**environ):
    """The production settings as they would load with these environment variables."""
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("SECRET_KEY", environ.pop("SECRET_KEY", LONG_KEY))
        for name, value in environ.items():
            patch.setenv(name, value)
        with fresh_settings_modules():
            return importlib.import_module("config.settings.prod")


# ---------------------------------------------------------------------------------- env


def test_env_prefers_the_variable_then_the_file_then_the_default(monkeypatch, tmp_path):
    secret = tmp_path / "secret"
    secret.write_text("from-file\n")
    monkeypatch.delenv("DEMO", raising=False)
    monkeypatch.setenv("DEMO_FILE", str(secret))

    assert env("DEMO") == "from-file"  # trailing newline stripped
    monkeypatch.setenv("DEMO", "from-env")
    assert env("DEMO") == "from-env"
    monkeypatch.delenv("DEMO")
    monkeypatch.delenv("DEMO_FILE")
    assert env("DEMO", "fallback") == "fallback"
    assert env("DEMO") is None


def test_an_unreadable_secret_file_raises_instead_of_falling_back(monkeypatch, tmp_path):
    monkeypatch.delenv("DEMO", raising=False)
    monkeypatch.setenv("DEMO_FILE", str(tmp_path / "missing"))

    with pytest.raises(FileNotFoundError):
        env("DEMO", "a-dev-default-must-not-hide-this")


@pytest.mark.parametrize(("raw", "expected"), [("1", True), ("TRUE", True), (" yes ", True), ("on", True), ("0", False), ("no", False), ("", False)])
def test_env_bool(monkeypatch, raw, expected):
    monkeypatch.setenv("FLAG", raw)

    assert env_bool("FLAG") is expected


def test_env_bool_default_applies_only_when_unset(monkeypatch):
    monkeypatch.delenv("FLAG", raising=False)

    assert env_bool("FLAG") is False
    assert env_bool("FLAG", True) is True


def test_env_list_splits_trims_and_drops_blanks(monkeypatch):
    monkeypatch.setenv("HOSTS", " a.example , ,b.example,")

    assert env_list("HOSTS") == ["a.example", "b.example"]
    monkeypatch.delenv("HOSTS")
    assert env_list("HOSTS") == []
    assert env_list("HOSTS", "x,y") == ["x", "y"]


# ---------------------------------------------------------------------- DATABASE_URL


def test_postgres_url():
    config = db_from_url("postgres://user:p%40ss@db.internal:5433/app")

    assert config == {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "app",
        "USER": "user",
        "PASSWORD": "p@ss",
        "HOST": "db.internal",
        "PORT": "5433",
    }


def test_postgres_url_with_defaults():
    config = db_from_url("postgresql://db")

    assert (config["NAME"], config["USER"], config["PASSWORD"], config["HOST"], config["PORT"]) == ("postgres", "", "", "db", "")


def test_sqlite_urls():
    assert db_from_url("sqlite:///db.sqlite3")["NAME"] == "db.sqlite3"
    assert db_from_url("sqlite://")["NAME"] == ":memory:"


def test_an_unknown_scheme_is_an_error_not_a_guess():
    with pytest.raises(ValueError, match="mysql"):
        db_from_url("mysql://x/y")
    with pytest.raises(ValueError, match="nothing"):
        db_from_url("not-a-url")


# ----------------------------------------------------------------------- production


def test_production_refuses_the_development_secret_key():
    with pytest.raises(ImproperlyConfigured, match="SECRET_KEY"):
        load_prod_settings(SECRET_KEY="unsafe-dev-secret-change-me")


def test_production_reads_the_secret_key_from_a_file(tmp_path):
    key_file = tmp_path / "key"
    key_file.write_text(LONG_KEY + "\n")
    with pytest.MonkeyPatch.context() as patch:
        patch.delenv("SECRET_KEY", raising=False)
        patch.setenv("SECRET_KEY_FILE", str(key_file))
        with fresh_settings_modules():
            prod = importlib.import_module("config.settings.prod")

    assert prod.SECRET_KEY == LONG_KEY


def test_production_security_settings():
    prod = load_prod_settings(SECURE_HSTS_SECONDS="31536000", SECURE_SSL_REDIRECT="true")

    assert prod.DEBUG is False
    assert prod.SESSION_COOKIE_SECURE and prod.CSRF_COOKIE_SECURE
    assert prod.SECURE_HSTS_SECONDS == 31536000
    assert prod.SECURE_SSL_REDIRECT is True
    assert prod.SECURE_PROXY_SSL_HEADER == ("HTTP_X_FORWARDED_PROTO", "https")
    assert prod.SECURE_HSTS_PRELOAD is False


def test_production_defaults_are_cautious():
    prod = load_prod_settings()

    assert prod.SECURE_HSTS_SECONDS == 3600
    assert prod.SECURE_SSL_REDIRECT is False


def test_the_development_settings_allow_any_host_and_turn_debug_on():
    from config.settings import dev

    assert dev.DEBUG is True
    assert dev.ALLOWED_HOSTS == ["*"]


# ---------------------------------------------------------------------- entry points


def test_wsgi_and_asgi_entry_points_import():
    from config import asgi, wsgi

    assert callable(wsgi.application)
    assert callable(asgi.application)


def test_celery_app_is_wired_to_django_settings():
    from config import celery_app

    assert celery_app.main == "config"
    assert celery_app.conf.task_default_queue == "default"
    assert celery_app.conf.task_serializer == "json"
    assert "core.record_heartbeat" in celery_app.tasks
