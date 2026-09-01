# RUNBOOK.md — what to do when something breaks

Written for someone who is not a coder. Each entry: the symptom as you would see it, the check, the
fix, and when to escalate.

*This file is populated as the system is built. An empty section means that part does not exist yet,
not that it never fails.*

## The application will not start

**Symptom.** `docker compose up` prints red text and stops.

**Check.** Look for the word `port is already allocated`. If you see it, something else is using port
8000 — usually a copy of the app you forgot to stop.

**Fix.** Close the other terminal window, or run `docker compose down` and try again.

**Escalate if.** The red text says anything else. Copy the last twenty lines and paste them into the
session.

## A document is stuck and never appears in the review queue

*To be written in Phase 2.*

## The customer says extraction accuracy has dropped

*To be written in Phase 5, when the aggregate accuracy export exists.*

## A customer's AWS bill looks wrong

*To be written in Phase 4.*
