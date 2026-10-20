import pytest


@pytest.fixture(autouse=True)
def run_tasks_inline(request, settings):
    """Unit tests run Celery tasks inline: no broker, no worker. `integration` tests use the real ones.

    Celery reads its configuration from Django's settings (namespace CELERY_), so the switch has to be flipped
    there; assigning `celery_app.conf.task_always_eager` is silently ignored.
    """
    if not request.node.get_closest_marker("integration"):
        settings.CELERY_TASK_ALWAYS_EAGER = True


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user("alice", password="correct horse battery staple")


@pytest.fixture
def signed_in(client, user):
    client.force_login(user)
    return client
