"""Threshold routing: below the line a human looks at it, at or above the line it flows through.

The threshold itself lives in one place, settings.REVIEW_CONFIDENCE_THRESHOLD, and is copied onto
each field as it is decided so that tuning the setting later does not rewrite history.
"""

import pytest
from django.conf import settings

from documents.models import ExtractedField

pytestmark = pytest.mark.django_db

AUTO = ExtractedField.Routing.AUTO
REVIEW = ExtractedField.Routing.REVIEW


@pytest.mark.parametrize(
    ("confidence", "threshold", "expected"),
    [
        pytest.param(0.99, 0.85, AUTO, id="clearly sure"),
        pytest.param(0.60, 0.85, REVIEW, id="clearly unsure"),
        pytest.param(0.85, 0.85, AUTO, id="exactly on the threshold flows through"),
        pytest.param(0.8499, 0.85, REVIEW, id="a hair under the threshold does not"),
        pytest.param(0.0, 0.85, REVIEW, id="no idea at all"),
        pytest.param(1.0, 0.85, AUTO, id="certain"),
    ],
)
def test_the_routing_rule(confidence, threshold, expected):
    assert ExtractedField.route_for(confidence, threshold) == expected


def test_routing_is_decided_on_save_when_the_caller_does_not_say(make_field):
    unsure = make_field(field_key="gross_weight_kg", confidence=0.42)
    sure = make_field(field_key="port_of_loading", confidence=0.98)

    assert unsure.routing == REVIEW
    assert sure.routing == AUTO


def test_the_threshold_in_force_is_recorded_on_the_field(extraction_run):
    field = ExtractedField.objects.create(
        extraction_run=extraction_run,
        field_key="invoice_total",
        value_raw="12450.00",
        value_normalised="12450.00",
        confidence=0.93,
        threshold_applied=None,
    )
    assert field.threshold_applied == settings.REVIEW_CONFIDENCE_THRESHOLD


def test_changing_the_threshold_later_does_not_rewrite_past_decisions(make_field, settings):
    """Yesterday's field was judged against yesterday's threshold, and still says so."""
    field = make_field(confidence=0.90, threshold_applied=0.85)
    assert field.routing == AUTO

    settings.REVIEW_CONFIDENCE_THRESHOLD = 0.95
    field.refresh_from_db()

    assert field.threshold_applied == 0.85
    assert field.routing == AUTO


def test_a_field_can_be_read_from_a_page_and_a_place_on_it(make_field):
    """The review screen needs to put a box around the value it is asking about."""
    field = make_field(page_index=1, bbox=[72.0, 640.0, 260.0, 656.0])
    field.refresh_from_db()
    assert field.page_index == 1
    assert field.bbox == [72.0, 640.0, 260.0, 656.0]


def test_a_document_can_have_many_values_under_one_key(make_field):
    """An invoice has line items. They share a field key and that is correct."""
    make_field(field_key="line_item_description", value="Ceramic tiles, 20x20", confidence=0.95)
    make_field(field_key="line_item_description", value="Grout, 25kg bags", confidence=0.95)
    assert ExtractedField.objects.filter(field_key="line_item_description").count() == 2
