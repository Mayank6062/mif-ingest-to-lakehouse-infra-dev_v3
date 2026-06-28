"""Shared constants: ENVIRONMENTS, WORKER_TYPES, JOB_TYPES, ENTERPRISE_FUNCTIONS, SUBGROUPS.

This module defines all application-wide constant sets used throughout the MIF Copilot.
Every constant has a single authoritative source in the frozen architecture.

Reference: doc/02_BACKEND_MODULE_ARCHITECTURE.md §2.5 (Knowledge Layer - Confirmed values)
          doc/01_REPOSITORY_MASTER_STRUCTURE.md §1.6 (Knowledge Layer - registries)
Constants extracted from confirmed values and registry specifications.
"""

# === ENVIRONMENTS ===
# Authoritative source: doc/02_BACKEND_MODULE_ARCHITECTURE.md (confirmed values)
# Rule: All three environments supported; topic paths per BR-A-15; prod path subject to CQ-14 (unresolved)

ENVIRONMENTS = {
    "dev": "Development environment",
    "staging": "Staging/pre-production environment",
    "prod": "Production environment",
}
"""Supported environments. Immutable list for Phase-1."""

ENVIRONMENT_VALUES = tuple(ENVIRONMENTS.keys())
"""Tuple of environment names for validation."""

DEFAULT_ENVIRONMENT = "dev"
"""Default environment for new sessions."""


# === WORKER TYPES ===
# Authoritative source: doc/02_BACKEND_MODULE_ARCHITECTURE.md §2.5
# Confirmed value: worker_type G.1X/G.2X/G.4X default G.1X
# Subject to CQ-04: default workers 1 vs 4, max 10 (unresolved)

WORKER_TYPES = {
    "G.1X": "1 DPU worker (cost-effective, suitable for small/medium jobs)",
    "G.2X": "2 DPU workers (balanced performance)",
    "G.4X": "4 DPU workers (high-performance, suitable for large jobs)",
}
"""Available Glue worker types. Immutable list for Phase-1."""

WORKER_TYPE_VALUES = tuple(WORKER_TYPES.keys())
"""Tuple of worker type names for validation."""

DEFAULT_WORKER_TYPE = "G.1X"
"""Default worker type for new Glue jobs (frozen confirmed value)."""

DEFAULT_WORKER_COUNT = 1
"""Default number of workers. CQ-04 flags disagreement (1 vs 4). Using 1 (Backend reconciliation)."""

MAX_WORKER_COUNT = 10
"""Maximum number of workers per job (CQ-04 flags as unresolved; 10 assumed from context)."""


# === JOB TYPES ===
# Authoritative source: doc/02_BACKEND_MODULE_ARCHITECTURE.md §2.5
# Confirmed value: job_type unified

JOB_TYPES = {
    "unified": "Unified job type for Kafka-to-Iceberg ingestion (Phase-1)",
}
"""Glue job types. Only 'unified' supported in Phase-1."""

JOB_TYPE_VALUES = tuple(JOB_TYPES.keys())
"""Tuple of job type names for validation."""

DEFAULT_JOB_TYPE = "unified"
"""Default and only job type for Phase-1 (frozen confirmed value)."""


# === JOB VERSIONS ===
# Authoritative source: doc/02_BACKEND_MODULE_ARCHITECTURE.md §2.5
# Confirmed value: job_version 0.3.0

DEFAULT_JOB_VERSION = "0.3.0"
"""Glue job version (frozen confirmed value). Immutable for Phase-1."""


# === GLUE VERSIONS ===
# Authoritative source: doc/02_BACKEND_MODULE_ARCHITECTURE.md §2.5
# Confirmed value: glue_version 5.1

DEFAULT_GLUE_VERSION = "5.1"
"""AWS Glue version (frozen confirmed value). Immutable for Phase-1."""

GLUE_VERSION_VALUES = ("4.0", "3.0", "2.0")  # Supported versions
"""Fallback versions if needed (not used in Phase-1)."""


# === ENTERPRISE FUNCTIONS ===
# Authoritative source: doc/02_BACKEND_MODULE_ARCHITECTURE.md §2.5 + Decisions.md §8 (CQ-03)
# Confirmed value: NOT YET - CQ-03 flags disagreement between SPEC/CORP
# Subject to CQ-03: Enterprise set AGTR/FOOD/SPEC vs AGTR/FOOD/CORP (unresolved)
# Implementation: Using SPEC variant per Backend reconciliation; can be updated when CQ-03 resolves

ENTERPRISE_FUNCTIONS = {
    "AGTR": "Agriculture function",
    "FOOD": "Food & Beverage function",
    "SPEC": "Specialty function (CQ-03: may become CORP)",
}
"""Enterprise functions. Subject to CQ-03 (SPEC vs CORP - unresolved).

Note: Backend reconciliation adopted SPEC naming; will update if CQ-03 resolves to CORP.
Do not change this without explicit CQ-03 resolution and Decisions.md update.
"""

