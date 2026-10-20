# CLAUDE.md

Rules for working in this repository. They are enforced by tests wherever a test can enforce them; where one cannot, they are on you.
The reasoning is in https://github.com/cornyhorse/cornyhorse-design-guidance (docs/).

## Stack
- Python 3.14 on `ghcr.io/cornyhorse/python-base` (it has `python3` and `pip3`, not `python` or `pip`), Django, PostgreSQL, Celery with Redis as
  broker only, gunicorn + WhiteNoise. Docker-first: no local virtualenv. Run everything through `make`.
- **As few dependencies as possible.** Every package in `requirements/*.txt` needs a row in `DEPENDENCIES.md` (a test checks). Ask in order: Django or
  the standard library? About 30 lines of our own? Does it need to be in the web container at all? Pin exact versions. Pre-approved, no need to ask (still add a ledger row): Django REST framework (the default for an API),
  django-ninja, django-crispy-forms + crispy-bootstrap5, factory-boy. Mind the CSP: DRF's JSON renderer only; self-host or disable API docs UIs.
- **Node is out.** No npm, no bundler, no `node_modules`. Stop and ask the owner if you think you need it.
- Heavy or non-Python dependencies go in their own worker image and Celery queue. The web container imports nothing heavy; import heavy libraries
  inside the task function; send tasks by name; pass IDs and JSON.

## Code
- `config/` is the project; apps are `apps/<name>` with `label = "<name>"`. Views are thin, logic is in `services.py`. UUID primary keys.
- Settings come from the environment, through `config/env.py` (`NAME` or `NAME_FILE`). Never print, log or commit a secret. Credentials live in
  MattStash; refer to entries by name.
- `/healthz/` touches the database. Monitor data freshness, not just the process.

## Front end (a test fails on every one of these)
- Nothing from outside this server: no CDN (never a CDN Bootstrap), no remote fonts or images, no analytics. Third-party files are vendored under `static/vendor/` and
  recorded with a SHA-256 in `static/vendor/README.md`. **Ask the owner before downloading anything**, with the exact list.
- Strict CSP: no inline script, no inline handlers, no `<style>`, no `style=""`. A data-driven bar is an SVG `<rect width>` (`{% usage_bar %}`).
- JavaScript: none if at all possible; otherwise one small external vanilla file. Ask before adding any. No frameworks.
- Use the tokens and components in `static/css/` and the status vocabulary in `apps/core/templatetags/ui.py` (`{% status_chip %}`); never hand-copy chip
  markup, never use colour alone for state, never an icon font. Add new pages to `pages()` in `tests/test_self_hosted.py`.
- Light and dark must both work. Check new UI in a real browser at 320 and 1280 px.

## Tests
- 100% line and branch coverage (`make cov`). For a line that seems untestable: test it, mock it, delete it if it is dead, and only then
  `# pragma: no cover - <reason>` (the reason is mandatory).
- Add an integration test (`tests/integration/`, `make integration`) for every seam between systems; if a seam cannot be tested for real, say so in the PR.
- A new test must be able to fail: break the code and watch it go red.
- Before calling anything done: `make cov`, `make integration`, `check --deploy` under the production settings, and look at the page in a browser.

## Git
- As few PRs as possible: one for a coherent change with its tests and docs. Never push to `main`; do not merge unless the owner names the PR.
- Say in the PR what you could not verify.
