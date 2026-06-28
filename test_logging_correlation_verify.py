#!/usr/bin/env python
"""Verification that backend/core/logging.py and correlation.py are correctly implemented."""

import sys
import os
import importlib.util

# Add current directory to path so imports work
sys.path.insert(0, os.getcwd())

try:
    # Direct import of correlation.py by bypassing __init__.py
    spec = importlib.util.spec_from_file_location(
        "backend.core.correlation",
        "backend/core/correlation.py",
    )
    correlation_mod = importlib.util.module_from_spec(spec)
    sys.modules["backend.core.correlation"] = correlation_mod
    spec.loader.exec_module(correlation_mod)
    print("✓ backend.core.correlation loads successfully")
    
    # Test correlation ID generation
    cid = correlation_mod.new_correlation_id()
    assert isinstance(cid, str) and len(cid) > 0, "Correlation ID not a non-empty string"
    print(f"✓ new_correlation_id() works: {cid[:12]}...")
    
    # Test setting and getting
    correlation_mod.set_correlation_id(cid)
    retrieved = correlation_mod.get_correlation_id()
    assert retrieved == cid, f"Retrieved {retrieved}, expected {cid}"
    print("✓ set_correlation_id() and get_correlation_id() work correctly")
    
    # Test context dict
    context = correlation_mod.get_correlation_context()
    assert isinstance(context, dict), "get_correlation_context() should return dict"
    assert "correlation_id" in context, "context should have correlation_id key"
    print("✓ get_correlation_context() works")
    
    # Test clear
    correlation_mod.clear_correlation_context()
    assert correlation_mod.get_correlation_id() is None, "clear_correlation_context() failed"
    print("✓ clear_correlation_context() works")
    
    # Test request ID
    correlation_mod.set_correlation_context(
        correlation_id=cid,
        request_id=correlation_mod.new_request_id(),
        trace_id=correlation_mod.new_trace_id()
    )
    ctx = correlation_mod.get_correlation_context()
    assert ctx["correlation_id"] == cid, "set_correlation_context failed for correlation_id"
    print("✓ set_correlation_context() works")
    
    # Now test logging module
    spec_logging = importlib.util.spec_from_file_location(
        "backend.core.logging",
        "backend/core/logging.py",
    )
    logging_mod = importlib.util.module_from_spec(spec_logging)
    sys.modules["backend.core.logging"] = logging_mod
    spec_logging.loader.exec_module(logging_mod)
    print("✓ backend.core.logging loads successfully")
    
    # Test get_logger
    logger = logging_mod.get_logger("test.module")
    assert logger is not None, "get_logger() returned None"
    assert logger.name == "test.module", f"Logger name is {logger.name}, expected test.module"
    print("✓ get_logger() works")
    
    # Test configure_logging
    logging_mod.configure_logging(log_level="INFO")
    print("✓ configure_logging() works")
    
    # Test CorrelationIdFilter
    filter_obj = logging_mod.CorrelationIdFilter()
    assert filter_obj is not None, "CorrelationIdFilter() instantiation failed"
    print("✓ CorrelationIdFilter() instantiates correctly")
    
    # Test logging with correlation ID
    logger = logging_mod.get_logger("mif_copilot.test")
    correlation_mod.set_correlation_id("test-correlation-id-12345")
    logger.info("Test message with correlation ID")
    print("✓ Logging with correlation ID works")
    
    print("\n✓✓✓ VERIFICATION PASSED ✓✓✓")
    print("backend/core/logging.py and correlation.py are correctly implemented")
    
except Exception as e:
    print(f"✗ FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
