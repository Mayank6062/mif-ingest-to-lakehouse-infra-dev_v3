"""Pydantic Settings loader.

Purpose: Provide a single `Settings` object loaded from environment variables
using Pydantic's `BaseSettings`. This module intentionally avoids making
business-rule decisions or resolving Clarification Questions (CQ). Any
configuration item that depends on an unresolved CQ is left optional and
must be provided by the environment or higher-level provisioning.

Responsibility: Read-only application configuration surface for the
backend. Consumers must call `get_settings()` to obtain the application
settings singleton.

Consumers: backend.main, dependency injection, CLI scripts, and tests.

Restrictions: This module is part of backend core and must not import
other backend modules. It may import external stable libraries (pydantic).

Reference documents: Architecture_Freeze.md, doc/01_REPOSITORY_MASTER_STRUCTURE.md
"""

from functools import lru_cache
from typing import Optional

try:
	from pydantic import BaseSettings, SecretStr, Field, validator
except Exception as e:  # pragma: no cover - clear error if dependency missing
	raise RuntimeError(
		"pydantic is required for backend.core.config - install pydantic"
	) from e


class Settings(BaseSettings):
	"""Application settings loaded from environment variables.

	Fields that are unresolved by frozen architecture (CQ items) are
	declared optional and default to ``None`` so callers can detect missing
	values and escalate rather than rely on implicit defaults.
	"""

	# Mandatory gating value per CPRS: environment must be explicitly set
	environment: str = Field(..., description="Operational environment ('dev'|'prod')")

	# OAuth / GitHub
	github_client_id: Optional[str] = Field(None, description="OAuth client id")
	github_client_secret: Optional[SecretStr] = Field(
		None, description="OAuth client secret (SecretStr)"
	)
	# Target repository (CQ-15 unresolved) — must be provided by deploy
	github_target_repository: Optional[str] = Field(
		None, description="Target repository full name (owner/repo)"
	)

	# Datastore endpoints
	database_url: Optional[str] = Field(None, description="Postgres DSN")
	redis_url: Optional[str] = Field(None, description="Redis connection URL")

	# External tools
	terraform_cli_path: Optional[str] = Field(None, description="Path to terraform CLI")

	# Observability / operational
	log_level: str = Field("INFO", description="Logging level")
	rate_limit_per_min: int = Field(100, description="Per-user rate limit (requests/min)")

	class Config:
		env_prefix = "MIF_"
		case_sensitive = False

	@validator("environment")
	def validate_environment(cls, v: str) -> str:
		if v not in ("dev", "prod"):
			raise ValueError("environment must be 'dev' or 'prod'")
		return v


@lru_cache(maxsize=1)
def get_settings() -> Settings:
	"""Return cached Settings instance loaded from environment.

	Callers should call this once at application startup and pass the
	resulting object to DI containers or startup hooks.
	"""

	return Settings()