ENTERPRISE_FUNCTION_VALUES = tuple(ENTERPRISE_FUNCTIONS.keys())
"""Tuple of enterprise function names for validation."""

DEFAULT_ENTERPRISE_FUNCTION = "SPEC"
"""Default enterprise function (subject to CQ-03 resolution)."""


# === SUBGROUPS ===
# Authoritative source: doc/02_BACKEND_MODULE_ARCHITECTURE.md §2.5
# Confirmed value: subgroup APAC/NA/LATAM default APAC

SUBGROUPS = {
    "APAC": "Asia-Pacific region",
    "NA": "North America region",
    "LATAM": "Latin America region",
}
"""Geographic subgroups (frozen confirmed values)."""

SUBGROUP_VALUES = tuple(SUBGROUPS.keys())
"""Tuple of subgroup names for validation."""

DEFAULT_SUBGROUP = "APAC"
"""Default subgroup (frozen confirmed value)."""


# === SCHEDULING / RUN MODES ===
# Authoritative source: doc/02_BACKEND_MODULE_ARCHITECTURE.md §2.5
# Confirmed values: stop_before_start true; sink_trigger availableNow
# Subject to CQ-05: Run mode Manual vs daily 1AM (unresolved)

SCHEDULING_MODES = {
    "Manual": "Manual trigger only (on-demand)",
    "Scheduled": "Scheduled execution with cron expression",
}
"""Scheduling modes for Glue jobs."""

SCHEDULING_MODE_VALUES = tuple(SCHEDULING_MODES.keys())
"""Tuple of scheduling mode names for validation."""

DEFAULT_SCHEDULING_MODE = "Manual"
"""Default scheduling mode (CQ-05 flags as unresolved; Manual assumed from context)."""

STOP_BEFORE_START = True
"""Always stop job before starting new run (frozen confirmed value)."""

SINK_TRIGGER = "availableNow"
"""Sink trigger type: availableNow (frozen confirmed value)."""


# === GLUE JOB CONFIGURATION DEFAULTS ===
# Authoritative sources: Multiple sections of doc/02_BACKEND_MODULE_ARCHITECTURE.md §2.5

DEFAULT_SINK_TYPE = "iceberg"
"""Sink type: iceberg (frozen confirmed value). Immutable for Phase-1."""

DEFAULT_CATALOG = "glue"
"""Catalog type: glue (frozen confirmed value). Immutable for Phase-1."""

DEFAULT_ASSUME_SESSION_NAME = "mif-glue-iceberg"
"""Assume session name for Glue job (frozen confirmed value)."""


# === SOURCE TYPE OPTIONS ===
# Authoritative source: doc/02_BACKEND_MODULE_ARCHITECTURE.md (node specs)
# Confirmed value: Kafka for Phase-1; JDBC/FlatFile/API are placeholders

SOURCE_TYPES = {
    "Kafka": "Apache Kafka (Phase-1 supported)",
    "JDBC": "JDBC sources (placeholder - CQ-A1 future phase)",
    "FlatFile": "Flat file sources (placeholder - future phase)",
    "API": "REST API sources (placeholder - future phase)",
}
"""Source types supported. Kafka is Phase-1; others are placeholders per node_prompts/placeholder.py."""

SOURCE_TYPE_VALUES = tuple(SOURCE_TYPES.keys())
"""Tuple of source type names for validation."""

DEFAULT_SOURCE_TYPE = "Kafka"
"""Default and primary source type for Phase-1."""

PHASE1_SOURCE_TYPES = ("Kafka",)  # Only Kafka supported in Phase-1
"""Source types officially supported in Phase-1."""


# === DRAFT LIFECYCLE STATUSES ===
# Authoritative source: Backend Module Architecture §2.8 + Decisions.md §8 (CQ-06)
# Confirmed value (Backend-v1 reconciliation): OPEN/REVIEW/PR_CREATED/ABANDONED
# Subject to CQ-06: Bible uses DRAFT_EDITING/REVIEW_READY/PR_CREATING/... (unresolved)

DRAFT_STATUSES = {
    "OPEN": "Draft is being edited (corresponds to DRAFT_EDITING per CQ-06)",
    "REVIEW": "Draft ready for review before PR (corresponds to REVIEW_READY per CQ-06)",
    "PR_CREATED": "Pull request has been created (corresponds to PR_CREATING/PR_CREATED per CQ-06)",
    "ABANDONED": "Draft has been abandoned",
}
"""Draft lifecycle statuses. CQ-06 flags terminology disagreement; Backend names adopted pending resolution."""

DRAFT_STATUS_VALUES = tuple(DRAFT_STATUSES.keys())
"""Tuple of draft status names for validation."""


