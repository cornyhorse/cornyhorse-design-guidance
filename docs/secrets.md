# Secrets: MattStash

Credentials, tokens, signing keys and anything else sensitive live in **[MattStash](https://github.com/cornyhorse/mattstash)**, the
owner's KeePass-backed store (a CLI, a Python API and an optional HTTP server; `pip install mattstash`). It is a public repository, so
anyone adopting this guidance can use it too, or substitute their own store and keep the rest of the pattern.

## Ground rules

- **Never print, log, commit or type a secret.** Not in code, not in tests, not in a PR description, not in chat. An agent that needs a new
  credential generates it straight into the store and refers to it by name.
- **Nothing sensitive in the image.** Secrets are not `COPY`'d, not `ARG`s, not in the compose file, not in a committed `.env`.
  `.dockerignore` excludes `.env` and `.env.*` (a test checks it): the first image of the reference project had a `.env` baked in.
- **`.env` holds development defaults only** (`SECRET_KEY=unsafe-dev-secret-change-me`). `.env.example` is committed, `.env` is not.
  `config/settings/prod.py` **refuses to start** on the development key.
- **Files beat environment variables.** A value in the environment is visible to `docker inspect` and to anything that can read
  `/proc/<pid>/environ`. So every secret setting also accepts `NAME_FILE`: `config/env.py` reads `SECRET_KEY` from the environment, or
  else from the file named by `SECRET_KEY_FILE`. A file that is named but unreadable **raises** rather than falling back to a default,
  because a silent fallback hides a deployment mistake.
- **Do not type credentials into login forms** on the owner's behalf; they do their own logins. (A test account you generated for the
  app you are building, on localhost, is fine; do not repeat its values in chat.)

## What goes in it

| Goes in MattStash | Does not |
| --- | --- |
| `SECRET_KEY`, database and broker passwords | Anything public: a site name, a hostname, a feature flag |
| API tokens, OAuth client secrets, SMTP/S3 credentials | A user's *login* password (Django hashes those in the database) |
| Signing keys, webhook secrets, per-device or per-service credentials | WebAuthn/passkey *public* credentials, which are not secrets and belong in the database |
| Recovery codes and other one-time secrets the **app** holds | The MattStash master password itself (see below) |

Name entries `<project-slug>.<setting-name>`, for example `media-hub.secret-key` or `media-hub.database-url`. The prefix lets
`mattstash env --prefix media-hub. --upper` turn them into `SECRET_KEY` and `DATABASE_URL`.

## Pattern 1 (default): files, written at deploy time

The app needs no MattStash dependency at all. At deploy, an operator (or a script) writes each secret to a file with a private mode,
and compose mounts it:

```bash
umask 077
mkdir -p secrets
mattstash get "media-hub.secret-key" --raw > secrets/secret_key      # --raw: only the value, for scripts
mattstash get "media-hub.database-url" --raw > secrets/database_url  # the whole URL, password included
```

```yaml
# docker-compose.prod.yml (excerpt)
secrets:
  secret_key: {file: ./secrets/secret_key}
  database_url: {file: ./secrets/database_url}

services:
  web:
    image: ghcr.io/<owner>/<repo>:latest
    secrets: [secret_key, database_url]
    environment:
      DJANGO_SETTINGS_MODULE: config.settings.prod
      SECRET_KEY_FILE: /run/secrets/secret_key       # config/env.py reads NAME, or else the file at NAME_FILE
      DATABASE_URL_FILE: /run/secrets/database_url
    ports: ["127.0.0.1:8000:8000"]
```

Notes:

- Any setting read through `config/env.py` works this way: `SECRET_KEY`, `DATABASE_URL` and `CELERY_BROKER_URL` all accept a `_FILE`
  twin. A URL that embeds a password is itself a secret, so the whole URL goes in the file.
- Outside Swarm, compose mounts a file secret with the **host file's** owner and mode. The container user (uid 10001 in the starter)
  has to be able to read it. Check this on the real host rather than assuming; this repository did not test it on a Linux host.
- Never commit `secrets/`. Add it to `.gitignore` and `.dockerignore`.

## Pattern 2: inject at start with `mattstash exec` / `env`

