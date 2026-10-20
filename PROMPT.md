# Prompt: build a new project the cornyhorse way

Copy everything inside the code block into a new coding agent, after filling in the `<...>` inputs. The prompt is
self-contained on purpose: an agent that cannot browse GitHub still gets every rule. An agent that can should also
read the files it points to; they carry the reasoning and the working code.

The rules come from a real project (a private Django dashboard whose design was reviewed, broken, fixed and shipped)
and from the owner's other repositories. Where a rule is here, there was a reason; the reason is in [docs/](docs/).

---

```text
You are building a new web project for its owner (GitHub handle: cornyhorse). The owner has a settled way of building
these: a small, boring, heavily tested Django service in containers, with an instrument-panel look and almost no
JavaScript. This brief records the decisions already made so you do not re-litigate them. Where this brief and a habit
of yours disagree, follow this brief. Where this brief and the reference repo disagree, tell the owner.

Inputs:
- PROJECT_NAME:   <e.g. "Media Hub">
- PROJECT_SLUG:   <kebab-case>
- PURPOSE:        <the question(s) it answers, in one or two sentences; also what it is NOT>
- DATA SOURCES:   <what feeds it; who pushes and who pulls>
- USERS / ACCESS: <just the owner? a household? a private network only?>
- HOST:           <where it runs; default: a Docker host behind the owner's reverse proxy>
- WORKERS:        <does it need heavy Python libraries, or non-Python binaries (Rust, Go, ffmpeg...)? default: no>

READ FIRST. The reference repo is https://github.com/cornyhorse/cornyhorse-design-guidance. Read, do not guess:
- docs/architecture.md   stack, dependency budget, Celery and worker isolation
- docs/container.md      the base image, how to use it, how to build your own
- docs/frontend.md       self-hosting, CSP, WhiteNoise, the vendoring rule, the JavaScript policy
- docs/design-language.md  the aesthetic and the status vocabulary
- docs/testing.md        100% coverage policy, mocks, pragmas, integration tests
- docs/secrets.md        MattStash
- docs/workflow.md       PRs, deploys, what to verify
- starter/               a working, tested Django project that already follows all of this. START FROM IT.

## 0. Start from the starter
Copy `starter/` into the new repository root and rename it (PROJECT_NAME is one setting: `SITE_NAME`). Do not rebuild the
design kit, the CSP, the static-file pipeline or the guard tests from scratch. They exist, they pass, and they carry
lessons (see section 9). Keep them passing as you add features. Python modules are imported as `apps.<name>`; the
project package is `config`.

## 1. Product philosophy
- A small tool that answers a few specific questions, not a platform. Say in the README what it is NOT.
- Top of the page = only what needs attention ("4 things need attention."). Healthy things are collapsed by default. A
  quiet page is a good page.
- It must keep working when the things it watches are down, and "I cannot reach that" is a real state, not a pile of
  false alarms.
- Data comes IN through a schema-validated, idempotent ingest (validate everything first, then one transaction). The
  app does not read other repos, hold SSH keys or reach into other systems unasked. A sync retires rows
  (`retired_at`), never deletes them. Slugs are the stable identity. Measurements belong to pollers, not to feeds.
- Alerts are gentle: nothing is "emergency priority" unless a person's safety depends on it.
- Show how fresh the data is ("checked 11 s ago, source ..."), so a stale page says it is stale.

## 2. Stack and dependency policy
- Python 3.14, the current Django release (6.x: its built-in CSP middleware is used), PostgreSQL via `DATABASE_URL`
  (parsed with the standard library), Redis only as the Celery broker. Gunicorn behind the host's reverse proxy,
  published on 127.0.0.1 only.
- AS FEW DEPENDENCIES AS POSSIBLE. Every package in `requirements/*.txt` needs a row in `DEPENDENCIES.md` saying why it
  earns its place and what the alternative would cost; a test fails otherwise. Before adding one, in order: can Django
  or the standard library do it? Can about 30 lines of our own code do it? Does it have to be in the web container at
  all? Pin exact versions. PRE-APPROVED, no need to ask (each still gets a ledger row when you install it): Django REST
  framework (the DEFAULT for an HTTP API of any size), django-ninja (approved alternative), django-crispy-forms with
  crispy-bootstrap5, and factory-boy. Anything else needs a reason in the ledger and, if it is a new idea, the owner's OK.
  The starter does not ship the pre-approved ones; add them when the project needs them. Mind the CSP: use DRF's JSON renderer
  only, and self-host or turn off any API docs page that loads from a CDN.
- Docker-first. No local virtualenv, no uv/Poetry. `requirements/{base,prod,worker,test}.txt`. `pyproject.toml` holds
  tool configuration only.
- Layout: `config/` is the project package; apps under `apps/<name>` with `AppConfig.label = "<name>"`; templates and
  static at the repository root; settings split `base/dev/prod`, every value from environment variables with safe
  development defaults, and production refuses to start on the development secret.
- Views are thin; logic lives in `services.py`. UUID primary keys, `created_at`/`updated_at`. A custom user model from
  the first migration. Session login for people; if machines need an API, plain `JsonResponse` views with a hashed API
  key first, and a framework only when the API is genuinely large.
- A health endpoint that does not touch the database says "healthy" while the database is down. Monitor the data
  ("a heartbeat in the last few minutes"), not just the process.
- Say where the data lives and whether it is backed up. Do not assume.
- NODE IS OUT. No npm, webpack, Vite or a `node_modules` in the repo or in any runtime image (a test enforces it). If
  something truly cannot be done without Node, stop and ask the owner; do not decide it yourself.

## 3. Workers: isolate dependencies with Celery
- The web container imports no heavy library. Anything heavy or compiled (pandas, PDF/OCR/ML libraries, image tools, a
  native binary) runs in a worker container that listens on its OWN queue and installs its OWN requirements file. The
  web container only sends tasks, by explicit name (`app.send_task("documents.extract", args=[id], queue="documents")`).
- One queue per dependency set, one worker image target per queue (`--target worker` with
  `--build-arg WORKER_REQUIREMENTS=requirements/documents.txt`). Import the heavy library inside the task function,
  never at module top, so the web container can still import the module.
- Non-Python binaries (Rust, Go, C tools): build them in a throwaway builder stage and copy only the binary into that
  worker image; the task calls it with `subprocess.run([...], check=True, timeout=...)` and a JSON-in/JSON-out
  contract. A long-running native service is its own container with a documented contract, not a Celery task.
- Tasks take IDs and JSON-serialisable arguments, are idempotent, have timeouts, and write their results to the
  database. No result backend by default.
- Details and the compose topology: docs/architecture.md.

## 4. The container
- Build on the owner's public image, `ghcr.io/cornyhorse/python-base:3.14` (Debian slim, CPython compiled from source with
  PGO + LTO, multi-arch, no compiler in it; source: https://github.com/cornyhorse/cornyhorse-debian-python). The
  starter Dockerfile already does; pin it by digest for releases. It has `python3` and `pip3` only (no `python`, no
  `pip`), runs as root until you add a user, and has no gcc: a worker that must compile a wheel installs a toolchain in
  its own stage; the web image never does.
- Someone without access to it, or who prefers to own it, builds it themselves: docs/container.md has the steps, and
  `--build-arg PYTHON_BASE_IMAGE=python:3.14-slim` swaps in the official image.
- Multi-stage Dockerfile, one target per kind of container (`web`, `worker`, `test`). Non-root user with a fixed uid.
  `collectstatic` at image build. `.dockerignore` excludes `.env`, `.git` and secrets: the first image of the reference
  project had a `.env` baked in.
- Decide up front whether production images are built on the host or pulled; a GHCR package is private until you make it
  public, and the server may not be logged in.

## 5. Secrets
- Never print, log, commit or type a secret. The owner keeps credentials in MattStash (https://github.com/cornyhorse/mattstash,
  a KeePass-backed store with a CLI, a Python API and an HTTP server). Generate new credentials straight into it.
- Preferred runtime pattern, with no code dependency: secrets arrive as FILES (`SECRET_KEY_FILE=/run/secrets/...`,
  which `config/env.py` already reads) or as environment variables injected at start with `mattstash exec`/`mattstash env`.
  Only an app that must create or rotate secrets at runtime (signing keys, per-device tokens, recovery codes) depends
  on the `mattstash` package, behind one small module like the one in docs/secrets.md, and says so in the ledger.
- Do not type credentials into login forms; the owner does their own logins. (Test credentials you generated, for the
  app you are building on localhost, are fine; never repeat their values in chat.)

## 6. Front end rules (non-negotiable)
- ZERO third-party requests on page load: no CDN, no Google Fonts, no analytics, no remote images. In particular NEVER
  link Bootstrap (CSS or JS) from a CDN, even if an older template, cookiecutter or prompt says to; the starter vendors it. Everything the site
  shows is in the repository and served by the site. The starter already vendors what it needs under `static/vendor/`
  (Bootstrap CSS only, an SVG icon sprite built from Bootstrap Icons, IBM Plex Sans and Mono) with version, source URL,
  SHA-256 and licence recorded in `static/vendor/README.md`, and a test that checks every hash.
- Any other download (a new icon, another font, a library) needs the owner's explicit OK first: ask once, with the exact
  list, filenames, sources and sizes. Fetch it with `curl` from a pinned version, never with npm.
- Static files are served by WhiteNoise from the web container (hashed and compressed by `collectstatic` at image
  build) unless something else in the stack already serves them. Keep static files in the repo, not on a CDN.
- Enforced, not promised: a strict Content-Security-Policy (`default-src 'self'`, `script-src 'self'`, `style-src 'self'`,
  `frame-ancestors 'none'`, `object-src 'none'`, `img-src 'self' data:`), pinned by tests. No inline script, no inline
  handlers, no `style=""` attributes (a data-driven bar is an inline SVG whose `<rect width>` is an attribute). A test
  fails on any absolute or protocol-relative URL, inline script or style in a rendered page or stylesheet. When you add a
  page, add it to `tests/test_self_hosted.py::pages()`.
- JavaScript policy, strictest first: (1) none: `<details>` for folds, GET forms for search and filters, POST forms with CSRF
  for actions; (2) a small hand-written vanilla file, external, no inline, no build step (the starter ships exactly one,
  about 50 lines, for the theme toggle); (3) a vendored library only if it is incredibly popular, only with the owner's OK, and
  recorded in `static/vendor/README.md`. Never a framework, never a bundler. Ask before adding any JS.
- Light AND dark. Follow the OS by default; a Light / Auto / Dark toggle remembered in localStorage and applied by a
  synchronous `<head>` script so there is no flash. Colours are tokens written once with `light-dark()`. Browser floor:
  Chrome 123, Safari 17.5, Firefox 120; say so.
- Icons are an inline SVG sprite built by `scripts/build_icon_sprite.py` from vendored SVGs. Never an icon font: when it
  fails to load every icon-only button becomes an empty box.
- One source of truth for status vocabulary in Python (`STATES` plus `{% status_chip %}`). Never hand-copy chip markup.

## 7. Aesthetic: "instrument panel"
Use the starter's tokens, components and `/design/` reference page; extend them, do not restyle them. It must NOT look
like generic Tailwind or AI-dashboard output.
- Warm "paper and graphite" neutrals, not cool grey. One azure accent for links, focus, active nav and data marks only,
  never for status.
- IBM Plex Sans for prose, IBM Plex Mono for names, ids and small-caps labels.
- Rectangular "annunciator" status chips: icon + label + tinted fill, always, never colour alone. Hairlines instead of
  shadows, no gradients, 2-4 px radius. No card grids, stat boxes or hero tiles as the main device.
- Status hues are chosen for separation under colour blindness: Up teal-leaning green, Degraded amber, Down red, Stale
  VIOLET (not orange: it sat next to red and read as the same chip), Expected-offline grey, Unknown dashed grey,
  Site-unreachable filled red. "We do not know" must never look like "it is on fire".
- Contrast AA everywhere in both themes, measured with a script in the page, not by eye. Visible focus on every control,
  a skip link, 44 px touch targets, no horizontal scroll at 320 px. Long-form detail: docs/design-language.md.
- If the project needs a NEW kind of page or component, design it before building it: write the plain-HTML options, open
  them in a real browser at 320, 375, 768, 1000, 1280 and 1440 px in light and dark, run contrast, focus and overflow
  checks, record what failed and what you fixed, and let the owner choose. The reference project's first mockups had an
  unreadable "site unreachable" card; looking is not optional.

## 8. Tests and coverage
- Target 100% line AND branch coverage, enforced (`fail_under = 100`, CI fails below it). When a line looks untestable,
  decide on purpose, in this order: write a test; use a mock; if the line turns out to be unreachable it is dead code, so
  delete it; only if it truly cannot run in a test, mark it `# pragma: no cover - <why>`. The reason is mandatory and a
  test fails a bare pragma.
- Unit tests live next to the app (`apps/<name>/tests/`). Project-wide guards live in `tests/` (self-hosting, CSP, vendor
  hashes, production static files, dependency ledger, no Node, `check --deploy`, no missing migrations).
- Integration tests are not optional. For every seam where two things meet (web to broker to worker to database, a
  payment or mail provider, an import from another system) add an integration test in `tests/integration/` (marker
  `integration`, `make integration`) that exercises the real thing in the compose stack. If a seam truly cannot be
  tested for real (a paid or live third-party service), say so in the report with the reason, and cover it with a
  contract test against recorded or mocked responses instead.
- A new test must be able to fail: break the code it guards and watch it go red. Several tests in the reference project
  turned out to be vacuous this way.
- Run tests in the containers (`make test`, `make cov`, `make integration`). Test the production image's
  `collectstatic`, not just dev.

## 9. Traps already hit (do not repeat them)
- Bootstrap's CSS ends with a `sourceMappingURL` comment for a `.map` file you did not ship. Django's hashing storage
  then fails `collectstatic` ("could not be found"). `config/storage.py` drops that rule. Test the production build.
- `{# ... #}` is a SINGLE-LINE comment in Django. A multi-line one renders as visible text. Use `{% comment %}`.
- Django's `LoginView` puts its own `site_name` (the request host) into the template context and overrides a context
  processor of the same name. The starter uses `product_name`.
- Celery with `config_from_object(..., namespace="CELERY")` ignores `app.conf.task_always_eager = True`; flip it through
  Django settings. The `conftest.py` fixture does.
- Compose on a server needs `--env-file` (the project directory defaults to the first `-f` file's directory), or you
  get default insecure settings and production refuses to start.
- `<meta http-equiv="refresh">` reloads the page and closes folds the user opened; avoid it on pages with folds.
- A scheduled GitHub workflow in a public repository is switched off after 60 days without a commit. Anything that must
  run forever (a weekly image rebuild) needs a keep-alive or a reminder.
- Wrong early claims cost more than slow ones: verify with a restore, a query or a browser, then state the result.

## 10. How to work
1. Plan first, in a short doc: what you will build from the starter, what you will add, the downloads you want approved
   (if any), and the questions you cannot answer yourself. Wait for the owner's go-ahead before coding.
2. Use as FEW PULL REQUESTS as possible. One PR for the scaffold; after that one per user-visible milestone. Do not split
   by layer, by file type or into "tests" and "docs" PRs: a change, its tests and its docs travel together. Never push
   to main, never merge unless the owner names the PR.
3. Never print secrets. Deploy only when asked, and verify on the real host. Say what you could not verify.
4. Before calling anything done, run `make cov`, `make integration`, `manage.py check --deploy` under the production
   settings, and look at the pages in a real browser.

## 11. Deliverables
A running stack in Docker with all tests passing at 100% coverage; `README.md` (what it is and is not), `DEVELOPING.md`,
`DEPENDENCIES.md`, `docs/` with the data contract and ops notes, the vendor record, a Makefile (`build up down test cov
integration migrate createsuperuser logs`), and a short report that lists every decision you made that this brief did not
cover, every seam you could not integration-test and why, and anything you could not verify, so the owner can accept or
change it.

Start by reading the reference files, then post the one-page plan and your questions. Do not start coding until the owner
approves the plan and any download list.
```
