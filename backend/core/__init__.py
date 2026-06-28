"""Backend core primitives package (leaf within backend).

Purpose: Provide low-level primitives used across the backend such as
configuration, constants, exception types, structured logging helpers,
correlation id management and secret handling.

Responsibility: Export the stable core surface for other backend modules.

Consumers: backend.* modules (services, api, repositories, langgraph).

Restrictions: This package is a leaf - it MUST NOT import other backend
modules. Keep dependencies minimal and stable.

Reference documents: Architecture_Freeze.md, doc/01_REPOSITORY_MASTER_STRUCTURE.md,
doc/02_BACKEND_MODULE_ARCHITECTURE.md
"""

from .config import Settings, get_settings
from .constants import (
	CORRELATION_HEADER,
	BRANCH_PREFIX,
	BRANCH_NAME_PATTERN,
	DEFAULT_RATE_LIMIT,
)
from .exceptions import (
	CopilotException,
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
from .logging import configure_logging, get_logger, CorrelationIdFilter
from .correlation import (
	new_correlation_id,
	set_correlation_id,
	get_correlation_id,
)
from .security import SecretStrType, mask_secret
from .types import CorrelationId, UUIDStr, Timestamp

__all__ = [
	"Settings",
	"get_settings",
	"CORRELATION_HEADER",
	"BRANCH_PREFIX",
	"BRANCH_NAME_PATTERN",
	"DEFAULT_RATE_LIMIT",
	"CopilotException",
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
	"configure_logging",
	"get_logger",
	"CorrelationIdFilter",
	"new_correlation_id",
	"set_correlation_id",
	"get_correlation_id",
	"SecretStrType",
	"mask_secret",
	"CorrelationId",
	"UUIDStr",
	"Timestamp",
]
