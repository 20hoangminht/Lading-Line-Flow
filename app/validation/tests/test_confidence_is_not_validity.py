"""Invariant: a field can be read perfectly and still be wrong.

The model's confidence answers "did I read those characters correctly?". Validation answers "is
that value right?". They are different questions with different answers, and the single most
damaging shortcut available in this product is to treat a high confidence score as a pass.

The confidently-wrong field is the one that costs a customer money: a container number scanned
cleanly at 0.99 that fails its check digit, a consignee the customer has never traded with, an
invoice whose line items do not add up to its total. A system that only reviews low-confidence
fields waves all three through.

These tests exist so that anyone who later tries to collapse the two ideas has to delete a test
that says why not.
"""

import pytest
from django.db import IntegrityError, transaction

from documents.models import ExtractedField
from validation.models import ValidationResult

pytestmark = pytest.mark.django_db


def test_a_field_read_with_high_confidence_can_still_fail_validation(make_field):
    """The central case. 0.99 confidence, and the check digit says no."""
    field = make_field(field_key="container_number", value="MSCU1234563", confidence=0.99)
    assert field.routing == ExtractedField.Routing.AUTO

    ValidationResult.objects.create(
        extracted_field=field,
        rule_code="container_check_digit",
        outcome=ValidationResult.Outcome.FAIL,
        detail="Check digit is 3; the number MSCU123456 computes to 7.",
    )

    field.refresh_from_db()
    # Confidence is untouched by the failure. It was never a statement about correctness.
    assert field.confidence == 0.99
    # Routing is untouched too. Routing records the model's uncertainty and nothing else.
    assert field.routing == ExtractedField.Routing.AUTO
    # And yet a human must see it.
    assert field.failed_validation is True
    assert field.needs_human_attention is True


def test_a_field_read_with_low_confidence_can_pass_every_rule(make_field):
    """The mirror case. A smudged scan that nonetheless says something true."""
    field = make_field(field_key="port_of_discharge", value="AUSYD", confidence=0.55)
    assert field.routing == ExtractedField.Routing.REVIEW

    ValidationResult.objects.create(
        extracted_field=field,
        rule_code="port_code_known",
        outcome=ValidationResult.Outcome.PASS,
    )

    assert field.failed_validation is False
    # A human still looks, because the model was not sure it read it right.
    assert field.needs_human_attention is True


def test_two_fields_with_the_same_confidence_can_validate_differently(make_field):
    """If validation were a function of confidence, this test could not pass."""
    good = make_field(field_key="hs_code", value="6907.21", confidence=0.92)
    bad = make_field(field_key="gross_weight_kg", value="0", confidence=0.92)

    ValidationResult.objects.create(
        extracted_field=good,
        rule_code="hs_code_format",
        outcome=ValidationResult.Outcome.PASS,
    )
    ValidationResult.objects.create(
        extracted_field=bad,
        rule_code="weight_is_plausible",
        outcome=ValidationResult.Outcome.FAIL,
        detail="Gross weight of zero on a container shipment.",
    )

    assert good.confidence == bad.confidence
    assert good.failed_validation is False
    assert bad.failed_validation is True


def test_validation_has_no_concept_of_confidence_at_all():
    """Structural, not behavioural: there is nowhere on this model to put a confidence score.

    If someone adds one, this test fails and they have to explain themselves in a pull request.
    """
    column_names = {field.name for field in ValidationResult._meta.get_fields()}
    assert not any("confidence" in name for name in column_names), (
        "ValidationResult grew a confidence field. A validation outcome is not weighted by how "
        "sure the model was. See the module docstring in validation/models.py."
    )


def test_routing_cannot_be_used_to_record_a_validation_failure(make_field):
    """The database refuses the shortcut.

    Sending a confident-but-invalid field to review by flipping `routing` looks harmless and
    destroys the distinction: the exception queue would no longer separate "the model could not
    read it" from "the value is wrong", and the accuracy numbers reported to the customer would mix
    two different failures. The check constraint holds routing to the confidence rule.
    """
    field = make_field(confidence=0.99, threshold_applied=0.85)
    field.routing = ExtractedField.Routing.REVIEW

    with pytest.raises(IntegrityError), transaction.atomic():
        field.save()


def test_a_rule_has_one_current_answer_per_field(make_field):
    """Re-running validation updates the answer rather than piling up history."""
    field = make_field()
    ValidationResult.objects.create(
        extracted_field=field,
        rule_code="party_known",
        outcome=ValidationResult.Outcome.UNKNOWN,
        detail="Customer master data does not cover this party yet.",
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        ValidationResult.objects.create(
            extracted_field=field,
            rule_code="party_known",
            outcome=ValidationResult.Outcome.PASS,
        )


def test_not_checked_is_not_the_same_as_passed(make_field):
    """UNKNOWN exists so an unchecked field can never be reported as a clean one."""
    field = make_field()
    result = ValidationResult.objects.create(
        extracted_field=field,
        rule_code="party_known",
        outcome=ValidationResult.Outcome.UNKNOWN,
    )
    assert result.outcome != ValidationResult.Outcome.PASS
    assert field.failed_validation is False
    # An unknown does not force a review on its own; the confidence decision still governs.
    assert field.needs_human_attention is (field.routing == ExtractedField.Routing.REVIEW)


def test_a_warning_is_surfaced_without_blocking(make_field):
    field = make_field(field_key="shipped_on_date", value="2027-11-02", confidence=0.97)
    ValidationResult.objects.create(
        extracted_field=field,
        rule_code="date_is_plausible",
        outcome=ValidationResult.Outcome.WARN,
        detail="Shipment date is more than a year in the future.",
    )
    assert field.failed_validation is False
    assert field.needs_human_attention is False


def test_one_field_carries_the_results_of_several_rules(make_field):
    field = make_field(field_key="container_number", value="MSCU1234567", confidence=0.96)
    for code, outcome in [
        ("container_check_digit", ValidationResult.Outcome.PASS),
        ("container_prefix_known", ValidationResult.Outcome.PASS),
        ("container_on_this_booking", ValidationResult.Outcome.FAIL),
    ]:
        ValidationResult.objects.create(extracted_field=field, rule_code=code, outcome=outcome)

    assert field.validation_results.count() == 3
    # One failure out of three is still a failure. The reviewer is told which one.
    assert field.failed_validation is True
    failed = field.validation_results.get(outcome=ValidationResult.Outcome.FAIL)
    assert failed.rule_code == "container_on_this_booking"
