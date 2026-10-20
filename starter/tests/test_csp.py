"""The Content-Security-Policy that makes the browser enforce "everything from this server"."""

import pytest
from django.conf import settings

pytestmark = pytest.mark.django_db

EXPECTED = {
    "default-src": ["'self'"],
    "script-src": ["'self'"],
    "style-src": ["'self'"],
    "img-src": ["'self'", "data:"],
    "font-src": ["'self'"],
    "connect-src": ["'self'"],
    "object-src": ["'none'"],
    "base-uri": ["'self'"],
    "form-action": ["'self'"],
    "frame-ancestors": ["'none'"],
}


def parse(header: str) -> dict[str, list[str]]:
    directives = {}
    for part in header.split(";"):
        name, *sources = part.split()
        directives[name] = sources
    return directives


def test_policy_is_exactly_the_strict_one():
    assert settings.SECURE_CSP == EXPECTED


def test_policy_allows_no_inline_code_no_wildcards_and_no_other_origin():
    allowed_sources = {"'self'", "'none'", "data:"}
    for name, sources in settings.SECURE_CSP.items():
        assert set(sources) <= allowed_sources, f"{name} allows {sources}"
        assert "'unsafe-inline'" not in sources and "'unsafe-eval'" not in sources
    # data: is for images only (Bootstrap's own CSS embeds a few); never for scripts or styles.
    assert [n for n, s in settings.SECURE_CSP.items() if "data:" in s] == ["img-src"]


@pytest.mark.parametrize("url", ["/login/", "/", "/design/", "/healthz/", "/admin/login/", "/no-such-page/"])
def test_every_response_carries_the_policy(signed_in, url):
    assert parse(signed_in.get(url)["Content-Security-Policy"]) == EXPECTED


def test_a_redirect_carries_the_policy(client):
    response = client.get("/")

    assert response.status_code == 302
    assert parse(response["Content-Security-Policy"]) == EXPECTED


def test_no_page_is_exempt():
    """Unlike a Swagger UI or a browsable API, nothing here needs an exemption. Keep it that way."""
    assert not hasattr(settings, "CONTENT_SECURITY_POLICY_EXEMPT_PREFIXES")
    assert not getattr(settings, "SECURE_CSP_REPORT_ONLY", None)


def test_middleware_runs_early_so_error_pages_get_it():
    middleware = list(settings.MIDDLEWARE)
    assert middleware.index("django.middleware.csp.ContentSecurityPolicyMiddleware") < middleware.index(
        "django.middleware.common.CommonMiddleware"
    )
