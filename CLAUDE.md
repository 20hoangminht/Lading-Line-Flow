# Working instructions for Claude Code and Codex

Read this file before doing anything in this repository. `AGENTS.md` is a copy of it for Codex.

## Who you are building for

The owner is **not a coder**. He has strong business and management judgement and uses AI tools
daily, but he does not read code, cannot debug a stack trace, and will not know what a missing
environment variable is. He is in Hanoi (GMT+7).

This constrains how you work, not what you build.

- **Every instruction must be copy-pasteable.** Never write "configure your environment" — write the
  exact file, the exact line, the exact value.
- **Never leave the repository in a broken state at the end of a session.** Finish it or revert it,
  and say which.
- **Ask before spending money.** Any paid account, service or upgrade — surface the cost first and
  wait.
- **When something breaks, give a decision, not a diagnosis.** "Extraction is failing on scanned
  PDFs; I can add an OCR pass which costs about A$0.004 a page — yes or no?"
- Explain trade-offs in cost, risk and time. Not in engineering terms.
- Assume a hired Vietnamese engineer takes over within a year. Plain code, English comments, no
  clever tricks.
- **Every phase ends with an acceptance test the owner can run himself, written in plain language,
  without asking a question.** This is the definition of done.

## Hard boundaries — never violate these

1. **No customer document, extracted field value, or personal data may ever leave the customer's AWS
   account.** Not in logs, not in error messages, not in support bundles, not in telemetry. See
   `docs/decree-356-boundaries.md`.
2. **Lading Line holds no credentials in a customer account, ever.** No IAM user, no role, no
   cross-account trust, no API key, no recovery path. The customer launches the stack themselves.
3. **Flow never submits anything to a government system.** It prepares data. The licensed broker
   files.
4. **Never commit secrets, customer documents, or real personal data.** Synthetic and redacted only.
5. **Never write to `main` directly.** Task branch, draft pull request, owner review, merge.
6. **Anything that touches money or document counts has tests.** Not optional.

## Locked decisions — do not relitigate without an ADR

| Area | Locked choice |
|---|---|
| Language / framework | Python 3.12, Django 5.x, Django Ninja. **Not FastAPI** (D-005) |
| UI | Server-rendered templates, HTMX, minimal Alpine.js, self-hosted pdf.js. No SPA (D-007) |
| Database | PostgreSQL 17, one instance, row-level security for isolation (D-006) |
| Job queue | Procrastinate on Postgres. **No Redis, no Celery, no n8n** (D-004, D-006) |
| Model | Claude Haiku 4.5 on Amazon Bedrock, AU geographic inference profile (D-002) |
| PDF | pypdfium2 / pdfplumber. **PyMuPDF avoided on licensing grounds** (D-013) |
| Compute | ECS on Fargate, ARM/Graviton |
| Network | Public subnets, public task IPs, security group closed except from the load balancer. **No NAT gateway** — it costs A$120/month and buys nothing here |
| Delivery | Customer-launched CloudFormation quick-create. **Not AWS account assignment** |

If you believe one of these is wrong, say so in writing with reasoning and add an ADR to
`DECISIONS.md`. Do not just build something different.

## Definition of done for any phase

1. It runs.
2. The owner has personally run it, following written instructions, without asking a question.
3. There is a written way to tell whether it is working correctly.
4. `SETUP.md` and `RUNBOOK.md` are updated.
5. Actual monthly cost is stated against the budget.

## At the end of every session, state plainly

What now works. What does not yet work. What it costs per month so far. The exact next step.
