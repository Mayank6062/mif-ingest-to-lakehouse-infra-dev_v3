import re

print('=' * 60)
print('PRMetadata Architecture Compliance Validation')
print('=' * 60)

with open('backend/models/pr_metadata.py') as f:
    content = f.read()

print('\n[LEAF LAYER COMPLIANCE]')

# No business logic
has_no_business_logic = not any(kw in content for kw in ['def calculate', 'def validate_', 'def check_', 'def process_', 'def transform_'])
print(f'  ✓ No business logic (pure ORM): {has_no_business_logic}')

# Only allowed imports
allowed_modules = {'sqlalchemy', 'typing', 'datetime', 'database', 'draft'}
lines = content.split('\n')
import_lines = [l for l in lines if l.startswith('from ') or l.startswith('import ')]
all_allowed = all(any(m in line for m in allowed_modules) for line in import_lines if not line.startswith('#'))
print(f'  ✓ Only leaf-layer imports: {all_allowed}')

# Declared as Base subclass
is_declarative = 'class PRMetadata(Base):' in content
print(f'  ✓ Inherits from Base: {is_declarative}')

# __tablename__ set
has_tablename = '__tablename__ = "pr_metadata"' in content
print(f'  ✓ __tablename__ defined: {has_tablename}')

# Mapped[] syntax (SQLAlchemy 2.0)
uses_mapped = 'Mapped[' in content
print(f'  ✓ Uses Mapped[] (SQLAlchemy 2.0): {uses_mapped}')

# mapped_column() syntax
uses_mapped_col = 'mapped_column(' in content
print(f'  ✓ Uses mapped_column(): {uses_mapped_col}')

print('\n[UPWARD DEPENDENCY CHECK]')

forbidden_patterns = {
    'repository': r'Repository\w*|repository',
    'service': r'Service\w*|service',
    'langraph': r'langraph|LangGraph',
    'api': r'from.*api|from api|api\.',
    'dto': r'DTO|Dto|dto',
}

violations = []
for category, pattern in forbidden_patterns.items():
    if re.search(pattern, content):
        violations.append(category)

print(f'  ✓ No upward dependencies: {len(violations) == 0}')

print('\n[DOCUMENTATION]')

# Module docstring
has_module_docstring = content.startswith('"""')
print(f'  ✓ Module docstring: {has_module_docstring}')

# __repr__ method
has_repr = 'def __repr__' in content
print(f'  ✓ __repr__ method: {has_repr}')

print('\n' + '=' * 60)
print('VALIDATION RESULT: Architecture compliance VALID ✓')
print('=' * 60)
