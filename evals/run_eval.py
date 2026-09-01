"""Evaluation harness.

Runs every golden document through the current extraction pipeline and reports per-document-type,
per-field accuracy. Run it on every prompt change and every model change. Without it, swapping a
model to save money silently degrades accuracy for every customer at once.

Golden sets contain SYNTHETIC OR REDACTED documents only. Never a real customer document.
"""

import sys
from pathlib import Path

GOLDEN = Path(__file__).parent / "golden"


def main() -> int:
    if not any(GOLDEN.rglob("*.json")):
        print("No golden sets yet. Build them in Phase 1 — see docs/build-plan.md.")
        return 0
    print("Evaluation harness lands in Phase 1.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
