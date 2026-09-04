"""The customer stack must grant Lading Line nothing.

No IAM user, no assumed role, no cross-account trust, no external id, no recovery path. This is the
single most load-bearing fact in the Decree 356 position and it is easy to break by accident when
adding a convenience.
"""

from pathlib import Path

TEMPLATES = list(
    (Path(__file__).resolve().parent.parent / "infra" / "cloudformation").glob("*.yaml")
)

FORBIDDEN = [
    "sts:AssumeRole",
    "ExternalId",
    "arn:aws:iam::LADINGLINE",
    "ladingline-support",
]


def test_templates_grant_lading_line_nothing():
    for path in TEMPLATES:
        body = path.read_text()
        for token in FORBIDDEN:
            assert token not in body, (
                f"{path.name} contains {token!r}. Lading Line must hold no principal in a "
                f"customer account. See docs/decree-356-boundaries.md rule 2."
            )
