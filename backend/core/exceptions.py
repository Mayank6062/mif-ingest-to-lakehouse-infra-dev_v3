"""Backend core exceptions package (re-exports from shared).

Purpose: Provide a backend-specific entry point for importing exceptions
from the canonical shared exception hierarchy. This module maintains the
single source of truth for all exception definitions.

Responsibility: Re-export all exception classes from shared/exceptions.py
without modification or extension. The shared module is the sole authority.

Consumers: backend.services, backend.api, backend.repositories, middleware,
and error handlers throughout the backend layer.

Restrictions: Do NOT create new exception classes here. Do NOT modify
exception behavior. Do NOT add backend-specific subclasses. All exception
definitions live in shared/ only.

Reference documents: Architecture_Freeze.md §3 (Frozen Dependencies),
doc/02_BACKEND_MODULE_ARCHITECTURE.md §2.10 (Exception Architecture),
Decisions.md §4 (Dependency Rules)

Design pattern: This is a pass-through re-export module (no new types).
All exception classes are defined in shared/exceptions.py and imported
here for backend convenience.
"""

from shared.exceptions import (
    CopilotException,
    ApplicationException,
    AuthenticationException,
    SessionException,
    KnowledgeException,
    RegistryLoadException,
    RegistryValidationException,
    DerivationException,
    TemplateRenderException,
    ParserException,
    PriorityResolutionException,
    ValidationException,
    RepositoryException,
    DraftException,
    GitHubException,
    TerraformException,
    PRException,
    ConflictException,
)

__all__ = [
    "CopilotException",
    "ApplicationException",
    "AuthenticationException",
    "SessionException",
    "KnowledgeException",
    "RegistryLoadException",
    "RegistryValidationException",
    "DerivationException",
    "TemplateRenderException",
    "ParserException",
    "PriorityResolutionException",
    "ValidationException",
    "RepositoryException",
    "DraftException",
    "GitHubException",
    "TerraformException",
    "PRException",
    "ConflictException",
]
