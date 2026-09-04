"""The row-level-security plumbing works, before anything depends on it.

No policy is applied to any table yet - tenancy arrives with authentication and roles. What these
tests prove is that the mechanism a policy will read is real: PostgreSQL accepts the session
variable, hands it back, and keeps it across statements.

Proving it now is cheap. Discovering later that the plumbing never worked, while also debugging a
policy, is not.
"""

import pytest

from config.rls import (
    TENANT_SESSION_VARIABLE,
    FlowModel,
    RowLevelSecurityManager,
    disable_rls_sql,
    enable_rls_sql,
    get_current_tenant,
    set_current_tenant,
    tenant_scope,
)
from documents.models import ExtractedField, ExtractionRun, LogicalDocument, Page, SourceFile
from validation.models import ValidationResult

pytestmark = pytest.mark.django_db

ALL_FLOW_MODELS = [
    SourceFile,
    Page,
    LogicalDocument,
    ExtractionRun,
    ExtractedField,
    ValidationResult,
]


def test_the_session_variable_round_trips_through_postgresql():
    set_current_tenant("acme-forwarding")
    assert get_current_tenant() == "acme-forwarding"


def test_an_unset_tenant_reads_as_nothing_rather_than_raising():
    """current_setting with missing_ok, so a query before the tenant is set fails a policy check
    rather than blowing up with a database error nobody can read."""
    set_current_tenant(None)
    assert get_current_tenant() is None


def test_the_setting_survives_more_than_one_statement():
    """Set for the session, not the transaction. Django opens and closes transactions underneath a
    request, and the tenant has to outlive them."""
    set_current_tenant("acme-forwarding")
    SourceFile.objects.count()
    SourceFile.objects.exists()
    assert get_current_tenant() == "acme-forwarding"


def test_a_scope_puts_the_connection_back_when_it_finishes():
    """Background jobs borrow a connection. They must hand it back as they found it."""
    set_current_tenant("acme-forwarding")
    with tenant_scope("other-customer"):
        assert get_current_tenant() == "other-customer"
    assert get_current_tenant() == "acme-forwarding"


def test_a_scope_puts_the_connection_back_even_when_the_job_fails():
    """A job that crashes must not leave the next job holding its tenant."""
    set_current_tenant("acme-forwarding")
    with pytest.raises(RuntimeError), tenant_scope("other-customer"):
        raise RuntimeError("extraction failed halfway through")
    assert get_current_tenant() == "acme-forwarding"


def test_every_flow_model_uses_the_shared_manager():
    """One manager class, so turning policies on is one change and not six."""
    for model in ALL_FLOW_MODELS:
        assert isinstance(model.objects, RowLevelSecurityManager), (
            f"{model.__name__} does not use RowLevelSecurityManager. Every Flow model inherits "
            f"from config.rls.FlowModel so tenant isolation has one place to live."
        )
        assert issubclass(model, FlowModel)


def test_the_policy_sql_forces_the_policy_on_the_table_owner():
    """FORCE is the load-bearing word.

    The application connects as the role that owns these tables, and a table owner bypasses its own
    policies unless the table is set to FORCE. Without it the isolation is decorative.
    """
    statements = enable_rls_sql("documents_sourcefile")
    joined = " ".join(statements)
    assert "ENABLE ROW LEVEL SECURITY" in joined
    assert "FORCE ROW LEVEL SECURITY" in joined
    assert TENANT_SESSION_VARIABLE in joined
    assert "WITH CHECK" in joined, "Without WITH CHECK a tenant could write a row it cannot read."


def test_the_policy_sql_can_be_undone():
    """A migration that cannot be rolled back is a migration nobody dares run."""
    joined = " ".join(disable_rls_sql("documents_sourcefile"))
    assert "DROP POLICY" in joined
    assert "DISABLE ROW LEVEL SECURITY" in joined


def test_no_policy_is_applied_to_any_table_yet():
    """Deliberate: tenancy arrives with authentication and roles.

    This test is the reminder. When policies go on, it fails, and whoever turns them on replaces it
    with a test that the isolation actually holds.
    """
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute("SELECT tablename FROM pg_policies WHERE schemaname = 'public'")
        assert cursor.fetchall() == []
