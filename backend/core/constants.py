"""Backend operational constants (non-business).

Purpose: Define HTTP headers, logger names, API paths, encoding, and other
backend infrastructure identifiers used throughout the application.

Responsibility: Provide stable constants for HTTP layer, logging layer,
and internal backend operations. Do NOT include domain constants (those
belong to shared/) or runtime configuration (those belong to config/).

Consumers: API layer, middleware, logging setup, correlation management.

Restrictions: Must NOT include business logic, Glue Job defaults, validation
rules, Terraform arguments, or any configuration that varies by environment
(environment-specific values belong to config.Settings).

Reference documents: Architecture_Freeze.md §4 (Layer Responsibilities),
doc/01_REPOSITORY_MASTER_STRUCTURE.md §1.3 (Backend Structure),
doc/02_BACKEND_MODULE_ARCHITECTURE.md §2.11 (Logging & Observability)
"""

# ==============================================================================
# HTTP HEADERS
# ==============================================================================
# Purpose: Standard HTTP header names used for correlation and request tracking.
# Owner: Backend Core (infrastructure layer)
# Consumer: API middleware, logging, services
# Reference: doc/02_BACKEND_MODULE_ARCHITECTURE.md §2.11 (identifiers)

CORRELATION_HEADER = "X-Correlation-ID"
"""HTTP header name for correlation ID tracking across requests."""

REQUEST_ID_HEADER = "X-Request-ID"
"""HTTP header name for individual request identification."""

TRACE_ID_HEADER = "X-Trace-ID"
"""HTTP header name for distributed trace identification."""

CONTENT_TYPE_JSON = "application/json"
"""Standard JSON content type for API responses."""

# ==============================================================================
# API PATHS
# ==============================================================================
# Purpose: Stable API path prefixes and constants for HTTP endpoints.
# Owner: Backend Core (API routing layer)
# Consumer: API routes, middleware, frontend configuration
# Reference: doc/02_BACKEND_MODULE_ARCHITECTURE.md §2.2 (API Layer)

API_V1_PREFIX = "/api/v1"
"""Primary API version prefix for client-facing endpoints."""

API_V1_INTERNAL_PREFIX = "/api/v1/internal"
"""Internal service-only endpoint prefix (service tokens, not user tokens)."""

HEALTH_ENDPOINT = "/health"
"""Liveness check endpoint (always /health, not versioned)."""

HEALTH_READY_ENDPOINT = "/health/ready"
"""Readiness check endpoint (DB + Redis connectivity)."""

# ==============================================================================
# LOGGER CONFIGURATION
# ==============================================================================
# Purpose: Canonical logger names for structured logging setup.
# Owner: Backend Core (logging layer)
# Consumer: logging.configure_logging(), get_logger()
# Reference: doc/02_BACKEND_MODULE_ARCHITECTURE.md §2.11 (Logging)

DEFAULT_LOGGER_NAME = "mif_copilot"
"""Root logger name for the application."""

LOGGER_API = "mif_copilot.api"
"""Logger for API routes and HTTP layer."""

LOGGER_SERVICES = "mif_copilot.services"
"""Logger for business logic layer."""

LOGGER_REPOSITORIES = "mif_copilot.repositories"
"""Logger for data access layer."""

LOGGER_KNOWLEDGE = "mif_copilot.knowledge"
"""Logger for knowledge layer (registries, derivers, validators)."""

LOGGER_LANGGRAPH = "mif_copilot.langgraph"
"""Logger for LangGraph orchestration."""

LOGGER_DATABASE = "mif_copilot.database"
"""Logger for database/ORM operations."""

DEFAULT_LOG_FORMAT = (
    "%(asctime)s - %(name)s - %(levelname)s - "
    "[%(correlation_id)s] - %(message)s"
)
"""Default log format with correlation ID tracking."""

DEFAULT_LOG_LEVEL = "INFO"
"""Default logging level if not overridden by configuration."""

# ==============================================================================
# ENCODING & SERIALIZATION
# ==============================================================================
# Purpose: Default encoding and serialization constants.
# Owner: Backend Core (infrastructure layer)
# Consumer: API responses, file handling, logging
# Reference: Python standard practices

DEFAULT_ENCODING = "utf-8"
"""Default text encoding for all string operations and file I/O."""

DEFAULT_JSON_ENCODER = "json.JSONEncoder"
"""Default JSON encoder class for FastAPI and serialization."""

# ==============================================================================
# CORRELATION ID MANAGEMENT
# ==============================================================================
# Purpose: Context variable names for async-aware correlation tracking.
# Owner: Backend Core (correlation layer)
# Consumer: correlation.set_correlation_id(), get_correlation_id()
# Reference: doc/02_BACKEND_MODULE_ARCHITECTURE.md §2.11 (Identifiers)

