"""Invariant: the same file ingested twice is one document, and one charge.

This is a money test. CLAUDE.md, hard boundary 6: anything touching document counts has tests.

The scenario is not hypothetical. A forwarder forwards the same arrival notice to two colleagues,
both of whom send it to Flow. An SFTP poller re-reads a directory after a restart. A broker uploads
a file again because the page looked slow. In each case the same bytes arrive twice, and in each
case the customer must be charged once.

The billing half of this - that no second MeterEvent is written - is tested with MeterEvent.
"""

import pytest
from django.db import IntegrityError, transaction

from documents.ingest import ingest_source_file, sha256_of_bytes, sha256_of_file
from documents.models import ExtractionRun, LogicalDocument, SourceFile

pytestmark = pytest.mark.django_db

SYNTHETIC_PDF = b"%PDF-1.7 synthetic arrival notice, not a real document"


def arrive(filename="arrival-notice.pdf", via=SourceFile.ReceivedVia.EMAIL, data=SYNTHETIC_PDF):
    """Simulate a file arriving at Flow."""
    return ingest_source_file(
        sha256=sha256_of_bytes(data),
        original_filename=filename,
        byte_size=len(data),
        page_count=2,
        received_via=via,
    )


def test_the_same_file_arriving_twice_is_one_source_file():
    first, first_created = arrive()
    second, second_created = arrive()

    assert first_created is True
    assert second_created is False, "The second arrival was treated as a new file."
    assert first.pk == second.pk
    assert SourceFile.objects.count() == 1


def test_the_same_file_by_a_different_route_under_a_different_name_is_still_one_file():
    """The bytes decide, not the envelope."""
    first, _ = arrive(filename="arrival-notice.pdf", via=SourceFile.ReceivedVia.EMAIL)
    second, created = arrive(filename="AN-77421-copy.pdf", via=SourceFile.ReceivedVia.UPLOAD)

    assert created is False
    assert first.pk == second.pk
    assert SourceFile.objects.count() == 1
    # The first arrival's details stand. Nothing downstream depends on the filename.
    assert second.original_filename == "arrival-notice.pdf"
    assert second.received_via == SourceFile.ReceivedVia.EMAIL


def test_a_second_arrival_produces_no_second_extraction():
    """The expensive, billable work happens once."""
    source_file, created = arrive()
    assert created is True

    document = LogicalDocument.objects.create(
        source_file=source_file,
        page_indexes=[0, 1],
        doc_type=LogicalDocument.DocType.ARRIVAL_NOTICE,
        doc_type_confidence=0.94,
    )
    ExtractionRun.objects.create(
        logical_document=document,
        model_id="au.anthropic.claude-haiku-4-5-20251001-v1:0",
        prompt_version="arrival_notice.v1",
        status=ExtractionRun.Status.SUCCEEDED,
    )

    # The same file arrives again. The caller sees created=False and stops.
    again, created_again = arrive()
    assert created_again is False

    assert LogicalDocument.objects.filter(source_file=again).count() == 1
    assert ExtractionRun.objects.count() == 1


def test_a_genuinely_different_file_is_a_different_row():
    """The guard must not be so eager that it swallows real work."""
    first, _ = arrive(data=SYNTHETIC_PDF)
    second, created = arrive(data=SYNTHETIC_PDF + b" second shipment")

    assert created is True
    assert first.pk != second.pk
    assert SourceFile.objects.count() == 2


def test_the_database_itself_rejects_a_duplicate_hash():
    """Not just the ingest helper - the constraint is in PostgreSQL.

    Two workers can pick up the same file at the same instant. Application-level checking would let
    both through; a unique index will not.
    """
    arrive()
    with pytest.raises(IntegrityError), transaction.atomic():
        SourceFile.objects.create(
            sha256=sha256_of_bytes(SYNTHETIC_PDF),
            original_filename="sneaked-in-around-the-side.pdf",
            byte_size=100,
            page_count=1,
            received_via=SourceFile.ReceivedVia.SFTP,
        )


def test_hashing_a_stream_and_hashing_bytes_agree(tmp_path):
    """The SFTP path hashes a file handle; the upload path hashes bytes. Same answer, or the
    guard has a hole in it."""
    path = tmp_path / "synthetic.pdf"
    path.write_bytes(SYNTHETIC_PDF)
    with path.open("rb") as handle:
        assert sha256_of_file(handle) == sha256_of_bytes(SYNTHETIC_PDF)
