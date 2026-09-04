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
