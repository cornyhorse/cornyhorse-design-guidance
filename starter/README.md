# Starter

A working Django project that already follows the guidance in the parent repository: self-hosted static files under a strict
Content-Security-Policy, the "instrument panel" design kit, a Celery worker in its own container, a Dockerfile on `python-base`, and a
test suite held at 100% coverage. It is deliberately small: a sign-in page, an overview, a component reference at `/design/`, a
`/healthz/` that touches the database, and a heartbeat that proves web, broker, worker and database all work.

## Run it

```bash
cp .env.example .env            # development defaults only; .env is git-ignored
make build                      # web, worker and test images, on ghcr.io/cornyhorse/python-base:3.14
make migrate
make createsuperuser
make up                         # http://127.0.0.1:8000  (web, worker, postgres, redis)
```

Sign in, press **Queue a heartbeat** on the overview: the web container sends `core.record_heartbeat` to Redis, the worker container runs it
and writes a row, and the page says "last beat N s ago".

```bash
make test          # unit tests
make cov           # unit tests + coverage; fails below 100%
make integration   # migrate, start the worker, run the integration tests (real broker, worker, database)
```

To use the official image as the base instead: `docker compose build --build-arg PYTHON_BASE_IMAGE=python:3.14-slim` (or edit the
`ARG` default in the `Dockerfile`). To build your own base, see `docs/container.md` in the parent repository.

## What is in it

```
config/             settings (base/dev/prod), urls, celery, env.py (NAME or NAME_FILE), storage.py (hashed static files)
apps/accounts/      custom user model (UUID key), from the first migration
apps/core/          views, services.py, a Celery task, the {% load ui %} tags (icons, status chips, usage bars), tests
templates/          base.html, includes/ partials, sign-in, overview, /design/
static/css/         tokens.css  components.css  app.css  fonts.css
static/js/          theme.js (the only script: Light / Auto / Dark)
static/vendor/      Bootstrap CSS, Bootstrap Icons sprite, IBM Plex: every file hashed in README.md
tests/              project-wide guards and tests/integration/
Dockerfile          targets: web, worker, test        docker-compose.yml   web, worker, db, redis, test
DEPENDENCIES.md     the dependency ledger (a test enforces it)
```

## Make it yours

1. Copy this directory to the root of a new repository. Delete nothing from `tests/`; those are the rules.
2. Set `SITE_NAME` (in `.env` and your deployment) to rename the product. Search for "Starter" for the few places that mention it.
3. Replace the `Heartbeat` demo with your own models, services and views under `apps/<name>/` (label = bare name, imported as
   `apps.<name>`), and add each new page to `pages()` in `tests/test_self_hosted.py`.
4. Add dependencies only with a row in `DEPENDENCIES.md`. Put heavy ones in their own worker (see `docs/architecture.md`).
5. In production: `DJANGO_SETTINGS_MODULE=config.settings.prod`, secrets as files (`SECRET_KEY_FILE`, `DATABASE_URL_FILE`), the container
   behind your reverse proxy on `127.0.0.1`. `prod.py` refuses to start on the development secret.
6. Read `CLAUDE.md`; it is the short version of the rules for whoever (or whatever) works in the repository next.

## Where the rules live

The reasoning is in the parent repository's `docs/`: [architecture](../docs/architecture.md), [container](../docs/container.md),
[front end](../docs/frontend.md), [design language](../docs/design-language.md), [testing](../docs/testing.md),
[secrets](../docs/secrets.md), [workflow](../docs/workflow.md).
