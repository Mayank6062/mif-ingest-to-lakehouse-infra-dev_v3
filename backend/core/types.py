"""Internal type aliases for backend infrastructure layer.

Purpose: Provide backend-specific type aliases for common infrastructure types
used throughout the backend layer. These are infrastructure conveniences, NOT
domain/business types (which belong in shared/types.py).

Responsibility: Define internal type names used in backend modules (api,
services, repositories, langgraph) for correlation IDs, UUIDs, timestamps, and
other infrastructure identifiers.

Consumers: All backend modules (api, services, repositories, langgraph, middleware).

Restrictions: Do NOT add business/domain types here (e.g., DraftState, GlueJobConfig).
Domain types belong in shared/types.py. Do NOT import from services, repositories,
models, database, knowledge, or langgraph. Only stdlib and typing imports allowed.

Reference documents: Architecture_Freeze.md §3 (Frozen Dependencies),
doc/02_BACKEND_MODULE_ARCHITECTURE.md §2.12 (DTO Mapping Chain),
Decisions.md §4 (Dependency Rules - CORE has zero dependencies)

Design pattern: Simple type aliases using Python's typing module. Provides semantic
clarity for function signatures and code readability. No runtime overhead.
"""

from typing import Any, Dict, TypeVar, Union
from uuid import UUID as PythonUUID
from datetime import datetime

# ==============================================================================
# IDENTIFIER TYPE ALIASES
# ==============================================================================
# Purpose: Semantic type names for common infrastructure identifiers.
# Owner: Backend Core (infrastructure layer)
# Consumer: Middleware, services, repositories, logging
# Reference: doc/02_BACKEND_MODULE_ARCHITECTURE.md §2.11 (Identifiers)

CorrelationId = str
"""Correlation ID as string (UUID format).

Used for distributed tracing across requests and async tasks.
Provides semantic clarity for correlation_id function parameters and returns.

Example:
    correlation_id: CorrelationId = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
"""

UUIDStr = str
"""UUID as string (standard string representation of UUID).

Used for ID fields that are serialized as strings in JSON/HTTP.
Provides semantic clarity without runtime type checking.

Example:
    session_id: UUIDStr = "12345678-1234-5678-1234-567812345678"
    draft_id: UUIDStr = str(uuid.uuid4())
"""

Timestamp = datetime
"""Timestamp as datetime object (UTC timezone-aware).

Used for all temporal tracking in the application.
Always UTC; assume timezone-aware datetime.

Example:
    created_at: Timestamp = datetime.utcnow()
    updated_at: Timestamp = datetime.now(timezone.utc)
"""

# ==============================================================================
# STRUCTURED DATA TYPE ALIASES
# ==============================================================================
# Purpose: Semantic type names for common structured data patterns.
# Owner: Backend Core (infrastructure layer)
# Consumer: Services, repositories, API handlers
# Reference: Python typing module documentation

JSONValue = Union[str, int, float, bool, None, Dict[str, Any], list]
"""JSON-serializable value.

Represents any value that can be serialized to JSON.
Used in generic functions that handle JSON data.

Example:
    value: JSONValue = {"key": "value", "count": 42}
    settings: Dict[str, JSONValue] = {"timeout": 30, "retry": True}
"""

JSONDict = Dict[str, Any]
"""Shorthand for JSON-compatible dictionary.

Common pattern for structured data represented as dictionaries.
Preferred over bare Dict[str, Any] in function signatures for clarity.

Example:
    def serialize_config(config: JSONDict) -> str:
        return json.dumps(config)
"""

# ==============================================================================
# GENERIC TYPE VARIABLES
# ==============================================================================
# Purpose: Type variables for generic functions and classes.
# Owner: Backend Core (infrastructure layer)
# Consumer: Services, repositories, utilities
# Reference: Python typing.TypeVar documentation

T = TypeVar('T')
"""Generic type variable for generic functions and classes."""

U = TypeVar('U')
"""Second generic type variable for functions with multiple type parameters."""

V = TypeVar('V')
"""Third generic type variable for functions with multiple type parameters."""

# ==============================================================================
# NOTES ON DOMAIN TYPES
# ==============================================================================
# Domain/business types that should NOT be in this file:
#
# ✗ ValidationResult — belongs in shared/types.py
# ✗ GlueJobConfig — belongs in shared/types.py
# ✗ DraftState — belongs in shared/types.py
# ✗ GitHubToken — belongs in shared/types.py
# ✗ PRMetadata — belongs in shared/types.py
# ✗ RepositoryFacts — belongs in shared/types.py
#
# This file provides infrastructure conveniences only.
# Domain types are centralized in shared/types.py to maintain
# cross-layer consistency and avoid duplication.
