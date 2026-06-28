"""Secret handling utilities and secure string masking.

Purpose: Provide infrastructure helpers for safe secret handling, masking, and
secure string formatting. Prevents secrets from appearing in logs, error messages,
or other output.

Responsibility: SecretStr wrapper, masking utilities, safe secret comparison,
and formatting helpers that maintain security properties throughout the app.

Consumers: Services (GitHub token, database passwords), middleware (logging),
error handlers, configuration management.

Restrictions: No authentication logic; no encryption (Pydantic SecretStr is used);
no token validation; no business logic. Only utility functions for safe handling
of secret values.

Reference documents: Architecture_Freeze.md §3 (No Secrets in Logs),
doc/02_BACKEND_MODULE_ARCHITECTURE.md §2.11 (Security & Logging),
doc/CPRS_v1.0.md §12 (SEC-1: Secrets never shown in logs)

Design pattern: Uses Pydantic's SecretStr for basic obfuscation + custom masking
utilities for logs. Not cryptographic security; prevents casual exposure.
For CQ-A7 (token encryption at rest), use application-level or system-level secrets
management (e.g., AWS Secrets Manager, HashiCorp Vault).

CQ Impact: CQ-A7 (Token encryption / Pydantic version) — token storage at rest
not covered here; this file handles in-flight and log masking only.
"""

import re
from typing import Any, Optional


# ==============================================================================
# SECRET STRING TYPE
# ==============================================================================
# Purpose: Type alias for Pydantic SecretStr or str-wrapped secret.
# Owner: Backend Core (security layer)
# Consumer: Services, repositories, configuration
# Reference: doc/02_BACKEND_MODULE_ARCHITECTURE.md §2.3 (Schemas)

try:
    from pydantic import SecretStr
    SecretStrType = SecretStr
except ImportError:
    # Fallback if Pydantic not available (should not happen in production)
    SecretStrType = str


def mask_secret(
    value: Any,
    mask_char: str = "*",
    visible_chars: int = 4,
) -> str:
    """Mask a secret value for safe logging/display.

    Purpose: Prevent sensitive values from appearing in logs, error messages,
    or user-facing strings while preserving enough context for debugging.

    Args:
        value: The secret value to mask (e.g., GitHub token, password, API key).
               Can be any type; will be converted to string.
        mask_char: Character to use for masking (default: "*").
                   Usually "*" or "•".
        visible_chars: Number of characters to leave visible at the end
                      (default: 4). Set to 0 to fully mask.

    Returns:
        Masked string in format: "****visible_end"
        Examples:
            mask_secret("ghp_1234567890abcdefghij", "*", 4) → "****ghij"
            mask_secret("password123", "*", 0) → "***********"

    Behavior:
        - Converts value to string first
        - Always masks if length > 8 characters
        - If length ≤ 8, masks completely (no context to leak)
        - Visible chars extracted from end of string
        - Never exposes more than visible_chars characters

    Examples:
        GitHub token:
        >>> mask_secret("ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefgh")
        '****efgh'

        Database password:
        >>> mask_secret("MyP@ssw0rd123", "*", 2)
        '***23'

        Short secret (fully masked):
        >>> mask_secret("secret")
        '***' (all masked, too short to show context)

    Reference:
        SEC-1 (Secrets never shown in logs)
        Decisions.md §7.16 (No Secrets in Logs)
    """
    if value is None:
        return "[None]"

    # Convert to string if not already
    secret_str = str(value)

    # If it's a Pydantic SecretStr, get the actual value
    if isinstance(value, SecretStrType) and hasattr(value, "get_secret_value"):
        secret_str = value.get_secret_value()

    # Minimum security: if length <= 8, mask completely
    if len(secret_str) <= 8:
        return mask_char * len(secret_str)

    # Extract visible portion from end
    visible_portion = secret_str[-visible_chars:] if visible_chars > 0 else ""

    # Calculate mask length
    mask_length = len(secret_str) - visible_chars

    # Return masked string
    return mask_char * mask_length + visible_portion


