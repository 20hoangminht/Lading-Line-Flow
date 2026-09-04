# DECISIONS.md — Flow architecture decision log

**Append-only. Never rewrite an entry.** If a decision changes, add a new entry that supersedes the
old one and says so. The history is the point.

Every entry states: what was decided, what was rejected, why, what it costs per month, and how hard
it is to reverse.

**Reversal cost:** Trivial (config change) · Low (a day or two) · Medium (a week or two, maybe a
migration) · High (a month or more, or client-visible) · Very high (effectively a rebuild).

This log starts at F-001. The strategic decisions D-001 to D-021 live in the previous repository and
in the Claude project; the ones that still bind are restated in `CLAUDE.md` under "Locked decisions".

---

## F-001 — Single-tenant, customer-owned AWS account

**Decided.** Flow runs entirely inside an AWS account the customer creates, owns, pays for and
controls, in ap-southeast-2 (Sydney). Lading Line publishes a signed container image and a
CloudFormation template and holds no credentials in that account at any point.

**Rejected — Lading Line-hosted multi-tenant SaaS.** It is the better product and the better
economics, and it is what the business will return to once a Singapore operating entity with real
substance exists. It is unavailable now because it puts a Vietnamese company squarely inside Decree
356 Article 21(1).

**Rejected — AWS account assignment (build then transfer).** Requires AWS's conditional consent
against eleven requirements, a root-credential handover and immediate replacement of billing and tax
details. Weeks of elapsed time, and it creates the one moment where Lading Line demonstrably held
keys to an account that will hold real data.

**Cost.** Roughly A$216/month per tenant, paid by the customer. **Reversal cost: Very high.**

---

## F-002 — No NAT gateway

**Decided.** Fargate tasks run in public subnets with public IPs and a security group that accepts
nothing inbound except from the load balancer. Publicly addressed, not publicly reachable. S3 uses a
free gateway endpoint.

**Rejected — NAT gateways.** Two cost A$120/month, more than half the optimised bill and nearly four
times the cost of the model inference that does the actual work.

**Rejected — VPC interface endpoints.** Counter-intuitively not cheaper: five endpoints
(`ecr.api`, `ecr.dkr`, `logs`, `secretsmanager`, `bedrock-runtime`) cost about the same as one NAT
gateway in a single availability zone and more across two.

**Cost.** Saves about A$110/month per tenant. **Reversal cost: Low.**

---

## F-003 — Content-free usage meter as the billing record of truth

**Decided.** Each deployment maintains an append-only meter table and posts a signed daily batch to
Lading Line containing only document UUID, type, timestamp, page count, status and a SHA-256 of the
source file. The signature proves the batch came from an unmodified build; sequence numbers make gaps
detectable. The customer sees the same table in Flow.

**Why.** Revenue is a per-document count and that count is the database. Under a customer-owned
architecture the database sits with the counterparty; without a meter there is no defensible invoice.

**Decree 356.** A count and a cryptographic hash carry no personal data, and running a billing meter
is neither providing nor operating a personal-data processing system. See
`docs/decree-356-boundaries.md`.

**Cost.** Negligible. **Reversal cost: Medium** — it is the invoice.

---

## F-004 — One source file, many logical documents

**Decided.** A file that arrives and a business document inside it are two different tables.
`SourceFile` is the PDF that turned up; `LogicalDocument` is the invoice, the bill of lading or the
arrival notice found inside it, holding a list of the page indexes it occupies. One file routinely
produces several documents.

**Rejected — document type and page range as columns on the file.** Simpler, and wrong. A customer
emailing one ten-page PDF containing an invoice, a house bill of lading and an arrival notice is the
ordinary case in freight, not an edge case. A one-file-one-document model would have to be unpicked
the first week of real documents, after live data existed.

**Also decided.** House and master bills of lading are separate document types rather than one type
with a flag. They name different parties and drive different work. Owner's call, 4 September 2026.

**Cost.** None. **Reversal cost: High** — client-visible and a data migration once documents exist.

---

## F-005 — Model confidence and validation are separate judgements, and the database enforces it

