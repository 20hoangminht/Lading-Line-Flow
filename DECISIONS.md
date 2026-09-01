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
