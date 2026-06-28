"""Shared validators: pure functions for common validation concerns.

This module defines validation functions used throughout the application.
All validators are pure functions with no side effects, no I/O, no database access.
Validators raise typed exceptions only; they never return mixed result types.

Validators in this module perform format/syntax validation only.
Business logic validation (e.g., "does this topic exist in the repo?") lives in services/knowledge.

Reference: doc/02_BACKEND_MODULE_ARCHITECTURE.md §2.4 (Service Layer)
          Decisions.md §7 (Design Patterns)
"""

import re
from typing import Tuple
from .exceptions import ValidationException


def validate_topic_format(topic_name: str) -> Tuple[bool, str]:
    """Validate Kafka topic name format.
    
    Purpose: Verify topic name follows frozen naming pattern and is syntactically valid.
    Responsibility: Format validation only; does NOT check if topic exists in repository.
    Consumers: Services, schema validators, LangGraph nodes.
    Restrictions: Pure function; no database access; no GitHub API calls.
    
    Topic format (frozen): {env}.{source}.{grain}.raw
    Example: dev.saptcc.po_detail.raw
    
    Args:
        topic_name: Topic name to validate (e.g., "dev.saptcc.po_detail.raw")
    
    Returns:
        Tuple[bool, str]: (is_valid, error_message or "")
        - If valid: (True, "")
        - If invalid: (False, "reason")
    
    Raises:
        ValidationException: Only if topic_name is None or not a string (type error).
    
    Reference: doc/02_BACKEND_MODULE_ARCHITECTURE.md §2.5 (confirmed values)
              TOPIC_NAME_PATTERN = "{env}.{source}.{grain}.raw"
    """
    
    if not isinstance(topic_name, str):
        raise ValidationException(
            user_message="Invalid topic format: expected string.",
            internal_details={"received_type": str(type(topic_name))},
        )
    
    if not topic_name.strip():
        return False, "Topic name cannot be empty."
    
    # Validate format: {env}.{source}.{grain}.raw
    # Frozen pattern: env.source.grain.raw
    # Each segment must be non-empty, lowercase alphanumeric + underscore + hyphen
    pattern = r"^[a-z0-9_-]+\.[a-z0-9_-]+\.[a-z0-9_-]+\.raw$"
    
    if not re.match(pattern, topic_name.lower()):
        return False, "Topic name must follow format: {env}.{source}.{grain}.raw (lowercase, alphanumeric, underscore, hyphen)."
    
    # Additional check: must have exactly 4 segments (env, source, grain, raw)
    segments = topic_name.split(".")
    if len(segments) != 4:
        return False, "Topic name must have exactly 4 segments: env.source.grain.raw"
    
    return True, ""


def validate_job_name_format(job_name: str) -> Tuple[bool, str]:
    """Validate Glue job name format.
    
    Purpose: Verify job name follows frozen naming pattern and is syntactically valid.
    Responsibility: Format validation only.
    Consumers: Services, draft repository, LangGraph nodes.
    Restrictions: Pure function; no database access; no GitHub API calls.
    
    Job name format (frozen): kafka-to-iceberg-batch-{source}-{grain}
    Example: kafka-to-iceberg-batch-saptcc-po_detail
    
    Args:
        job_name: Job name to validate (e.g., "kafka-to-iceberg-batch-saptcc-po_detail")
    
    Returns:
        Tuple[bool, str]: (is_valid, error_message or "")
        - If valid: (True, "")
        - If invalid: (False, "reason")
    
    Raises:
        ValidationException: Only if job_name is None or not a string (type error).
    
    Reference: doc/02_BACKEND_MODULE_ARCHITECTURE.md §2.5 (confirmed values)
              JOB_NAME_PATTERN = "kafka-to-iceberg-batch-{source}-{grain}"
    """
    
    if not isinstance(job_name, str):
        raise ValidationException(
            user_message="Invalid job name format: expected string.",
            internal_details={"received_type": str(type(job_name))},
        )
    
    if not job_name.strip():
        return False, "Job name cannot be empty."
    
    # Validate format: kafka-to-iceberg-batch-{source}-{grain}
    # Frozen prefix: kafka-to-iceberg-batch-
    # Source and grain must be lowercase alphanumeric + underscore + hyphen
    pattern = r"^kafka-to-iceberg-batch-[a-z0-9_-]+-[a-z0-9_-]+$"
    
    if not re.match(pattern, job_name.lower()):
        return False, "Job name must follow format: kafka-to-iceberg-batch-{source}-{grain} (lowercase, alphanumeric, underscore, hyphen)."
    
    # Additional check: must have prefix
    if not job_name.startswith("kafka-to-iceberg-batch-"):
        return False, "Job name must start with: kafka-to-iceberg-batch-"
    
    remaining = job_name[len("kafka-to-iceberg-batch-"):]
    if not remaining or remaining.count("-") < 1:
        return False, "Job name must have source and grain after prefix (e.g., kafka-to-iceberg-batch-saptcc-po_detail)."
    
    return True, ""


