"""Production static-file serving: WhiteNoise from the app container, no CDN and no extra nginx mount."""

import tempfile
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.test import override_settings

from config.storage import ManifestStaticFilesStorage
from tests.test_settings import load_prod_settings

PROD_STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "config.storage.ManifestStaticFilesStorage"},
}


def test_whitenoise_sits_right_after_the_security_middleware():
    middleware = list(settings.MIDDLEWARE)
    assert middleware[0] == "django.middleware.security.SecurityMiddleware"
    assert middleware[1] == "whitenoise.middleware.WhiteNoiseMiddleware"


def test_static_root_is_set_for_collectstatic():
    assert Path(settings.STATIC_ROOT).name == "staticfiles"


def test_production_settings_use_hashed_compressed_static_storage():
    prod = load_prod_settings()

    assert prod.STORAGES == PROD_STORAGES
    assert prod.DEBUG is False


def test_collectstatic_with_the_production_storage_produces_a_manifest_and_hashed_files():
    with tempfile.TemporaryDirectory() as tmp:
        with override_settings(STATIC_ROOT=tmp, STORAGES=PROD_STORAGES):
            call_command("collectstatic", interactive=False, verbosity=0)
        out = Path(tmp)
        assert (out / "staticfiles.json").exists()
        hashed = [p for p in out.rglob("*.css") if p.stem.count(".") >= 1]
        assert hashed, "expected content-hashed CSS files"
        assert list(out.rglob("*.css.gz")), "expected pre-compressed CSS"
        # The fonts are referenced from fonts.css; hashing must rewrite those urls, or they 404 in production.
        manifest = (out / "staticfiles.json").read_text()
        assert "ibm-plex-sans-latin-400-normal" in manifest


def test_the_storage_ignores_source_map_comments_but_keeps_resolving_real_url_references():
    flat = [rule if isinstance(rule, str) else rule[0] for _ext, rules in ManifestStaticFilesStorage.patterns for rule in rules]
    assert not any("sourceMappingURL" in rule for rule in flat)
    # url(...) and @import rewriting for stylesheets must still be there, or fonts would 404 after hashing.
    assert any("url\\(" in rule or "url(" in rule for rule in flat)
