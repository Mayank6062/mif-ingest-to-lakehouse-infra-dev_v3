"""Structured logging setup and configuration.

Purpose: Provide structured logging infrastructure with correlation ID tracking,
logger factory, and custom formatting for all application layers.

Responsibility: Configure logging with correlation_id support, provide get_logger()
factory for layer-specific loggers, implement CorrelationIdFilter for automatic
correlation_id injection, and support masked secrets in logs.

Consumers: All backend modules (api, services, repositories, langgraph, knowledge).

Restrictions: No business logic; no I/O beyond log handlers; no database access;
framework-independent (stdlib logging only); never log secrets or internal paths.

Reference documents: doc/02_BACKEND_MODULE_ARCHITECTURE.md §2.11 (Logging & Observability),
Architecture_Freeze.md §3 (Frozen Dependencies), Decisions.md §7.16 (No Secrets in Logs)

Design pattern: CorrelationIdFilter injects correlation_id from contextvars into
every log record. Custom formatter includes correlation_id in output. Thread-safe
and async-safe via contextvars.
"""

import logging
import logging.config
from typing import Optional
from contextlib import contextmanager

from .constants import (
    DEFAULT_LOGGER_NAME,
    DEFAULT_LOG_FORMAT,
    DEFAULT_LOG_LEVEL,
    CORRELATION_CONTEXT_VAR,
    REQUEST_ID_CONTEXT_VAR,
    TRACE_ID_CONTEXT_VAR,
)


class CorrelationIdFilter(logging.Filter):
    """Logging filter that injects correlation_id from async context into log records.
    
    Purpose: Automatically add correlation_id, request_id, trace_id to every
    log record without requiring explicit argument passing.
    
    Design: Uses contextvars.get() for thread-safe and async-safe context
    retrieval. If context vars are not set, injects empty strings (not None,
    to maintain log format stability).
    """
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Inject correlation context variables into the log record.
        
        Args:
            record: The log record to enrich.
            
        Returns:
            True (always allow the record to be logged).
        """
        from contextvars import get_context
        
        # Get the current context (works in async functions)
        try:
            context = get_context()
            # Retrieve from context variable storage
            correlation_id = context.get(CORRELATION_CONTEXT_VAR, "")
            request_id = context.get(REQUEST_ID_CONTEXT_VAR, "")
            trace_id = context.get(TRACE_ID_CONTEXT_VAR, "")
        except (RuntimeError, LookupError):
            # contextvars not available or not in async context
            correlation_id = ""
            request_id = ""
            trace_id = ""
        
        # Add to log record (used by formatter)
        record.correlation_id = correlation_id or ""
        record.request_id = request_id or ""
        record.trace_id = trace_id or ""
        
        # Always allow the record
        return True


def configure_logging(
    log_level: Optional[str] = None,
    config_dict: Optional[dict] = None,
) -> None:
    """Configure structured logging with correlation ID support.
    
    Purpose: Initialize logging system with correlation_id filter, formatter,
    and per-layer logger names. This should be called once at application startup.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
                   If None, uses DEFAULT_LOG_LEVEL from constants.
        config_dict: Optional dict-based logging config (overrides defaults).
                     If provided, ignores log_level parameter.
    
    Behavior:
        - Creates root logger with console handler
        - Adds CorrelationIdFilter to all handlers
        - Sets formatter to include correlation_id
        - Configures per-layer logger levels (may be customized later)
        - Thread-safe: safe to call multiple times (subsequent calls are no-ops)
        
    Reference:
        Python logging.config: https://docs.python.org/3/library/logging.config.html
        
    Example:
        configure_logging(log_level="INFO")
        logger = get_logger("mif_copilot.services")
        logger.info("Service started")
        # Output: "2026-06-28 10:00:00,123 - mif_copilot.services - INFO - [correlation-123] - Service started"
    """
    if config_dict:
        # Use provided config dictionary
        logging.config.dictConfig(config_dict)
        _add_correlation_filter_to_loggers()
        return
    
    # Default logging configuration
    level = log_level or DEFAULT_LOG_LEVEL
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    
    # Create formatter with correlation_id field
    # Note: correlation_id field is added by CorrelationIdFilter
    formatter = logging.Formatter(DEFAULT_LOG_FORMAT)
    console_handler.setFormatter(formatter)
    
    # Add CorrelationIdFilter to handler
    correlation_filter = CorrelationIdFilter()
    console_handler.addFilter(correlation_filter)
    
    # Add handler to root logger
    root_logger.addHandler(console_handler)
    
    # Configure per-layer loggers (these inherit from root if not explicitly set)
    for logger_name in [
        DEFAULT_LOGGER_NAME,  # root
        "mif_copilot.api",
        "mif_copilot.services",
        "mif_copilot.repositories",
        "mif_copilot.knowledge",
        "mif_copilot.langgraph",
        "mif_copilot.database",
    ]:
        layer_logger = logging.getLogger(logger_name)
        layer_logger.setLevel(level)
        # Each layer logger also gets the filter for consistency
        layer_logger.addFilter(correlation_filter)


def _add_correlation_filter_to_loggers() -> None:
    """Add CorrelationIdFilter to all existing handlers (internal helper).
    
    Used when custom dict config is provided to ensure correlation_id
    injection still happens.
    """
    correlation_filter = CorrelationIdFilter()
    for logger_name in logging.Logger.manager.loggerDict:
        logger = logging.getLogger(logger_name)
        for handler in logger.handlers:
            if not any(isinstance(f, CorrelationIdFilter) for f in handler.filters):
                handler.addFilter(correlation_filter)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for the given module/layer name.
    
    Purpose: Provide a factory method for consistent logger creation across
    all application layers. Loggers are named by layer (e.g., mif_copilot.services)
    and include CorrelationIdFilter automatically.
    
    Args:
        name: Logger name (typically __name__ or a layer name like mif_copilot.services).
              If None, returns root logger.
    
    Returns:
        Configured logging.Logger instance with CorrelationIdFilter.
    
    Design: Python's logging.getLogger() returns the same logger instance for
    the same name (singleton pattern), so this is safe to call multiple times.
    
    Example:
        logger = get_logger("mif_copilot.services")
        logger.info("Processing request")
    """
    logger = logging.getLogger(name or DEFAULT_LOGGER_NAME)
    
    # Ensure CorrelationIdFilter is added if not already present
    if not any(isinstance(f, CorrelationIdFilter) for f in logger.filters):
        logger.addFilter(CorrelationIdFilter())
    
    return logger


@contextmanager
def temporary_log_level(level: str):
    """Context manager to temporarily change logging level.
    
    Purpose: Support temporary verbose logging for debugging without
    restarting the application.
    
    Args:
        level: Temporary logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    
    Usage:
        with temporary_log_level("DEBUG"):
            logger.debug("Verbose output only in this block")
    """
    root_logger = logging.getLogger()
    original_level = root_logger.level
    try:
        root_logger.setLevel(level)
        yield
    finally:
        root_logger.setLevel(original_level)
