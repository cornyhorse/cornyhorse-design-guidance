"""Design rule, enforced: a page loads nothing from outside this server.

These tests render every page the site has (signed out and signed in, empty and populated) and fail on
anything a browser would fetch or run that is not same-origin: absolute or protocol-relative URLs, scripts
without a same-origin `src`, inline scripts, inline event handlers, `<style>` blocks and `style=""`
attributes. The served CSS is scanned too, and so is every static file the pages point at (it must exist).
The Content-Security-Policy that makes the browser enforce the same rules is tested in test_csp.py.

`<a href>` is a link the person clicks, not something the page loads. A link to an external site is allowed
only if the URL is in `allowed_outbound` (feed it from the database for data-driven links). A link written
into a template fails.

When you add a page, add it to `pages()` below. A page that is not listed here is not protected.
"""

from __future__ import annotations

import posixpath
import re
from html.parser import HTMLParser
from urllib.parse import unquote, urlsplit

import pytest
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.contrib.messages.storage.base import Message
from django.contrib.staticfiles import finders
from django.template.loader import render_to_string
from django.test import Client, RequestFactory

from apps.core.models import Heartbeat

pytestmark = pytest.mark.django_db

STATIC_PREFIX = "/" + settings.STATIC_URL.strip("/") + "/"

URL_ATTRIBUTES = {
    "src", "href", "srcset", "action", "formaction", "poster", "data", "cite", "background",
    "longdesc", "ping", "manifest", "usemap", "xlink:href",
}
FORBIDDEN_TAGS = {"style", "iframe", "frame", "object", "embed", "applet"}
FORBIDDEN_LINK_RELS = {"preconnect", "dns-prefetch", "prefetch", "prerender", "preload", "modulepreload"}


def is_external(url: str) -> bool:
    """Absolute http(s), protocol-relative, or a scheme that is never a local file."""
    cleaned = url.strip().lower()
    return cleaned.startswith(("http://", "https://", "//", "ftp:", "ws:", "wss:", "javascript:"))


class PageScan(HTMLParser):
    """What a browser would fetch or execute from one HTML document, and what is wrong with it."""

    def __init__(self, allowed_outbound: set[str] = frozenset()):
        super().__init__(convert_charrefs=True)
        self.allowed_outbound = allowed_outbound
        self.problems: list[str] = []
        self.scripts: list[str] = []
        self.stylesheets: list[str] = []
        self.static_refs: list[str] = []
        self.sprite_refs: list[str] = []
        self.outbound_links: list[str] = []

    def handle_starttag(self, tag, attrs):
        attrs = {name: (value or "") for name, value in attrs}
        where = f"<{tag}>"
        if tag in FORBIDDEN_TAGS:
            self.problems.append(f"{where} is not allowed (inline or embedded content)")
        if tag == "meta" and "http-equiv" in attrs:
            self.problems.append(f"{where} http-equiv={attrs['http-equiv']!r} is not allowed")
        for name, value in attrs.items():
            if name.startswith("on"):
                self.problems.append(f"{where} has an inline event handler: {name}")
            if name == "style":
                self.problems.append(f"{where} has an inline style attribute: {value!r}")
        if tag == "script":
            src = attrs.get("src")
            if not src:
                self.problems.append("<script> without src (inline script)")
            elif is_external(src):
                self.problems.append(f"<script src> is not same-origin: {src}")
            else:
                self.scripts.append(src)
        if tag == "link":
            rel = set(attrs.get("rel", "").lower().split())
            if rel & FORBIDDEN_LINK_RELS:
                self.problems.append(f"<link rel={attrs.get('rel')!r}> is not allowed")
            if "stylesheet" in rel and attrs.get("href"):
                self.stylesheets.append(attrs["href"])
        for name, value in attrs.items():
            if name not in URL_ATTRIBUTES or not value:
                continue
            urls = [part.split()[0] for part in value.split(",") if part.strip()] if name == "srcset" else [value]
            for url in urls:
                self._check_url(tag, name, url)

    def _check_url(self, tag: str, name: str, url: str) -> None:
        if is_external(url):
            if tag == "a" and name == "href" and url in self.allowed_outbound:
                self.outbound_links.append(url)
            else:
                self.problems.append(f"<{tag} {name}> points outside this server: {url}")
            return
        if tag == "use":
            self.sprite_refs.append(url)
        if url.startswith(STATIC_PREFIX):
            self.static_refs.append(url)


def static_file(url: str):
    """Absolute path of the static file a `/static/...` URL names, or None."""
    path = unquote(urlsplit(url).path)
    return finders.find(path.removeprefix(STATIC_PREFIX))


CSS_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
CSS_URL = re.compile(r"""url\(\s*(["']?)(.*?)\1\s*\)""", re.DOTALL | re.IGNORECASE)
CSS_IMPORT = re.compile(r"@import", re.IGNORECASE)


