"""A walk through the data model in plain English, using made-up documents.

A data model is invisible. This command makes it visible: it builds a realistic shipment out of
synthetic documents, prints what the database now believes, and then throws all of it away.

Nothing it creates survives. The whole command runs inside a transaction that is rolled back at the
end, so it can be run as many times as you like on any database without leaving a mark.

Run it with:

    python manage.py show_data_model
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from documents.ingest import ingest_source_file, sha256_of_bytes
from documents.models import ExtractedField, ExtractionRun, LogicalDocument, Page
from validation.models import ValidationResult

# Not a real document. Not a real company. Not a real shipment.
SYNTHETIC_PDF = b"%PDF-1.7 synthetic ten-page bundle for demonstration only"


class Command(BaseCommand):
    help = "Walk through the data model with synthetic documents, then roll it all back."

    def handle(self, *args, **options):
        try:
            with transaction.atomic():
                self._walk_through()
                raise _Finished()
        except _Finished:
            pass

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "Everything above was rolled back. The database is exactly as you left it."
            )
        )

    # -- the walk-through, step by step ---------------------------------------------------

    def _walk_through(self):
        source_file = self._step_one_a_file_arrives()
        self._step_two_the_same_file_arrives_again(source_file)
        documents = self._step_three_one_file_holds_three_documents(source_file)
        field = self._step_four_the_model_reads_the_invoice(documents["invoice"])
        self._step_five_confident_and_wrong(field)

    def _heading(self, number, text):
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING(f"{number}. {text}"))

    def _step_one_a_file_arrives(self):
        self._heading(1, "A ten-page PDF arrives by email")

        source_file, _created = ingest_source_file(
            sha256=sha256_of_bytes(SYNTHETIC_PDF),
            original_filename="HCM-SYD-shipment-bundle.pdf",
            byte_size=len(SYNTHETIC_PDF),
            page_count=10,
            received_via="email",
        )
        for index in range(10):
            Page.objects.create(
                source_file=source_file,
                index=index,
                width=595.0,
                height=842.0,
                # The first three pages are a scan with no text on them.
                has_text_layer=index >= 3,
            )

        self.stdout.write(f"   Filename        {source_file.original_filename}")
        self.stdout.write(f"   Fingerprint     {source_file.sha256[:24]}...")
        self.stdout.write(f"   Pages           {source_file.page_count}")
        self.stdout.write("   New to Flow?    yes")
        scanned = source_file.pages.filter(has_text_layer=False).count()
        self.stdout.write(
            f"   Flow can see that {scanned} of the {source_file.page_count} pages are scans "
            f"rather than proper text. Those cost more to read."
        )
        return source_file

    def _step_two_the_same_file_arrives_again(self, source_file):
        self._heading(2, "The same file arrives again, forwarded, under a different name")

        duplicate, created = ingest_source_file(
            sha256=sha256_of_bytes(SYNTHETIC_PDF),
            original_filename="FW_ FW_ shipment docs (2).pdf",
            byte_size=len(SYNTHETIC_PDF),
            page_count=10,
            received_via="upload",
        )
        self.stdout.write("   Arrived as      FW_ FW_ shipment docs (2).pdf")
        self.stdout.write("   New to Flow?    no - Flow has seen these exact bytes before")
        self.stdout.write(f"   Resolved to     {duplicate.original_filename}")
        self.stdout.write(
            self.style.WARNING(
                "   No second reading. No second charge. This is the rule that stops a "
                "forwarded email being billed twice."
            )
        )
        assert duplicate.pk == source_file.pk
        assert created is False

    def _step_three_one_file_holds_three_documents(self, source_file):
        self._heading(3, "Inside that one file are three different business documents")

        invoice = LogicalDocument.objects.create(
            source_file=source_file,
            page_indexes=[0, 1, 2],
            doc_type=LogicalDocument.DocType.COMMERCIAL_INVOICE,
            doc_type_confidence=0.96,
        )
        house_bill = LogicalDocument.objects.create(
            source_file=source_file,
            page_indexes=[3, 4],
            doc_type=LogicalDocument.DocType.HOUSE_BILL_OF_LADING,
            doc_type_confidence=0.91,
        )
        arrival_notice = LogicalDocument.objects.create(
            source_file=source_file,
            page_indexes=[5, 6, 7, 8, 9],
            doc_type=LogicalDocument.DocType.ARRIVAL_NOTICE,
            doc_type_confidence=0.88,
        )

        for document in (invoice, house_bill, arrival_notice):
            pages = ", ".join(str(index + 1) for index in document.page_indexes)
            self.stdout.write(
                f"   {document.get_doc_type_display():<24} pages {pages:<14} "
                f"sure it is this type: {document.doc_type_confidence:.0%}"
            )
        self.stdout.write(
            "   One file in, three documents out. That is the normal case in freight, and it is "
            "why the file and the document are separate things in the database."
        )
        return {"invoice": invoice, "house_bill": house_bill, "arrival_notice": arrival_notice}

    def _step_four_the_model_reads_the_invoice(self, invoice):
        self._heading(4, "The model reads the invoice, and says how sure it is of each field")

        run = ExtractionRun.objects.create(
            logical_document=invoice,
            model_id="au.anthropic.claude-haiku-4-5-20251001-v1:0",
            prompt_version="commercial_invoice.v1",
            status=ExtractionRun.Status.SUCCEEDED,
            input_tokens=3200,
            output_tokens=480,
        )

        readings = [
            ("container_number", "MSCU1234563", 0.99),
            ("invoice_total", "18,420.00", 0.97),
            ("port_of_loading", "VNSGN", 0.94),
            ("gross_weight_kg", "12,4O0", 0.61),
        ]
        container_field = None
        for field_key, value, confidence in readings:
            field = ExtractedField.objects.create(
                extraction_run=run,
                field_key=field_key,
                value_raw=value,
                value_normalised=value,
                confidence=confidence,
                page_index=0,
                threshold_applied=0.85,
            )
            if field_key == "container_number":
                container_field = field
            verdict = (
                "goes straight through"
                if field.routing == ExtractedField.Routing.AUTO
                else "a person must check it"
            )
            self.stdout.write(
                f"   {field_key:<20} {value:<14} {field.confidence:.0%} sure   -> {verdict}"
            )

        self.stdout.write(
            "   The threshold is 85%. The weight came out at 61% because the scan turned a zero "
            "into a letter O, so a person looks at that one."
        )
        return container_field

    def _step_five_confident_and_wrong(self, field):
        self._heading(5, "The important case: read perfectly, and still wrong")

        ValidationResult.objects.create(
            extracted_field=field,
            rule_code="container_check_digit",
            outcome=ValidationResult.Outcome.FAIL,
            detail="Last digit is 3. For MSCU123456 it should be 6.",
        )
        ValidationResult.objects.create(
            extracted_field=field,
            rule_code="container_prefix_known",
            outcome=ValidationResult.Outcome.PASS,
        )

        self.stdout.write(f"   Field           {field.field_key} = {field.value_raw}")
        self.stdout.write(f"   Model was       {field.confidence:.0%} sure it read it correctly")
        self.stdout.write("   And it was      - the characters on the page really do say that")
        self.stdout.write("")
        for result in field.validation_results.all():
            mark = "FAIL" if result.outcome == ValidationResult.Outcome.FAIL else "pass"
            self.stdout.write(f"   {mark}   {result.rule_code:<26} {result.detail}")
        self.stdout.write("")
        self.stdout.write(
            self.style.ERROR(
                "   A container number cannot end in 3 here. The number is wrong on the document "
                "itself, and no amount of confidence fixes that."
            )
        )
        self.stdout.write(
            f"   Sent to a person: {'yes' if field.needs_human_attention else 'no'} "
            f"- not because the model was unsure, but because the value failed a rule."
        )
        self.stdout.write(
            "   This is the case that earns the customer's trust. A system that only checks the "
            "fields it was unsure about would have let this one through."
        )


class _Finished(Exception):
    """Raised to roll the transaction back once the walk-through has printed."""