For a one-off command, a dev shell, or a host that prefers environment variables, MattStash hands secrets to a process without writing
them to disk or printing them:

```bash
# run a command with the secrets in its environment; the command's exit status is preserved
mattstash exec --prefix media-hub. --upper -- docker compose up -d

# or load them into the current shell (shell-safe: a value cannot break out of the eval)
out=$(mattstash env --prefix media-hub. --upper) && eval "$out"
```

Use `exec` rather than a bare `eval "$(...)"`: if `mattstash` fails, the bare form carries on silently with nothing set. And remember
that variables passed on to a container this way are visible to `docker inspect`; prefer Pattern 1 for production.

## Pattern 3: the app talks to the store at runtime

Only when the **app itself** has to create, read or rotate secrets while it runs (a per-device token, a signing key it generates, recovery
codes). Then `mattstash` becomes a dependency of that project (one row in `DEPENDENCIES.md`), behind **one small module**, so the rest of
the code never imports it. The shape that has worked, from the owner's monitoring project:

```python
"""apps/<name>/secrets.py: the only module that imports mattstash."""
from __future__ import annotations

import logging
from typing import Any

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)
_stash: Any = None


def _read_password_file(path: str) -> str:
    with open(path, encoding="utf-8-sig") as handle:
        password = handle.read().strip()
    if not password:
        raise ImproperlyConfigured("MATTSTASH_PASSWORD_FILE is set but the file is empty")
    return password


def _get_stash() -> Any:
    """A lazy singleton. Constructing MattStash does not open the database; the first get/put does."""
    global _stash
    if _stash is None:
        from mattstash import MattStash

        password_file = getattr(settings, "MATTSTASH_PASSWORD_FILE", None)
        password = _read_password_file(password_file) if password_file else None  # else mattstash resolves it itself
        _stash = MattStash(path=getattr(settings, "MATTSTASH_DB_PATH", None), password=password)
    return _stash


def reset_stash() -> None:  # used by tests
    global _stash
    _stash = None


def get_device_token(device_id: str) -> str | None:
    """None only when there is no such secret. A vault that cannot be used raises a MattStashError subclass."""
    entry = _get_stash().get(f"media-hub.device-{device_id}", show_password=True)
    return None if entry is None else entry["value"] if isinstance(entry, dict) else entry.password
```

Semantics worth keeping (MattStash 0.2): a **missing secret** is `None`/`False`; a **missing, locked or unopenable database** raises a typed
error (`DatabaseNotFoundError`, `DatabaseAccessError`, `DatabaseLockError`) and is never reported as "not found", so callers must not
treat it as "no credentials". The database is never created implicitly: create it once, explicitly, with `mattstash setup`.

Test it like any boundary: a fake `MattStash` class patched into `sys.modules`, `reset_stash()` between tests, one test per branch
(missing secret, empty password file, vault error). The module is small enough that 100% coverage needs no `pragma`.

## Pattern 4: MattStash as a service

For several containers on a private network, MattStash also runs as an image (`ghcr.io/cornyhorse/mattstash:latest`, health check at
`/api/health`, credential endpoints under `/api/v1/`), and the CLI can target it with `--server-url` and `--api-key-file` (or
`MATTSTASH_SERVER_URL` and `MATTSTASH_API_KEY_FILE`). Give it the database read-only (`-v /path:/data:ro`). Keep it off the public
network; the client warns when a non-localhost `http://` URL carries the API key in clear text.

## The master password

- Keep the MattStash database password **out of the database's own mount**: with `--sidecar` the key sits next to the `.kdbx`, which
  protects a copy of the file but not anyone who can read the directory. For services, point `KDBX_PASSWORD_FILE` at a file in a
  *different* mount.
- Back the database up with `mattstash backup` (a consistent, private copy), and rotate with `mattstash rotate-password` after a backup.
- Command-line arguments are visible to every local user and land in shell history. Use stdin or files:
  `printf '%s' "$TOKEN" | mattstash put "media-hub.api-token" --value -`.

## For agents

Generate credentials directly into the store, name them `<slug>.<setting>`, refer to them by name in code and docs, and report which
entries you created. If a task seems to need the *value* of a secret in your context, it almost certainly needs a file mount or an
`exec` wrapper instead.
