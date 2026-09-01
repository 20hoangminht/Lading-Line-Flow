# CloudFormation

`tenant.yaml` — the full per-customer stack. `trial.yaml` — the cut-down fortnight footprint.

Both land in Phase 4. Two things are not optional when they are written:

**The customer launches these themselves**, from a quick-create link with parameters pre-filled.
Lading Line never holds credentials in the account. `tests/test_no_standing_credentials.py` enforces
it.

**Teardown must be engineered, not documented.** A stack delete fails outright if the S3 bucket still
holds objects, and a failed delete leaves RDS and the load balancer running at about A$300 a month.
So: an S3 lifecycle rule that expires objects, a custom resource that empties the bucket on delete,
`DeletionPolicy: Delete` and `DeleteAutomatedBackups: true` explicitly set on RDS overriding the
`Snapshot` default, and log groups declared inside the stack with a retention period.
