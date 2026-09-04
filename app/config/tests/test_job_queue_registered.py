"""The job queue stays registered, so the worker container keeps booting.

Procrastinate is registered in INSTALLED_APPS and nothing in our own code imports it, which makes
it the easiest line in the project to delete by accident while tidying. The cost of that mistake is
not a failing import: it is a worker container that starts, exits with "Unknown command", and
restarts forever, while jobs pile up silently in the database.

These tests cost nothing to run and turn that into a red build instead.
"""

from django.conf import settings
from django.core.management import get_commands

JOB_QUEUE_APP = "procrastinate.contrib.django"


def test_the_job_queue_is_installed():
    assert JOB_QUEUE_APP in settings.INSTALLED_APPS, (
        f"{JOB_QUEUE_APP} is missing from INSTALLED_APPS. Procrastinate on PostgreSQL is the "
        f"locked choice of job queue (D-004); removing it stops the worker from starting."
    )


def test_the_worker_command_exists():
    """The real check: this is what `manage.py procrastinate worker` looks up.

    Asserting on INSTALLED_APPS alone would pass even if the app were registered in a way that
    never contributed its management commands.
    """
    assert "procrastinate" in get_commands(), (
        "`manage.py procrastinate` is not a registered command, so the worker cannot start. "
        "This is the failure that looks like a crash-looping container rather than a code error."
    )
