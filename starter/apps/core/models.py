import uuid

from django.db import models


class Heartbeat(models.Model):
    """One beat written by the worker. The newest row proves web, broker, worker and database all work.

    Monitoring the *data* ("a beat in the last few minutes") catches a worker that is up but stuck;
    monitoring the process would not.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.source} @ {self.created_at:%Y-%m-%d %H:%M:%S}"
