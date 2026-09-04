"""Shared test fixtures for the Flow application.

Everything here is synthetic. No real document, no real party name, no real shipment.
See CLAUDE.md, hard boundary 4.
"""

import hashlib

import pytest

from documents.models import ExtractedField, ExtractionRun, LogicalDocument, SourceFile


def synthetic_sha256(seed):
    """A believable SHA-256 for a file that does not exist."""
    return hashlib.sha256(seed.encode()).hexdigest()


@pytest.fixture
def source_file(db):
    """A five-page PDF that arrived by email."""
    return SourceFile.objects.create(
        sha256=synthetic_sha256("bundle-one"),
        original_filename="synthetic-bundle.pdf",
        byte_size=204_800,
        page_count=5,
        received_via=SourceFile.ReceivedVia.EMAIL,
    )


@pytest.fixture
def logical_document(source_file):
    """A commercial invoice occupying the first two pages of that file."""
    return LogicalDocument.objects.create(
        source_file=source_file,
        page_indexes=[0, 1],
        doc_type=LogicalDocument.DocType.COMMERCIAL_INVOICE,
        doc_type_confidence=0.97,
    )


@pytest.fixture
def extraction_run(logical_document):
    """One successful attempt to read that invoice."""
    return ExtractionRun.objects.create(
        logical_document=logical_document,
        model_id="au.anthropic.claude-haiku-4-5-20251001-v1:0",
        prompt_version="commercial_invoice.v1",
        status=ExtractionRun.Status.SUCCEEDED,
        input_tokens=3200,
        output_tokens=480,
    )


@pytest.fixture
def make_field(extraction_run):
    """Build an extracted field. Routing is left to the model unless a test forces it."""

    def _make(field_key="container_number", value="MSCU1234566", confidence=0.99, **kwargs):
        kwargs.setdefault("threshold_applied", 0.85)
        kwargs.setdefault("page_index", 0)
        return ExtractedField.objects.create(
            extraction_run=extraction_run,
            field_key=field_key,
            value_raw=value,
            value_normalised=value,
            confidence=confidence,
            **kwargs,
        )

    return _make
