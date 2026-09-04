"""The documents data model.

The shape of the whole product is here, so it is worth stating plainly:

    SourceFile          one PDF that arrived, by email, SFTP or upload
      Page              one page of it - size, and whether it has real text or is a scan
      LogicalDocument   one *business* document inside that file
        ExtractionRun   one attempt by the model to read that business document
          ExtractedField  one field the model read, with a confidence score

One source file holds one or more business documents. A single PDF containing a commercial invoice
followed by a bill of lading is the ordinary case in freight, not an unusual one, which is why
LogicalDocument exists as its own row rather than as a few columns on SourceFile. Retrofitting that
split later would mean migrating live customer data.
"""

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.db.models import F, Q
from django.utils import timezone

from config.rls import FlowModel

# A SHA-256 written as lowercase hexadecimal is always exactly 64 characters.
SHA256_HEX = RegexValidator(
    r"^[0-9a-f]{64}$",
    "Must be a SHA-256 as 64 lowercase hexadecimal characters.",
)

# Confidence and thresholds are probabilities. Reused on several fields.
CONFIDENCE_RANGE = [MinValueValidator(0.0), MaxValueValidator(1.0)]


class SourceFile(FlowModel):
    """One file that arrived, exactly once.

    **`sha256` is the idempotency key for the entire system.** The same bytes arriving a second time
    - the customer forwards the same email twice, an SFTP poller re-reads a file, a broker uploads
    what was already sent - must resolve to this same row and must never start a second extraction,
    because a second extraction is a second line on the customer's invoice for one document.

    The uniqueness is enforced by the database, not by a check in application code, so there is no
    race between two workers ingesting the same file at the same moment: the second one loses.
    Everything that ingests a file must go through `documents.ingest.ingest_source_file`, which is
    the only supported way to create one of these rows.

    The billing consequence is tested where billing lives, with MeterEvent.
    """

    class Status(models.TextChoices):
        RECEIVED = "received", "Received"
        PROCESSING = "processing", "Processing"
        PROCESSED = "processed", "Processed"
        FAILED = "failed", "Failed"

    class ReceivedVia(models.TextChoices):
        EMAIL = "email", "Email"
        SFTP = "sftp", "SFTP"
        UPLOAD = "upload", "Upload"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sha256 = models.CharField(
        max_length=64,
        unique=True,
        validators=[SHA256_HEX],
        help_text=(
            "SHA-256 of the file's bytes. The idempotency key: the same file ingested twice "
            "resolves to this row and never produces a second billable extraction."
        ),
    )
    # A filename can carry a party name ("ACME-Pty-Ltd-invoice.pdf"). It stays in the customer's
    # database and never goes into the usage meter or a log line.
    # See docs/decree-356-boundaries.md rules 3 and 4.
    original_filename = models.CharField(max_length=500)
    mime_type = models.CharField(max_length=100, default="application/pdf")
    byte_size = models.PositiveBigIntegerField()
    page_count = models.PositiveIntegerField()
    # When the file arrived, which is not always when this row was written - an emailed file
    # carries the time the email was received.
    received_at = models.DateTimeField(default=timezone.now)
    received_via = models.CharField(max_length=10, choices=ReceivedVia.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RECEIVED)

    class Meta:
        ordering = ["-received_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["-received_at"]),
        ]

    def __str__(self):
        return f"{self.original_filename} ({self.sha256[:12]})"


class Page(FlowModel):
    """One page of a source file.

    `has_text_layer` is the decision point for scans: a page with no text layer needs a different
    and more expensive extraction path, and knowing the answer per page rather than per file means
    a mostly-digital PDF with one scanned page does not get treated as a scan throughout.
    """

    source_file = models.ForeignKey(SourceFile, on_delete=models.CASCADE, related_name="pages")
    # Zero-based, matching how every PDF library counts. Page 1 of the file is index 0.
    index = models.PositiveIntegerField()
    # Page size in PDF points (1/72 inch). Needed to make sense of a bounding box.
    width = models.FloatField()
    height = models.FloatField()
    has_text_layer = models.BooleanField()

    class Meta:
        ordering = ["source_file", "index"]
        constraints = [
            models.UniqueConstraint(fields=["source_file", "index"], name="page_unique_per_file"),
        ]

    def __str__(self):
        return f"page {self.index} of {self.source_file_id}"


