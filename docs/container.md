# The container: `python-base`

Projects here build on **`ghcr.io/cornyhorse/python-base`**: Debian slim with **CPython compiled from source**, in a small multi-stage
image with no compiler in it. The owner publishes it; source and workflows are at
**<https://github.com/cornyhorse/cornyhorse-debian-python>**. Others can pull the owner's image, build their own from that repository,
or swap in the official `python:3.14-slim` with one build argument.

## What it is (checked, not remembered)

| | |
| --- | --- |
| Image | `ghcr.io/cornyhorse/python-base` |
| Tags | `3.14`, `3.13`, `3.12` (rolling minor), `3.14.x` / `3.13.x` / `3.12.x` (exact patch), `latest` (= `3.14`) |
| Platforms | `linux/amd64` and `linux/arm64` (multi-arch manifests) |
| Pull | **public and anonymous**: no `docker login` needed (verified against the registry's token endpoint) |
| OS | Debian 12 "bookworm" slim (`DEBIAN_VERSION` build arg) |
| Python | built from the python.org source tarball into `/opt/python`, with `/opt/python/bin` on `PATH` |
| Configure flags | `--enable-optimizations` (PGO) `--with-lto` `--with-computed-gotos` `--with-system-expat` `--with-system-ffi` `--enable-loadable-sqlite-extensions` |
| Environment | `PYTHONUNBUFFERED=1`, `PYTHONDONTWRITEBYTECODE=1`, `LANG=C.UTF-8` |
| In the image | `python3`, `pip3`, setuptools, wheel, and only the runtime shared libraries (`libssl3`, `libffi8`, `libsqlite3-0`, `libexpat1`, `zlib1g`, `libbz2-1.0`, `liblzma5`, `libreadline8`, `libncurses6`, `libgdbm6`, `libuuid1`) |
| **Not** in the image | a compiler or any `-dev` package; a `python` or `pip` command (only `python3` / `pip3`); a non-root user (it runs as root) |

## Use it

```dockerfile
ARG PYTHON_BASE_IMAGE=ghcr.io/cornyhorse/python-base:3.14
FROM ${PYTHON_BASE_IMAGE} AS base
WORKDIR /app
RUN useradd --system --uid 10001 --create-home app

FROM base AS web
COPY requirements/ requirements/
RUN pip3 install --no-cache-dir -r requirements/prod.txt
COPY --chown=app:app . .
USER app
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
```

The starter's [`Dockerfile`](../starter/Dockerfile) is the full version: one file, one **target per kind of container** (`web`, `worker`,
`test`), `collectstatic` at build time, a healthcheck that needs no `curl`, and a non-root user.

- **Pin for releases.** `:3.14` moves with each rebuild. For a reproducible production image pin by digest, as the owner's other
  projects do: `docker buildx imagetools inspect ghcr.io/cornyhorse/python-base:3.14` and use
  `--build-arg PYTHON_BASE_IMAGE=ghcr.io/cornyhorse/python-base@sha256:<digest>`. Bump it on purpose, with the tests, not by accident.
- **Use `python3` and `pip3`.** Every command in the Dockerfile, Makefile and compose files says so. (Some of the owner's older images add
  `ln -s "$(command -v python3)" /usr/local/bin/python`; the starter avoids needing it.)