CORRELATION_CONTEXT_VAR = "mif_correlation_id"
"""Context variable name for storing correlation_id in async context."""

REQUEST_ID_CONTEXT_VAR = "mif_request_id"
"""Context variable name for storing request_id in async context."""

TRACE_ID_CONTEXT_VAR = "mif_trace_id"
"""Context variable name for storing trace_id in async context."""

# ==============================================================================
# BACKEND METADATA
# ==============================================================================
# Purpose: Application version and metadata.
# Owner: Backend Core (application metadata)
# Consumer: Health check endpoints, monitoring, deployment info
# Reference: doc/02_BACKEND_MODULE_ARCHITECTURE.md §2.11 (Observability)

BACKEND_VERSION = "0.1.0"
"""Backend API version (semver). Phase-1 implementation."""

BACKEND_NAME = "mif-copilot-backend"
"""Application identifier for monitoring and deployment tooling."""

# ==============================================================================
# RATE LIMITING OPERATIONAL CONSTANTS
# ==============================================================================
# Purpose: Identifiers and keys for rate limiting state management.
# Owner: Backend Core (middleware/operational layer)
# Consumer: Rate limiter middleware, Redis clients
# Reference: Architecture_Freeze.md §3 (API Contract)

RATE_LIMIT_KEY_PREFIX = "ratelimit:"
"""Redis key prefix for rate limit counters (keyed by user_id)."""

RATE_LIMIT_WINDOW_NAME = "mif_copilot_rate_limit"
"""Name of the rate limit window for operational tracking."""

# ==============================================================================
# HTTP METHOD CONSTANTS
# ==============================================================================
# Purpose: Standard HTTP method names (convenience constants).
# Owner: Backend Core (HTTP layer)
# Consumer: API middleware, testing
# Reference: HTTP/1.1 standard (RFC 7231)

HTTP_GET = "GET"
"""HTTP GET method."""

HTTP_POST = "POST"
"""HTTP POST method."""

HTTP_PUT = "PUT"
"""HTTP PUT method."""

HTTP_DELETE = "DELETE"
"""HTTP DELETE method."""

HTTP_PATCH = "PATCH"
"""HTTP PATCH method."""

# ==============================================================================
# HTTP STATUS CODES (SEMANTIC)
# ==============================================================================
# Purpose: Symbolic names for common HTTP status codes.
# Owner: Backend Core (HTTP layer)
# Consumer: Exception handlers, API responses
# Reference: HTTP/1.1 standard (RFC 7231)

HTTP_STATUS_OK = 200
"""HTTP 200 OK."""

HTTP_STATUS_CREATED = 201
"""HTTP 201 Created."""

HTTP_STATUS_BAD_REQUEST = 400
"""HTTP 400 Bad Request."""

HTTP_STATUS_UNAUTHORIZED = 401
"""HTTP 401 Unauthorized."""

HTTP_STATUS_FORBIDDEN = 403
"""HTTP 403 Forbidden."""

HTTP_STATUS_NOT_FOUND = 404
"""HTTP 404 Not Found."""

HTTP_STATUS_CONFLICT = 409
"""HTTP 409 Conflict (draft frozen, merge conflict, etc.)."""

HTTP_STATUS_UNPROCESSABLE_ENTITY = 422
"""HTTP 422 Unprocessable Entity (validation failure)."""

HTTP_STATUS_RATE_LIMITED = 429
"""HTTP 429 Too Many Requests."""

HTTP_STATUS_INTERNAL_ERROR = 500
"""HTTP 500 Internal Server Error."""

HTTP_STATUS_BAD_GATEWAY = 502
"""HTTP 502 Bad Gateway (GitHub/Terraform unreachable)."""

HTTP_STATUS_SERVICE_UNAVAILABLE = 503
"""HTTP 503 Service Unavailable (database/Redis down, registry load failed)."""

# ==============================================================================
# APPLICATION CONTEXT IDENTIFIERS
# ==============================================================================
# Purpose: Internal string identifiers for context propagation and state management.
# Owner: Backend Core (state management layer)
# Consumer: Middleware, services, LangGraph nodes
# Reference: doc/02_BACKEND_MODULE_ARCHITECTURE.md §2.4 (Service Layer)

CONTEXT_USER_ID = "user_id"
"""Context key for the authenticated user's ID."""

CONTEXT_SESSION_ID = "session_id"
"""Context key for the current session ID."""

CONTEXT_DRAFT_ID = "draft_id"
"""Context key for the current draft ID."""

CONTEXT_ENVIRONMENT = "environment"
"""Context key for the target environment (dev/prod)."""

CONTEXT_GITHUB_USERNAME = "github_username"
"""Context key for the GitHub username of the authenticated user."""