**Decided.** Two different questions get two different tables. `ExtractedField.confidence` is the
model's opinion that it read the characters correctly. `ValidationResult` is whether the value is
right: check digits, known parties, totals that reconcile, dates that exist. `ExtractedField.routing`
is held to the confidence rule alone by a database check constraint, so routing cannot be quietly
repurposed to mean "a validation rule failed". `ValidationResult` has no confidence column and no
reference to one.

**Rejected — one quality score, or a single valid/invalid flag on the field.** It reads as an
economy and is the most damaging shortcut available in the product. The errors that cost a customer
money are the confidently wrong ones: a clean scan of the wrong container number sails through at
0.99. A system that only reviews low-confidence fields waves those through, and the customer finds
out before Flow does.

**Consequence.** A field reaches a human if the model was unsure **or** a rule failed. The two are
stored apart and read together at the moment of asking.

**Cost.** None. **Reversal cost: High** — it is the accuracy claim the product is sold on.

---

## F-006 — SHA-256 of the file is the idempotency key

**Decided.** `SourceFile.sha256` is unique in the database. The same bytes arriving a second time
resolve to the existing row and start no new work: no new pages, no new logical documents, no new
extraction run, no new meter event. Everything that takes a file in goes through
`documents.ingest.ingest_source_file`.

**Rejected — filename and byte size.** The same document arrives under different names constantly:
a forwarder forwards an email, a broker re-uploads, an SFTP poller re-reads a directory after a
restart. Names are not identity.

**Rejected — a deduplication pass after ingestion.** By then the model has already been called and
the document has already been counted, which is the thing being prevented.

**Why it matters.** Revenue is a per-document count (F-003). A duplicate charge is the kind of
billing error a customer finds first, and it costs more in trust than in money.

**Cost.** None. **Reversal cost: Low.**

---

## F-007 — Billing follows content, not bytes

**Decided.** A document that arrives again with different bytes but an identical extracted field set
is not charged a second time. A re-send whose field set differs in any way **is** charged, because
Flow re-read it, re-scored it and refiled it, and that work is what is being sold.

This extends F-006 rather than replacing it. F-006 catches the byte-identical file at the door,
before any model call, and remains the first line of defence and the idempotency key that
`docs/pricing.md` locks. F-007 catches what F-006 cannot see: a forwarded email or an internal
re-send routinely re-encodes a PDF — a different producer, different compression, a rebuilt cover
page — so the bytes change while the document does not. Both keys stay in force.

**Mechanism.** A content fingerprint over the canonicalised, normalised field set of a logical
document. Confidence scores and bounding boxes are excluded: they are the model's opinion about the
reading, not the content of the document, and they move between runs on identical input.

**The normaliser, precisely.**

| Field kind | Normalised to |
|---|---|
| Numbers and amounts | Separators and currency symbols stripped, compared as decimals. `A$18,420.00`, `18420` and `18,420.00` are one value |
| Names and party fields | Upper-cased, punctuation removed, repeated whitespace collapsed to a single space |
| Dates | ISO 8601 `YYYY-MM-DD`, whatever the source format |
| Codes — port, HS, container prefix, currency | Upper-cased |

Two things the normaliser must never smooth away:

- **Absent is not empty.** A field the model did not find and a field it found blank are different
  documents. They must fingerprint differently.
- **Any changed digit is a change.** No rounding, no tolerance, no fuzzy matching on numbers. A
  gross weight of 12400 and one of 12401 are different documents.

**Rejected — charging on every arrival.** Defensible on the argument that Flow did the work, and
wrong commercially. The customer experiences one document and sees two charges, and "your mail
server re-encoded the attachment" is not an explanation that survives a billing conversation.

**Rejected — fingerprinting the extracted text layer instead of the field set.** Cheaper, and it
fails exactly where it is needed: a re-encoded scan produces different text for the same document,
and a re-flowed PDF changes word order without changing a single value.

**Timing.** The fingerprint is computed and stored from Phase 5, with the meter. The column is added
on Friday alongside MeterEvent, so no migration is needed later against live customer data.

**Risk — the model cost is spent before the duplicate is known.** The document must be read before
its field set exists, so a duplicate costs one full extraction and earns nothing: roughly US$0.009
of inference against A$2.20 of forgone revenue at the first metered band. Immaterial, and accepted.

