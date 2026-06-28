"""CopilotException hierarchy (canonical) with proper inheritance and correlation tracking.

This module defines all custom exceptions used throughout the MIF Copilot application.
Exception hierarchy must exactly follow the frozen architecture (Backend Module Architecture §2.10).
Every exception carries correlation_id for distributed tracing and proper user messages.

Key design rules (frozen):
- Never catch-and-swallow exceptions; always log+propagate/recover
- Every exception carries correlation_id
- User messages never expose paths, rule logic, or secrets
- Internal details available for logging only

Reference: doc/02_BACKEND_MODULE_ARCHITECTURE.md §2.10 (Exception Architecture)
          Decisions.md §7.16 (Pattern: No Secrets in Logs)
"""

from typing import Any, Dict, Optional
from uuid import UUID


class CopilotException(Exception):
    """Base exception for all MIF Copilot custom exceptions.
    
    Purpose: Provide unified exception hierarchy with correlation tracking.
    Responsibility: Store correlation_id, user-safe messages, and internal details.
    Consumers: All error handlers, middleware, logging.
    Restrictions: Never expose secrets, internal paths, or rule logic in user_message.
    
    Design pattern: Immutable exception data; all details provided at creation.
    """
    
    def __init__(
        self,
        user_message: str,
        internal_details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[UUID] = None,
    ):
        """Initialize a CopilotException.
        
        Args:
            user_message: Safe message for user/client (never exposes internals).
            internal_details: Technical context for logging/debugging (not sent to user).
            correlation_id: Request correlation ID for distributed tracing.
        """
        self.user_message = user_message
        self.internal_details = internal_details or {}
        self.correlation_id = correlation_id
        super().__init__(user_message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dict for JSON serialization (client-safe).
        
        Returns only user_message and correlation_id; never includes internal_details.
        """
        return {
            "error": self.__class__.__name__,
            "message": self.user_message,
            "correlation_id": str(self.correlation_id) if self.correlation_id else None,
        }


ApplicationException = CopilotException


class AuthenticationException(CopilotException):
    """Authentication failed (invalid token, session expired, etc.).
    
    HTTP: 401 Unauthorized
    User message: Session expired. Please sign in again.
    Retry: Yes (re-authenticate)
    """
    pass


class SessionException(CopilotException):
    """Session-related error (restore failed, not found, etc.).
    
    HTTP: 404 Not Found or 500 Internal Server Error
    User message: We couldn't restore your session.
    Retry: No
    """
    pass


class KnowledgeException(CopilotException):
    """Base exception for knowledge layer errors.
    
    Subclasses: RegistryLoadException, RegistryValidationException, DerivationException,
                TemplateRenderException, ParserException, PriorityResolutionException
    """
    pass


class RegistryLoadException(KnowledgeException):
    """Registry loading failed (file not found, parse error, etc.).
    
    HTTP: 503 Service Unavailable
    User message: Service unavailable.
    Retry: No (fatal startup error)
    Scope: Registry loading is critical path; failure blocks application startup.
    """
    pass


class RegistryValidationException(KnowledgeException):
    """Registry validation failed (schema mismatch, missing required fields, etc.).
    
    HTTP: 503 Service Unavailable
    User message: Service unavailable.
    Retry: No (fatal startup error)
    Scope: Registry format error; requires code/data fix before restart.
    """
    pass


class DerivationException(KnowledgeException):
    """Value derivation failed (missing required input, computation error, etc.).
    
    HTTP: 500 Internal Server Error
    User message: We need more information to continue.
    Retry: No (user must provide missing input)
    Scope: Raised when deriver cannot compute value; never fabricates gap-flagged values.
    Reference: doc/02_BACKEND_MODULE_ARCHITECTURE.md §2.5 (CQ-A1 preservation)
    """
    pass


class TemplateRenderException(KnowledgeException):
    """Template rendering failed (variable substitution error, syntax error, etc.).
    
    HTTP: 500 Internal Server Error
    User message: Could not generate configuration.
    Retry: No (template/data error)
    """
    pass


class ParserException(KnowledgeException):
    """Repository file parsing failed (HCL parse error, invalid format, etc.).
    
    HTTP: 502 Bad Gateway
    User message: We couldn't read a repository file.
    Retry: Yes (transient GitHub read error possible)
    Scope: Raised by HCL/Terraform parsers when repository files are malformed.
    """
    pass


class PriorityResolutionException(KnowledgeException):
    """Priority resolution failed (conflicting sources, ambiguous precedence, etc.).
    
    HTTP: 500 Internal Server Error
    User message: Configuration conflict detected.
    Retry: No (business logic error)
    Scope: Raised when BR-A-10 (source-of-truth hierarchy) cannot determine precedence.
    """
    pass


class ValidationException(CopilotException):
    """Validation rule evaluation failed or returned failure.
    
    HTTP: 422 Unprocessable Entity
    User message: Rule-specific (from validation_messages.json, never exposes rule logic)
    Retry: Yes (user can retry after fixing input)
    Scope: Topic validation, job validation, schema validation.
    Note: User sees rule_id suppressed; internal_details available for logs.
    """
    pass


class RepositoryException(CopilotException):
    """Data persistence error (transaction failed, constraint violation, etc.).
    
    HTTP: 500 Internal Server Error
    User message: Something went wrong. Please try again.
    Retry: Yes (with optimistic locking backoff)
    Scope: Database/repository layer errors (not application logic).
    """
    pass


class DraftException(CopilotException):
    """Draft-specific error (frozen draft, optimistic lock failure, etc.).
    
    HTTP: 409 Conflict
    User message: Your draft is being processed. or This draft is frozen.
    Retry: Yes (with optimistic locking backoff)
    Scope: Draft mutation failures; often recoverable with retry.
    Reference: Decisions.md §7.14 (Optimistic Locking Pattern)
    """
    pass


class GitHubException(CopilotException):
    """GitHub API error (rate limit, network, server error, etc.).
    
    HTTP: 502 Bad Gateway or 429 Too Many Requests
    User message: GitHub is unavailable. Retrying... or Rate limited. Please wait.
    Retry: Yes (3× exponential backoff)
    Scope: All GitHub API calls (reads, writes, OAuth).
    Reference: Decisions.md §7.15 (Fail-Safe GitHub Operations)
    """
    pass


class TerraformException(CopilotException):
    """Terraform CLI error (validation failed, init error, format error, etc.).
    
    HTTP: 500 Internal Server Error
    User message: Validation could not run. or rule-specific validation failure message
    Retry: Yes (CLI may be transient)
    Scope: Terraform init/fmt/validate operations.
    """
    pass


class PRException(CopilotException):
    """Pull request creation error (branch exists, commit failed, PR creation failed, etc.).
    
    HTTP: 502 Bad Gateway
    User message: Could not create the pull request.
    Retry: Yes (idempotent retry with GitHub service)
    Scope: PR creation workflow errors; often recoverable.
    """
    pass


class ConflictException(CopilotException):
    """Git conflict detected during PR creation or rebase.
    
    HTTP: 409 Conflict
    User message: There's a conflict to resolve.
    Retry: Yes (manual or auto-resolution)
    Scope: Raised by ConflictService when merge conflict detected.
    Reference: doc/02_BACKEND_MODULE_ARCHITECTURE.md §2.4.6 (ConflictService)
    """
    pass