def mask_error_details(error_message: str) -> str:
    """Mask secrets in error messages using common patterns.

    Purpose: Sanitize error messages that might contain secrets before
    sending to logs or error handlers.

    Args:
        error_message: Error message that may contain secrets.

    Returns:
        Error message with secrets masked.

    Behavior:
        - Detects common secret patterns: tokens, keys, passwords
        - Masks GitHub tokens (ghp_, ghu_, github_pat_)
        - Masks API keys (api_key, apikey patterns)
        - Masks passwords and secrets in quoted strings
        - Preserves message structure for debugging

    Examples:
        >>> mask_error_details("Failed with token ghp_1234567890abcdef")
        "Failed with token ****cdef"

        >>> mask_error_details("Error: secret=mysecretpassword123")
        "Error: secret=***123"

    Reference:
        SEC-1 (Secrets never shown in logs)
    """
    result = error_message

    # Mask GitHub tokens (ghp_, ghu_, github_pat_ formats)
    result = re.sub(
        r'(ghp_|ghu_|github_pat_)[A-Za-z0-9_]{20,}',
        lambda m: mask_secret(m.group(0)),
        result,
    )

    # Mask API keys: "key=<value>" or "api_key: <value>"
    result = re.sub(
        r'(api_?key|secret|password|token|auth|bearer)\s*[:=]\s*[^\s\),}]+',
        lambda m: m.group(1) + m.group(0)[len(m.group(1)):].split('=')[0] + '=' + mask_secret(
            m.group(0).split('=')[1] if '=' in m.group(0) else m.group(0).split(':')[1]
        ),
        result,
        flags=re.IGNORECASE,
    )

    return result


def should_mask_log_field(field_name: str) -> bool:
    """Determine if a log field should be masked based on its name.

    Purpose: Help logging formatters and handlers decide which fields
    to mask before outputting to logs.

    Args:
        field_name: Name of the field to check (e.g., "github_token", "password").

    Returns:
        True if the field should be masked; False otherwise.

    Behavior:
        - Checks against known secret field names
        - Case-insensitive
        - Matches common naming patterns: token, secret, password, key, etc.

    Examples:
        >>> should_mask_log_field("github_token")
        True

        >>> should_mask_log_field("user_id")
        False

        >>> should_mask_log_field("SECRET_PASSWORD")
        True

    Reference:
        SEC-1 (Secrets never shown in logs)
        Decisions.md §7.16 (No Secrets in Logs)
    """
    secret_keywords = {
        "token",
        "secret",
        "password",
        "api_key",
        "apikey",
        "auth",
        "bearer",
        "credential",
        "private_key",
        "private",
        "ssh_key",
        "encryption_key",
        "database_password",
        "db_password",
    }

    field_lower = field_name.lower()
    return any(keyword in field_lower for keyword in secret_keywords)


def safe_secret_repr(value: Any, label: str = "secret") -> str:
    """Create a safe string representation of a secret for logging.

    Purpose: Provide a consistent way to represent secrets in log output
    that is safe and informative.

    Args:
        value: The secret value to represent (any type).
        label: Human-readable label for the secret (e.g., "GitHub token", "password").

    Returns:
        Safe representation like "<GitHub token: ****1234>"

    Examples:
        >>> safe_secret_repr("ghp_1234567890abcdef", "GitHub token")
        "<GitHub token: ****abcd>"

        >>> safe_secret_repr(None, "API key")
        "<API key: [None]>"

    Reference:
        SEC-1 (Secrets never shown in logs)
    """
    masked = mask_secret(value) if value else "[None]"
    return f"<{label}: {masked}>"


def compare_secrets(secret1: Any, secret2: Any) -> bool:
    """Safely compare two secret values without exposing them.

    Purpose: Compare secrets for equality (e.g., token validation) without
    revealing the values in logs or error messages.

    Args:
        secret1: First secret to compare.
        secret2: Second secret to compare.

    Returns:
        True if secrets are equal; False otherwise.

    Behavior:
        - Converts both to strings if needed
        - Handles Pydantic SecretStr properly
        - Constant-time comparison (as much as Python allows) to resist timing attacks
        - Never logs the secrets

    Examples:
        >>> token1 = "ghp_1234567890abcdef"
        >>> token2 = "ghp_1234567890abcdef"
        >>> compare_secrets(token1, token2)
        True

    Reference:
        SEC-1 (Secrets never shown in logs)
        CQ-A7 (Token encryption / Pydantic version)
    """
    try:
        # Convert both to strings, handling Pydantic SecretStr
        str1 = str(secret1)
        str2 = str(secret2)

        if isinstance(secret1, SecretStrType) and hasattr(secret1, "get_secret_value"):
            str1 = secret1.get_secret_value()

        if isinstance(secret2, SecretStrType) and hasattr(secret2, "get_secret_value"):
            str2 = secret2.get_secret_value()

        # Use constant-time comparison if available (Python 3.3+)
        import hmac
        return hmac.compare_digest(str1, str2)

    except Exception:
        # Fallback to regular comparison if constant-time not available
        # (should not happen in Python 3.3+)
        return str(secret1) == str(secret2)
