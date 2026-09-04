"""Point the guardrail tests at Django's settings.

These tests live outside `app/`, so they do not pick up the pytest configuration in
`app/pyproject.toml`, and `from django.conf import settings` has nothing to read. Four lines here
rather than a second copy of the pytest configuration at the repository root.

No database is needed: nothing in `tests/` touches one.
"""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