**Risk — extraction is not deterministic.** The same document read twice can produce a field set
that differs in some small way, so a genuine duplicate can fingerprint as new and be charged. This
is the failure that matters, because it is a wrong invoice rather than a missed one. The
normalisation must therefore be aggressive, and the false-positive rate must be measured against the
golden sets built in Phase 1 before this goes anywhere near an invoice.

**Cost.** Negligible — one hash per document, plus the occasional unbilled extraction above.
**Reversal cost: Medium** — it is the invoice.

---

## F-008 — Flow flags, it never corrects

**Decided.** A value that fails validation but was read correctly is flagged to the customer and
released with the flag attached. Flow never alters it and never blocks the document.

**Why.** A container number that is wrong on the bill of lading is wrong in the world. The shipment
still has to move, and the forwarder resolves it with the carrier exactly as they would have without
Flow. Blocking would make Flow a bottleneck inside someone else's operation on the strength of a
rule Flow wrote. Correcting would make Lading Line the author of a document it did not issue.

This is positioning as much as behaviour, and it belongs beside rule 5 of
`docs/decree-356-boundaries.md`: Flow never submits to a government system. Flow reads, checks and
hands back. It does not act on the customer's behalf.

**Rejected — auto-correcting obvious errors.** A check digit one transposition away from valid is
tempting to fix silently. A wrong correction is worse than a wrong value, because the flag is
visible and the correction is not: the reviewer sees a clean field and has no reason to look.

**Rejected — blocking the document until the flag is cleared.** It turns a data-quality signal into
an operational stoppage, and the first time it holds up a container the customer switches the whole
feature off.

**Consequence for Friday.** ReviewEvent needs a **"confirmed as printed"** action: the reviewer says
the value really is what the document says, and the field is released with its failing
ValidationResult intact. The flag is not cleared, because it is still true. Confirming is a
statement about the reading, not about the world.

**Cost.** None. **Reversal cost: High** — client-visible, and part of how Flow is sold.

---

## F-009 — Document-type classification has its own threshold, 90%

**Decided.** Classification confidence is judged separately from field confidence, and at a higher
bar: **0.90**, against 0.85 for fields. Below it the document goes to a person *before* extraction
runs. Added as `CLASSIFY_CONFIDENCE_THRESHOLD` in `app/config/settings.py` and `.env.example`,
alongside `REVIEW_CONFIDENCE_THRESHOLD`.

**Why higher.** A field below threshold is one field a person checks. A document type below
threshold is every field wrong at once, because the type chooses the schema: an arrival notice read
against a commercial invoice schema does not produce a few doubtful values, it produces a page of
confident nonsense. The two thresholds govern errors of very different size and do not belong on the
same number.

**The review action.** A row of buttons, one per type — Commercial invoice, House bill of lading,
Master bill of lading, Arrival notice. Pressing one completes the review and sends the document back
for field extraction against the corrected schema. The set of types is small and fixed, so a button
row is the entire interaction: no search, no dropdown, no free text.

**Out of scope for v1 — correcting page boundaries.** The classifier can group pages correctly and
label them wrongly, or group them wrongly and label the group plausibly. Only the first is fixed by
a button. v1 gets a single **"pages are wrong"** escalation that flags the file for manual handling.
Whether that earns a real page-range editor is a question for the Accuracy Test, not one to answer
in advance.

**A reclassify must not produce a second MeterEvent.** The meter counts documents, not runs.
`docs/pricing.md` already states that billing is never inferred from an extraction run, and a
reclassify is precisely the case where the two would get wired together by mistake: the document is
genuinely read a second time, so it looks like a second unit of work. It is not. It is the same
document, already counted — and the second read exists because Flow got the type wrong, which is
not something to invoice for.

**Not a commitment.** Thresholds, document types and field schemas are configuration rows, editable
through the admin screens without a deploy (build plan, phases 1 and 2). 0.90 is a starting value
chosen before a single real document has been classified. The Accuracy Test will move it.

**Cost.** None to run. A higher threshold sends more documents to a person, which spends reviewer
seconds rather than money — and spends them on the error that would otherwise cost the most to
unpick. **Reversal cost: Trivial** for the number, which is a config row. **Low** for the button row.
