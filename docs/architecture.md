# Architecture

A small Django service in containers: one web container, one or more worker containers, a database and a broker.
The guiding idea is that **the web container stays small and boring, and everything heavy lives somewhere else.**

```
                 reverse proxy (TLS)  ← not part of the project; terminates https
                        │  127.0.0.1:8000
                  ┌─────▼─────┐        send_task("name", queue=…)       ┌──────────────┐
   browser ──────►│    web    │ ───────────────────────────────────────►│    redis     │
                  │ gunicorn  │                                         │ (broker only)│
                  │ whitenoise│                                         └──────┬───────┘
                  └─────┬─────┘                                                │ one queue per
                        │ SQL                                                  │ dependency set
                  ┌─────▼─────┐         SQL (results written here)      ┌──────▼───────┐
                  │ postgres  │◄────────────────────────────────────────│   worker(s)  │
                  └───────────┘                                         │ own image,   │
                                                                        │ own requirements
                                                                        └──────────────┘
```

## The stack and why

| Choice | Why |
| --- | --- |
| Django (current release) | Batteries included: ORM, auth, admin, migrations, forms, templates, and from 6.0 a Content-Security-Policy middleware. Fewer packages to add means fewer to audit. |
| PostgreSQL via `DATABASE_URL` | Web and worker are different containers that share one database, which SQLite cannot do safely. `config/settings/base.py` parses the URL with the standard library; it also accepts `sqlite:///` for a project with no workers. |
| Celery + Redis (broker only) | The queue that lets heavy work live in other containers. Redis is a pipe, not a store: no result backend by default, tasks write their results to the database. |
| Gunicorn + WhiteNoise | One container serves the app and its own static files. No nginx container, no shared static volume, no CDN. |
| Python 3.14 on `python-base` | See [container.md](container.md). |
| Server-rendered HTML | Pages are Django templates. The JavaScript policy is in [frontend.md](frontend.md). |

## The dependency budget

**As few dependencies as possible, and each one earns its place in writing.** The starter's `DEPENDENCIES.md` is a ledger,
and `tests/test_policy.py` fails when `requirements/*.txt` and the ledger disagree. The questions to ask, in order:

1. Can Django or the standard library do it?
2. Can about 30 lines of our own code do it? (`config/env.py` and the `DATABASE_URL` parser are exactly this; they replaced
   `django-environ` and `dj-database-url`.)
3. Does it have to be in the **web** container, or can it live in a worker?
4. Only then add it: pinned exactly, in the narrowest requirements file that needs it, with a row saying what it replaces
   and what the alternative costs.

**Pre-approved packages** (the owner's standing OK; each still gets a ledger row when you install it, and the starter does not ship them):
Django REST framework, which is the **default for an HTTP API**; `django-ninja` as the approved alternative; `django-crispy-forms` with
`crispy-bootstrap5`; and `factory-boy` for tests. They have to live with the front-end rules: use DRF's JSON renderer only (the browsable
API has inline styles that the CSP blocks), and self-host or switch off any API documentation page that loads from a CDN (the default
Swagger UI of `drf-spectacular` does). Everything else needs a reason in the ledger, and a new idea needs the owner's OK.

The ledger also lists what is deliberately left out until a project needs it (`drf-spectacular`, `django-filter`,
`django-celery-results`, `moto`, environment helpers). An early project's review found three packages installed and never used.

