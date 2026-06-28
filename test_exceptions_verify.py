#!/usr/bin/env python
"""Quick verification that backend/core/exceptions.py is correctly structured."""

import importlib.util
import sys

# Load backend/core/exceptions.py directly
spec = importlib.util.spec_from_file_location("backend_core_exceptions", "backend/core/exceptions.py")
module = importlib.util.module_from_spec(spec)

# Load shared.exceptions first (required dependency)
from shared.exceptions import CopilotException as SharedCopilot
print("✓ shared.exceptions imports successfully")

# Load backend/core/exceptions
spec.loader.exec_module(module)
print("✓ backend.core.exceptions module loads successfully")

# Verify exports
print(f"Exported items: {len(module.__all__)}")
expected_exports = [
    "CopilotException",
    "ApplicationException",
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
]

for exc in expected_exports:
    assert exc in module.__all__, f"{exc} not in __all__"
    assert hasattr(module, exc), f"{exc} not accessible as attribute"

print(f"✓ All {len(expected_exports)} exception classes exported and accessible")

# Verify no circular imports
try:
    from backend.core.exceptions import ValidationException
    print("✓ Direct import from backend.core.exceptions works")
except Exception as e:
    print(f"✗ Direct import failed: {e}")
    sys.exit(1)

print("\n✓✓✓ VERIFICATION PASSED ✓✓✓")
print("backend/core/exceptions.py is correctly implemented")
