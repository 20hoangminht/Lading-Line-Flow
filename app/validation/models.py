"""Validation: is the value right, as opposed to legibly read.

This app exists as a separate thing from extraction for one reason, and it is worth being blunt
about it because collapsing the two is the most tempting shortcut in the product.

The model returns a confidence score. That score answers one question: *how sure is the model that
it read those characters correctly?* It does not answer, and cannot answer:

  - Is MSCU1234567 a real container number? (Check digit says no.)
  - Is "Acme Freight Pty Ltd" a party this customer has ever traded with? (Master data says no.)
  - Do the line items add up to the invoice total? (Arithmetic says no.)
  - Is 30 February 2026 a date? (The calendar says no.)
  - Is SGSIN a port code? (The code list says yes; the shipment says the cargo left Haiphong.)

A value can be read at 0.99 confidence and fail every one of those. A value can be read at 0.60
confidence and be perfectly correct. The two numbers are about different things, they are stored in
different tables, and no code path in Flow may derive one from the other.

The commercial reason: the customer's trust in Flow rests on it catching errors, and the errors
that matter most are the confidently-wrong ones. A system that only reviews low-confidence fields
is a system that waves through a clean scan of the wrong container number.
"""

from django.db import models

from config.rls import FlowModel


class ValidationResult(FlowModel):
    """The outcome of running one validation rule against one extracted field.

    One row per rule per field, so a field that passes four rules and fails one shows exactly which
    one failed and why. The alternative - a single valid/invalid flag on the field - loses the
    reason, and the reason is what the reviewer needs.

    Note what is deliberately absent from this model: there is no confidence column, and no
    reference to one. A validation outcome is not weighted by how sure the model was.
    """

    class Outcome(models.TextChoices):
        # The rule ran and the value satisfied it.
        PASS = "pass", "Pass"
        # The rule ran and the value did not satisfy it. A human must look, whatever the confidence.
        FAIL = "fail", "Fail"
        # The rule ran and the value is odd but not wrong - a date far in the future, a weight at
        # the edge of plausible. Surfaced, not blocking.
        WARN = "warn", "Warn"
        # The rule could not run. Usually the customer's master data does not cover this yet.
        # Distinct from PASS on purpose: "we did not check" must never read as "we checked".
        UNKNOWN = "unknown", "Unknown"

    extracted_field = models.ForeignKey(
        "documents.ExtractedField",
        on_delete=models.CASCADE,
        related_name="validation_results",
    )
    # A stable short code for the rule, e.g. "container_check_digit", "party_known",
    # "totals_reconcile". Stable because accuracy reporting groups on it across releases.
    rule_code = models.CharField(max_length=100)
    outcome = models.CharField(max_length=10, choices=Outcome.choices)
    # Why, in words a reviewer can act on: "check digit is 3, expected 7". This may quote the
    # value, because it stays inside the customer's own database. It must never be copied into the
    # usage meter, a log line or a support bundle. See docs/decree-356-boundaries.md rules 3 and 4.
    detail = models.TextField(blank=True)
    checked_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["extracted_field", "rule_code"]
        constraints = [
            # A rule has one current answer for a field. Re-running it updates the row.
            models.UniqueConstraint(
                fields=["extracted_field", "rule_code"],
                name="validationresult_one_row_per_rule_per_field",
            ),
        ]
        indexes = [models.Index(fields=["outcome"])]

    def __str__(self):
        return f"{self.rule_code}: {self.outcome}"
