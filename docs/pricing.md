# Pricing — locked, v3 (1 September 2026)

The code must implement this and nothing else. Changes need an ADR.

## The card

- **Platform fee: A$4,250 per month**, including **750 documents**.
- **Metered above 750**, marginal rates (not retroactive):

| Band | Rate per document |
|---|---:|
| 751 – 2,500 | A$2.20 |
| 2,501 – 6,000 | A$2.00 |
| 6,001 and above | A$1.85 |

- **Setup and implementation: A$4,900** one-off.
- **Spike rule, the only one:** a month more than 40% above the customer's trailing three-month
  average is billed at that average instead of actual.
- **Billing: quarterly in advance**, metered usage in arrears the following quarter.
- **Minimum: 1,000 documents a month.** Below that the platform fee dominates and the customer does
  not save enough. Disqualify rather than discount.

## What this means for the code

- The **usage meter is the invoice**. Append-only, one row per document, with an idempotency key
  derived from the source-file hash so the same file uploaded twice is never billed twice.
- Billing is **never inferred from an extraction run**. A retry is not a document. A re-extraction is
  not a document. Only an explicit, deduplicated meter event is billable.
- The trailing three-month average must be computed from meter data, not estimated.
- The customer must be able to see the full meter inside Flow, with a page showing exactly what was
  sent to Lading Line and when.

## Reference prices at volume

| Documents/month | Monthly price | Effective A$/doc |
|---:|---:|---:|
| 1,000 | A$4,800 | 4.80 |
| 1,200 | A$5,240 | 4.37 |
| 1,500 | A$5,900 | 3.93 |
| 2,200 | A$7,440 | 3.38 |
| 4,000 | A$11,100 | 2.77 |
| 6,000 | A$15,100 | 2.52 |
| 12,000 | A$26,200 | 2.18 |

Use these as fixtures in the billing tests.
