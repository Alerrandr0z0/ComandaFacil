from contextvars import ContextVar

# Stores the current tenant_id for the duration of each HTTP request
tenant_context_var: ContextVar[str] = ContextVar("tenant_id", default="")


def get_current_tenant_id() -> str:
    """Returns the current tenant_id from context."""
    return tenant_context_var.get()
