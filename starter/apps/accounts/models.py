import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """A custom user from the first migration: swapping the user model later is painful."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
