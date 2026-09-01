"""The usage meter may carry these fields and no others.

A count and a hash carry no personal data, which is what keeps the meter outside Decree 356.
Widening this schema is a legal decision, not an engineering one.
"""

METER_FIELDS = {
    "document_uuid",
    "document_type",
    "processed_at",
    "page_count",
    "status",
    "source_sha256",
    "sequence",
}

FORBIDDEN_SUBSTRINGS = ("name", "address", "value", "shipper", "consignee", "filename", "text")


def test_no_meter_field_hints_at_content():
    for field in METER_FIELDS:
        for bad in FORBIDDEN_SUBSTRINGS:
            assert bad not in field, f"Meter field {field!r} looks like it carries content."


def test_meter_schema_is_closed():
    """When metering/schema.py exists it must expose exactly METER_FIELDS."""
    try:
        from metering.schema import METER_PAYLOAD_FIELDS
    except ImportError:
        return  # Not built yet — Phase 5.
    assert set(METER_PAYLOAD_FIELDS) == METER_FIELDS
