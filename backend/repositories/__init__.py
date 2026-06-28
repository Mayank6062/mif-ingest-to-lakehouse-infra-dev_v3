"""Data access repositories package (CRUD only).

Purpose: Provide repository classes for CRUD operations on all domain entities.

Responsibility: Data access abstraction using Repository pattern.
All business logic delegated to services; repositories coordinate transactions
via Unit of Work pattern.

Consumers: Services, LangGraph nodes (via services).

Restrictions: No business logic; no service imports; no API imports; only CRUD.

Reference documents: Architecture_Freeze.md §3, 
doc/02_BACKEND_MODULE_ARCHITECTURE.md §2.9 (Repository Layer)
"""

from .uow import UnitOfWork

__all__ = ["UnitOfWork"]