def validate_source_system_name(source_system: str) -> Tuple[bool, str]:
    """Validate source system name format.
    
    Purpose: Verify source system name is a valid identifier.
    Responsibility: Format validation only; does NOT check if source exists in repository.
    Consumers: Services, LangGraph nodes, schema validators.
    Restrictions: Pure function; no database access; no GitHub API calls.
    
    Source system format: lowercase alphanumeric + underscore, 2-50 characters
    Examples: saptcc, saptce, my_source_123
    
    Args:
        source_system: Source system name to validate (e.g., "saptcc")
    
    Returns:
        Tuple[bool, str]: (is_valid, error_message or "")
        - If valid: (True, "")
        - If invalid: (False, "reason")
    
    Raises:
        ValidationException: Only if source_system is None or not a string (type error).
    
    Reference: Frozen naming conventions (from Decisions.md §1.14)
    """
    
    if not isinstance(source_system, str):
        raise ValidationException(
            user_message="Invalid source system name: expected string.",
            internal_details={"received_type": str(type(source_system))},
        )
    
    if not source_system.strip():
        return False, "Source system name cannot be empty."
    
    # Validate format: lowercase alphanumeric + underscore, 2-50 chars
    pattern = r"^[a-z0-9_]{2,50}$"
    
    if not re.match(pattern, source_system.lower()):
        return False, "Source system name must be 2-50 characters, lowercase alphanumeric and underscores only."
    
    return True, ""


def validate_schema_grain_format(schema_grain: str) -> Tuple[bool, str]:
    """Validate schema grain (topic grain) name format.
    
    Purpose: Verify schema grain is a valid identifier.
    Responsibility: Format validation only.
    Consumers: Services, LangGraph nodes, schema validators.
    Restrictions: Pure function; no database access; no GitHub API calls.
    
    Schema grain format: lowercase alphanumeric + underscore, 1-100 characters
    Examples: po_detail, md_material, customer_data
    
    Args:
        schema_grain: Schema grain name to validate (e.g., "po_detail")
    
    Returns:
        Tuple[bool, str]: (is_valid, error_message or "")
        - If valid: (True, "")
        - If invalid: (False, "reason")
    
    Raises:
        ValidationException: Only if schema_grain is None or not a string (type error).
    
    Reference: Frozen naming conventions (from Decisions.md §1.14)
    """
    
    if not isinstance(schema_grain, str):
        raise ValidationException(
            user_message="Invalid schema grain: expected string.",
            internal_details={"received_type": str(type(schema_grain))},
        )
    
    if not schema_grain.strip():
        return False, "Schema grain cannot be empty."
    
    # Validate format: lowercase alphanumeric + underscore, 1-100 chars
    pattern = r"^[a-z0-9_]{1,100}$"
    
    if not re.match(pattern, schema_grain.lower()):
        return False, "Schema grain must be 1-100 characters, lowercase alphanumeric and underscores only."
    
    return True, ""