Node, npm, webpack and Vite are **out**. A test fails if `package.json` or `node_modules` appears. Front-end files that
normally come from npm (Bootstrap, fonts, icons) are fetched once with `curl` from a pinned URL, committed, and recorded
with a hash ([frontend.md](frontend.md#the-vendoring-rule)). If something truly cannot be done without Node, that is a
question for the owner, not a decision for the agent; if the answer is yes, it runs in a throwaway build stage that emits
static files into the repo, never in a runtime image.

## Layout and conventions

```
config/            project package: settings/{base,dev,prod}.py, urls, celery, wsgi/asgi, env.py, storage.py
apps/<name>/       one Django app each; AppConfig.label = "<name>"; imported as apps.<name>
  models.py  services.py  views.py  tasks.py  templatetags/  tests/  migrations/
templates/         at the repository root, with includes/ partials prefixed with _
static/            css/ js/ img/ vendor/ (vendored third-party files, with a README of hashes)
requirements/      base.txt prod.txt worker.txt test.txt (+ one file per heavy worker)
tests/             project-wide guards and tests/integration/
```

- **Views are thin, logic lives in `services.py`.** Services are plain functions that are easy to test with a fixed `now`.
- **UUID primary keys** and `created_at` / `updated_at` on domain models. **A custom user model from the first
  migration**: swapping it in later is painful.
- **Settings come from the environment**, with `NAME_FILE` support for secrets ([secrets.md](secrets.md)). `dev.py` turns
  `DEBUG` on; `prod.py` refuses to start on the development `SECRET_KEY` and sets secure cookies and HSTS (start low and
  raise it: a long HSTS value cannot be taken back).
- **`/healthz/` touches the database.** A health endpoint that does not touch it says "healthy" while the database is
  down. Better still, monitor the *data*: the starter's `Heartbeat` table is written by the worker, and a page that shows "last beat 3
  min ago" catches a worker that is up but stuck, which a process check never will.
- **Say where the data lives and whether it is backed up.** A new project's README should answer this on day one.

## Data coming in: idempotent, validated ingest

For projects that are fed by other systems (a catalog, an inventory, a metrics export), the pattern that worked:

1. Define the contract as a JSON Schema and version it (`schema_version`). Reject unknown keys.
2. Validate the **whole** payload first (schema, then references, then cycles). Write nothing if anything is wrong, and
   report errors with a path ("`hosts[3].parent`: no such host").
3. Apply in **one transaction**, idempotently: the same payload twice changes nothing.
4. **Never delete.** A row that disappears from its feed gets `retired_at`; lists filter on an `active()` manager. Rows made
   by hand carry a `manual` source and are never retired by a feed.
5. **Slugs are the stable identity**, not database ids. Measurements (usage, status) belong to pollers and are not
   overwritten by the feed: inside an item, absent keys are left alone and present keys (even `null`) are applied.
6. The app **does not go and read** other repositories or hold SSH keys. The feed is pushed in (management command or an
   authenticated POST); the app just validates and stores it.

## Celery: isolate dependencies in workers

The web container only **sends** tasks. Anything heavy, compiled or non-Python runs in a worker container that listens
on its own queue and installs its own requirements.

### Rules

- **One queue per dependency set.** `default` for light tasks; `documents` for the PDF/OCR stack; `native` for the Rust
  binary. A worker listens only on the queues it can serve.
- **Send by name.** Give every task an explicit name (`@shared_task(name="documents.extract")`) and send it with
  `app.send_task("documents.extract", args=[document_id], queue="documents")`. The queue contract then does not depend on a
  Python module path, and the web container never has to import the module.
- **Import heavy libraries inside the task function**, never at module top. `autodiscover_tasks()` imports every
  `tasks.py` in every container; a top-level `import pandas` would break the web container that does not have pandas.
- **IDs and JSON only.** Pass primary keys, not model instances; arguments must survive JSON.
- **Idempotent, bounded, observable.** Safe to run twice, with `soft_time_limit`/`time_limit`, and writing their outcome to
  the database (a status column, or a row like `Heartbeat`) rather than to a result backend.
- **Unit tests run tasks inline** (`CELERY_TASK_ALWAYS_EAGER`, set through Django settings: see the trap in
  [workflow.md](workflow.md#traps)). The seam to the real broker and worker is covered by an integration test
  ([testing.md](testing.md#integration-tests)).

### Pattern A: same code, default worker (what the starter does)

The `worker` target of the Dockerfile installs `requirements/worker.txt`, which is just `-r base.txt`. Same code as web, no
extra dependencies, queue `default`.

### Pattern B: a heavy Python dependency in its own worker

Add `requirements/documents.txt` with `-r base.txt` and the heavy library, and one compose service plus one image build:

```yaml
  worker-documents:
    <<: *app
    build:
      context: .
      target: worker
      args:
        WORKER_REQUIREMENTS: requirements/documents.txt
    command: celery -A config worker --loglevel=info --queues=documents
```

```python
@shared_task(name="documents.extract", soft_time_limit=120)
def extract(document_id: int) -> None:
    import pandas  # heavy: only the documents worker image has it

    ...
```

The web image never installs it, so it builds faster, is smaller, and has less to patch. If the library needs a compiler,
the toolchain goes into *that worker's* stage only (the base image has no gcc; see [container.md](container.md)).

### Pattern C: a non-Python binary (Rust, Go, ffmpeg, a C tool)

Compile it in a throwaway builder stage and copy only the binary into the worker image. A Celery task shells out to it
with a strict contract: JSON in, JSON out, a timeout, and a checked exit status.

```dockerfile
FROM rust:1 AS native-build
WORKDIR /src
COPY native/ .
RUN cargo build --release

FROM base AS worker-native
COPY requirements/ requirements/
RUN pip3 install -r requirements/worker.txt
COPY --from=native-build /src/target/release/convert /usr/local/bin/convert
COPY --chown=app:app . .
USER app
CMD ["celery", "-A", "config", "worker", "--loglevel=info", "--queues=native"]
```

```python
@shared_task(name="native.convert", time_limit=300)
def convert(job_id: int) -> None:
    job = Job.objects.get(pk=job_id)
    completed = subprocess.run(
        ["convert", "--input", job.input_path, "--json"],
        check=True, capture_output=True, timeout=240, text=True,
    )
    job.record(json.loads(completed.stdout))
```

> Patterns B and C are the documented shape, not something this repository builds in CI: only pattern A is exercised by
> the starter's tests. Treat the Dockerfile and task above as a sketch to adapt, and add an integration test for the
> real seam when you use it.

If the native tool is a **long-running service** (not a job that starts, runs and ends), do not wedge it into Celery: give
it its own container and a documented contract (HTTP with a JSON schema, or its own queue), and treat it like any other
external system with an integration test.

### Compose topology

| Service | Image target | Listens on | Notes |
| --- | --- | --- | --- |
| `web` | `web` | 127.0.0.1:8000 | gunicorn; no heavy libraries; sends tasks |
| `worker` | `worker` | queue `default` | same code, `requirements/worker.txt` |
| `worker-<name>` | `worker` + `WORKER_REQUIREMENTS` | queue `<name>` | one per heavy dependency set |
| `worker-native` | a derived target | queue `native` | binary copied in from a builder stage |
| `db` | `postgres:16-alpine` | internal | volume on the host, covered by the host's backup |
| `redis` | `redis:7-alpine` | internal | broker only |
| `test` | `test` | n/a | profile `test`; `make test` |

Nothing but the reverse proxy's upstream is published, and only on `127.0.0.1`.
