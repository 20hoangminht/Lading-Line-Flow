"""The owner's acceptance test is a command, so the command has a test.

`python manage.py show_data_model` is how a non-coder sees that the data model works. If it breaks,
he cannot tell whether the product is broken or the demonstration is. These tests keep the two
apart, and check that it leaves nothing behind.
"""

from io import StringIO

import pytest
from django.core.management import call_command

from documents.models import ExtractedField, ExtractionRun, LogicalDocument, Page, SourceFile
from validation.models import ValidationResult

pytestmark = pytest.mark.django_db


@pytest.fixture
def walkthrough():
    output = StringIO()
    call_command("show_data_model", stdout=output)
    return output.getvalue()


def test_it_shows_one_file_becoming_three_documents(walkthrough):
    assert "Commercial invoice" in walkthrough
    assert "House bill of lading" in walkthrough
    assert "Arrival notice" in walkthrough


def test_it_shows_the_duplicate_being_caught(walkthrough):
    assert "No second reading. No second charge." in walkthrough


def test_it_shows_a_confident_field_failing_validation(walkthrough):
    assert "99% sure it read it correctly" in walkthrough
    assert "container_check_digit" in walkthrough
    assert "Sent to a person: yes" in walkthrough


def test_it_leaves_nothing_behind(walkthrough):
    """It runs on the owner's own database. It must not litter it."""
    assert "rolled back" in walkthrough
    for model in (
        SourceFile,
        Page,
        LogicalDocument,
        ExtractionRun,
        ExtractedField,
        ValidationResult,
    ):
        assert model.objects.count() == 0, f"{model.__name__} rows survived the walk-through."
