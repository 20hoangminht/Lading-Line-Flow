# Lading Line — Flow

Automated extraction, validation and human-review routing for freight and customs documents,
built for Australian freight forwarders and licensed customs brokers with 5–75 staff handling
Vietnam and South-East Asia origin cargo.

**This repository is the single workspace for building Flow.** Tech stack and pricing are locked —
see `docs/tech-stack.md` and `docs/pricing.md`. Strategy, market research and corporate matters live
in the Claude project, not here.

## The product in one paragraph

The customer's documents arrive. Flow reads them, extracts the fields that matter with a confidence
score on every field, checks those values against the customer's own master data, routes anything
below threshold to a human review queue rather than guessing, pushes clean data into the TMS the
customer already runs, and produces export-ready declaration data for the customer's own licensed
staff to lodge. **Flow never files anything with a government.**

## The one architectural fact that governs everything

Flow runs **inside the customer's own AWS account**, which the customer creates, owns, pays for and
controls. Lading Line writes and licenses the software and never holds credentials in that account
at any point in its lifecycle. Read `docs/decree-356-boundaries.md` before writing any code that
moves data. It is not a style guide; it is the reason the company can operate.

## Layout

| Path | What lives there |
|---|---|
| `app/` | The Django application — the whole product |
| `infra/cloudformation/` | The per-customer stack, and the cut-down trial stack |
| `evals/` | Golden sets and the evaluation harness. Synthetic documents only |
| `site/` | The public landing page, deployed to Cloudflare Pages |
| `docs/` | Locked product scope, stack, pricing, build plan and boundaries |
| `tests/` | Tests. Anything touching money or document counts must have them |

## Getting started

See `SETUP.md`. See `CLAUDE.md` before making any change.
