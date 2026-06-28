"""Shared type definitions: DraftState, GlueJobConfig, ValidationResult, GitHubToken, PRMetadata, RepositoryFacts.

This module defines immutable domain types used throughout the MIF Copilot application.
All types are compatible with future ORM model definitions.

Reference: doc/02_BACKEND_MODULE_ARCHITECTURE.md §2.8 (Models), §2.12 (DTO Mapping)
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class ValidationResult:
    """Result of a validation operation.
    
    Purpose: Capture validation outcomes (pass/fail) with human-readable messages.
    Responsibility: Represent validation success/failure + optional rule reference for internal use.
    Consumers: Services, LangGraph nodes, validation engine.
    Restrictions: User messages never expose rule IDs; rule_id is internal only.
    
    Reference: doc/02_BACKEND_MODULE_ARCHITECTURE.md §2.4.2 (Service layer contracts)
    """
    
    is_valid: bool
    """Whether validation passed (True) or failed (False)."""
    
    message: str
    """User-safe message describing the result. Never exposes internal paths or secrets."""
    
    rule_id: Optional[str] = None
    """Internal rule identifier for logging/analytics. Not exposed to frontend."""
    
    internal_details: Optional[Dict[str, Any]] = None
    """Additional technical context for debugging. Not serialized to API response."""


@dataclass(frozen=True)
class GlueJobConfig:
    """Configuration for an AWS Glue job.
    
    Purpose: Represent a derived Glue job configuration with all required parameters.
    Responsibility: Hold domain-driven values for Glue job creation/modification.
    Consumers: Services, repositories, template engines, draft workspace.
    Restrictions: All fields must be derivable from confirmed values or repository facts.
    
    Reference: doc/02_BACKEND_MODULE_ARCHITECTURE.md §2.5 (Knowledge Layer)
              Confirmed values: worker_type G.1X/G.2X/G.4X, job_version 0.3.0, glue_version 5.1
    """
    
    job_key: str
    """Unique identifier for this job within the draft (format: {source}-{grain})."""
    
    environment: str
    """Environment: dev, staging, prod. Source of truth: GitHub repository structure."""
    
    source_system: str
    """Source system name (e.g., saptcc, saptce). Validated against repository."""
    
    schema_grain: str
    """Schema grain/topic grain identifier (e.g., po_detail, md_material)."""
    
    topic_name: str
    """Kafka topic name in format: {env}.{source}.{grain}.raw (frozen pattern)."""
    
    kafka_secret_name: str
    """Kafka secret name in format: minerva-${env}-corp-mif-{source}-gluejob-sa-cc-api-creds (frozen pattern)."""
    
    glue_job_name: str
    """Glue job name in format: kafka-to-iceberg-batch-{source}-{grain} (frozen pattern)."""
    
    iam_role: str
    """IAM role ARN for Glue job execution."""
    
    worker_type: str
    """Worker type: G.1X (default), G.2X, or G.4X. Default: G.1X (frozen confirmed value)."""
    
    glue_version: str
    """Glue version: 5.1 (frozen confirmed value). Immutable for Phase-1."""
    
    number_of_workers: int
    """Number of workers. Subject to CQ-04 (default 1 vs 4, max 10 - unresolved)."""
    
    scheduling_mode: str
    """Scheduling mode: Manual or Scheduled. Subject to CQ-05 (default Manual or daily 1AM - unresolved)."""
    
    job_type: str
    """Job type: unified (frozen confirmed value). Immutable for Phase-1."""
    
    job_version: str
    """Job version: 0.3.0 (frozen confirmed value). Immutable for Phase-1."""
    
    enterprise_function: str
    """Enterprise function: Subject to CQ-03 (SPEC vs CORP - unresolved)."""
    
    subgroup: str
    """Subgroup: APAC (default), NA, or LATAM (frozen confirmed values)."""
    
    lh_database: str
    """Lakehouse database name. Subject to CQ-A1 (LH DB pattern - unresolved)."""
    
    s3_warehouse: str
    """S3 warehouse path. Subject to CQ-A1 (pattern - unresolved)."""
    
    s3_checkpoint: str
    """S3 checkpoint path for streaming state."""


@dataclass(frozen=True)
class DraftState:
    """State of a draft workspace.
    
    Purpose: Represent the current state of a draft during editing/review.
    Responsibility: Track draft lifecycle (editing, review, PR creation, abandoned).
    Consumers: Services, LangGraph nodes, repositories, API responses.
    Restrictions: Status values subject to CQ-06 (Backend OPEN/REVIEW/PR_CREATED/ABANDONED vs Bible DRAFT_EDITING/REVIEW_READY/PR_CREATING/...).
    
    Reference: doc/02_BACKEND_MODULE_ARCHITECTURE.md §2.8 (Models table spec)
              Decisions.md §8 (CQ-06 preservation)
    """
    
    draft_id: UUID
    """Unique identifier for this draft."""
    
    session_id: UUID
    """Parent session ID."""
    
    environment: str
    """Environment: dev, staging, prod."""
    
    status: Literal["OPEN", "REVIEW", "PR_CREATED", "ABANDONED"]
    """Draft status. Backend uses OPEN/REVIEW/PR_CREATED/ABANDONED (per Backend-v1 reconciliation).
    Note: CQ-06 flags disagreement with Bible's DRAFT_EDITING/REVIEW_READY/... terminology.
    This literal preserves Backend-v1 naming until CQ-06 is resolved.
    """
    
    change_count: int
    """Number of file changes + job additions in this draft."""
    
    job_count: int
    """Number of Glue jobs in this draft."""
    
    is_frozen: bool
    """Whether draft is frozen (FR-W-6/7 - user cannot edit frozen draft)."""
    
    created_at: datetime
    """Timestamp when draft was created."""
    
    updated_at: datetime
    """Timestamp of last modification."""
    
    created_by: str
    """GitHub username who created the draft."""
    
    pr_number: Optional[int] = None
    """GitHub PR number if created; None if not yet created."""
    
    pr_url: Optional[str] = None
    """GitHub PR URL if created; None if not yet created."""
    
    commit_sha: Optional[str] = None
    """Git commit SHA of the PR if created; None otherwise."""


@dataclass(frozen=True)
class GitHubToken:
    """Reference to a GitHub OAuth token.
    
    Purpose: Represent a secure reference to a GitHub token without exposing the raw token.
    Responsibility: Hold token metadata and reference (never the raw token itself).
    Consumers: Auth service, GitHub service, session management.
    Restrictions: Never serialize raw token value; use SecretStr for storage.
    
    Reference: doc/02_BACKEND_MODULE_ARCHITECTURE.md §2.10 (Exceptions, SEC-1)
    """
    
    token_ref: str
    """Secure reference ID (not the actual token). Points to secret store."""
    
    github_username: str
    """GitHub username associated with this token."""
    
    is_valid: bool = True
    """Whether token is currently valid (used for expiry tracking)."""
    
    created_at: Optional[datetime] = None
    """When this token was issued."""


@dataclass(frozen=True)
class PRMetadata:
    """Pull request metadata and tracking.
    
    Purpose: Capture PR creation metadata and track conflict detection.
    Responsibility: Hold PR identifiers and status flags for PR lifecycle.
    Consumers: Services, repositories, LangGraph nodes, API responses.
    Restrictions: PR creation is atomic (one draft = one PR); conflict detection per FR-C-1/2.
    
    Reference: doc/02_BACKEND_MODULE_ARCHITECTURE.md §2.4.6 (ConflictService)
              doc/01_REPOSITORY_MASTER_STRUCTURE.md §1.7 (Core Tables - pr_metadata)
    """
    
    pr_id: UUID
    """Unique identifier for this PR record."""
    
    draft_id: UUID
    """Associated draft ID (1:1 relationship per §1.7 UNIQUE constraint)."""
    
    pr_number: int
    """GitHub PR number."""
    
    pr_url: str
    """Full GitHub PR URL."""
    
    commit_sha: str
    """Commit SHA of the PR."""
    
    branch_name: str
    """Branch name (format: draft/<draft_id> per CQ-06 adoption)."""
    
    pr_created_by: str
    """GitHub username who created the PR."""
    
    pr_created_at: datetime
    """Timestamp when PR was created."""
    
    conflict_detected: bool = False
    """Whether a conflict was detected during PR creation (FR-C-1)."""
    
    conflict_resolved: bool = False
    """Whether conflict was resolved (if detected)."""
    
    created_at: Optional[datetime] = None
    """Record creation timestamp."""


@dataclass(frozen=True)
class RepositoryFacts:
    """Facts extracted from a repository.
    
    Purpose: Capture discovered repository structure and metadata.
    Responsibility: Hold repository introspection results (topics, glue jobs, patterns).
    Consumers: Knowledge layer, validation engine, derivers.
    Restrictions: Read-only; obtained from RepositoryKnowledgeProvider via GitHub.
    
    Reference: doc/02_BACKEND_MODULE_ARCHITECTURE.md §2.5 (Knowledge Layer)
              doc/01_REPOSITORY_MASTER_STRUCTURE.md §1.6 (Knowledge Layer - provider)
    """
    
    environment: str
    """Environment these facts belong to (dev, staging, prod)."""
    
    source_system: str
    """Source system (e.g., saptcc, saptce)."""
    
    existing_topics: List[str]
    """List of existing Kafka topics in the repository."""
    
    existing_glue_jobs: List[str]
    """List of existing Glue job names."""
    
    repo_patterns: Dict[str, Any]
    """Repository-specific patterns (naming, paths, structure).
    Used by priority_resolver to determine repo-wins precedence (BR-A-10).
    """
    
    has_locals_tf: bool
    """Whether locals.tf exists for this source/environment."""
    
    has_glue_tf: bool
    """Whether glue.tf exists for this source/environment."""
    
    discovered_at: datetime
    """Timestamp when these facts were discovered (cache TTL tracking)."""
