# Dependencies

The rule: **as few as possible, and each one has to earn its place here.** A test
(`tests/test_policy.py`) fails if a package is in `requirements/*.txt` without a row below, or has a row
without being in the requirements. Adding a row is a decision, not a formality: say what it replaces and
what the alternative would cost.

Before adding a package, ask in this order: can Django or the standard library do it? Can ~30 lines of our
own code do it? Does it need to live in the web container, or should it live in a worker (see
`docs/architecture.md`)? Only then add it, pinned exactly, in the narrowest requirements file that needs it.

## Python

| Package | File | Why it is here | Alternative considered |
| --- | --- | --- | --- |
| `django` | base | The framework. ORM, auth, admin, forms, templates, migrations, and (6.0+) the Content-Security-Policy middleware. | none: it is the point |
| `whitenoise` | base | Serves the repo's own static files from the web container, hashed and compressed, so no CDN and no nginx mount are needed. | an nginx container with a static volume (more moving parts) |
| `psycopg` | base | PostgreSQL driver (`[binary]` ships libpq, so the image needs no system packages). Postgres because web and worker containers share one database. | SQLite (cannot be shared safely between containers) |
| `celery` | base | Task queue. The web container only *sends* tasks (it needs the client); the heavy work runs in worker containers. `[redis]` pulls the Redis client for the broker. | Django's `tasks` framework (no production backend yet), cron (no retries, no fan-out) |
| `gunicorn` | prod | Production WSGI server for the web image. | `runserver` (not for production) |
| `pytest` | test | Test runner. | Django's `unittest` runner (no fixtures, no markers) |
| `pytest-django` | test | Django integration for pytest: database, client, settings fixtures. | hand-rolled setup |
| `pytest-cov` | test | Coverage with a hard 100% floor. | `coverage run` by hand |

## Pre-approved: the owner's standing OK

These need no permission. They still need a row in the table above the moment you install one (a test enforces it), in the narrowest
requirements file that needs them, and they are still only added when the project needs them: the starter does not ship them.

| Package | Use it for | Watch for |
| --- | --- | --- |
| `djangorestframework` | **The default for an HTTP API** that is more than a couple of views: serializers, permissions, pagination. | Use the JSON renderer only; the browsable API has an inline `<style>` and `style=""` attributes and breaks the CSP. For schema docs use `drf-spectacular`, whose Swagger UI loads from a CDN by default; self-host it with `drf-spectacular-sidecar` or leave the UI off. API keys are stored hashed. |
| `django-ninja` | An approved alternative to DRF when a typed, annotation-driven API fits better. It brings Pydantic with it. | Its interactive docs page may load Swagger UI from a CDN: check, and turn the docs off or self-host them, then add the page to `pages()` in `tests/test_self_hosted.py` if you keep it. Do not run DRF and ninja side by side without a reason. |
| `django-crispy-forms` with `crispy-bootstrap5` | Rendering forms. | Its output must pass the self-hosting scan (no inline styles or handlers) and should look like the kit: map its Bootstrap classes onto the tokens in `components.css`. Not built or verified in the starter; the scan will say if it is wrong. |
| `factory-boy` | Model factories for tests. | `test.txt` only. Without it, a plain `objects.create` in a fixture is fine and has no dependency. |

## Deliberately not here (ask first)

Things that are common elsewhere and are left out on purpose. Add one only with a reason you can write down, and ask.

- **drf-spectacular, django-filter, django-celery-results, django-fernet-fields**: bring them in with the project that needs them, with a row
  saying why. (An early project carried three such packages that were installed and never used.)
- **moto, Faker, dj-database-url, django-environ**: `config/env.py` and `db_from_url` are about 40 lines; `moto` only in a project that
  talks to S3.
- **Any JavaScript or CSS framework beyond the vendored Bootstrap CSS**, and anything from npm. See `static/vendor/README.md` and
  `docs/frontend.md`.

## Not Python dependencies, but recorded here

- Base image: `ghcr.io/cornyhorse/python-base` (see `docs/container.md`).
- `postgres:16-alpine` and `redis:7-alpine` containers in `docker-compose.yml`.
- Front-end assets: only what is listed in `static/vendor/README.md`, each with a hash.
