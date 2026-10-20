#!/usr/bin/env python3
"""Build the inline-SVG icon sprite from the vendored Bootstrap Icons files.

    python scripts/build_icon_sprite.py          # rewrite static/vendor/bootstrap-icons/sprite.svg
    python scripts/build_icon_sprite.py --check  # exit 1 if the sprite on disk is out of date

Input is every `static/vendor/bootstrap-icons/icons/<name>.svg` (byte-identical copies of the files in
the `bootstrap-icons@1.13.1` npm package, see static/vendor/README.md). Output is one `<symbol
id="<name>">` per icon, so a page can draw it with `<use href="/static/.../sprite.svg#<name>">`
and no icon font, no CDN and no JavaScript. Pure standard library, no network.

To add an icon: fetch `icons/<name>.svg` from the pinned package as README.md describes, record its
sha256 there, run this script, commit all three.
"""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ICON_DIR = ROOT / "static" / "vendor" / "bootstrap-icons" / "icons"
SPRITE = ROOT / "static" / "vendor" / "bootstrap-icons" / "sprite.svg"
SVG_NS = "http://www.w3.org/2000/svg"


def _symbol(path: Path) -> str:
    root = ET.fromstring(path.read_text(encoding="utf-8"))
    view_box = root.get("viewBox", "0 0 16 16")
    inner = []
    for child in root:
        # Shapes only; fill comes from `currentColor` on the <svg> that references the symbol.
        tag = child.tag.removeprefix(f"{{{SVG_NS}}}")
        attrs = "".join(f' {key}="{value}"' for key, value in child.attrib.items())
        inner.append(f"<{tag}{attrs}/>")
    return f'<symbol id="{path.stem}" viewBox="{view_box}">{"".join(inner)}</symbol>'


def build(icon_dir: Path = ICON_DIR) -> str:
    symbols = [_symbol(path) for path in sorted(icon_dir.glob("*.svg"))]
    return f'<svg xmlns="{SVG_NS}">\n' + "\n".join(symbols) + "\n</svg>\n"


def main(argv: list[str]) -> int:
    sprite = build()
    if "--check" in argv:
        if not SPRITE.exists() or SPRITE.read_text(encoding="utf-8") != sprite:
            print(f"{SPRITE} is out of date; run scripts/build_icon_sprite.py", file=sys.stderr)
            return 1
        return 0
    SPRITE.write_text(sprite, encoding="utf-8")
    print(f"wrote {SPRITE.relative_to(ROOT)} ({len(sprite)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
