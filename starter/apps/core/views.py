from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import connection
from django.db.utils import Error as DatabaseError
from django.http import JsonResponse
from django.shortcuts import redirect
from django.views import View
from django.views.generic import TemplateView

from . import services


class HomeView(LoginRequiredMixin, TemplateView):
    template_name = "core/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        beat = services.last_heartbeat()
        context["heartbeat"] = beat
        context["heartbeat_age"] = services.age_phrase(beat.created_at) if beat else ""
        return context


class DesignView(TemplateView):
    """A living reference of every component in the kit, rendered by the real templates."""

    template_name = "core/design.html"


class HeartbeatView(LoginRequiredMixin, View):
    http_method_names = ["post"]

    def post(self, request):
        services.enqueue_heartbeat("web")
        messages.success(request, "Heartbeat queued. Refresh in a moment to see the worker's answer.")
        return redirect("home")


def healthz(request):
    """Liveness that touches the database: a process that cannot reach its data is not healthy."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except DatabaseError:
        return JsonResponse({"status": "database unavailable"}, status=503)
    return JsonResponse({"status": "ok"})
