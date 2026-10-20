"""House rules that are cheaper to enforce with a test than to remember."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRAGMA = re.compile(r"#\s*pragma:\s*no cover(?P<rest>.*)")


def python_sources():
    for folder in ("apps", "config"):
        for path in (ROOT / folder).rglob("*.py"):
            if "migrations" in path.parts or "tests" in path.parts:
                continue
            yield path


def test_every_no_cover_pragma_says_why():
    """We aim for 100% coverage; an exclusion must be a considered rejection, with the reason on the line."""
    bare = []
    for path in python_sources():
        for number, line in enumerate(path.read_text().splitlines(), start=1):
            match = PRAGMA.search(line)
            if match and len(match.group("rest").strip(" -:")) < 12:
                bare.append(f"{path.relative_to(ROOT)}:{number}")
    assert not bare, "pragma: no cover needs a reason, e.g. `# pragma: no cover - needs a live Redis`: " + ", ".join(bare)


def requirement_names():
    names = set()
    for path in (ROOT / "requirements").glob("*.txt"):
        for line in path.read_text().splitlines():
            line = line.split("#")[0].strip()
            if line and not line.startswith("-"):
                names.add(re.split(r"[\[=<>~! ]", line, maxsplit=1)[0].lower())
    return names


def installed_ledger() -> str:
    """The ledger's table of installed packages: everything before the pre-approved (not installed) list."""
    return (ROOT / "DEPENDENCIES.md").read_text().split("## Pre-approved")[0].lower()


def test_every_dependency_is_justified_in_DEPENDENCIES_md():
    """The dependency budget: a package cannot be added without saying why it earns its place."""
    ledger = installed_ledger()
    unjustified = sorted(name for name in requirement_names() if f"`{name}`" not in ledger)
    assert not unjustified, f"add a row to DEPENDENCIES.md for: {unjustified}"


def test_no_dependency_is_listed_that_the_requirements_do_not_have():
    ledger = installed_ledger()
    listed = set(re.findall(r"^\| `([a-z0-9._-]+)` \|", ledger, flags=re.MULTILINE))
    assert listed == requirement_names(), "DEPENDENCIES.md and requirements/*.txt disagree"


def test_there_is_no_node_toolchain():
    """Node is out unless it is completely unavoidable; if it ever is, this test is where that is decided."""
    forbidden = ("package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "webpack.config.js", "vite.config.js")
    found = [p for p in ROOT.rglob("*") if p.name in forbidden and ".git" not in p.parts and "node_modules" not in p.parts]
    assert not found, found
    assert not (ROOT / "node_modules").exists()


def test_the_image_is_built_on_the_python_base_image():
    dockerfile = (ROOT / "Dockerfile").read_text()

    assert "ARG PYTHON_BASE_IMAGE=ghcr.io/cornyhorse/python-base:" in dockerfile
    assert "FROM ${PYTHON_BASE_IMAGE}" in dockerfile


def test_the_image_never_bakes_in_a_dotenv():
    ignored = (ROOT / ".dockerignore").read_text().splitlines()

    assert ".env" in ignored and ".env.*" in ignored and "!.env.example" in ignored
    assert ".git" in ignored

