# Workflow: plans, pull requests, deploys, and traps

## Plan first, then build

1. Read this repository and the project's own README.
2. Post a **one-page plan**: what you will take from `starter/`, what you will add, the downloads you want approved (exact files),
   and the questions only the owner can answer. Wait for a go-ahead.
3. For any new kind of page, follow the design process in [design-language.md](design-language.md#designing-something-new): options,
   real browser, measurements, a written review, and the owner's choice, before building.
4. Build with tests as you go (100% coverage; see [testing.md](testing.md)).

## As few pull requests as possible

- **One PR for the scaffold**: starter copied in, renamed, wired to the project's data. Not "add Dockerfile", then "add tests", then "add
  CSS".
- **After that, one PR per user-visible milestone** ("catalog sync and the three read-only pages"), not per layer, per file type or per
  commit. A change, its tests and its docs travel together.
- Fixes noticed along the way go into the PR of the change that prompted them. A docs correction does not earn its own PR.
- Branch off `main`, **never push to `main`**, and **do not merge** unless the owner names the PR. Keep commits meaningful; the PR is the
  unit of review.
- Open the PR only when `make cov`, `make integration` and `check --deploy` pass and the pages have been looked at in a browser. Say in the
  description what you could **not** verify.

What a small number of large PRs costs: more to review per PR. What it buys: fewer half-built states, fewer merge conflicts between
your own branches, and a main branch that moves in steps a person can follow. Keep each PR coherent enough to describe in a paragraph.

## Before calling anything done

```bash
make cov                      # unit tests, 100% line and branch coverage
make integration              # the real broker, a real worker, the real database
docker compose run --rm web python3 manage.py check
docker compose run --rm web python3 manage.py makemigrations --check --dry-run
```

and then **open the pages in a real browser**: both themes, a phone width, the network tab (one origin), the console (no errors). The
starter's tests did not catch the sign-in page showing the request host instead of the product name; looking did.

## Deploying

Deploy only when asked, and **verify on the real host**: the page renders, the healthcheck is `healthy`, static files are served hashed
with long cache headers, the worker answers a heartbeat. State what you checked and what you could not.

- **Run the web container behind the host's reverse proxy**, published on `127.0.0.1` only. The proxy terminates TLS and sets
  `X-Forwarded-Proto`; `prod.py` trusts it. Start with a low `SECURE_HSTS_SECONDS` and raise it once https works everywhere.
- **Build or pull?** Decide up front. A GHCR package is **private until you make it public**, and a server that is not logged in
  cannot pull it. If the host builds its own images, it needs the base image too (public and anonymous for `python-base`).
- **Compose on a server needs `--env-file`.** The project directory defaults to the directory of the first `-f` file, so without it the
  `.env` next to your compose file is not read, the app starts with default insecure settings, and production refuses to boot. Pass
  `--env-file` explicitly.
- **Data**: the database volume belongs on storage the host already backs up (bind-mount it from a snapshotted dataset), and the README
  says where it is and how it is restored. Prove a restore once; do not assume one.
- **Secrets** arrive as files ([secrets.md](secrets.md)); the server's `docker inspect` should show no secret values.
- Monitor the **data**, not the process: alert on "no heartbeat in N minutes", not only on "container is up". A feed in one of the
  owner's projects went unfetched for eight weeks behind a `/healthz/` that never touched the database.

## Traps

Each of these was hit for real. The starter already avoids them, and most have a test.

| Trap | What happens | What to do |
| --- | --- | --- |
| Bootstrap's `sourceMappingURL` comment | `collectstatic` fails with `The file '...bootstrap.min.css.map' could not be found` when hashing static files | `config/storage.py` drops that pattern; test the production build, not just dev ([frontend.md](frontend.md#the-source-map-trap)) |
| `.env` copied into an image | dev secrets and `DEBUG=True` baked into a published image | `.dockerignore` excludes `.env` and `.env.*`; a test checks it |
| `{# ... #}` over several lines | Django treats `{# #}` as single-line, so a multi-line one renders as visible text | `{% comment %}`; a test scans the templates |
| `LoginView` and `site_name` | Django's auth view puts the request host in `site_name`, overriding a context processor of that name; the top bar showed `127.0.0.1:8000` | use `product_name`; a test pins it |
| `task_always_eager` ignored | `app.conf.task_always_eager = True` does nothing when Celery is configured from Django settings (`namespace="CELERY"`), so tests quietly hit the real broker | set `settings.CELERY_TASK_ALWAYS_EAGER` through Django; the autouse fixture does |
| Test database vs worker | pytest-django's `test_<name>` database is invisible to the worker container | integration tests use `django_db_blocker.unblock()` and the real database, and clean up after themselves |
| `python` and `pip` do not exist | the base image ships `python3` and `pip3` only | use `python3` / `pip3` in the Dockerfile, Makefile and compose commands |
| No compiler in the base image | `pip install` of a package without a wheel fails | add a toolchain in the one worker stage that needs it, never the web image |
| Health endpoint that skips the database | `/healthz/` says healthy while the database is down | it runs `SELECT 1`; and monitor data freshness too |
| `<meta http-equiv="refresh">` | reloads the page and closes any fold the user opened | avoid it on pages with folds; the self-hosting test rejects it |
| Compose without `--env-file` on a server | defaults load, production refuses to start | always pass `--env-file` |
| Private GHCR package | the server cannot pull | make it public, or log the server in, and decide before the first deploy |
| Scheduled GitHub workflows | in a public repo they are switched off after **60 days with no commit** (`disabled_inactivity`); a "weekly rebuild" quietly stops | add a keep-alive, or a reminder to check; look at `gh workflow list` |
| Wrong early claims | "it works" said before it was checked costs more than a slow, correct answer | verify with a restore, a query or a browser, then state the result |
| Unlisted page | a new page that is not in `pages()` escapes the self-hosting scan | add it in the same change |
| Downloading while you are in there | an unapproved file gets vendored | the vendoring test fails; ask first |
