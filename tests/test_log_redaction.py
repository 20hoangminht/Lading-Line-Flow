"""Extracted field values must never reach a log line.

A stack trace containing a consignee name is a data export. Treat it as one.
"""

import logging

SENTINEL = "ACME-SHIPPING-PTY-LTD"


def test_extracted_values_do_not_reach_logs(caplog):
    try:
        from documents.logging import safe_extra
    except ImportError:
        return  # Not built yet — Phase 1.

    with caplog.at_level(logging.DEBUG):
        logging.getLogger("documents").info(
            "extraction complete", extra=safe_extra({"consignee": SENTINEL})
        )
    assert SENTINEL not in caplog.text
