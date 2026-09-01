# Product scope — locked

## Flow does

1. **Reads** commercial invoices, packing lists, house and master bills of lading, arrival notices,
   delivery orders, and the data set behind an import declaration.
2. **Extracts** shipper, consignee, container number, weight, value, port, dates and the rest of the
   per-type schema, **with a confidence score on every field**.
3. **Validates** against the customer's own master data: known parties, container check digits, port
   and country codes, HS code format, date sanity, totals reconciliation.
4. **Routes** anything below threshold to a human review queue rather than guessing.
5. **Pushes clean data to the TMS the customer already runs** — API where one exists, otherwise
   structured file drop or SFTP.
6. **Produces export-ready declaration data** for the customer's licensed staff to review and lodge.

## Flow does not, at any tier

- Lodge or submit anything to a government system.
- Give customs advice, tariff classification opinions, or trade-compliance advice.
- Hold customer documents or extracted personal fields in Lading Line infrastructure.

## Phase 1 document types — build three, not six

Commercial invoice, bill of lading, arrival notice. Add packing list, delivery order and declaration
data in Phase 6. Six types on day one is scope creep.

## Open decision

**The Australian declaration output format is not settled.** Australian import declarations go
through the Integrated Cargo System, and brokers lodge directly or via their declaration software.
Flow's output should be a structured payload into that software, or a review screen the broker works
from. Settle this with the first prospect who will describe their workflow — it is roughly a week of
Phase 3.

## Frozen

ISF data preparation. It is a United States requirement, it does not belong in Australian collateral,
and CBP ruling HQ H350722 makes offshore development of entry-data tooling a regulatory problem until
a US entity exists.