class LogicalDocument(FlowModel):
    """One business document found inside a source file.

    `page_indexes` records which pages of the source file this document occupies - `[0, 1]` for an
    invoice on the first two pages of a five-page PDF. It is a list rather than a start/end pair
    because a scanned bundle does not always keep a document's pages together.

    The primary key is a UUID because this identifier is the one thing about a document that leaves
    the customer's deployment: the usage meter posts it to Lading Line as proof of a billable
    document (F-003). A sequential integer would tell Lading Line the customer's document volume;
    a UUID tells it nothing.
    """

    class DocType(models.TextChoices):
        COMMERCIAL_INVOICE = "commercial_invoice", "Commercial invoice"
        HOUSE_BILL_OF_LADING = "house_bill_of_lading", "House bill of lading"
        MASTER_BILL_OF_LADING = "master_bill_of_lading", "Master bill of lading"
        ARRIVAL_NOTICE = "arrival_notice", "Arrival notice"
        # Classification could not decide. Not a failure - it routes to a human.
        UNKNOWN = "unknown", "Unknown"

    class Status(models.TextChoices):
        IDENTIFIED = "identified", "Identified"
        EXTRACTING = "extracting", "Extracting"
        NEEDS_REVIEW = "needs_review", "Needs review"
        READY = "ready", "Ready"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source_file = models.ForeignKey(
        SourceFile, on_delete=models.CASCADE, related_name="logical_documents"
    )
    page_indexes = models.JSONField(
        default=list,
        help_text="Zero-based page indexes of the source file this document occupies, e.g. [0, 1].",
    )
    doc_type = models.CharField(max_length=30, choices=DocType.choices, default=DocType.UNKNOWN)
    doc_type_confidence = models.FloatField(default=0.0, validators=CONFIDENCE_RANGE)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.IDENTIFIED)

    class Meta:
        ordering = ["source_file", "id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(doc_type_confidence__gte=0.0) & Q(doc_type_confidence__lte=1.0),
                name="logicaldocument_confidence_is_a_probability",
            ),
        ]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["doc_type"]),
        ]

    def __str__(self):
        return f"{self.get_doc_type_display()} pages {self.page_indexes}"

    def clean(self):
        """Check the page list is a sensible set of pages that exist in the source file."""
        if not isinstance(self.page_indexes, list) or not self.page_indexes:
            raise ValidationError(
                {"page_indexes": "A logical document must cover at least one page."}
            )
        if not all(isinstance(i, int) and not isinstance(i, bool) for i in self.page_indexes):
            raise ValidationError({"page_indexes": "Page indexes must be whole numbers."})
        if any(i < 0 for i in self.page_indexes):
            raise ValidationError(
                {"page_indexes": "Page indexes are zero-based and cannot be negative."}
            )
        if len(set(self.page_indexes)) != len(self.page_indexes):
            raise ValidationError({"page_indexes": "The same page is listed twice."})
        if self.source_file_id and max(self.page_indexes) >= self.source_file.page_count:
            raise ValidationError(
                {"page_indexes": "A page index is past the end of the source file."}
            )

    @property
    def page_count(self):
        """How many pages this document occupies. The usage meter bills on this."""
        return len(self.page_indexes)


class ExtractionRun(FlowModel):
    """One attempt by the model to read one logical document.

    A run per attempt, rather than overwriting: when accuracy is argued about six months from now,
    the record of which model and which prompt produced which answer is the argument.

    `model_id` and `prompt_version` are recorded on the row rather than read from settings at
    display time, because settings change and history does not.
    """

    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"

    logical_document = models.ForeignKey(
        LogicalDocument, on_delete=models.CASCADE, related_name="extraction_runs"
    )
    # The Bedrock model that produced this run, e.g. the AU inference profile in
    # settings.BEDROCK_MODEL_ID. When settings.BEDROCK_ENABLED is off, local runs record the
    # fixture source here instead, so a run can never be mistaken for a real model call.
    model_id = models.CharField(max_length=200)
    prompt_version = models.CharField(max_length=50)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.QUEUED)
    input_tokens = models.PositiveIntegerField(null=True, blank=True)
    output_tokens = models.PositiveIntegerField(null=True, blank=True)
    # A failure category and a short technical message. NEVER a document, a page of text, a model
    # response body, or an extracted value: an error string is one of the easiest ways for customer
    # data to end up somewhere it must never be. See docs/decree-356-boundaries.md rule 3.
    error = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status"])]

    def __str__(self):
        return f"run {self.pk} of {self.logical_document_id} ({self.status})"

    @property
    def duration_seconds(self):
        """How long the run took, or None if it has not finished."""
        if self.started_at and self.finished_at:
            return (self.finished_at - self.started_at).total_seconds()
        return None


