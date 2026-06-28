"""Correlation ID propagation and async context management.

Purpose: Manage correlation_id, request_id, trace_id lifecycle with async-safe
context variable storage. Enables distributed tracing across async tasks and threads.

Responsibility: Generate unique correlation/request/trace IDs, store them in
async context variables, retrieve them for logging/tracing, and provide utilities
for context propagation across async boundaries.

Consumers: Middleware (assignment), logging (retrieval), services (propagation),
LangGraph nodes (async context preservation).

Restrictions: No business logic; no I/O; no database; no GitHub/Terraform;
async-safe via contextvars; thread-safe for concurrent requests.

Reference documents: doc/02_BACKEND_MODULE_ARCHITECTURE.md §2.11 (Identifiers),
doc/02_BACKEND_MODULE_ARCHITECTURE.md §2.2.2 (Middleware Stack),
Architecture_Freeze.md §3 (Frozen Dependencies)

Design pattern: Uses Python contextvars for async-safe context storage.
Each request/task gets its own correlation_id (UUID), request_id, and trace_id
that are propagated across async boundaries and available to logging filters.
"""

import uuid
from contextvars import ContextVar
from typing import Optional
from uuid import UUID

from .constants import (
    CORRELATION_CONTEXT_VAR,
    REQUEST_ID_CONTEXT_VAR,
    TRACE_ID_CONTEXT_VAR,
)


# Context variables for async-safe storage
# These are thread-local and task-local in async contexts
_correlation_id_var: ContextVar[Optional[str]] = ContextVar(
    CORRELATION_CONTEXT_VAR,
    default=None,
)
_request_id_var: ContextVar[Optional[str]] = ContextVar(
    REQUEST_ID_CONTEXT_VAR,
    default=None,
)
_trace_id_var: ContextVar[Optional[str]] = ContextVar(
    TRACE_ID_CONTEXT_VAR,
    default=None,
)


def new_correlation_id() -> str:
    """Generate a new correlation ID as UUID string.
    
    Purpose: Create a unique identifier for a request/workflow that persists
    across all async operations and log entries for that request.
    
    Returns:
        UUID as string (hex format, no hyphens expected by default but standard uuid4().hex).
        
    Design: Uses uuid.uuid4() for high entropy and uniqueness across distributed systems.
    
    Example:
        correlation_id = new_correlation_id()  # e.g., "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
    """
    return str(uuid.uuid4())


def new_request_id() -> str:
    """Generate a new request ID as UUID string.
    
    Purpose: Create a unique identifier for individual HTTP requests or tasks.
    
    Returns:
        UUID as string.
    """
    return str(uuid.uuid4())


def new_trace_id() -> str:
    """Generate a new trace ID as UUID string.
    
    Purpose: Create a unique identifier for distributed tracing spans.
    
    Returns:
        UUID as string.
    """
    return str(uuid.uuid4())


def set_correlation_id(correlation_id: str) -> None:
    """Store correlation_id in async context.
    
    Purpose: Assign a correlation_id for the current request/workflow.
    Typically called by correlation_middleware early in request processing.
    
    Args:
        correlation_id: UUID as string. If None or empty, clears the context var.
    
    Behavior:
        - Sets the context variable for this request/task
        - Propagates to all async child tasks spawned in this context
        - Thread-safe via contextvars (each thread/task has its own value)
    
    Example (in middleware):
        correlation_id = request.headers.get("X-Correlation-ID") or new_correlation_id()
        set_correlation_id(correlation_id)
    """
    if correlation_id:
        _correlation_id_var.set(correlation_id)
    else:
        _correlation_id_var.set(None)


def get_correlation_id() -> Optional[str]:
    """Retrieve correlation_id from async context.
    
    Purpose: Get the current correlation_id for logging, tracing, or propagation
    to downstream systems.
    
    Returns:
        UUID as string, or None if not set.
    
    Behavior:
        - Thread-safe and async-safe via contextvars
        - Returns the value set in this context (request/task)
        - Safe to call from any thread or async task
    
    Example (in logging filter):
        correlation_id = get_correlation_id()
        if correlation_id:
            logger.extra["correlation_id"] = correlation_id
    """
    return _correlation_id_var.get()


def set_request_id(request_id: str) -> None:
    """Store request_id in async context.
    
    Purpose: Assign a request_id for the current HTTP request.
    Typically called by correlation_middleware.
    
    Args:
        request_id: UUID as string.
    """
    if request_id:
        _request_id_var.set(request_id)
    else:
        _request_id_var.set(None)


def get_request_id() -> Optional[str]:
    """Retrieve request_id from async context.
    
    Returns:
        UUID as string, or None if not set.
    """
    return _request_id_var.get()


def set_trace_id(trace_id: str) -> None:
    """Store trace_id in async context for distributed tracing.
    
    Purpose: Assign a trace_id for OpenTelemetry or similar tracing systems.
    Typically called by correlation_middleware.
    
    Args:
        trace_id: UUID as string.
    """
    if trace_id:
        _trace_id_var.set(trace_id)
    else:
        _trace_id_var.set(None)


def get_trace_id() -> Optional[str]:
    """Retrieve trace_id from async context.
    
    Returns:
        UUID as string, or None if not set.
    """
    return _trace_id_var.get()


def clear_correlation_context() -> None:
    """Clear all correlation context variables.
    
    Purpose: Reset context at end of request or for cleanup.
    Typically called in error handlers or finally blocks to prevent
    context variable leakage across requests.
    
    Behavior:
        - Sets all context variables to None
        - Safe to call multiple times
        - Thread-safe via contextvars
    
    Example (in middleware error handler):
        try:
            process_request()
        finally:
            clear_correlation_context()
    """
    _correlation_id_var.set(None)
    _request_id_var.set(None)
    _trace_id_var.set(None)


def get_correlation_context() -> dict[str, Optional[str]]:
    """Get all correlation context variables as a dict.
    
    Purpose: Convenient access to all correlation IDs for propagation
    to external systems or logging.
    
    Returns:
        Dictionary with keys: correlation_id, request_id, trace_id.
        Values are strings (UUID) or None if not set.
    
    Example:
        context = get_correlation_context()
        # context = {"correlation_id": "abc123", "request_id": "def456", "trace_id": "ghi789"}
        headers = {k.upper().replace("_", "-"): v for k, v in context.items() if v}
        # headers = {"CORRELATION-ID": "abc123", ...}
    """
    return {
        "correlation_id": get_correlation_id(),
        "request_id": get_request_id(),
        "trace_id": get_trace_id(),
    }


def set_correlation_context(
    correlation_id: Optional[str] = None,
    request_id: Optional[str] = None,
    trace_id: Optional[str] = None,
) -> None:
    """Set all correlation context variables at once.
    
    Purpose: Bulk set context variables (useful for middleware or context restoration).
    
    Args:
        correlation_id: Correlation ID (if None, clears).
        request_id: Request ID (if None, clears).
        trace_id: Trace ID (if None, clears).
    
    Example (in middleware):
        set_correlation_context(
            correlation_id=request.headers.get("X-Correlation-ID") or new_correlation_id(),
            request_id=request.headers.get("X-Request-ID") or new_request_id(),
            trace_id=request.headers.get("X-Trace-ID") or new_trace_id(),
        )
    """
    set_correlation_id(correlation_id)
    set_request_id(request_id)
    set_trace_id(trace_id)
