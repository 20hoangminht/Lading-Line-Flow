"""Row-level security plumbing.

Flow isolates tenants in the database, not in application code (D-006). The reason is simple: a
`WHERE tenant_id = ...` clause that someone forgets is a data leak, and someone always forgets one.
PostgreSQL enforcing a policy on the table cannot be forgotten.

This module is the wiring. It does three things:

1. Puts the current tenant into a PostgreSQL session variable (`flow.tenant_id`), which is what a
   row-level-security policy reads.
2. Gives every Flow model one shared base class and one shared manager, so when policies are turned
   on there is a single place to change.
3. Generates the SQL that turns a policy on for a table.

**No policy is applied to any table yet.** Tenancy itself — who a tenant is, how a request is
attached to one — lands with authentication and roles. Until then this module is inert: the helpers
work, the manager behaves like a normal Django manager, and `enable_rls_sql()` is written but not
called. That is deliberate. Wiring it now means the later change is a migration, not a rewrite of
every query in the application.
"""

from contextlib import contextmanager

from django.db import connections, models

# The PostgreSQL session variable a policy reads. Namespaced with "flow." because PostgreSQL
# requires a dotted name for a custom setting.
TENANT_SESSION_VARIABLE = "flow.tenant_id"


def set_current_tenant(tenant_id, using="default"):
    """Tell the database which tenant the current connection is acting for.

    Passing None clears it. The value is set for the whole session (is_local=False) so it survives
    the individual transactions Django opens and closes underneath a request.
    """
    value = "" if tenant_id is None else str(tenant_id)
    with connections[using].cursor() as cursor:
        cursor.execute("SELECT set_config(%s, %s, false)", [TENANT_SESSION_VARIABLE, value])


def get_current_tenant(using="default"):
    """Read back the tenant the current connection is acting for, or None if unset."""
    with connections[using].cursor() as cursor:
        cursor.execute("SELECT current_setting(%s, true)", [TENANT_SESSION_VARIABLE])
        value = cursor.fetchone()[0]
    return value or None


@contextmanager
def tenant_scope(tenant_id, using="default"):
    """Run a block of code as one tenant, then put the connection back as it was.

    Used by background jobs, which have no request to take a tenant from.
    """
    previous = get_current_tenant(using=using)
    set_current_tenant(tenant_id, using=using)
    try:
        yield
    finally:
        set_current_tenant(previous, using=using)


def enable_rls_sql(table_name, tenant_column="tenant_id"):
    """Return the SQL that puts a table behind a row-level-security policy.

    Not called yet — it is here so the migration that eventually turns policies on is a short one
    and so the exact statements can be reviewed now rather than invented under pressure later.

    FORCE is the important word. Without it the table owner, which is the role the application
    connects as, bypasses its own policy and the isolation is decorative.
    """
    policy = f"{table_name}_tenant_isolation"
    # The row this tenant may see, and equally the row it may write. Both halves are needed:
    # USING alone would let a tenant insert a row belonging to someone else and then not see it.
    matches_tenant = f"{tenant_column}::text = current_setting('{TENANT_SESSION_VARIABLE}', true)"
    create_policy = (
        f"CREATE POLICY {policy} ON {table_name} "
        f"USING ({matches_tenant}) WITH CHECK ({matches_tenant});"
    )
    return [
        f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY;",
        f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY;",
        create_policy,
    ]


def disable_rls_sql(table_name):
    """The reverse of enable_rls_sql, so the migration can be rolled back."""
    policy = f"{table_name}_tenant_isolation"
    return [
        f"DROP POLICY IF EXISTS {policy} ON {table_name};",
        f"ALTER TABLE {table_name} NO FORCE ROW LEVEL SECURITY;",
        f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY;",
    ]


class RowLevelSecurityManager(models.Manager):
    """The manager every Flow model uses.

    Today it is an ordinary manager. It exists so that there is exactly one manager class to change
    when policies go on, and so no model quietly grows its own.

    It deliberately does not filter by tenant in Python. Filtering in Python is the thing row-level
    security replaces; doing both would hide a broken policy behind a working query.
    """

    def current_tenant(self):
        """The tenant this manager's queries will be scoped to once policies are applied."""
        return get_current_tenant(using=self.db)


class FlowModel(models.Model):
    """Abstract base for every Flow model. Carries the shared manager and creation timestamp."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = RowLevelSecurityManager()

    class Meta:
        abstract = True
