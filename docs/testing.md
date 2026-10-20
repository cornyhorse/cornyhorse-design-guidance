# Testing: 100% coverage, on purpose

The target is **100% line and branch coverage**, enforced by the tooling rather than by good intentions. `pyproject.toml` has
`fail_under = 100` with `branch = true`; `make cov` and CI fail below it. The starter is at 100% (230 statements, 18 branches) with
138 unit tests and 2 integration tests, and *every* exclusion in a project has to carry its reason in the code.

100% coverage does not mean the code is correct. It means no line was written that no test even *ran*, which is where most
surprises hide. Treat it as a floor, and read the "a new test must be able to fail" section below as the other half.

## Where tests live

```
apps/<name>/tests/       unit tests, next to the code they test
tests/                   project-wide guards (self-hosting, CSP, vendor hashes, production static, policy, health, settings)
tests/integration/       real broker, real worker, real database (marker: integration)
conftest.py              shared fixtures (user, signed_in, tasks run inline)
```

Run everything in the containers, on the same image and database the project ships with:

```bash
make test           # unit tests, no broker needed
make cov            # the same, with the coverage report; fails below 100%
make integration    # migrate, start the worker, run the integration tests
```

Stack: `pytest`, `pytest-django`, `pytest-cov`. `factory-boy` is pre-approved for model factories when a project's setup outgrows a few lines of
`objects.create`; it goes in `test.txt` with a row in `DEPENDENCIES.md`. Faker and `moto` are not by default (`moto` only in a project that
talks to S3). A fixture is a function.

## The coverage policy: test, mock, delete, then pragma

When a line looks untestable, decide on purpose, in this order:

1. **Write a test.** Most "untestable" lines are untested lines. Pass `now` in as an argument so time is deterministic; parametrize
   the branches (`test_age_phrase` covers all four units and the clamp in one table).
2. **Use a mock** for things that are genuinely outside your control: a failing database
   (`patch("apps.core.views.connection")` with `OperationalError`), a provider's HTTP API, the clock, the filesystem. Patch where the
   name is *used*, not where it is defined. Keep mocks at the edge; a test that mocks three internal functions proves nothing.
3. **If the line turns out to be unreachable, it is dead code: delete it.** Several lines in the reference project went this way,
   and the code was better for it.
4. **Only if it truly cannot run in a test**, mark it `# pragma: no cover - <why>`. The reason is **mandatory**:
   `tests/test_policy.py` fails a bare pragma (fewer than 12 characters of explanation). Good reasons name the missing capability:
   `# pragma: no cover - needs a live Redis (see tests/integration)`, `# pragma: no cover - only reachable on a read-only
   filesystem`. A pragma with no reason, or with "hard to test", is a refusal to decide.

`coverage` also excludes `if TYPE_CHECKING:` and `raise NotImplementedError` via `exclude_also`. Migrations and test files are
omitted; everything else under `apps/` and `config/` is measured, including `wsgi.py`, `asgi.py` and the settings modules (they are
imported in tests, which also proves they import).

## Unit tests

- **Services directly**, with plain arguments. **Views** through the Django test client for status codes, redirects, permissions and
  what the response contains. **Template tags** by rendering a small template. **Settings** by loading them fresh with a patched
  environment (see `load_prod_settings` in `tests/test_settings.py`).
- Test the **failure paths** as hard as the happy ones: the 503 when the database is down, the refusal to boot on the development
  secret key, the unreadable secret file that must raise instead of falling back to a default.
- **Celery tasks run inline** in unit tests: `conftest.py` sets `CELERY_TASK_ALWAYS_EAGER` through Django settings. (Assigning
  `celery_app.conf.task_always_eager = True` is silently ignored when Celery is configured from Django settings; the first test run
  of the starter caught this: three failures, rows never written.)
- Mock **at the boundary**, assert on **behaviour**. `record_heartbeat("unit")` is asserted by the row it wrote, not by how it called
  the ORM.

## Integration tests

Integration tests are **not optional**. A unit test proves a piece; an integration test proves the seam between pieces, which is
where multi-container systems break: queue names, task names, serialisation, a worker with different database settings.

