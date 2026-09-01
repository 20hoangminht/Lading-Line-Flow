"""Every host Flow may talk to is listed in settings.EGRESS_ALLOWLIST.

If you add an outbound call, add its host here in the same commit. This test exists because a
single unreviewed outbound call is how customer data leaves an environment it should never leave.
See docs/decree-356-boundaries.md.
"""

EXPECTED_HOSTS = {
    "bedrock-runtime.ap-southeast-2.amazonaws.com",
    "s3.ap-southeast-2.amazonaws.com",
    "secretsmanager.ap-southeast-2.amazonaws.com",
    "kms.ap-southeast-2.amazonaws.com",
    "logs.ap-southeast-2.amazonaws.com",
    "meter.ladingline.com",
}


def test_allowlist_matches_this_file():
    from django.conf import settings

    assert set(settings.EGRESS_ALLOWLIST) == EXPECTED_HOSTS, (
        "settings.EGRESS_ALLOWLIST changed without updating this test. "
        "Adding an outbound destination is a decision, not a detail — say why in the pull request."
    )
