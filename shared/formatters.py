"""Shared formatters: pure string formatting functions for common concerns.

This module defines formatting functions used throughout the application.
All formatters are pure functions with deterministic output.
Formatters apply frozen naming patterns consistently.

Formatters never have side effects, never access I/O, never access state.
Formatters return formatted strings following frozen patterns.

Reference: doc/02_BACKEND_MODULE_ARCHITECTURE.md §2.5 (confirmed values - patterns)
          shared/constants.py (frozen pattern definitions)
"""

from uuid import UUID
from datetime import datetime
from typing import Optional


def format_topic_name(environment: str, source_system: str, schema_grain: str) -> str:
    """Format a Kafka topic name using frozen pattern.
    
    Purpose: Generate topic name following frozen pattern: {env}.{source}.{grain}.raw
    Responsibility: Pure formatting; does NOT validate or check existence.
    Consumers: Services, derivers, template engines.
    Restrictions: Pure function; no database/API calls; deterministic.
    
    Frozen pattern: {env}.{source}.{grain}.raw
    Example output: dev.saptcc.po_detail.raw
    
    Args:
        environment: Environment (dev, staging, prod)
        source_system: Source system name (e.g., saptcc, saptce)
        schema_grain: Schema grain (e.g., po_detail, md_material)
    
    Returns:
        Formatted topic name string
    
    Example:
        >>> format_topic_name("dev", "saptcc", "po_detail")
        "dev.saptcc.po_detail.raw"
    
    Reference: doc/02_BACKEND_MODULE_ARCHITECTURE.md §2.5
              TOPIC_NAME_PATTERN = "{env}.{source}.{grain}.raw"
    """
    return f"{environment.lower()}.{source_system.lower()}.{schema_grain.lower()}.raw"


def format_glue_job_name(source_system: str, schema_grain: str) -> str:
    """Format a Glue job name using frozen pattern.
    
    Purpose: Generate job name following frozen pattern: kafka-to-iceberg-batch-{source}-{grain}
    Responsibility: Pure formatting; does NOT validate or check existence.
    Consumers: Services, derivers, template engines.
    Restrictions: Pure function; no database/API calls; deterministic.
    
    Frozen pattern: kafka-to-iceberg-batch-{source}-{grain}
    Example output: kafka-to-iceberg-batch-saptcc-po_detail
    
    Args:
        source_system: Source system name (e.g., saptcc, saptce)
        schema_grain: Schema grain (e.g., po_detail, md_material)
    
    Returns:
        Formatted job name string
    
    Example:
        >>> format_glue_job_name("saptcc", "po_detail")
        "kafka-to-iceberg-batch-saptcc-po_detail"
    
    Reference: doc/02_BACKEND_MODULE_ARCHITECTURE.md §2.5
              JOB_NAME_PATTERN = "kafka-to-iceberg-batch-{source}-{grain}"
    """
    return f"kafka-to-iceberg-batch-{source_system.lower()}-{schema_grain.lower()}"


def format_terraform_path(environment: str, source_system: str, file_type: str = "locals") -> str:
    """Format a Terraform file path for repository navigation.
    
    Purpose: Generate repository path to Terraform files following repository structure.
    Responsibility: Path formatting; does NOT validate or check existence.
    Consumers: Services, GitHub navigation, validation.
    Restrictions: Pure function; no filesystem access; deterministic.
    
    File structure (frozen):
    - {env}_{source}/locals.tf
    - {env}_{source}/glue.tf
    
    Example outputs:
    - dev_saptcc/locals.tf
    - dev_saptcc/glue.tf
    - prod_saptce/locals.tf
    
    Args:
        environment: Environment (dev, staging, prod)
        source_system: Source system name (e.g., saptcc, saptce)
        file_type: File type (locals or glue), defaults to locals
    
    Returns:
        Formatted Terraform file path (relative to repository root)
    
    Example:
        >>> format_terraform_path("dev", "saptcc", "locals")
        "dev_saptcc/locals.tf"
        >>> format_terraform_path("prod", "saptce", "glue")
        "prod_saptce/glue.tf"
    
    Reference: doc/01_REPOSITORY_MASTER_STRUCTURE.md (repository structure)
              Terraform reference folders: confluent_minerva_dev/, saptcc/, saptce/
    """
    folder = f"{environment.lower()}_{source_system.lower()}"
    filename = f"{file_type.lower()}.tf"
    return f"{folder}/{filename}"