# === OPERATION TYPES ===
# Authoritative source: doc/02_BACKEND_MODULE_ARCHITECTURE.md §2.6 (LangGraph - Operation node)
# Confirmed values: create, modify, review

OPERATION_TYPES = {
    "create": "Create new Glue job",
    "modify": "Modify existing Glue job or files",
    "review": "Review draft before PR creation",
}
"""User-facing operations available per operation node."""

OPERATION_TYPE_VALUES = tuple(OPERATION_TYPES.keys())
"""Tuple of operation type names for validation."""


# === VALIDATION MESSAGE TEMPLATES ===
# Authoritative source: doc/02_BACKEND_MODULE_ARCHITECTURE.md §2.5 (validation_messages.json registry)
# These are placeholders; actual messages loaded from registries at runtime

VALIDATION_MESSAGE_TEMPLATES = {
    "TR-001": "Topic validation failed: topic not found in repository",
    "TR-002": "Topic validation failed: topic exists but format is invalid",
    "JR-001": "Job validation failed: duplicate job name detected",
    "JR-002": "Job validation failed: invalid job configuration",
    "TF-001": "Terraform validation failed: init error",
    "TF-002": "Terraform validation failed: format check error",
    "TF-003": "Terraform validation failed: validate error",
}
"""Template validation messages (loaded from registry at runtime). Used as fallbacks only."""


# === RATE LIMITING ===
# Authoritative source: doc/02_BACKEND_MODULE_ARCHITECTURE.md §2.2.2 (middleware stack)
# Frozen decision: Rate limiting per session on /agent/message endpoint

RATE_LIMIT_REQUESTS_PER_MINUTE = 100
"""Rate limit: requests per minute per session on /agent/message endpoint (frozen decision)."""

RATE_LIMIT_WINDOW_SECONDS = 60
"""Rate limit window duration in seconds."""


# === PATTERN TEMPLATES ===
# Authoritative source: doc/02_BACKEND_MODULE_ARCHITECTURE.md §2.5 (confirmed values)
# These patterns are frozen; used by formatters and derivers

TOPIC_NAME_PATTERN = "{env}.{source}.{grain}.raw"
"""Topic naming pattern: env.source.grain.raw (frozen confirmed value)."""

JOB_NAME_PATTERN = "kafka-to-iceberg-batch-{source}-{grain}"
"""Glue job naming pattern (frozen confirmed value)."""

KAFKA_SECRET_PATTERN = "minerva-${env}-corp-mif-{source}-gluejob-sa-cc-api-creds"
"""Kafka secret naming pattern (frozen confirmed value). Note: ${env} uses shell syntax."""

BRANCH_NAME_PATTERN = "draft/{draft_id}"
"""Git branch naming pattern (adopted per CQ-06; frozen)."""


# === TIMEOUT VALUES ===
# Authoritative source: doc/02_BACKEND_MODULE_ARCHITECTURE.md (system context)

GITHUB_API_TIMEOUT_SECONDS = 30
"""Timeout for GitHub API calls."""

TERRAFORM_VALIDATION_TIMEOUT_SECONDS = 60
"""Timeout for Terraform validation command."""

DATABASE_QUERY_TIMEOUT_SECONDS = 10
"""Timeout for database queries."""


# === SESSION & DRAFT RETENTION ===
# Authoritative source: CQ-10 (unresolved)
# Placeholder values pending CQ-10 resolution

DRAFT_RETENTION_DAYS = 30
"""Draft retention period in days (CQ-10 - unresolved; 30 days assumed)."""

SNAPSHOT_RETENTION_DAYS = 60
"""Snapshot retention period in days (CQ-10 - unresolved; 60 days assumed)."""

SESSION_EXPIRY_HOURS = 8
"""Session expiry time in hours."""


# === TERRAFORM CONFIGURATION ===
# Authoritative source: doc/02_BACKEND_MODULE_ARCHITECTURE.md §2.4.5 (TerraformService)
# Frozen decision: Terraform CLI ≥01.0

MINIMUM_TERRAFORM_VERSION = "1.0"
"""Minimum required Terraform CLI version (frozen requirement)."""

TERRAFORM_INIT_ARGS = ("-upgrade",)
"""Arguments for terraform init command."""

TERRAFORM_FMT_ARGS = ("-recursive", "-check",)
"""Arguments for terraform fmt command (check mode)."""

TERRAFORM_VALIDATE_ARGS = ()
"""Arguments for terraform validate command."""


# === VALIDATION RULES PREFIXES ===
# Authoritative source: doc/02_BACKEND_MODULE_ARCHITECTURE.md §2.5 (rule IDs)

TOPIC_RULE_PREFIX = "TR-"
"""Prefix for topic validation rule IDs."""

JOB_RULE_PREFIX = "JR-"
"""Prefix for job validation rule IDs."""

TERRAFORM_RULE_PREFIX = "TF-"
"""Prefix for Terraform validation rule IDs."""