def scan_css(url: str) -> list[str]:
    """Problems in one served stylesheet: external url(), any @import, files that do not exist."""
    path = static_file(url)
    if path is None:
        return [f"stylesheet is not served by the static files: {url}"]
    problems: list[str] = []
    with open(path, encoding="utf-8") as handle:
        css = CSS_COMMENT.sub("", handle.read())
    if CSS_IMPORT.search(css):
        problems.append(f"{url}: @import (every stylesheet must be linked from the page)")
    here = posixpath.dirname(urlsplit(url).path)
    for _quote, target in CSS_URL.findall(css):
        target = target.strip()
        if target.startswith("data:") or target.startswith("#"):
            continue
        if is_external(target):
            problems.append(f"{url}: url() points outside this server: {target[:80]}")
            continue
        resolved = posixpath.normpath(posixpath.join(here, urlsplit(target).path))
        if static_file(resolved) is None:
            problems.append(f"{url}: url({target}) names a file that is not in the static files")
    return problems


def scan(html: str, allowed_outbound: set[str] = frozenset()) -> PageScan:
    page = PageScan(allowed_outbound)
    page.feed(html)
    page.close()
    return page


# ----------------------------------------------------------------------------------- pages


def pages() -> list[tuple[str, bool, str]]:
    """(label, signed_in, url) for every page. Add new pages here."""
    return [
        ("login", False, "/login/"),
        ("login with next", False, "/login/?next=/"),
        ("design reference", False, "/design/"),
        ("design reference, signed in", True, "/design/"),
        ("home", True, "/"),
    ]


def rendered_pages(user) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []

    def client(signed_in: bool) -> Client:
        c = Client()
        if signed_in:
            c.force_login(user)
        return c

    out.append(("home, no heartbeat", client(True).get("/").content.decode()))
    Heartbeat.objects.create(source="worker")
    for label, signed_in, url in pages():
        response = client(signed_in).get(url)
        assert response.status_code == 200, f"{label}: {response.status_code}"
        out.append((label, response.content.decode()))
    # A queued heartbeat shows the success notice; a failed sign-in shows the error state of the form.
    out.append(("home with notice", client(True).post("/heartbeat/", follow=True).content.decode()))
    failed = client(False).post("/login/", {"username": "nobody", "password": "wrong"})
    assert failed.status_code == 200
    out.append(("login, wrong password", failed.content.decode()))
    # Django messages, every level.
    request = RequestFactory().get("/")
    request.user = AnonymousUser()
    levels = ((10, "debug"), (20, "info"), (25, "success"), (30, "warning"), (40, "error"))
    messages = [Message(level, f"A {tag} message") for level, tag in levels]
    out.append(("messages", render_to_string("includes/_messages.html", {"messages": messages}, request=request)))
    return out


@pytest.fixture
def all_pages(user):
    return rendered_pages(user)


def test_every_page_is_rendered_and_has_content(all_pages):
    assert len(all_pages) >= 8
    assert all(html.strip() for _, html in all_pages)


def test_no_page_loads_or_runs_anything_from_outside(all_pages):
    failures = [f"{label}: {problem}" for label, html in all_pages for problem in scan(html).problems]
    assert not failures, "\n".join(failures)


def test_every_static_file_a_page_points_at_exists(all_pages):
    failures = [
        f"{label}: {url} is not found by the static files finders"
        for label, html in all_pages
        for url in scan(html).static_refs
        if static_file(url) is None
    ]
    assert not failures, "\n".join(failures)


def test_served_stylesheets_reference_only_this_server(all_pages):
    sheets = set()
    for _label, html in all_pages:
        sheets.update(scan(html).stylesheets)
    assert len(sheets) >= 5  # bootstrap, fonts, tokens, components, app
    assert all(sheet.startswith(STATIC_PREFIX) for sheet in sheets), sheets
    problems = [problem for sheet in sorted(sheets) for problem in scan_css(sheet)]
    assert not problems, "\n".join(problems)


def test_every_stylesheet_we_ship_is_clean():
    """Also the ones no page links yet: nothing under static/ may reach outside."""
    problems = []
    for css in sorted((settings.BASE_DIR / "static").rglob("*.css")):
        url = STATIC_PREFIX + css.relative_to(settings.BASE_DIR / "static").as_posix()
        problems.extend(scan_css(url))
    assert not problems, "\n".join(problems)


