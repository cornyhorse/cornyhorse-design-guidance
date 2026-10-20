"""Project-wide gates: the checks to run before calling a change done."""

import os
import subprocess
import sys
from io import StringIO
from pathlib import Path

import pytest
from django.core.management import call_command

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.django_db
def test_system_check_is_clean():
    call_command("check", stdout=StringIO(), stderr=StringIO())


@pytest.mark.django_db
def test_no_model_change_is_missing_a_migration():
    try:
        call_command("makemigrations", "--check", "--dry-run", stdout=StringIO(), stderr=StringIO())
    except SystemExit as exc:  # --check exits 1 when changes are detected
        pytest.fail(f"models changed without a migration; run `make makemigrations` (exit {exc.code})")


def test_the_deploy_checklist_is_clean_under_the_production_settings():
    """`check --deploy` with a real-looking environment must have nothing left to say."""
    environ = {
        **os.environ,
        "DJANGO_SETTINGS_MODULE": "config.settings.prod",
        "SECRET_KEY": "abcdefghij" * 7,
        "SECURE_SSL_REDIRECT": "true",
        "SECURE_HSTS_SECONDS": "31536000",
        "DATABASE_URL": "sqlite:///:memory:",
    }
    result = subprocess.run(
        [sys.executable, "manage.py", "check", "--deploy", "--fail-level", "WARNING"],
        cwd=ROOT, env=environ, capture_output=True, text=True, check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
