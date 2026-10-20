from django.core.exceptions import ImproperlyConfigured

from config.env import env, env_bool

from .base import *  # noqa: F401, F403
from .base import DEV_SECRET_KEY, SECRET_KEY

if SECRET_KEY == DEV_SECRET_KEY:
    raise ImproperlyConfigured("SECRET_KEY (or SECRET_KEY_FILE) must be set when DJANGO_SETTINGS_MODULE is config.settings.prod")

DEBUG = False

# TLS is terminated by the reverse proxy in front of this container; trust its header.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
# The proxy normally redirects http to https. Turn this on only if it does not.
SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", False)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
# Start low, raise once https works everywhere (a long HSTS value cannot be taken back).
SECURE_HSTS_SECONDS = int(env("SECURE_HSTS_SECONDS", "3600"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = False  # preload is a one-way door; opt in per project, not by default
SILENCED_SYSTEM_CHECKS = ["security.W021"]  # the check that asks for SECURE_HSTS_PRELOAD: decided above

# Hashed, compressed static files served by WhiteNoise (collectstatic runs at image build time).
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "config.storage.ManifestStaticFilesStorage"},
}
