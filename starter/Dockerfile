# One Dockerfile, one target per kind of container:
#
#   docker build --target web    .   production web: gunicorn + WhiteNoise, no test or heavy libraries
#   docker build --target worker .   Celery worker: same code, its own requirements file and queue
#   docker build --target test   .   worker + pytest, for `make test`
#
# The base is the owner's PGO+LTO CPython image (public, multi-arch, no compiler in it):
#   https://github.com/cornyhorse/cornyhorse-debian-python
# To build your own, see docs/container.md. For reproducible builds pin it by digest:
#   --build-arg PYTHON_BASE_IMAGE=ghcr.io/cornyhorse/python-base@sha256:<digest>
ARG PYTHON_BASE_IMAGE=ghcr.io/cornyhorse/python-base:3.14

FROM ${PYTHON_BASE_IMAGE} AS base
# The base image provides python3 and pip3 only (no `python`, no `pip`), so use those names everywhere.
ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
# Non-root, fixed uid so bind mounts and volumes have a predictable owner.
RUN useradd --system --uid 10001 --create-home app


FROM base AS web
COPY requirements/base.txt requirements/prod.txt requirements/
RUN pip3 install -r requirements/prod.txt
COPY --chown=app:app . .
# Hash and compress static files into /app/staticfiles for WhiteNoise. Needs no database and no real secret.
RUN SECRET_KEY=build-only DJANGO_SETTINGS_MODULE=config.settings.prod python3 manage.py collectstatic --noinput
USER app
EXPOSE 8000
# The base image has no curl; the standard library is enough. /healthz/ touches the database.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python3", "-c", "import urllib.request as u; u.urlopen('http://127.0.0.1:8000/healthz/', timeout=3)"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]


FROM base AS worker
# A worker that must compile a wheel needs a toolchain, which the base image deliberately lacks:
#   RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && rm -rf /var/lib/apt/lists/*
# Prefer a wheel; add the toolchain only to the worker that needs it, never to the web image.
ARG WORKER_REQUIREMENTS=requirements/worker.txt
COPY requirements/ requirements/
RUN pip3 install -r ${WORKER_REQUIREMENTS}
COPY --chown=app:app . .
USER app
CMD ["celery", "-A", "config", "worker", "--loglevel=info", "--queues=default"]


FROM base AS test
COPY requirements/ requirements/
RUN pip3 install -r requirements/test.txt
COPY --chown=app:app . .
USER app
CMD ["pytest"]