def test_no_template_has_a_multi_line_hash_comment():
    """`{# ... #}` is a SINGLE-LINE comment in Django. A multi-line one is not a comment at all: the template
    engine passes it through and the browser renders it as visible text on the page, which no rendered-page
    assertion would notice as wrong. Use `{% comment %}` for anything that needs more than one line.
    """
    offenders = []
    for path in sorted((settings.BASE_DIR / "templates").rglob("*.html")):
        text = path.read_text(encoding="utf-8")
        for match in re.finditer(r"\{#", text):
            end = text.find("#}", match.start())
            if end == -1 or "\n" in text[match.start() : end]:
                line = text[: match.start()].count("\n") + 1
                offenders.append(f"{path.relative_to(settings.BASE_DIR)}:{line}")
    assert not offenders, "multi-line {# #} comments render as visible text; use {% comment %}: " + ", ".join(offenders)


def test_no_page_renders_raw_template_syntax(all_pages):
    leaks = [f"{label}: {token}" for label, html in all_pages for token in ("{#", "#}", "{%") if token in html]
    assert not leaks, "\n".join(leaks)


def test_pages_ask_for_the_assets_we_expect(all_pages):
    """The same five stylesheets, one script (theme.js, in <head> before the CSS) and the sprite."""
    html = dict(all_pages)["home, no heartbeat"]
    page = scan(html)
    assert page.scripts == [STATIC_PREFIX + "js/theme.js"]
    assert page.stylesheets == [
        STATIC_PREFIX + name
        for name in ("vendor/bootstrap/bootstrap.min.css", "css/fonts.css", "css/tokens.css", "css/components.css", "css/app.css")
    ]
    assert html.index("theme.js") < html.index("bootstrap.min.css"), "theme.js must load first, in <head>, so there is no flash"
    assert page.sprite_refs, "icons should be drawn from the sprite"
    assert {urlsplit(ref).path for ref in page.sprite_refs} == {STATIC_PREFIX + "vendor/bootstrap-icons/sprite.svg"}


def test_no_page_has_an_outbound_link_unless_it_is_allowed(all_pages):
    assert all(scan(html).outbound_links == [] for _label, html in all_pages)


# ----------------------------------------------------------- the scanner itself catches things


@pytest.mark.parametrize(
    "snippet",
    [
        '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">',
        '<link rel="stylesheet" href="//fonts.googleapis.com/css2?family=IBM+Plex+Sans">',
        '<link rel="preconnect" href="https://fonts.gstatic.com">',
        '<link rel="icon" href="http://example.com/favicon.ico">',
        '<script src="https://unpkg.com/x.js"></script>',
        "<script>alert(1)</script>",
        '<img src="https://example.com/p.png">',
        '<img srcset="/static/a.png 1x, https://example.com/b.png 2x" src="/static/a.png">',
        '<form action="https://example.com/post" method="post"></form>',
        '<button onclick="go()">x</button>',
        '<div style="width: 40%"></div>',
        "<style>.a{color:red}</style>",
        '<iframe src="/x/"></iframe>',
        '<meta http-equiv="refresh" content="0;url=https://example.com">',
        '<a href="https://tracker.example.com/">not allowed</a>',
        '<a href="//tracker.example.com/">protocol-relative</a>',
        '<a href="javascript:void(0)">js</a>',
    ],
)
def test_scanner_flags_each_kind_of_external_or_inline_thing(snippet):
    assert scan(snippet).problems, snippet


def test_scanner_accepts_a_clean_fragment():
    clean = (
        '<link rel="stylesheet" href="/static/css/app.css"><script src="/static/js/theme.js"></script>'
        '<img src="/static/img/favicon.svg"><a href="/design/">x</a><form action="/design/"></form>'
    )
    assert scan(clean).problems == []


def test_scanner_lets_an_explicitly_allowed_outbound_link_through():
    page = scan('<a href="https://example.com/docs">docs</a>', {"https://example.com/docs"})

    assert page.problems == []
    assert page.outbound_links == ["https://example.com/docs"]


def test_css_scanner_flags_external_urls_and_imports(tmp_path, settings):
    bad = tmp_path / "bad.css"
    bad.write_text(
        '@import url("https://fonts.googleapis.com/css2?family=IBM+Plex+Sans");\n'
        "@font-face { src: url(https://cdn.example.com/f.woff2); }\n"
        '.a { background: url("//cdn.example.com/x.png"); }\n'
        ".b { background: url(missing.png); }\n"
        '.c { background: url("data:image/svg+xml,%3csvg xmlns=\'http://www.w3.org/2000/svg\'/%3e"); }\n'
        "/* url(https://in-a-comment.example.com/ignored.png) */\n"
    )
    settings.STATICFILES_DIRS = [*settings.STATICFILES_DIRS, tmp_path]

    text = "\n".join(scan_css("/static/bad.css"))

    assert "@import" in text
    assert "cdn.example.com/f.woff2" in text
    assert "//cdn.example.com/x.png" in text
    assert "missing.png" in text
    assert "w3.org" not in text and "in-a-comment" not in text


def test_css_scanner_reports_a_stylesheet_that_is_not_served():
    assert "not served" in scan_css("/static/css/nope.css")[0]