Write one **whenever a feature crosses an app or a system boundary**: web to broker to worker to database, an import from another
system, a mail or payment provider, a reverse-proxy header. Not for every feature: if the seam does not exist yet, there is nothing to
test.

`tests/integration/test_worker_roundtrip.py` is the pattern:

- It is marked `integration`, so `pytest` skips it by default and `make integration` runs it (`-m integration`).
- It sends the task **by name** with `app.send_task(...)`, exactly as a web container that does not import the task module would.
- It talks to the **real database**, not pytest-django's throwaway `test_<name>` one, because the worker is another process that
  writes to the real one. The `real_database` fixture uses `django_db_blocker.unblock()`; the test cleans up its own rows.
- It polls with a deadline instead of sleeping a fixed time, and its failure message says what to check.

If a seam **cannot** be tested for real (a paid or live third-party service, hardware), do not quietly skip it. Say so, in the PR and in
the delivery report, with the reason, and cover it with a **contract test** instead: recorded or hand-written responses checked against
the shape you depend on, so a change in the provider's format shows up as a failing test in your repo.

## Guard tests: rules enforced by the suite

Anything cheaper to enforce with a test than to remember becomes a test. The starter ships these:

| Test file | Fails when |
| --- | --- |
| `test_self_hosted.py` | any rendered page or stylesheet loads or runs something not served by this site (external URL, inline script/style, `style=""`, handler, `@import`), a static file a page references is missing, a template has a multi-line `{# #}` comment, raw template syntax leaks into a page |
| `test_csp.py` | the policy differs by a source from the strict one; `unsafe-inline`/`unsafe-eval`/wildcards appear; a response lacks the header |
| `test_vendor_assets.py` | a vendored file's hash differs from the README; a file is unrecorded; an unapproved package, JS file or icon font appears; the sprite is stale; an icon is vendored but unused (or used but missing); a second script appears or `theme.js` grows |
| `test_production_static.py` | WhiteNoise is not right after `SecurityMiddleware`; production `collectstatic` fails or does not hash and compress |
| `test_policy.py` | a `pragma: no cover` has no reason; `requirements/*.txt` and `DEPENDENCIES.md` disagree; a Node toolchain file appears; the Dockerfile is not on the base image; `.dockerignore` would bake in `.env` |
| `test_project_health.py` | `manage.py check` is not clean; a model change lacks a migration; `check --deploy` under the production settings has any warning |
| `test_settings.py` | production accepts the development secret key; the environment reader, `DATABASE_URL` parser or secret-file fallback misbehave |

**When you add a page, add it to `pages()` in `test_self_hosted.py`.** A page that is not listed there is not protected.

## A new test must be able to fail

A test that cannot fail is decoration. Several tests in the reference project were found vacuous this way. After writing a guard,
**break the thing it guards and watch it go red**. The starter's guards were checked like this, each mutation applied to a copy and
reverted:

| Mutation | Caught by |
| --- | --- |
| a CDN `<link>` added to `base.html` | `test_self_hosted` |
| `style="color:red"` on an element | `test_self_hosted` |
| an inline `<script>` before `</body>` | `test_self_hosted` |
| a font `url()` pointed at fonts.gstatic.com | `test_self_hosted` |
| one byte appended to `bootstrap.min.css` | `test_vendor_assets` |
| `'unsafe-inline'` added to `script-src` | `test_csp` |
| `left-pad==1.0` added to `base.txt` | `test_policy` |
| a bare `# pragma: no cover` | `test_policy` |
| an untested function added to `services.py` | `make cov` (99.6%, build fails) |
| the old `site_name` context name restored | `test_the_login_page_shows_our_name_not_the_host` |

That last row is a real bug: Django's `LoginView` injects its own `site_name` (the request host), which overrode the context
processor's value, so the sign-in page's top bar read "127.0.0.1:8000". It was found by *looking* at the page in a browser, not by the
suite, and the test was added afterwards. Tests do not replace looking.

## CI

`starter/.github/workflows/ci.yml` builds the test image, runs the unit tests with the coverage floor, then runs `make integration`.
The repository's own `.github/workflows/starter-ci.yml` does the same against `starter/` so the guidance and its code cannot drift
apart. Workflows are the one piece of this repository that was written but not executed locally (they need GitHub's runners); the
commands inside them are the same ones that were run here.
