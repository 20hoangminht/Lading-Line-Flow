# Decree 356 boundaries — the rules the code must never break

Vietnam's Decree 356/2025/NĐ-CP (effective 1 January 2026) makes "personal data processing services"
a conditional business line requiring a certificate from the Ministry of Public Security. Article
21(1) catches a business that **provides *and operates*** automated software to process personal data
**on behalf of** a controller.

Flow's entire architecture exists to sever the "operates" limb. Every rule below is downstream of
that. This is not a legal opinion — classification is a question for Vietnamese counsel — but the
factual position the code creates is what counsel will be asked to opine on. Weaken the facts and the
opinion changes.

## The five rules

**1. The customer owns and operates the environment.** They create the AWS account, hold root, set
MFA, pay the bill, control IAM, KMS and Secrets Manager, and invoke Bedrock with their own task role.
Lading Line supplies a signed software artifact and nothing else.

**2. Lading Line holds no credentials in a customer account at any point.** Not during build, not
during onboarding, not for support. No IAM user, no assumed role, no cross-account trust, no access
key, no recovery email, no break-glass path. If a support case genuinely cannot be solved without
access, it is an explicit, logged, time-boxed, customer-authorised exception — never a standing
arrangement, and never a default in code or documentation.

**3. Nothing containing personal data leaves the customer's account.** Shipper and consignee names,
addresses, contact names, signatures, commercial values tied to a named party — none of it, in any
channel. This includes log lines, stack traces, error payloads, crash reports, support bundles,
metrics labels and analytics events. When in doubt, do not send it.

**4. Three channels may send data to Lading Line, and only these three.**

| Channel | May contain | Must never contain |
|---|---|---|
| **Usage meter** | Document UUID, document type, timestamp, page count, status, SHA-256 of the source file, sequence number, signature | File names, any extracted value, any party name |
| **Aggregate accuracy export** | Per-document-type counts and percentages: field-level first-pass accuracy, exception rate, median seconds per exception, volume | Any individual field value, any document, any identifier that resolves to a shipment |
| **Redacted failure signature** | Document type, field name, model confidence, error category, character-class shape of the wrong and right values (e.g. `NN/NN/NNNN`) | The actual values, in any form, including partial |

A fourth channel — a **consented failure sample** — may carry a whole document, but only when a
customer administrator has enabled it and a reviewer has explicitly chosen that document. Off by
default. Per-document. Never bulk, never automatic.

**5. Flow never submits to a government system.** It produces export-ready declaration data for the
customer's own licensed staff to review and lodge. No direct ICS, ABF, CBP or any other filing
integration. Separately, CBP ruling HQ H350722 (16 January 2026) treats developing an OCR tool that
identifies what data will appear on a US customs entry as customs business requiring US territory —
so declaration-data preparation is Australia-only until a US entity with US-based staff exists.

## Tests that enforce this

- `tests/test_egress_allowlist.py` — every outbound HTTP destination is on a fixed allowlist.
- `tests/test_meter_payload.py` — the meter payload schema rejects any field not in the table above.
- `tests/test_log_redaction.py` — extracted field values never appear in log output at any level.
- `tests/test_no_standing_credentials.py` — the CloudFormation template contains no Lading Line
  principal, no cross-account trust and no external ID.

If you add an outbound call, add it to the allowlist test in the same commit or the build fails.
