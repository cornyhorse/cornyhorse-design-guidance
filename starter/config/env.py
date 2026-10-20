"""Read configuration from the environment, with Docker/Kubernetes-style secret files.

`env("SECRET_KEY")` returns `$SECRET_KEY`; if that is unset it reads the file named by `$SECRET_KEY_FILE`
(for example `/run/secrets/secret_key`); if neither is set it returns `default`. A file path that is set but
unreadable raises: a deployment mistake must not quietly fall back to a development default.

Why files: a value in the environment is visible to `docker inspect` and to every process that can read
`/proc/<pid>/environ`. See docs/secrets.md in the guidance repo for where the files come from (MattStash).
"""

from __future__ import annotations

import os
from pathlib import Path

TRUE_VALUES = {"1", "true", "yes", "on"}


def env(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name)
    if value is not None:
        return value
    path = os.environ.get(f"{name}_FILE")
    if path:
        return Path(path).read_text(encoding="utf-8").rstrip("\r\n")
    return default


def env_bool(name: str, default: bool = False) -> bool:
    value = env(name)
    return default if value is None else value.strip().lower() in TRUE_VALUES


def env_list(name: str, default: str = "") -> list[str]:
    return [item.strip() for item in (env(name, default) or "").split(",") if item.strip()]
