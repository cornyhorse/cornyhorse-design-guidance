from django.urls import path

from . import views

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("design/", views.DesignView.as_view(), name="design"),
    path("heartbeat/", views.HeartbeatView.as_view(), name="heartbeat"),
    path("healthz/", views.healthz, name="healthz"),
]