- **No compiler means wheels only.** `psycopg[binary]` ships its own `libpq`, so the web image needs **no `apt-get` at all**. A worker whose
  dependency has no wheel installs a toolchain in *that worker's* stage (`apt-get install -y --no-install-recommends gcc libpq-dev`), never
  in the web image. See [architecture.md](architecture.md#celery-isolate-dependencies-in-workers).
- **Add a user.** The base runs as root; create a fixed-uid user and `USER` to it so bind mounts and volumes have a predictable owner.
- **Check freshness.** `docker run --rm ghcr.io/cornyhorse/python-base:3.14 python3 -VV` says which patch release you are on; compare with
  <https://www.python.org/ftp/python/>. See "Keeping it fresh" below.

## How it compares to the official image

Measured on the same machine (arm64), October 2026:

| | `ghcr.io/cornyhorse/python-base:3.14` | `python:3.14-slim` (official) |
| --- | --- | --- |
| Python | built from source with `--enable-optimizations --with-lto --with-computed-gotos` | built with `--enable-optimizations --with-lto` |
| libpython | static (no `--enable-shared`) | shared (`--enable-shared`) |
| Layout | `/opt/python`, `python3` and `pip3` only | `/usr/local`, with `python`, `python3`, `pip` and `pip3` |
| Debian | 12 (bookworm), pinned by `DEBIAN_VERSION` | 13 (trixie) |
| Size (uncompressed) | 252 MB | 204 MB |

### Is it faster? What was measured, and what was not

The owner has seen this image run a Django data-transformation tool several times faster than a stock `python` image (as much as 8x in one
case). **This repository could not reproduce that at the interpreter level, and it is worth knowing why before relying on it.**

What was measured (`docs/bench/`, arm64 Mac, Docker Desktop, `--cpus 2`, nine stdlib workloads shaped like data transformation: tight
loops, string building, dict aggregation, JSON round trips, regex extraction, `decimal`, `strptime`, `sqlite3`, `csv`; interleaved
rounds, best time of many):

- `python-base:3.14` (3.14.4) against `python:3.14-slim` (3.14.8): **within about 7% overall**, python-base ahead on most tests
  (up to 1.38x on regex, 1.24x on dict work) and behind on a few (`sqlite3` 0.81x, `decimal` 0.92x). The official image is **also** built
  with `--enable-optimizations --with-lto`, and the compiler flags in `sysconfig` are otherwise identical; the differences are static vs shared
  libpython, `--with-computed-gotos` (the official build reports it off), the Debian/GCC release, and the patch version.
- **Single runs are not evidence.** The first run of the same comparison showed the official image *faster* by 1.4x overall; repeating the
  same containers moved individual tests by up to 2x. Docker Desktop on a laptop is noisy. `docs/bench/compare.sh` interleaves the images
  and keeps the best of many rounds for exactly this reason.

So an 8x gap is not coming from PGO, LTO or a static interpreter; those are worth roughly 0 to 25%. It came from something else that
differed between the two setups. Candidates, cheapest to rule out first (none of these were reproduced here):

| Suspect | How to check |
| --- | --- |
| **Emulation.** An `amd64` image on an Apple-silicon host runs under QEMU/Rosetta, commonly several times slower; a multi-arch tag avoids it, a pinned single-arch one does not | `docker image inspect <image> --format '{{.Architecture}}'` against `uname -m`; `docker run --rm <image> python3 -c "import platform;print(platform.machine())"` |
| **Python version.** An older minor (3.9 to 3.11) against 3.14 is typically 1.2x to 1.6x on pure-Python code, more on specific features | `python3 -VV` in each |
| **libc.** An Alpine (musl) image: slower allocator and threading, and wheels that fall back to source builds | `cat /etc/os-release` |
| **Wheels vs pure Python.** `psycopg` without `[binary]` runs its pure-Python implementation; a library installed from source without its C extension is far slower | `python3 -c "import psycopg; print(psycopg.pq.__impl__)"` should say `binary` or `c`, not `python` |
| **Django settings.** `DEBUG=True` makes Django record every SQL query in memory, so a long data-transformation run slows down and bloats | compare `DEBUG` and `DJANGO_SETTINGS_MODULE` in both containers |
| **Bind mounts.** Reading input data from a bind-mounted macOS directory is much slower than from the image layer or a volume | run both with the data in the same place |
| **Resource limits.** `--cpus`, memory limits and swapping, or BLAS/OpenMP thread counts for numpy/pandas | compare `docker run` limits and `nproc` inside |

If you have the tool that showed the gap, the useful experiment is: run **the same code, same data, same settings, same
architecture, same Python minor** in both images with `docs/bench/compare.sh`'s approach (interleaved, best of many) and then change one
suspect at a time. Whatever the cause turns out to be, record it here, because it decides whether the base image is worth the
maintenance.

### Why run your own base anyway

Even with no measured interpreter advantage, there are reasons: **control** (you choose the Python patch release and the Debian suite and
rebuild on your schedule), **consistency** between a Mac and a server (same layout and flags, both architectures), **no surprises** such
as extra packages, and a **supply chain** you can read end to end. The cost is **maintenance**: someone has to keep rebuilding it (below).
If you do not want that job, use the official image and move on:

```bash
docker build --target web --build-arg PYTHON_BASE_IMAGE=python:3.14-slim -t myapp .
```

(The starter's test suite passes on that base too; see the verification notes at the end.)

## Build your own

You need Docker with Buildx and, for the other architecture, either a native builder for it or patience (QEMU emulation is slow).

```bash
git clone https://github.com/cornyhorse/cornyhorse-debian-python
cd cornyhorse-debian-python

# One platform, the one you are on. PGO + LTO make this the slow part (see the timing below).
docker build --build-arg PYTHON_VERSION=3.14.8 -t ghcr.io/<you>/python-base:3.14.8 .

docker run --rm ghcr.io/<you>/python-base:3.14.8 python3 -VV
docker push ghcr.io/<you>/python-base:3.14.8          # after: docker login ghcr.io
```

Measured: **577 seconds** for `PYTHON_VERSION=3.14.8` on an Apple-silicon Mac (native arm64, Docker Desktop), producing a 253 MB image. The
Dockerfile's own comments say 20 to 30 minutes, which is a fair allowance for a slower machine; under QEMU emulation it is far worse.

Build arguments: `PYTHON_VERSION` (the CPython release to compile; the Dockerfile's default is a pinned old patch, so pass the current
one from <https://www.python.org/ftp/python/>) and `DEBIAN_VERSION` (the Debian suite, default `bookworm`).

### What the Dockerfile does, and why

**Stage 1, `builder`** (full `debian`): installs the compiler and the `-dev` headers CPython needs (`build-essential`, `libssl-dev`,
`libffi-dev`, `zlib1g-dev`, `libsqlite3-dev`, `libreadline-dev`, `liblzma-dev`, `libbz2-dev`, `libncurses-dev`, `libgdbm-dev`,
`libexpat1-dev`, `uuid-dev`, `pkg-config`), downloads the source tarball from python.org, and configures:

| Flag | Effect |
| --- | --- |
| `--enable-optimizations` | **PGO**: build once instrumented, run the test-suite subset `--pgo` to record which paths are hot, rebuild using that profile. This is what makes the build slow. |
| `--with-lto` | **LTO**: optimize across translation units at link time. |
| `--with-computed-gotos` | a faster bytecode dispatch loop (on by default where the compiler supports it; made explicit here). |
| `--with-system-expat`, `--with-system-ffi` | link the Debian libraries instead of bundled copies, so security fixes arrive with `apt`, not a Python rebuild. |
| `--enable-loadable-sqlite-extensions` | lets `sqlite3` load extensions (off by default in some builds). |
| `--prefix=/opt/python` | an isolated tree that is trivial to `COPY` into the next stage. |
| *(no `--enable-shared`)* | a statically linked interpreter. |

`make -j"$(nproc)" PROFILE_TASK="-m test --pgo -x test_xml_etree -x test_xml_etree_c"` runs the build with two profiling tests skipped
because they fail in minimal container environments. Then `ensurepip` installs `pip`, `setuptools` and `wheel`, and the stage trims
what a runtime does not need: test directories, `*.a` static libraries, `__pycache__`, and `strip --strip-unneeded` on shared objects.

**Stage 2, `runtime`** (`debian:<suite>-slim`): installs only the **runtime** shared libraries (no `-dev`, no compiler), then
`COPY --from=builder /opt/python /opt/python`, puts `/opt/python/bin` on `PATH`, sets the three environment variables, and checks that
`python3 --version` and `pip3 --version` run.

### Known gaps in the published build, and the fix

A from-source build tells you which optional extension modules it could not build, near the end of the `make` output
(`The necessary bits to build these optional modules were not found`). Building the repository's Dockerfile at 3.14.8 listed three:

| Module | What is missing | Effect |
| --- | --- | --- |
| `_zstd` | `libzstd-dev` in the builder | **`compression.zstd` does not exist** (`ModuleNotFoundError: No module named '_zstd'`). Python 3.14's new standard-library Zstandard support, and anything built on it (for example zstd members in `tarfile` and `zipfile`), is unavailable. The official `python:3.14-slim` has it. |
| `_dbm` | `libgdbm-compat-dev` in the builder | `dbm.ndbm` is unavailable (`dbm.gnu` works). Rarely used. The official image has it. |
| `_tkinter` | Tk | Unavailable, and fine: a server image has no use for it. The official slim image lacks it too. |

The same two gaps are in the **published** `python-base:3.14` image (checked by importing the modules in it). The fix is four lines in the
Dockerfile, one pair per stage, and was verified by building it:

```diff
   # stage 1 (builder): -dev packages
+    libgdbm-compat-dev \
     libgdbm-dev \
 ...
+    libzstd-dev \
     zlib1g-dev \

   # stage 2 (runtime): shared libraries
+    libgdbm-compat4 \
     libgdbm6 \
 ...
+    libzstd1 \
     zlib1g \
```

Result of that build (3.14.8, arm64): `compression.zstd` and `dbm.ndbm` both import, a zstd compress/decompress round trip passes, only
`_tkinter` is reported missing, the image is 0.3 MB larger, and the starter's full test suite passes on it. **When you build your own,
read the "optional modules were not found" lines and decide which you need**; when you add a stdlib-backed feature that depends on a
system library, add both halves (the `-dev` package to the builder, the runtime package to the final stage).

### Multi-arch and keeping it fresh

- **Both architectures**: a registry manifest lists an `amd64` and an `arm64` image under one tag. Emulating arm64 under QEMU on an
  amd64 runner makes a PGO build very slow (the scheduled workflow does exactly that in one job and needs a 180-minute timeout). The
  push-to-main path avoids it: it builds each platform in its own job and merges the two into one tag with
  `docker buildx imagetools create`. Prefer that shape, and build arm64 on an arm64 runner if you have one.
- **Publishing**: the repository's workflows push to GHCR with the built-in `GITHUB_TOKEN`. A new GHCR package is **private**; make it
  public under the package's settings if others (or your server) should pull it without logging in.
- **Staying current**: the repository checks python.org weekly for new 3.12 / 3.13 / 3.14 patch releases and rebuilds when a tag is
  missing, plus a monthly run. **GitHub switches scheduled workflows off after 60 days with no commit to the repository**
  (state `disabled_inactivity`), after which a "weekly" rebuild silently never happens and the image ages. Check
  `gh workflow list -R <you>/cornyhorse-debian-python --all`, re-enable if needed (`gh workflow enable`), and give the repository a
  reason to commit at least every couple of months (a keep-alive commit, or bumping the default `PYTHON_VERSION`).
- **Other Debian suites**: the runtime stage lists package names by hand. Debian 13 renamed several libraries with a `t64` suffix
  (the 64-bit `time_t` transition), so moving `DEBIAN_VERSION` to `trixie` needs that list checked; do not just change the argument.

## Verification notes

Things checked while writing this page, on an arm64 Mac with Docker 29, so you know what is evidence and what is not:

- The published image pulls anonymously; its `python3 -VV`, `CONFIG_ARGS`, OS, size and importable modules are as quoted above. The
  official image's `CONFIG_ARGS` and modules were read from the running container.
- The starter's `web`, `worker` and `test` targets build on `python-base:3.14`, and the same 138 unit tests and 2 integration tests pass
  at 100% line and branch coverage on **three** bases: the published image, the official `python:3.14-slim`, and an image built from
  the repository's Dockerfile at 3.14.8 (and on the patched build above). Database PostgreSQL 16, broker Redis 7.
- Building the repository's Dockerfile at `PYTHON_VERSION=3.14.8` succeeded; timing and the missing modules are quoted above.
- The benchmark above ran on arm64 only. The emulation hypothesis could not be measured (this Docker setup has no amd64 emulation).
- Not checked: an `amd64` build, the GitHub workflows (they need GitHub's runners), Debian 13 (`trixie`) as `DEBIAN_VERSION`, and any
  benchmark.
