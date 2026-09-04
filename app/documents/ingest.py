"""Taking a file in, exactly once.

Every route into Flow - the email poller, the SFTP watcher, the upload form - comes through here.
That is the whole point of the module: there is one place where a file becomes a row, so there is
one place where "have we already seen this?" is answered.

Why it matters commercially: Flow charges per document. A forwarder forwarding the same email to
two colleagues, an SFTP poller re-reading a directory, a broker uploading a file a second time
because the first attempt looked slow - each of those would otherwise become a second extraction
and a second line on the invoice for one document. That is the kind of billing error a customer
finds before you do.
"""

import hashlib

from documents.models import SourceFile

# Read the file in chunks rather than loading it into memory. Some scanned bundles are large.
_CHUNK_BYTES = 1024 * 1024


def sha256_of_bytes(data):
    """The SHA-256 of some bytes, as 64 lowercase hexadecimal characters."""
    return hashlib.sha256(data).hexdigest()


def sha256_of_file(file_object):
    """The SHA-256 of an open binary file, read in chunks. Leaves the file rewound."""
    digest = hashlib.sha256()
    file_object.seek(0)
    for chunk in iter(lambda: file_object.read(_CHUNK_BYTES), b""):
        digest.update(chunk)
    file_object.seek(0)
    return digest.hexdigest()


def ingest_source_file(
    *,
    sha256,
    original_filename,
    byte_size,
    page_count,
    received_via,
    mime_type="application/pdf",
    received_at=None,
):
    """Record a file that has arrived. Returns (source_file, created).

    `created` is False when this file has been seen before. When it is False the caller must stop:
    no new pages, no new logical documents, no new extraction run, no new meter event. The existing
    row already has all of those, and the customer has already been charged for them once.

    The check is `get_or_create` on a column the database holds unique, so two workers racing on the
    same file cannot both win - the loser gets the winner's row back.

    The details of the second arrival are deliberately not written over the first. If the same bytes
    arrive under a different filename, the filename recorded is the one from the first arrival, and
    the second arrival is not an event Flow keeps. Nothing downstream depends on the filename.
    """
    defaults = {
        "original_filename": original_filename,
        "mime_type": mime_type,
        "byte_size": byte_size,
        "page_count": page_count,
        "received_via": received_via,
        "status": SourceFile.Status.RECEIVED,
    }
    if received_at is not None:
        defaults["received_at"] = received_at

    source_file, created = SourceFile.objects.get_or_create(sha256=sha256, defaults=defaults)
    return source_file, created