class ExtractedField(FlowModel):
    """One field the model read out of one logical document.

    **Confidence is not correctness.** `confidence` is the model's own opinion of how sure it is
    that it read the characters correctly. It says nothing about whether the value is right in the
    real world: a container number can be read perfectly at 0.99 confidence and still fail its
    check digit, and a consignee name can be read perfectly and still not be a party the customer
    has ever traded with. That second judgement lives in `validation.ValidationResult` and the two
    are never merged. See `validation/tests/test_confidence_is_not_validity.py`.

    `routing` is therefore the confidence decision and only the confidence decision: below the
    threshold a human looks at it, at or above the threshold it flows through. A database check
    constraint holds `routing` to exactly that rule, so it is not possible to quietly repurpose the
    column to mean "a validation rule failed" - that would collapse the two ideas this model exists
    to keep apart.

    `threshold_applied` stores the threshold that was in force at the time. The setting
    `REVIEW_CONFIDENCE_THRESHOLD` will be tuned; without this column, changing it would silently
    rewrite the meaning of every routing decision already made.
    """

    class Routing(models.TextChoices):
        AUTO = "auto", "Automatic"
        REVIEW = "review", "Human review"

    extraction_run = models.ForeignKey(
        ExtractionRun, on_delete=models.CASCADE, related_name="fields"
    )
    # Per-document-type field schemas arrive in Phase 1 as configuration rows, so this stays a
    # plain string for now. There is deliberately no uniqueness on (run, field_key): an invoice has
    # many line items, and they share a key.
    field_key = models.CharField(max_length=100)
    value_raw = models.TextField(blank=True)
    value_normalised = models.TextField(blank=True)
    confidence = models.FloatField(validators=CONFIDENCE_RANGE)
    # Where on the file the value was found, so the review screen can show the reviewer the spot.
    page_index = models.PositiveIntegerField(null=True, blank=True)
    # [x0, y0, x1, y1] in PDF points on that page. Null when the model cannot cite a location.
    bbox = models.JSONField(null=True, blank=True)
    threshold_applied = models.FloatField(validators=CONFIDENCE_RANGE)
    routing = models.CharField(max_length=10, choices=Routing.choices)

    class Meta:
        ordering = ["extraction_run", "field_key"]
        constraints = [
            models.CheckConstraint(
                condition=Q(confidence__gte=0.0) & Q(confidence__lte=1.0),
                name="extractedfield_confidence_is_a_probability",
            ),
            models.CheckConstraint(
                condition=Q(threshold_applied__gte=0.0) & Q(threshold_applied__lte=1.0),
                name="extractedfield_threshold_is_a_probability",
            ),
            # Routing means "the model was not sure enough", and nothing else. Enforced here so no
            # future code can express "this failed validation" by setting routing to review.
            models.CheckConstraint(
                condition=(
                    Q(confidence__lt=F("threshold_applied"), routing="review")
                    | Q(confidence__gte=F("threshold_applied"), routing="auto")
                ),
                name="extractedfield_routing_follows_confidence_alone",
            ),
        ]
        indexes = [
            models.Index(fields=["routing"]),
            models.Index(fields=["field_key"]),
        ]

    def __str__(self):
        return f"{self.field_key} @ {self.confidence:.2f} ({self.routing})"

    @staticmethod
    def route_for(confidence, threshold):
        """The routing rule, in one place: below the threshold a human looks at it.

        This is the only function in the system permitted to decide `routing`. It takes a
        confidence and a threshold and nothing else - in particular it cannot see validation
        results, which is the point.
        """
        if confidence < threshold:
            return ExtractedField.Routing.REVIEW
        return ExtractedField.Routing.AUTO

    def save(self, *args, **kwargs):
        """Fill in the threshold and the routing decision if the caller did not."""
        if self.threshold_applied is None:
            self.threshold_applied = settings.REVIEW_CONFIDENCE_THRESHOLD
        if not self.routing:
            self.routing = self.route_for(self.confidence, self.threshold_applied)
        super().save(*args, **kwargs)

    @property
    def failed_validation(self):
        """True if any validation rule said this value is wrong. Independent of confidence."""
        return self.validation_results.filter(outcome="fail").exists()

    @property
    def needs_human_attention(self):
        """The two separate judgements, combined at the moment of asking and not before.

        A field reaches a human if the model was unsure (`routing`) **or** if a validation rule
        failed (`failed_validation`). They are stored apart and read together, deliberately: a
        field can be perfectly legible and still wrong, and the review queue must show it.
        """
        return self.routing == self.Routing.REVIEW or self.failed_validation