def format_kafka_secret_name(environment: str, source_system: str) -> str:
    """Format a Kafka secret name using frozen pattern.
    
    Purpose: Generate secret name for Kafka credentials.
    Responsibility: Pure formatting; does NOT create secrets.
    Consumers: Services, derivers, Glue job configuration.
    Restrictions: Pure function; no I/O; deterministic.
    
    Frozen pattern: minerva-${env}-corp-mif-{source}-gluejob-sa-cc-api-creds
    Note: ${env} uses shell variable syntax; literal env name substituted here.
    
    Example output: minerva-dev-corp-mif-saptcc-gluejob-sa-cc-api-creds
    
    Args:
        environment: Environment (dev, staging, prod)
        source_system: Source system name (e.g., saptcc, saptce)
    
    Returns:
        Formatted secret name string
    
    Example:
        >>> format_kafka_secret_name("dev", "saptcc")
        "minerva-dev-corp-mif-saptcc-gluejob-sa-cc-api-creds"
    
    Reference: doc/02_BACKEND_MODULE_ARCHITECTURE.md §2.5
              KAFKA_SECRET_PATTERN = "minerva-${env}-corp-mif-{source}-gluejob-sa-cc-api-creds"
    """
    return f"minerva-{environment.lower()}-corp-mif-{source_system.lower()}-gluejob-sa-cc-api-creds"


def format_git_branch_name(draft_id: UUID) -> str:
    """Format a Git branch name for draft PRs.
    
    Purpose: Generate branch name for draft-specific pull requests.
    Responsibility: Pure formatting; does NOT create branches.
    Consumers: Services, PR creation workflow.
    Restrictions: Pure function; no I/O; deterministic.
    
    Frozen pattern: draft/{draft_id}
    Example: draft/550e8400-e29b-41d4-a716-446655440000
    
    Args:
        draft_id: UUID of the draft
    
    Returns:
        Formatted branch name string
    
    Example:
        >>> format_git_branch_name(UUID('550e8400-e29b-41d4-a716-446655440000'))
        "draft/550e8400-e29b-41d4-a716-446655440000"
    
    Reference: doc/02_BACKEND_MODULE_ARCHITECTURE.md §2.4.2 (DraftService)
              Decisions.md §7 (CQ-06 adoption: branch/<draft_id> pattern)
    """
    return f"draft/{str(draft_id)}"


def format_iso8601_datetime(dt: datetime) -> str:
    """Format a datetime as ISO 8601 string (UTC).
    
    Purpose: Serialize datetime for API responses and logs.
    Responsibility: Pure formatting; deterministic.
    Consumers: API serialization, logging, timestamps.
    Restrictions: Pure function; no I/O.
    
    Format: ISO 8601 UTC (e.g., 2026-06-28T14:30:45Z)
    
    Args:
        dt: datetime object
    
    Returns:
        ISO 8601 formatted string with 'Z' suffix (UTC)
    
    Example:
        >>> format_iso8601_datetime(datetime(2026, 6, 28, 14, 30, 45))
        "2026-06-28T14:30:45Z"
    """
    iso_str = dt.isoformat()
    return iso_str if iso_str.endswith("Z") else iso_str + "Z"


def format_pr_title(source_system: str, schema_grain: str, operation: str = "Create") -> str:
    """Format a GitHub PR title.
    
    Purpose: Generate consistent PR titles for automated PRs.
    Responsibility: Pure formatting; does NOT create PRs.
    Consumers: PR creation service.
    Restrictions: Pure function; deterministic.
    
    Format: {operation} Glue job: {source}-{grain}
    Example: Create Glue job: saptcc-po_detail
    
    Args:
        source_system: Source system name
        schema_grain: Schema grain
        operation: Operation type (Create, Modify), defaults to Create
    
    Returns:
        Formatted PR title string
    
    Example:
        >>> format_pr_title("saptcc", "po_detail", "Create")
        "Create Glue job: saptcc-po_detail"
    """
    return f"{operation} Glue job: {source_system}-{schema_grain}"
