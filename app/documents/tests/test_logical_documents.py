"""One PDF, several business documents.

A customer emails a single ten-page PDF. Inside it are a commercial invoice, a house bill of lading
and an arrival notice. That is the ordinary case in freight, and the data model has to hold it
without anyone doing anything clever.
"""

import pytest
from django.core.exceptions import ValidationError

from documents.models import LogicalDocument, Page, SourceFile

pytestmark = pytest.mark.django_db


@pytest.fixture
def bundle(db):
    """A ten-page mixed PDF, the first three pages of which are a scan."""
    source_file = SourceFile.objects.create(
        sha256="a" * 64,
        original_filename="synthetic-mixed-bundle.pdf",
        byte_size=1_048_576,
        page_count=10,
        received_via=SourceFile.ReceivedVia.EMAIL,
    )
    for index in range(10):
        Page.objects.create(
            source_file=source_file,
            index=index,
            width=595.0,
            height=842.0,
            has_text_layer=index >= 3,
        )
    return source_file


def test_one_file_splits_into_several_documents(bundle):
    LogicalDocument.objects.create(
        source_file=bundle,
        page_indexes=[0, 1, 2],
        doc_type=LogicalDocument.DocType.COMMERCIAL_INVOICE,
        doc_type_confidence=0.96,
    )
    LogicalDocument.objects.create(
        source_file=bundle,
        page_indexes=[3, 4],
        doc_type=LogicalDocument.DocType.HOUSE_BILL_OF_LADING,
        doc_type_confidence=0.91,
    )
    LogicalDocument.objects.create(
        source_file=bundle,
        page_indexes=[5, 6, 7, 8, 9],
        doc_type=LogicalDocument.DocType.ARRIVAL_NOTICE,
        doc_type_confidence=0.88,
    )

    documents = bundle.logical_documents.all()
    assert documents.count() == 3
    assert sum(document.page_count for document in documents) == bundle.page_count
    assert set(documents.values_list("doc_type", flat=True)) == {
        "commercial_invoice",
        "house_bill_of_lading",
        "arrival_notice",
    }


def test_a_document_can_occupy_pages_that_are_not_next_to_each_other(bundle):
    """Scanned bundles are not always collated in order."""
    document = LogicalDocument(
        source_file=bundle,
        page_indexes=[0, 4, 7],
        doc_type=LogicalDocument.DocType.MASTER_BILL_OF_LADING,
        doc_type_confidence=0.80,
    )
    document.full_clean()
    document.save()
    assert document.page_count == 3


def test_house_and_master_bills_are_different_document_types(bundle):
    """They name different parties and drive different work. Kept apart in the schema."""
    house = LogicalDocument.objects.create(
        source_file=bundle,
        page_indexes=[0],
        doc_type=LogicalDocument.DocType.HOUSE_BILL_OF_LADING,
        doc_type_confidence=0.93,
    )
    master = LogicalDocument.objects.create(
        source_file=bundle,
        page_indexes=[1],
        doc_type=LogicalDocument.DocType.MASTER_BILL_OF_LADING,
        doc_type_confidence=0.93,
    )
    assert house.doc_type != master.doc_type


def test_a_document_cannot_claim_a_page_the_file_does_not_have(bundle):
    document = LogicalDocument(
        source_file=bundle,
        page_indexes=[9, 10],
        doc_type=LogicalDocument.DocType.ARRIVAL_NOTICE,
        doc_type_confidence=0.5,
    )
    with pytest.raises(ValidationError):
        document.full_clean()


@pytest.mark.parametrize(
    "page_indexes",
    [
        pytest.param([], id="no pages at all"),
        pytest.param([1, 1], id="the same page twice"),
        pytest.param([-1], id="a negative page"),
        pytest.param(["1"], id="a page index that is text"),
    ],
)
def test_nonsense_page_lists_are_refused(bundle, page_indexes):
    document = LogicalDocument(
        source_file=bundle,
        page_indexes=page_indexes,
        doc_type=LogicalDocument.DocType.COMMERCIAL_INVOICE,
        doc_type_confidence=0.5,
    )
    with pytest.raises(ValidationError):
        document.full_clean()


def test_a_page_number_is_used_once_per_file(bundle):
    """The page inventory is a fact about the file, so it cannot list page 3 twice."""
    from django.db import IntegrityError, transaction

    with pytest.raises(IntegrityError), transaction.atomic():
        Page.objects.create(
            source_file=bundle, index=3, width=595.0, height=842.0, has_text_layer=True
        )


def test_scanned_pages_are_identified_page_by_page(bundle):
    """A mostly-digital bundle with three scanned pages is not a scanned bundle."""
    scanned = bundle.pages.filter(has_text_layer=False)
    assert list(scanned.values_list("index", flat=True)) == [0, 1, 2]


def test_deleting_the_file_deletes_everything_found_inside_it(bundle):
    """The customer deletes a document; nothing derived from it survives."""
    LogicalDocument.objects.create(
        source_file=bundle,
        page_indexes=[0],
        doc_type=LogicalDocument.DocType.COMMERCIAL_INVOICE,
        doc_type_confidence=0.9,
    )
    bundle.delete()
    assert LogicalDocument.objects.count() == 0
    assert Page.objects.count() == 0
