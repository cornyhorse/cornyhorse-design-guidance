# cornyhorse-design-guidance

How I build small web projects, written down so an agent (or a person) can start a new one without re-deciding everything.

It is three things:

| | |
| --- | --- |
| **[PROMPT.md](PROMPT.md)** | A copy-and-paste brief for a coding agent: the stack, the rules, the look, the traps. Fill in the inputs, paste, go. |
| **[docs/](docs/)** | The reasoning behind each rule, with the evidence. Read these when the prompt says "see docs". |
| **[starter/](starter/)** | A working, tested Django project that already follows all of it. Copy it, rename it, build on it. |

The rules came out of a real project (a private Django dashboard whose design was reviewed, broken, fixed and shipped) and my other
repositories. Where there is a rule there was a reason, and the reason is in the docs.

## The short version

- **Django, containers, few dependencies.** Python 3.14, Django, PostgreSQL, Celery. Every package in `requirements/` has to be justified in a
  ledger (`DEPENDENCIES.md`), and a test fails if it is not. DRF (default for APIs), django-ninja, crispy-forms and factory-boy are
  pre-approved. Node is out.
- **Heavy things live in workers.** The web container imports nothing heavy. Libraries and non-Python binaries go in their own Celery worker
  containers on their own queues. ([architecture](docs/architecture.md))
- **A lean base image you control.** Projects build on [`ghcr.io/cornyhorse/python-base`](https://github.com/cornyhorse/cornyhorse-debian-python)
  (Debian slim, CPython compiled from source, public, no compiler inside). Anyone can build their own; the steps are in
  [docs/container.md](docs/container.md).
- **Nothing from outside the server.** No CDN, no Google Fonts, no analytics. Third-party CSS, fonts and icons live in the repo, with
  hashes, and WhiteNoise serves them. A strict Content-Security-Policy makes the browser enforce it and tests fail on any exception.
  ([front end](docs/frontend.md))
- **Almost no JavaScript.** None by default, one 49-line file for the theme toggle, a popular vendored library only with permission.
- **An instrument-panel look.** Warm paper and graphite neutrals, IBM Plex, rectangular status chips (icon + label, never colour alone), light
  and dark that follow the OS, AA contrast measured rather than eyeballed. ([design language](docs/design-language.md))
- **100% coverage, on purpose.** Test, then mock, then delete dead code, then `pragma: no cover` with a mandatory reason. Integration tests for
  every seam. ([testing](docs/testing.md))
- **Secrets in MattStash**, delivered as files or injected at start; never printed, logged, committed or baked into an image.
  ([secrets](docs/secrets.md))
- **As few pull requests as possible.** One for the scaffold, then one per user-visible milestone. ([workflow](docs/workflow.md))

## Using it

**With an agent**: open [PROMPT.md](PROMPT.md), fill in the inputs, paste the block into a fresh session in an empty repository. The prompt
tells the agent to read these docs and start from `starter/`.

**By hand**:

```bash
cp -R starter/ ../my-new-project && cd ../my-new-project
cp .env.example .env
make build && make migrate && make up       # http://127.0.0.1:8000, sign in after `make createsuperuser`
make cov                                    # 100% coverage, or the build fails
make integration                            # web -> Redis -> worker container -> PostgreSQL
```

Rename the product with one setting (`SITE_NAME`), then read [starter/README.md](starter/README.md).

## What is verified

The starter was built and run, not just written:

- Built on `python-base:3.14` and on the official `python:3.14-slim` (the same 138 tests pass on both, at 100% line and branch coverage,
  on PostgreSQL 16).
- The integration tests send a task by name from the web side through Redis to a separate worker container and read the result back from
  PostgreSQL.
- The production image (`gunicorn` + WhiteNoise) serves hashed, gzipped static files with immutable cache headers, the full CSP, and passes
  its Docker healthcheck.
- In a real browser: one origin only, six fonts loaded from the site, zero inline styles, no console errors, no horizontal scroll at 320 px,
  light and dark.
- The guard tests were mutation-checked: a CDN link, an inline style or script, a changed vendored byte, a loosened CSP, an unlisted
  dependency, a bare pragma and an untested function each turn the build red.

Not verified here: the GitHub workflows (they need GitHub's runners), an `amd64` build, and anything on a Linux host. Details are in the docs
where they matter.

## License

MIT. The vendored files under `starter/static/vendor/` keep their own licences (Bootstrap and Bootstrap Icons: MIT; IBM Plex: SIL OFL 1.1);
the licence text is next to each.
