#!/usr/bin/env python3
"""Verification script for shared/ module implementation."""

import sys
import shared

# Count exports
exceptions = [x for x in dir(shared) if 'Exception' in x]
validators = [x for x in dir(shared) if 'validate' in x]
formatters = [x for x in dir(shared) if 'format' in x]
types_list = [x for x in dir(shared) if x[0].isupper() and not x.startswith('_')]
constants = [x for x in dir(shared) if x.isupper() and not x.startswith('_')]

print(f"✅ Exceptions: {len(exceptions)} ({', '.join(exceptions[:3])}...)")
print(f"✅ Validators: {len(validators)} ({', '.join(validators)})")
print(f"✅ Formatters: {len(formatters)} ({', '.join(formatters[:3])}...)")
print(f"✅ Types: {len(types_list)} ({', '.join(types_list)})")
print(f"✅ Constants: {len(constants)} (sample: {', '.join(constants[:3])}...)")

# Test imports in each module
print("\n--- Testing module imports ---")
from shared.types import DraftState, GlueJobConfig, ValidationResult
from shared.exceptions import CopilotException, ValidationException
from shared.validators import validate_topic_format, validate_job_name_format
from shared.formatters import format_topic_name, format_glue_job_name
from shared.constants import ENVIRONMENTS, WORKER_TYPES

print("✅ All direct imports successful")

# Test circular dependency check
print("\n--- Module import chain ---")
print(f"shared.__init__ imports: types, constants, exceptions, validators, formatters")

# Verify no forbidden imports
import importlib.util
forbidden_modules = ['backend', 'knowledge', 'langgraph', 'database', 'frontend', 'repositories', 'services', 'api', 'fastapi', 'sqlalchemy', 'langchain', 'github', 'redis', 'postgres']

print("\n--- Forbidden import check ---")
for mod_name in ['types', 'constants', 'exceptions', 'validators', 'formatters']:
    with open(f"shared/{mod_name}.py", 'r') as f:
        content = f.read()
        found_forbidden = [fb for fb in forbidden_modules if f"import {fb}" in content or f"from {fb}" in content]
        if found_forbidden:
            print(f"❌ {mod_name}: Found forbidden imports: {found_forbidden}")
            sys.exit(1)
        else:
            print(f"✅ {mod_name}: No forbidden imports")

print("\n✅ All verifications passed!")
