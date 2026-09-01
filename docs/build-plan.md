# Build plan

Elapsed weeks from 1 September 2026. The bottleneck is not code volume — it is verification, because
the owner cannot debug. Every phase ends in something he can run and judge himself.

| Phase | Content | Weeks | Cumulative |
|---|---|---|---|
| **0 — Foundations** | Repo, Django skeleton, full data model and migrations, local docker-compose, auth and roles, CI | 1.5 | 1.5 |
| **1 — Extraction core** | PDF ingest, document-type classification, per-type field schemas as config rows, Bedrock adapter with structured output and per-field confidence, threshold routing, **evaluation harness and first golden sets** | 3 | 4.5 |
| **2 — Review queue** | Keyboard-first review UI, pdf.js viewer, accept/correct/escalate, ReviewEvent capture, seconds-per-exception instrumentation, admin screens | 2 | 6.5 |
| **3 — Validation and output** | Validation against customer master data, structured export, one TMS adapter, export-ready declaration data | 2.5 | 9 |
| **4 — Cloud delivery** | CloudFormation template, signed image build and cross-account ECR, quick-create link generation, preflight page, trial mode, engineered teardown, update change sets | 3 | 12 |
| **5 — Commercial plumbing** | Signed usage meter and customer-visible meter page, aggregate accuracy export, consented-sample button, support package generator, monthly dashboard | 2 | 14 |
| **6 — Hardening** | Backup and restore tested, dependency scanning, security-review pack, SETUP and RUNBOOK, remaining document types, accuracy tuning | 2 | 16 |

**Full v1: 12–16 weeks, median 14 — mid-December 2026.**

## You do not need all of it to sell

| Milestone | Needs | Ready |
|---|---|---|
| **Landing page live** | `site/` deployed to Cloudflare Pages | ~week 2, mid-September |
| **Stage-zero demo** — synthetic documents extracted live on a screen-share | Phases 0–1 plus a rough review screen | ~week 5, early October |
| **Accuracy Test** — real documents, customer's own AWS account | Phases 0–2 plus the trial-mode subset of Phase 4 | ~week 9, early November |
| **First customer live** | Full v1, 30 days after signature | Mid-December onward |

Skip for the Accuracy Test: TMS integration, metering (invoice manually for the first two customers),
OIDC, the update mechanism, the support package.

## Ranked build risks

1. **Verification bottleneck.** Plain-language acceptance tests at every phase, or fourteen weeks
   becomes thirty.
2. **CloudFormation feedback loops are 20–30 minutes.** Phase 4 will feel disproportionately painful.
   Use `cfn-lint` and change sets, test in a disposable scratch account, automate teardown from day
   one.
3. **Extraction accuracy is the product.** Build the eval harness in Phase 1, before the UI.
4. **Six document types is scope creep.** Ship three.
5. **The declaration output format is undecided.** A week of Phase 3, needs a prospect conversation.
