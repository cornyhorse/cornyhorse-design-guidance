"""static/vendor/README.md is the record of every third-party file; these tests keep it true."""

import hashlib
import importlib.util
import re

from django.conf import settings

from apps.core.templatetags import ui

VENDOR = settings.BASE_DIR / "static" / "vendor"
README = VENDOR / "README.md"
ROW = re.compile(r"^\| `(static/vendor/[^`]+)` \| .* \| `([0-9a-f]{64})` \|$", re.MULTILINE)


def recorded() -> dict[str, str]:
    return dict(ROW.findall(README.read_text(encoding="utf-8")))


def sha256(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_every_recorded_hash_matches_its_file():
    rows = recorded()
    assert rows, "the README table has no rows"
    for path, digest in rows.items():
        file = settings.BASE_DIR / path
        assert file.is_file(), f"{path} is in the README but not on disk"
        assert sha256(file) == digest, f"{path} differs from the hash in the README"


def test_every_vendored_file_is_recorded():
    on_disk = {p.relative_to(settings.BASE_DIR).as_posix() for p in VENDOR.rglob("*") if p.is_file() and p != README}
    assert on_disk == set(recorded())


def test_only_the_approved_packages_are_vendored():
    """Widening this list is a decision for the owner: update the test in the same change, on purpose."""
    assert {p.name for p in VENDOR.iterdir()} == {"README.md", "bootstrap", "bootstrap-icons", "fonts"}
    assert {p.name for p in (VENDOR / "bootstrap").iterdir()} == {"bootstrap.min.css", "LICENSE"}, "CSS only, no Bootstrap JS"
    fonts = sorted(p.name for p in (VENDOR / "fonts").rglob("*.woff2"))
    assert fonts == sorted(f"ibm-plex-{family}-latin-{weight}-normal.woff2" for family in ("mono", "sans") for weight in (400, 500, 600))
    assert not list(VENDOR.rglob("*.js")), "no vendored JavaScript"
    assert not list(VENDOR.rglob("*.ttf")) and not list(VENDOR.rglob("*.woff")), "no icon font, no other font files"


def test_licence_texts_are_shipped_with_each_package():
    for folder, needle in (
        ("bootstrap", "MIT License"),
        ("bootstrap-icons", "MIT License"),
        ("fonts/ibm-plex-sans", "SIL OPEN FONT LICENSE"),
        ("fonts/ibm-plex-mono", "SIL OPEN FONT LICENSE"),
    ):
        assert needle.lower() in (VENDOR / folder / "LICENSE").read_text(encoding="utf-8").lower(), folder


def sprite_builder():
    path = settings.BASE_DIR / "scripts" / "build_icon_sprite.py"
    spec = importlib.util.spec_from_file_location("build_icon_sprite", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_sprite_is_built_from_the_vendored_icons():
    builder = sprite_builder()
    assert builder.SPRITE.read_text(encoding="utf-8") == builder.build(), "run: python3 scripts/build_icon_sprite.py"


def sprite_ids() -> set[str]:
    return set(re.findall(r'<symbol id="([^"]+)"', sprite_builder().SPRITE.read_text(encoding="utf-8")))


def icons_in_use() -> set[str]:
    used = set()
    for template in (settings.BASE_DIR / "templates").rglob("*.html"):
        used.update(re.findall(r"""{%\s*icon\s+["']([a-z0-9-]+)["']""", template.read_text(encoding="utf-8")))
    used.update(icon for icon, _label in ui.STATES.values())
    return used


def test_every_icon_the_templates_use_is_in_the_sprite():
    missing = icons_in_use() - sprite_ids()
    assert not missing, f"icons used but not vendored: {sorted(missing)}"


def test_no_vendored_icon_goes_unused():
    unused = sprite_ids() - icons_in_use()
    assert not unused, f"vendored but unused (delete them and rebuild the sprite): {sorted(unused)}"


def test_the_sprite_builder_check_mode_reports_a_stale_sprite(tmp_path, monkeypatch, capsys):
    builder = sprite_builder()
    monkeypatch.setattr(builder, "SPRITE", tmp_path / "missing.svg")

    assert builder.main(["--check"]) == 1
    assert "out of date" in capsys.readouterr().err


def test_the_sprite_builder_writes_and_then_checks_clean(tmp_path, monkeypatch, capsys):
    builder = sprite_builder()
    monkeypatch.setattr(builder, "SPRITE", tmp_path / "sprite.svg")
    monkeypatch.setattr(builder, "ROOT", tmp_path)

    assert builder.main([]) == 0
    assert "wrote" in capsys.readouterr().out
    assert builder.main(["--check"]) == 0


def test_the_only_script_we_ship_is_the_theme_control():
    scripts = sorted(p.name for p in (settings.BASE_DIR / "static").rglob("*.js"))
    assert scripts == ["theme.js"]
    source = (settings.BASE_DIR / "static" / "js" / "theme.js").read_text(encoding="utf-8")
    for forbidden in ("fetch(", "XMLHttpRequest", "WebSocket", "import(", "http://", "https://", "eval(", "document.write"):
        assert forbidden not in source
    assert len(source.splitlines()) < 60, "very little JS: this file should stay small"
