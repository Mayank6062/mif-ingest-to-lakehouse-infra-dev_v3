# ARCHITECTURE DECISIONS — LOCKED
## MIF Infrastructure Copilot — Phase 1 Bootstrap

**Status:** FROZEN (Read-only reference for implementation)  
**Created:** 2026-06-28  
**Authority:** doc/01_REPOSITORY_MASTER_STRUCTURE.md (v2.0), doc/CPRS_v1.0.md, doc/MIF_Implementation_Bible.md (v1.0 FINAL DRAFT), doc/02_BACKEND_MODULE_ARCHITECTURE.md, doc/TAS_reference.md  
**Scope:** Defines structural constraints, layer responsibilities, and frozen design intent. Does NOT include implementation details or pending CQ resolutions.

---

## 1. ARCHITECTURE AUTHORITY

### Single Source of Truth for Each Domain

| Domain | Authority | Version | Locked |
|--------|-----------|---------|--------|
| **Product Requirements** | doc/CPRS_v1.0.md | 1.0 | Yes |
| **Repository Structure** | doc/01_REPOSITORY_MASTER_STRUCTURE.md | 2.0 | Yes |
| **Implementation Specification** | doc/MIF_Implementation_Bible.md | 1.0 FINAL DRAFT | Yes |
| **Backend Architecture** | doc/02_BACKEND_MODULE_ARCHITECTURE.md | Implied from section 2 | Yes |
| **Technical Specification** | doc/TAS_reference.md | Per spec | Yes |
| **Glue Job Patterns** | doc/mif-glue-job-creation-terraform-script-process.md | 1.0 | Yes |
| **Terraform Reference** | confluent_minerva_dev/, saptcc/, saptce/ (existing repos) | Current state | Yes (read-only reference) |

### Conflict Resolution Hierarchy

When multiple sources provide guidance:

1. **Frozen requirements** (doc/CPRS_v1.0.md) — always authoritative
2. **Locked structure** (doc/01_REPOSITORY_MASTER_STRUCTURE.md v2.0) — never override
3. **Implementation specification** (MIF Implementation Bible) — interpretation of requirements
4. **Technical architecture** (TAS, Backend Module Architecture) — technical realization
5. **Terraform patterns** (glue-job process, reference repos) — domain-specific examples

**Rule:** If sources conflict, escalate as a Clarification Question (CQ) rather than decide unilaterally.

---

## 2. REPOSITORY OWNERSHIP

### Top-Level Folder Owners

| Folder | Owner role | Responsibility | Immutable |
|--------|-----------|----------------|-----------|
| **backend/** | Backend Platform team | API, services, repositories, models, core | No (implementation pending) |
| **frontend/** | Frontend team | React UI, state management, hooks, stores | No (implementation pending) |
| **langgraph/** | Orchestration team | Graph nodes, state machine, routing, checkpointing | No (implementation pending) |
| **knowledge/** | Knowledge/Data team | Registries, derivers, validators, templates, providers | No (implementation pending) |
| **database/** | Database team | ORM models, session management, migrations, schema | No (implementation pending) |
| **shared/** | Platform team | Types, constants, exceptions, validators, formatters | No (implementation pending) |
| **prompts/** | Prompt engineering team | System prompt, node prompts, templates, loader | No (implementation pending) |
| **config/** | Operations/Platform team | Environment configs, secrets refs, deployment settings | No (implementation pending) |
| **tests/** | QA + Development teams | Unit, integration, contract, e2e, recovery, failure tests | No (implementation pending) |
| **scripts/** | Platform/DevOps team | Validation, CI/CD helpers, local development | No (implementation pending) |
| **docker/** | Platform/DevOps team | Dockerfiles, compose files, container configs | No (implementation pending) |
| **docs/** | Technical Writing / Architecture | Specification, roadmap, reference, diagrams | Yes (authoritative, read-only after freeze) |
| **confluent_minerva_dev/** | Data/Kafka team | Topic definitions (Terraform modules) | Yes (reference, read-only) |
| **saptcc/, saptce/, ...** | Data/Glue team | Source system Glue job definitions | Yes (reference, read-only) |

---

## 3. LAYER RESPONSIBILITIES

### Responsibility Boundary: Hexagonal Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  FRONTEND LAYER (User Interaction)                          │
├─────────────────────────────────────────────────────────────┤
│  ✓ Rendering HTML/React components                          │
│  ✓ Capturing user input (text, selections, form data)        │
│  ✓ Display validation outcomes and messages                  │
│  ✗ Never: Business logic, validation rules, state decisions  │
│  ✗ Never: Direct DB access, GitHub API calls                │
└────────────────────┬────────────────────────────────────────┘
                     │ HTTP/REST + WebSocket
┌────────────────────▼────────────────────────────────────────┐
│  API LAYER (FastAPI - Single Entry Point)                   │
├─────────────────────────────────────────────────────────────┤
│  ✓ POST /agent/message routing to LangGraph                 │
│  ✓ GET /sessions, /auth/* endpoints                         │
│  ✓ Request validation, response serialization               │
│  ✓ Auth middleware (token verification)                      │
│  ✗ Never: Business logic (moves to services)                │
│  ✗ Never: Direct repository access (via API layer)          │
└────────────────────┬────────────────────────────────────────┘
                     │ In-process call
┌────────────────────▼────────────────────────────────────────┐
│  ORCHESTRATION LAYER (LangGraph)                            │
├─────────────────────────────────────────────────────────────┤
│  ✓ Node sequencing and state transitions                     │
│  ✓ User interrupt handling and resumption                    │
│  ✓ Routing (which branch, which node next)                   │
│  ✓ Calls to services for business operations                │
│  ✗ Never: Persistence (uses service layer)                  │
│  ✗ Never: Multiple responsibilities per node (SRP)          │
│  ✗ Never: Direct GitHub/validation operations               │
│  Reference: TAS T2, T3, CON-LG-1, CON-LG-2                  │
└────────────────────┬────────────────────────────────────────┘
                     │ In-process call
┌────────────────────▼────────────────────────────────────────┐
│  SERVICE LAYER (Business Logic)                             │
├─────────────────────────────────────────────────────────────┤
│  Owns:                                                      │
│  • ValidationService (validation logic, rule evaluation)    │
│  • DraftService (draft state management, persistence)       │
│  • KnowledgeService (derivation, registry loading)          │
│  • PRService (GitHub integration, PR creation)              │
│  • SessionService (session lifecycle)                       │
│  • GitHubService (repository reads, GitHub API)             │
│  • TerraformService (CLI execution, validation)             │
│  • RepositoryKnowledgeProvider (repo fact extraction)       │
│                                                              │
│  ✓ All business rules implemented here                      │
│  ✓ Calls repositories and knowledge layer                   │
│  ✓ External system integration (GitHub, Terraform CLI)      │
│  ✓ Error handling and retries                               │
│  ✗ Never: Direct persistence logic (delegates to repos)     │
│  ✗ Never: UI concerns or rendering                          │
│  ✗ Never: Workflow orchestration (LangGraph owns)           │
│  Reference: BR-* (business rules), §12 (API calls)          │
└────────────────────┬────────────────────────────────────────┘
                     │ In-process call
┌────────────────────▼────────────────────────────────────────┐
│  KNOWLEDGE LAYER (Configuration & Rules)                    │
├─────────────────────────────────────────────────────────────┤
│  Owns:                                                      │
│  • Registry loaders (JSON registries, hot-reload)           │
│  • Validation rules (TR-*, JR-*, TF-* rules)                │
│  • Derivation rules (repo patterns, defaults)               │
│  • Template engines (Terraform template rendering)          │
│  • Providers (repository knowledge extraction)              │
│  • Derivers (value computation engines)                     │
│  • Validators (rule application)                            │
│                                                             │
│  ✓ All configuration centralized in JSON registries         │
│  ✓ Rules are additive without code changes                  │
│  ✓ No persistence; all reads from registries or repo        │
│  ✓ Thread-safe caching of registry data                     │
│  ✗ Never: Direct DB access (read-only knowledge)            │
│  ✗ Never: Service-level decisions (moves to services)       │
│  Reference: §5, TAS T5, BR-A-10                             │
└────────────────────┬────────────────────────────────────────┘
                     │ In-process call
┌────────────────────▼────────────────────────────────────────┐
│  REPOSITORY LAYER (Data Access / CRUD)                      │
├─────────────────────────────────────────────────────────────┤
│  Owns:                                                      │
│  • UserRepository (users table CRUD)                        │
│  • SessionRepository (sessions table CRUD)                  │
│  • DraftRepository (drafts table CRUD + coordination)       │
│  • DraftGlueJobRepository (draft_glue_jobs CRUD)            │
│  • DraftFileRepository (draft_files CRUD)                   │
│  • SnapshotRepository (snapshots CRUD)                      │
│  • ValidationReportRepository (validation_reports CRUD)     │
│  • PRMetadataRepository (pr_metadata CRUD)                  │
│                                                              │
│  ✓ CRUD-only logic (no business rules)                      │
│  ✓ Transaction management & optimistic locking              │
│  ✓ Entity relationship coordination                         │
│  ✗ Never: Business logic (validation, derivation)           │
│  ✗ Never: External system calls                             │
│  ✗ Never: Direct service-level decisions                    │
│  Reference: §11, TAS T6, TAS T8                             │
└────────────────────┬────────────────────────────────────────┘
                     │ In-process call
┌────────────────────▼────────────────────────────────────────┐
│  PERSISTENCE LAYER (PostgreSQL + Redis)                     │
├─────────────────────────────────────────────────────────────┤
│  ✓ PostgreSQL: users, sessions, drafts, validation history  │
│  ✓ Redis: LangGraph checkpoints, session state cache        │
│  ✗ Never: Application logic at DB layer                     │
│  Reference: §11, §17 (backup strategy)                      │
└─────────────────────────────────────────────────────────────┘
```

### Layer Lifecycle Phases

| Layer | Phase 1 | Phase 2 | Phase 3+ | Notes |
|-------|---------|---------|----------|-------|
| **Frontend** | Skeleton (pages, routes) | Components, state | Polish, recovery | See §13 |
| **API** | Basic endpoints | Full contract | Versioning deferred | See §12 |
| **LangGraph** | Node stubs | Full nodes, graph | Recovery, complexity | See §3 (TAS T2, T3) |
| **Services** | Service stubs | Business logic | Optimization | See §2, §6-10 |
| **Knowledge** | Registry stubs | Derivation engine | Hot-reload, versioning | See §5 |
| **Repositories** | Schema + stubs | CRUD ops, locking | Optimization | See §11 |
| **Database** | Schema migrations | Data layer operations | Backup, retention | See §11 |
| **Shared** | Core types, exceptions | Validators, formatters | Extension | See §18 |
| **Prompts** | System prompt | Node prompts | Recovery, refinement | See §14 |
| **Tests** | Unit test stubs | Integration tests | E2E, recovery, failure | See §15 |
| **Docker** | Compose, Dockerfiles | Build automation | Registry, deployment | Deferred |
| **Scripts** | Validation helpers | CI/CD scripts | Performance testing | Deferred |

---

## 4. DEPENDENCY RULES (FROZEN)

### Allowed Dependency Directions

```
TIER 0 (No outbound dependencies except self)
  ↑
SHARED (core/, types.py, constants.py, exceptions.py)
  ↑
MODELS (domain entities; depends on SHARED only)
  ↑
KNOWLEDGE (registries, derivers; depends on MODELS + SHARED)
  ↑
REPOSITORIES (CRUD layer; depends on MODELS + SHARED, not SERVICES)
  ↑
SERVICES (business logic; depends on REPOSITORIES + KNOWLEDGE + SHARED)
  ↑
LANGGRAPH NODES (orchestration; depends on SERVICES)
  ↑
API LAYER (endpoints; depends on LANGGRAPH, SERVICES, SCHEMAS)
  ↑
FRONTEND (UI; depends on API contract only)
```

### Concrete Import Rules

| Import | Allowed? | Reason | Exception |
|--------|----------|--------|-----------|
| `repositories/` → `services/` | **NO** | Inversion of control; repositories are data access, services are logic | Explicit case: DraftRepository may coordinate other repositories (child) |
| `services/` → `repositories/` | **YES** | Services orchestrate repository operations | Standard pattern |
| `services/` → `knowledge/` | **YES** | Services use knowledge layer for derivation/validation | Standard pattern |
| `services/` → `api/` | **NO** | API layer calls services; not reverse | Violates dependency inversion |
| `langgraph/nodes/` → `services/` | **YES** | Nodes call services for business operations | TAS T3 requirement |
| `langgraph/nodes/` → `repositories/` | **NO** | Bypass via services | Violates separation of concerns |
| `api/` → `langgraph/` | **YES** | API routes to orchestrator | CON-API-1 requirement |
| `api/` → `services/` | **YES** | Direct service calls for auth, session mgmt | Limited scope, documented cases only |
| `frontend/` → `api/` | **YES** | Frontend consumes API | Standard client-server pattern |
| `frontend/` → backend internals | **NO** | Never direct; all via HTTP API | Security + coupling |
| `models/` → anything | **NO** | Models are leaf nodes; no dependencies except SHARED | Circular dependency prevention |
| `core/` → anything | **NO** | Core has zero dependencies; universal leaf | Architecture constraint |

### Circular Dependency Prevention

| Scenario | Status | Why |
|----------|--------|-----|
| Service A → Service B → Service A | ❌ FORBIDDEN | Refactor into shared dependency or new coordinator service |
| Repo A (users) → Repo B (sessions) → Repo A | ❌ FORBIDDEN | Use neutral coordinator (UnitOfWork) or split models |
| Model X → Model Y (bidirectional) | ❌ FORBIDDEN | Use navigation from one side only or separate aggregates |
| Knowledge → Repos → Knowledge | ❌ FORBIDDEN | Knowledge is read-only; repos don't call it back |

**Enforcement:** Linter rule (import_linter via `scripts/validate_architecture.py`) on every commit.

---

## 5. IMPORT RESTRICTIONS (LOCKED)

### By Module

#### **backend/core/**
- **Exports:** Types, exceptions, constants (all shared)
- **Imports from:** NOTHING (zero dependencies)
- **Imports allowed from:** All layers

#### **backend/models/**
- **Exports:** Domain entities (User, Session, Draft, etc.)
- **Imports from:** core/ only
- **Imports allowed from:** repositories/, services/, schemas/, knowledge/

#### **backend/schemas/**
- **Exports:** Pydantic DTOs (request/response shapes)
- **Imports from:** core/, models/
- **Imports allowed from:** api/
- **Never imported by:** services/, repositories/, langgraph/

#### **backend/repositories/**
- **Exports:** Repository classes (UserRepo, DraftRepo, etc.)
- **Imports from:** models/, core/, database/
- **Imports allowed from:** services/, langgraph/ (via services only)
- **Never imports:** services/, api/, knowledge/ (except configuration constants)

#### **backend/services/**
- **Exports:** Service classes (ValidationService, DraftService, etc.)
- **Imports from:** repositories/, knowledge/, core/, models/, database/
- **Imports allowed from:** api/, langgraph/
- **Never imports:** frontend/, langgraph/ implementation (only calls via orchestration)

#### **backend/api/**
- **Exports:** FastAPI app, endpoints, middleware
- **Imports from:** services/, schemas/, core/, langgraph/, models/
- **Imports allowed from:** NOTHING (top-level entry point)
- **Never imports:** repositories/ (all via services)

#### **backend/database/**
- **Exports:** SQLAlchemy engine, session factory, base
- **Imports from:** core/ only
- **Imports allowed from:** repositories/, models/

#### **langgraph/nodes/**
- **Exports:** Node implementations (async functions)
- **Imports from:** services/, core/, models/
- **Imports allowed from:** api/ (for request routing only)
- **Never imports:** repositories/, database/, frontend/

#### **langgraph/state/**
- **Exports:** State model definitions
- **Imports from:** core/, models/
- **Imports allowed from:** nodes/, api/
- **Never imports:** services/ (state is pure data)

#### **langgraph/routing/**
- **Exports:** Routing logic, transition guards
- **Imports from:** state/, core/
- **Imports allowed from:** nodes/, api/

#### **knowledge/**
- **Exports:** Registry loaders, derivers, validators, template engines
- **Imports from:** core/, models/
- **Imports allowed from:** services/, langgraph/
- **Never imports:** repositories/, database/, api/ (no side effects)

#### **shared/**
- **Exports:** Constants, validators, formatters, types
- **Imports from:** core/ only
- **Imports allowed from:** ALL (universal leaf)

#### **prompts/**
- **Exports:** Prompt templates, loader
- **Imports from:** core/, shared/
- **Imports allowed from:** langgraph/nodes/
- **Never imports:** services/, repositories/, api/ (configuration, not logic)

#### **tests/**
- **Exports:** Test fixtures, helpers
- **Imports from:** Everything (test-time only)
- **Imports allowed from:** CI/CD scripts only
- **Never in production:** Test code must not be packaged

#### **scripts/**
- **Exports:** Validation helpers, CI/CD utilities
- **Imports from:** core/, models/, (read-only repo analysis)
- **Imports allowed from:** CI/CD systems only
- **Never in production:** Scripts run offline only

#### **frontend/** (React+Vite)
- **Exports:** React components, hooks, stores
- **Imports from:** API contracts only (via HTTP)
- **Never imports:** backend code, domain models, services

---

## 6. FILE RESPONSIBILITIES

### Backend Folder Structure

| File/Folder | Responsibility | Imports From | Imported By | Phase |
|-------------|----------------|--------------|-------------|-------|
| **backend/main.py** | FastAPI app initialization, router setup, exception handlers | core/, api/ | External (CLI) | P1 |
| **backend/core/*** | Shared types, exceptions, constants | Nothing | All layers | P1 |
| **backend/models/*** | Domain entities (ORM + Pydantic) | core/, database/ | repos/, services/, schemas/ | P2 |
| **backend/schemas/*** | Request/response DTOs | core/, models/ | api/ | P5 |
| **backend/api/routes/agent.py** | POST /agent/message endpoint | langgraph/, services/, schemas/ | main.py | P5 |
| **backend/api/routes/auth.py** | OAuth endpoints | services/, schemas/, core/ | main.py | P5 |
| **backend/api/routes/sessions.py** | Session list/detail endpoints | services/, schemas/ | main.py | P5 |
| **backend/api/middleware/auth.py** | OAuth token validation | services/, core/ | main.py | P5 |
| **backend/services/draft_service.py** | Draft lifecycle & mutations | repositories/, database/, knowledge/ | langgraph/, api/ | P3 |
| **backend/services/validation_service.py** | Validation rule engine | knowledge/, repositories/, core/ | langgraph/, api/ | P3 |
| **backend/services/knowledge_service.py** | Registry loading, derivation orchestration | knowledge/, repositories/ | langgraph/, api/ | P3 |
| **backend/services/pr_service.py** | PR creation, branch management | repositories/, services/github/ | langgraph/, api/ | P8 |
| **backend/services/github_service.py** | GitHub API wrapper | core/ | services/ | P4 |
| **backend/services/terraform_service.py** | Terraform CLI execution | core/, shared/ | services/ | P7 |
| **backend/repositories/base.py** | Repository pattern base class | models/, core/ | All repos | P2 |
| **backend/repositories/draft_repository.py** | Draft CRUD + child coordination | models/, database/, base.py | services/ | P2 |
| **backend/repositories/user_repository.py** | User CRUD | models/, database/ | services/ | P2 |
| **backend/repositories/session_repository.py** | Session CRUD | models/, database/ | services/ | P2 |
| **backend/database/engine.py** | SQLAlchemy engine factory | core/ | repositories/, session.py | P1 |
| **backend/database/session.py** | SQLAlchemy session factory | engine.py, core/ | repositories/ | P1 |
| **backend/database/base.py** | Declarative base for ORM | core/ | models/ | P2 |
| **backend/database/migrations/*** | Alembic migration scripts | models/ (as reference) | Alembic CLI | P2 |

### Frontend Folder Structure

| File/Folder | Responsibility | Imports From | Imported By | Phase |
|-------------|----------------|--------------|-------------|-------|
| **frontend/src/pages/ChatPage.tsx** | Main chat layout (3-pane) | components/, services/, hooks/ | routes | P6 |
| **frontend/src/pages/LoginPage.tsx** | GitHub OAuth login UI | services/auth, hooks/ | routes | P5 |
| **frontend/src/components/Chat/MessageList.tsx** | Message display loop | types/, utils/, hooks/ | ChatPage | P6 |
| **frontend/src/components/Chat/MessageInput.tsx** | User input form | types/, services/ | ChatPage | P6 |
| **frontend/src/components/Chat/AgentMessage.tsx** | Renders agent response types (text, form, validation, etc.) | types/, components/widgets/ | MessageList | P6 |
| **frontend/src/components/workspace/ReviewWorkspace.tsx** | Draft review panel | types/, services/, hooks/ | ChatPage | P6 |
| **frontend/src/services/api.ts** | HTTP client (Axios/Fetch wrapper) | types/ | All components | P5 |
| **frontend/src/services/auth.ts** | GitHub OAuth flow | None (external APIs) | LoginPage, hooks/ | P5 |
| **frontend/src/hooks/useAgentStream.ts** | WebSocket/SSE listener for agent responses | types/, services/api | components/ | P6 |
| **frontend/src/hooks/useDraftState.ts** | Local draft summary state | types/, services/api | components/ | P6 |
| **frontend/src/store/sessionStore.ts** | Session history state (Zustand) | types/ | components/, hooks/ | P6 |
| **frontend/src/types/index.ts** | TypeScript interfaces (API contracts) | None | All frontend code | P5 |

### Knowledge Folder Structure

| File/Folder | Responsibility | Imports From | Imported By | Phase |
|-------------|----------------|--------------|-------------|-------|
| **knowledge/registries/validation_rules.json** | Validation rule definitions (TR-*, JR-*, TF-*) | None (data file) | validators/ | P3 |
| **knowledge/registries/terraform_templates.json** | Terraform output templates (locals, glue modules) | None (data file) | template_engine/ | P3 |
| **knowledge/registries/repo_patterns.json** | Repository structure patterns | None (data file) | repository_knowledge_provider/ | P3 |
| **knowledge/registries/constants_registry.json** | Default values (worker types, glue versions, etc.) | None (data file) | derivers/ | P3 |
| **knowledge/loader.py** | Registry loading + caching | core/, shared/ | service/ | P3 |
| **knowledge/derivers/value_engine.py** | Derived value computation | registries, models/ | services/ | P3 |
| **knowledge/validators/validation_engine.py** | Validation rule application | registries, core/ | services/ | P3 |
| **knowledge/providers/repository_knowledge_provider.py** | Extract facts from GitHub repo | core/, (GitHub API via service) | knowledge_service/ | P3 |
| **knowledge/templates/template_engine.py** | Render Terraform from templates | registries, models/ | services/ | P3 |

### LangGraph Folder Structure

| File/Folder | Responsibility | Imports From | Imported By | Phase |
|-------------|----------------|--------------|-------------|-------|
| **langgraph/state/workflow_state.py** | Central state model definition | core/, models/ | nodes/, checkpoint/ | P4 |
| **langgraph/graph.py** | Graph builder, node registration, routing setup | nodes/, state/, core/ | api/routes/agent.py | P4 |
| **langgraph/nodes/github_oauth.py** | OAuth node (authenticate user) | services/, state/, core/ | graph.py | P4 |
| **langgraph/nodes/session_manager.py** | Session creation/restore node | services/, state/ | graph.py | P4 |
| **langgraph/nodes/environment.py** | Environment selection node (dev/prod) | services/, state/ | graph.py | P4 |
| **langgraph/nodes/operation.py** | Operation menu router | services/, state/, core/ | graph.py | P4 |
| **langgraph/nodes/source_type.py** | Source type selection (Kafka/JDBC/etc.) | state/, core/ | graph.py | P4 |
| **langgraph/nodes/source_system.py** | Source system dropdown + new entry | services/, state/ | graph.py | P4 |
| **langgraph/nodes/schema_grain.py** | Schema grain free-text input | state/, core/ | graph.py | P4 |
| **langgraph/nodes/topic_validation.py** | Topic existence check | services/, state/, core/ | graph.py | P4 |
| **langgraph/nodes/duplicate_job_validation.py** | Job uniqueness check | services/, state/ | graph.py | P4 |
| **langgraph/nodes/knowledge_derivation.py** | Derive all config values | services/, state/ | graph.py | P4 |
| **langgraph/nodes/draft_workspace.py** | Persist changes to draft | services/, state/ | graph.py | P4 |
| **langgraph/nodes/review_workspace.py** | Present draft for review | services/, state/ | graph.py | P6 |
| **langgraph/nodes/terraform_validation.py** | Run Terraform validation | services/, state/ | graph.py | P7 |
| **langgraph/nodes/approval.py** | Final PR confirmation | state/, core/ | graph.py | P7 |
| **langgraph/nodes/pr_creation.py** | Create pull request | services/, state/ | graph.py | P8 |
| **langgraph/nodes/out_of_scope.py** | Handle unrecognized intents | state/, core/ | graph.py | P4 |
| **langgraph/routing/transition_guards.py** | Guard conditions for state transitions | state/, core/ | graph.py | P4 |
| **langgraph/checkpoint/redis_checkpointer.py** | LangGraph checkpoint persistence (Redis) | core/ | graph.py | P4 |

### Database Folder Structure

| File/Folder | Responsibility | Imports From | Imported By | Phase |
|-------------|----------------|--------------|-------------|-------|
| **database/engine.py** | SQLAlchemy engine configuration | core/ | repositories/, session.py | P1 |
| **database/session.py** | SQLAlchemy sessionmaker factory | engine.py | repositories/ | P1 |
| **database/base.py** | Declarative base + common mixins | core/ | models/ | P2 |
| **database/unit_of_work.py** | UnitOfWork pattern (transaction coordinator) | repositories/ | services/ | P2 |
| **database/migrations/env.py** | Alembic environment | None | Alembic CLI | P2 |
| **database/migrations/versions/001_initial_schema.py** | Create users, sessions, drafts, snapshots, etc. | None (SQL) | Alembic CLI | P2 |
| **database/migrations/versions/002_add_jobs_table.py** | draft_glue_jobs table | None (SQL) | Alembic CLI | P2 |
| **database/migrations/versions/003_add_files_table.py** | draft_files table | None (SQL) | Alembic CLI | P2 |
| **database/migrations/versions/004_add_validation_reports.py** | validation_reports table | None (SQL) | Alembic CLI | P2 |
| **database/migrations/versions/005_add_pr_metadata.py** | pr_metadata table | None (SQL) | Alembic CLI | P2 |
| **database/migrations/versions/006_add_indexes.py** | Performance indexes | None (SQL) | Alembic CLI | P2 |
| **database/migrations/versions/007_add_audit_columns.py** | created_at, updated_at, version columns on all tables | None (SQL) | Alembic CLI | P2 |

### Prompts Folder Structure

| File | Responsibility | Imports From | Imported By | Phase |
|------|----------------|--------------|-------------|-------|
| **prompts/system_prompt.txt** | Global system instructions for LLM agents (frozen) | None (text) | loader.py, LLM calls | P1 |
| **prompts/node_prompts/environment_node.txt** | Environment selection prompt | None (text) | langgraph/nodes/environment.py | P4 |
| **prompts/node_prompts/operation_node.txt** | Operation menu prompt template (dynamic) | None (text) | langgraph/nodes/operation.py | P4 |
| **prompts/node_prompts/source_system_node.txt** | Source system selection prompt | None (text) | langgraph/nodes/source_system.py | P4 |
| **prompts/node_prompts/schema_grain_node.txt** | Schema grain input prompt | None (text) | langgraph/nodes/schema_grain.py | P4 |
| **prompts/node_prompts/knowledge_derivation_node.txt** | Derivation result presentation prompt | None (text) | langgraph/nodes/knowledge_derivation.py | P4 |
| **prompts/node_prompts/out_of_scope_node.txt** | Out-of-scope redirect prompt | None (text) | langgraph/nodes/out_of_scope.py | P4 |
| **prompts/node_prompts/approval_node.txt** | PR confirmation prompt | None (text) | langgraph/nodes/approval.py | P7 |
| **prompts/loader.py** | Load + cache prompts from files | core/, shared/ | LLM services | P4 |
| **prompts/template_variables.py** | Variable substitution for dynamic prompts | shared/ | loader.py | P4 |

### Config Folder Structure

| File | Responsibility | Imports From | Imported By | Phase |
|------|----------------|--------------|-------------|-------|
| **.env.example** | Environment variable template (git-tracked reference) | None | Developer | P1 |
| **config/settings.py** | Pydantic settings loader from env | core/, (Pydantic) | main.py, database/ | P1 |
| **config/secrets.py** | Secret reference abstraction (never raw values) | core/, settings/ | services/ | P1 |

### Shared Folder Structure

| File/Folder | Responsibility | Imports From | Imported By | Phase |
|-------------|----------------|--------------|-------------|-------|
| **shared/types.py** | Common type aliases, enums | None | All layers | P1 |
| **shared/constants.py** | Application-wide constants (env names, defaults) | core/ | All layers | P1 |
| **shared/exceptions.py** | Custom exception hierarchy | core/ | All layers | P1 |
| **shared/validators.py** | Common validation functions (not rules, but logic) | core/ | services/, schemas/ | P2 |
| **shared/formatters.py** | String formatting, date utilities | core/ | All layers | P2 |

### Tests Folder Structure

| File/Folder | Responsibility | Imports From | Imported By | Phase |
|-------------|----------------|--------------|-------------|-------|
| **tests/conftest.py** | Pytest fixtures (DB, fixtures, mocks) | Everything (test-time) | Test files | P10 |
| **tests/unit/test_services.py** | Unit tests for services | services/ + mocks | CI/CD | P10 |
| **tests/unit/test_repositories.py** | Unit tests for CRUD | repositories/ + mocks | CI/CD | P10 |
| **tests/integration/test_draft_flow.py** | Draft creation → mutation → snapshot flow | services/, repositories/ | CI/CD | P10 |
| **tests/integration/test_validation.py** | Validation rule application | services/validation/ | CI/CD | P10 |
| **tests/contract/test_api_contract.py** | API request/response shapes | schemas/, types/ | CI/CD | P10 |
| **tests/conversation/test_create_job_flow.py** | End-to-end conversation: create Glue Job | langgraph/, services/ | CI/CD | P10 |
| **tests/recovery/test_session_recovery.py** | Session restore after interrupt | services/, repositories/ | CI/CD | P9 |
| **tests/failure/test_github_down.py** | Behavior when GitHub API unavailable | services/github/ + mocks | CI/CD | P9 |
| **tests/fixtures/sample_repositories/** | Git repo fixtures for testing | None (data files) | Contract tests | P10 |

### Docker Folder Structure

| File | Responsibility | Imports From | Imported By | Phase |
|------|----------------|--------------|-------------|-------|
| **docker/Dockerfile.backend** | Backend image build (Python, dependencies) | None (build artifact) | docker-compose | P1 |
| **docker/Dockerfile.frontend** | Frontend image build (Node, React build) | None (build artifact) | docker-compose | P1 |
| **docker-compose.dev.yml** | Local dev stack (app + Postgres + Redis) | None (orchestration) | Developer CLI | P1 |
| **docker-compose.prod.yml** | Production compose (if used) | None (orchestration) | Deployment | Deferred |

### Scripts Folder Structure

| File | Responsibility | Imports From | Imported By | Phase |
|------|----------------|--------------|-------------|-------|
| **scripts/validate_architecture.py** | Import linter (enforce dependency rules) | models/ (static analysis) | CI/CD pre-commit | P1 |
| **scripts/format_code.sh** | Black + Prettier formatting | None | CI/CD | P1 |
| **scripts/run_tests.sh** | Test discovery and execution | None | CI/CD | P1 |
| **scripts/db_migrate.sh** | Alembic migration runner | None | Deployment | P2 |

### Docs Folder Structure

| File/Folder | Responsibility | Status | Locked |
|-------------|----------------|--------|--------|
| **doc/01_REPOSITORY_MASTER_STRUCTURE.md** | Folder structure, file inventory, versioning | Final v2.0 | ✅ YES |
| **doc/02_BACKEND_MODULE_ARCHITECTURE.md** | Layer responsibilities, import rules | Final | ✅ YES |
| **doc/CPRS_v1.0.md** | Product requirements (AC-1 through AC-14) | Final v1.0 | ✅ YES |
| **doc/Implementation Specification.md** | Workflow steps, dataflow details | Final | ✅ YES |
| **doc/MIF_Implementation_Bible.md** | 18-section implementation specification (sections 1–18) | FINAL DRAFT v1.0 | ✅ YES |
| **doc/TAS_reference.md** | Technical architecture summary | Final | ✅ YES |
| **doc/mif-glue-job-creation-terraform-script-process.md** | Glue job configuration patterns | Final | ✅ YES |

---

## 7. FROZEN DECISIONS

### 7.1 Architecture Pattern: Hexagonal (Ports & Adapters)

**Decision:** MIF Copilot uses hexagonal architecture.

**Why:**  
- Isolates business logic (services) from external systems and UI concerns
- Enforces dependency inversion (high-level modules don't depend on low-level details)
- Enables testing in isolation (services can be tested without API or DB)

**Implication:**
- API layer is an adapter (port = HTTP)
- Repository layer is an adapter (port = SQL database)
- Knowledge layer is internal (configurable, not external)
- Frontend is a client adapter (port = HTTP client)

**Constraints:**
- Never mix adapter concerns (API logic + business logic = forbidden)
- Repositories must only do CRUD; business rules go to services
- Services orchestrate; they don't know UI or storage details

**Reference:** TAS T2, DOC-02_BACKEND_MODULE_ARCHITECTURE

### 7.2 Design Pattern: Single Responsibility (SRP)

**Decision:** Every class, module, and file has exactly one reason to change.

**Examples:**
- **ValidationService** changes only if validation logic rules change
- **DraftRepository** changes only if CRUD operations or schema change
- **EnvironmentNode** changes only if environment selection flow changes
- **TopicValidationNode** changes only if topic validation rules change

**Why:**
- Reduces cognitive load during maintenance
- Enables parallel development (teams work on independent services)
- Minimizes blast radius of changes

**Enforcement:**
- Code review checklist (see §18.5)
- Automated linting: if a class imports >3 dependencies, it may be doing too much

**Reference:** CON-LG-1

### 7.3 Pattern: Repository Pattern for Persistence

**Decision:** All database access goes through repository classes.

**Examples:**
- UserRepository (not services calling SQLAlchemy directly)
- DraftRepository (coordinates draft + jobs + files + snapshots)
- SessionRepository

**Why:**
- Centralizes query logic
- Enables in-memory test stubs (mock repositories)
- Swappable persistence layer (could replace Postgres with MongoDB if needed)

**Constraints:**
- Repositories are CRUD-only; no business logic
- Transactions are a repository concern (e.g., UnitOfWork pattern)
- Services call repositories; never the reverse

**Reference:** §11

### 7.4 Pattern: Service Layer for Business Logic

**Decision:** All business rules live in services.

**Examples:**
- ValidationService (applies validation rules)
- DraftService (manages draft state machine)
- KnowledgeService (orchestrates derivation)

**Why:**
- Single source of truth for business rules
- Services can be tested without UI or API
- Easy to share logic across multiple endpoints/nodes

**Constraints:**
- Services depend on repositories and knowledge layer
- Services do NOT depend on API or presentation layer
- Services are called from LangGraph nodes or API endpoints

**Reference:** §2, §3

### 7.5 Pattern: Knowledge Layer for Configuration

**Decision:** All rules, templates, and default values live in the knowledge layer.

**Consists of:**
- JSON registries (validation_rules.json, terraform_templates.json, repo_patterns.json, constants_registry.json)
- Registry loaders (with caching)
- Derivation engines (compute configuration values)
- Template engines (render Terraform)
- Validators (apply rules to inputs/values)

**Why:**
- New rules added without code changes (JSON only)
- Registries are versioned with the application
- Hot-reloadable configuration
- Single source of truth for what's derivable

**Constraints:**
- Knowledge layer does NOT persist to database
- Knowledge layer does NOT read/write external systems (except repo for extracting facts)
- Knowledge layer is read-only from services' perspective

**Reference:** §5, TAS T5

### 7.6 Pattern: Source-of-Truth Hierarchy

**Decision:** When sources conflict, resolve by this precedence:

1. **GitHub repository (live)** — always correct; source system existence, topic existence, job names
2. **Draft workspace (PostgreSQL)** — current working state; overrides knowledge base defaults
3. **Knowledge registries (JSON)** — defaults, rules, patterns
4. **LangGraph state (Redis)** — workflow position only; never business data

**Why:**
- Repo is the deployable artifact; it's the authority on what exists
- Draft is the user's current intent; it's authoritative until committed
- Registries provide sensible defaults but don't override reality
- LangGraph state is ephemeral; it's for workflow orchestration, not persistence

**Implication:** If GitHub says a source doesn't exist but the knowledge base says it does, GitHub wins. The user must create the topic first.

**Reference:** §1.4 (MIF Implementation Bible), BR-A-10

### 7.7 Pattern: Immutable Snapshots for Draft History

**Decision:** Every mutation of a draft creates an immutable snapshot.

**Mechanism:**
- User adds a job → snapshot created before add → snapshot created after add
- User undoes → previous snapshot restored → new snapshot created from restoration
- Snapshots are never modified; only read and copied

**Why:**
- Enables reliable undo (always has a previous state)
- Audit trail (all mutations recorded)
- Recovery (if system crashes, latest snapshot can be restored)

**Constraints:**
- Snapshots are stored in PostgreSQL (not ephemeral)
- Undo only goes back one level (not a full version control system)
- Snapshots have TTL (retention policy CQ-10)

**Reference:** §7 (MIF Implementation Bible), FR-W-3

### 7.8 Pattern: One Commit, One PR Rule

**Decision:** Each pull request contains exactly one commit.

**Why:**
- Simplifies PR review (one logical change)
- Consistent with single-responsibility changes
- Easier to revert if needed
- Aligns with GitOps best practices

**Implication:** All file operations for a session must be squashed into a single commit before PR creation. Users can accumulate multiple operations (create job + edit file) in the draft; all are committed together.

**Reference:** BR-S-1, BR-S-2, §10 (GitHub Integration Specification)

### 7.9 Pattern: Pessimistic Session Workflow (No Concurrent Edits)

**Decision:** One user = one session. One session = one active draft. Concurrent edits are not supported.

**Why:**
- Simplifies state management (no merge conflicts in draft)
- Matches the conversational UX (user talks to agent sequentially)
- Reduces database transaction complexity

**Implication:** If user opens the same session in two browser tabs, the second tab sees stale state. User must refresh or start a new session.

**Reference:** FR-W-2, FR-H-5

### 7.10 Pattern: Validation Before Derivation

**Decision:** Topic and duplicate-job validation happen BEFORE knowledge derivation.

**Order:**
1. Topic validation (does topic exist in repo?)
2. Duplicate-job validation (is the derived job name already in use?)
3. Knowledge derivation (compute all config values)

**Why:**
- Fail fast before expensive derivation
- Don't derive values for invalid inputs
- User gets immediate feedback on blocking issues

**Implication:** If topic validation fails, user is blocked and must change inputs; no derivation occurs.

**Reference:** BR-A-8, §2 (MIF Implementation Bible)

### 7.11 Pattern: Explicit Approval Gate Before PR

**Decision:** User must explicitly confirm "Raise Pull Request?" before any PR is created.

**Why:**
- Prevents accidental PRs from repeated clicks
- Gives user final chance to review
- Satisfies AC-7 (no duplicate PRs from rapid clicks)

**Constraint:** Only one confirmation total in the session; no "Do you want to continue?" prompts elsewhere.

**Reference:** FR-S-4, AC-7

### 7.12 Pattern: Terraform Validation Gate (Gated by CQ-13b)

**Decision:** Terraform validation runs before PR creation and outcomes are shown to user.

**CQ-13b:** Is passing Terraform validation REQUIRED before PR, or just informational?

**Current implementation (pending CQ-13b):**
- Terraform validation always runs
- Outcomes shown to user
- User can fix and re-validate
- PR creation blocked if CQ-13b = "required"; allowed if CQ-13b = "informational"

**Reference:** FR-Q-2, FR-Q-3, CQ-13b

### 7.13 Pattern: Rate Limiting on Agent Endpoint

**Decision:** POST /agent/message is rate-limited per session.

**Why:**
- Prevents abuse (rapid fire requests)
- Protects LLM API quota
- Fair usage across concurrent sessions

**Constraint:** Rate limit is enforced at API middleware layer; no business logic involved.

**Reference:** §12.5 (API error handling), §17.2 (monitoring)

### 7.14 Pattern: Optimistic Locking for Concurrent Safety

**Decision:** Drafts and sessions use optimistic locking (version field + WHERE clause).

**Mechanism:**
- Every draft and session has a `version` (integer, incremented on update)
- UPDATE includes `WHERE version = expected_version`
- If mismatch, transaction fails; client retries with fresh read

**Why:**
- Prevents lost updates if two concurrent requests modify the same draft
- Acceptable for this use case (single-session model reduces concurrency)
- Simpler than pessimistic locking

**Reference:** §11.5

### 7.15 Pattern: Fail-Safe GitHub Operations

**Decision:** All GitHub API operations include retry logic with exponential backoff.

**Why:**
- GitHub API is external and subject to transient failures
- Operations are idempotent (safe to retry)
- User experience improves (hidden retries feel seamless)

**Constraint:** After max retries, user is informed of connectivity issue; no silent failures.

**Reference:** §10 (GitHub Integration), §17.1 (Observability)

### 7.16 Pattern: No Secrets in Logs

**Decision:** Tokens, database passwords, GitHub secrets are never logged.

**Implementation:**
- Use `SecretStr` from Pydantic (masks on serialization)
- Log filtering in structured logging (redact known secret fields)
- Audit logging masks secrets

**Why:**
- Security best practice (prevents credential leaks in log stores)
- Compliance requirement (GDPR, SOC2, etc.)

**Reference:** SEC-1, §17 (Production Readiness)

### 7.17 Pattern: Async-First Architecture

**Decision:** Backend uses async/await (FastAPI + SQLAlchemy AsyncSession).

**Why:**
- Better resource utilization (single thread handles many requests)
- Non-blocking I/O (GitHub API, database queries don't block each other)
- Scales horizontally without thread pool explosion

**Constraint:** All service calls are async; blocking calls (Terraform CLI) are executed in thread pool.

**Reference:** §1.2 (System Context), Core technologies

### 7.18 Pattern: Content Negotiation (Frontend-Backend Contract)

**Decision:** API uses JSON exclusively. No XML, no form-encoded data.

**Why:**
- Standard for REST APIs
- Simple to deserialize (Pydantic)
- Frontend can use standard `fetch()` / Axios

**Reference:** §12 (API Specification)

---

## 8. KNOWN CQ / IMPLEMENTATION GAPS

All Clarification Questions from CPRS v1.0 and MIF Implementation Bible are listed below **exactly as stated**. These are **NOT resolved**; they are **PRESERVED** for future decision gates.

### Tier 0: Blockers (Multiple sections depend on resolution)

| CQ | Question | Blocks sections | Why unresolved |
|----|----------|-----------------|-----------------|
| **CQ-01** | Which review fields are user-editable vs read-only? Per-field classification needed. | §8 (Review Workspace), §13 (Frontend), §14 (Prompts), AC-13 (acceptance criteria) | Design choice deferred pending stakeholder input. Different field editability strategies have different UX costs. |
| **CQ-14** | For `prod` environment, which repository folder/file is checked for topic validation? Spec uses `confluent_minerva_<env>/topics_<source>.tf` but only `confluent_minerva_dev/` exists; what is the prod pattern? | §3 (TopicValidationNode), §5 (repo_patterns.json), §6 (Repository Navigation), §9 (Topic Validation), §10 (GitHub Integration) | Production infrastructure not yet deployed; pattern unknown. Prod repo may use different folder naming convention. |
| **CQ-15** | Which repository does the agent navigate and raise PRs against? Is `_v3` the same repo (target of PRs) or separate (reference)? Which GitHub org/repo is the target? | §3 (all GitHub nodes), §6 (Navigation), §9 (Validation), §10 (GitHub Integration), §16 (Roadmap phase 1) | Target repository identity deferred pending infrastructure team decision. May vary by environment or org structure. |

### Tier 1: High-impact (block specific sections)

| CQ | Question | Blocks sections | Why unresolved |
|----|----------|-----------------|-----------------|
| **CQ-02** | Topic name: strictly read-only (agent-derived only), or can user edit it after derivation? | §3 (SchemaGrainNode, state model), §8 (Review Workspace field classification), AC-13 | UX decision: does derived field editability extend to topic name itself, or only non-name fields? |
| **CQ-03** | Enterprise Function dropdown: AGTR/FOOD/SPEC? Or AGTR/FOOD/CORP? Or AGTR/FOOD/OTHER? | §5 (constants_registry.json defaults), §8 (Review Workspace dropdown options) | Business domain decision; multiple valid enumerations mentioned across sources. Needs product owner input. |
| **CQ-04** | Maximum number of workers per Glue job: exactly 10, or different per job type? | §5 (DerivedValueEngine defaults), §8 (workers field validation in Review Workspace) | Glue job capacity planning; depends on account quotas and cost policies. May vary by environment. |
| **CQ-05** | Default run mode for new Glue jobs: Manual (no schedule), or Scheduled with default cron? If scheduled, what cron expression and timezone? | §5 (constants_registry.json triggers), §8 (trigger_schedule field display), FR-A-9 (derived values) | Operational decision: does every job run on demand, or do some have default schedules? Timezone affects cron interpretation. |
| **CQ-09** | Diff rendering / change visualization in Review Workspace: Phase-1 or deferred to Phase-2+? | §8 (Review Workspace, FR-W-8 diff display), §13 (frontend DiffViewer component), §15.5 (test cases reference diffs) | UI feature scope; implementation complexity high. Can show summaries in Phase-1; full GitHub-style diffs may be Phase-2. |
| **CQ-13b** | Is passing Terraform validation REQUIRED before PR creation, or is it informational (user can ignore and proceed)? | §3 (ApprovalNode routing), §4 (PR Lifecycle state machine), §8 (Review Workspace gate), AC-14 | Policy decision: stricter gate (catch errors early) vs. permissive (user judgment). Affects user workflow and error rates. |

### Tier 2: Medium-impact (specific features)

| CQ | Question | Blocks sections | Why unresolved |
|----|----------|-----------------|-----------------|
| **CQ-06** | Draft lifecycle state names: DRAFT_EDITING / REVIEW_READY / PR_CREATING / PR_CREATED / ... ? Or different names? | §4 (Draft Lifecycle State Machine), §11 (CHECK constraint on drafts.status) | Engineering decision; multiple valid state machine designs exist. Needs DB schema lock. |
| **CQ-07** | Exact node list and count for LangGraph graph: how many nodes total, and which are uncertain? | §3 (Graph Topology, node list), node specifications | Architecture clarification; CQ notes uncertain nodes (TopicGenerationNode, SessionPersistNode, IntentRouterNode vs OperationNode). Affects graph complexity. |
| **CQ-08** | Authoritative table list and count: exactly 8 tables (users, sessions, drafts, draft_glue_jobs, draft_files, snapshots, validation_reports, pr_metadata), or more? | §11 (Entity Relationships, all table specs) | Data modeling decision; some sources list 8, others suggest 19. Needs agreement on which tables are Phase-1 vs Phase-2+. |
| **CQ-10** | Draft retention and cleanup: how long are completed/abandoned drafts kept? When are old snapshots deleted? | §7 (Snapshot TTL), §17 (Backup and Disaster Recovery) | Operations policy; affects storage costs and archival strategy. No retention policy defined yet. |
| **CQ-11** | Confirm removal of KnowledgeState from graph state model: was it in earlier versions, and is it confirmed gone? | §3 (Graph state shape) | Specification hygiene; ensures state model is minimal and correct. |
| **CQ-12** | Confirm `workspace.defaults` → `derived_values` rename throughout spec: is terminology now consistent? | §3 (state model field names) | Terminology cleanup; ensures implementation uses consistent naming. |

### Tier 3: Phase-1 scope decisions

| CQ | Question | Blocks sections | Why unresolved |
|----|----------|-----------------|-----------------|
| **CQ-A1** | New source system defaults: where do concrete defaults originate (e.g., LH DB naming, Kafka secret pattern, S3 warehouse path)? | §5 (DerivedValueEngine defaults for new sources), §8 (review fields), §10 (PR-created state) | Rules source unclear; may be hardcoded, registry, or repo metadata. Needs clarification before Phase-3. |
| **CQ-A4** | Conflict resolution depth in Phase-1: detection-only (show conflict, let user handle), or full (auto-attempt + manual resolution)? | §3 (ConflictResolutionNode, depth uncertain), §10 (GitHub Integration, conflict handling), §15 (tests for conflict scenarios) | Feature scope decision; full conflict resolution is complex. Phase-1 may only detect and block. |
| **CQ-A5** | Transformer/sink settings in Phase-1: shown in UI for editing, or always defaulted without user visibility? | §8 (Review Workspace fields), §14 (Prompts for transformer config) | UX decision: does user control transformer chain, or is it always automatic? Impacts field list in review. |
| **CQ-A6** | Guardrails for "Modify Existing Files": which files/folders are editable? Are there restrictions (e.g., cannot edit certain Terraform files), or is all navigation allowed? | §6 (Repository Navigation Specification), §9 (Validation for file edits) | Security/UX decision; prevents accidental modifications of protected files. May require allowlist or denylist. |
| **CQ-A7** | Token encryption at rest: is GitHub OAuth token encrypted before storage, or just stored as secret reference? If encrypted, which algorithm? | §10 (Token storage, SEC-4), §17 (Security, token encryption) | Security policy; depends on compliance requirements and key management infrastructure. |
| **CQ-A8** | Performance/scale targets: what are NFR values for response time (p50, p95, p99), active session count, PR creation time? | §15 (Performance testing, PT-01 through PT-05), §17 (Monitoring thresholds) | SLA decision; defines acceptable performance band and monitoring alerts. |
| **CQ-A9** | Post-approval workflow: is full package delivery mandatory (PR + session saved + history updated), or are steps gated (save session only if PR succeeds)? | §16 (Implementation Roadmap, phase 8 exit criteria) | Process design; affects error recovery and session state consistency. |
| **CQ-A2** | Project information cells (cell1.md–cell8.md): are these required reference documents for Phase-1, or reference-only for context? | §5 (if cells contain additional rules), §6 (if cells define patterns) | Documentation scope; if cells contain new rules not in main specs, they must be integrated into knowledge layer. |

---

## 9. ITEMS EXPLICITLY DEFERRED

| Item | Why deferred | Target phase | Reference |
|------|-------------|--------------|-----------|
| **RBAC (Role-Based Access Control)** | Phase-1 assumes single-user per session; no multi-user auth | Phase-2+ | SCOPE-11 |
| **Vault / Secret Rotation** | Manual secrets management acceptable for Phase-1; automatic rotation deferred | Phase-3+ | SEC-3 |
| **OTEL (OpenTelemetry)** | Basic correlation IDs sufficient for Phase-1; full tracing deferred | Phase-3+ | §17 (Observability) |
| **API Versioning** | v1.0 only in Phase-1; versioning strategy deferred | Phase-3+ | §12 |
| **Frontend Build Optimization** | Basic Vite build acceptable; code-splitting and lazy loading deferred | Phase-2+ | §13 |
| **Multi-Repository Support** | Phase-1 targets single repository; multi-repo navigation deferred | Phase-2+ | CQ-15 |
| **Scheduled Job Automation** | EventBridge integration deferred; manual trigger only in Phase-1 | Phase-2+ | §2 (Scheduling) |
| **Data Export/Analytics** | Session export, statistics dashboard deferred | Phase-2+ | CQ-10 |
| **Conflict Resolution (Full)** | Phase-1 detects conflicts; manual resolution UI deferred | Phase-2+ | CQ-A4 |
| **Mobile UI** | Desktop/browser-only in Phase-1; mobile adaptation deferred | Phase-3+ | UX scope |
| **Internationalization (i18n)** | English-only in Phase-1; multi-language support deferred | Phase-3+ | §13 |

---

## 10. ARCHITECTURE LOCK CHECKLIST

This checklist confirms that all major architectural decisions are frozen and documented.

### ✅ Decision Areas Locked

- [x] **Hexagonal architecture pattern** (section 7.1)
- [x] **Layer responsibilities** (section 3)
- [x] **Single Responsibility Principle** (section 7.2)
- [x] **Repository pattern for persistence** (section 7.3)
- [x] **Service layer for business logic** (section 7.4)
- [x] **Knowledge layer for configuration** (section 7.5)
- [x] **Source-of-truth hierarchy** (section 7.6)
- [x] **Immutable snapshots** (section 7.7)
- [x] **One commit, one PR rule** (section 7.8)
- [x] **Single-user session model** (section 7.9)
- [x] **Validation before derivation** (section 7.10)
- [x] **Approval gate before PR** (section 7.11)
- [x] **Terraform validation gate** (section 7.12, gated by CQ-13b)
- [x] **Rate limiting** (section 7.13)
- [x] **Optimistic locking** (section 7.14)
- [x] **Fail-safe GitHub ops** (section 7.15)
- [x] **No secrets in logs** (section 7.16)
- [x] **Async-first architecture** (section 7.17)
- [x] **JSON content negotiation** (section 7.18)

### ✅ Dependency Rules Locked

- [x] **Allowed dependency directions** (section 4, graph)
- [x] **Circular dependency prevention** (section 4)
- [x] **Import restrictions per module** (section 5)
- [x] **Backend module boundaries** (section 5, backend/*)
- [x] **Frontend boundaries** (section 5, frontend/*)
- [x] **LangGraph boundaries** (section 5, langgraph/*)
- [x] **Knowledge layer boundaries** (section 5, knowledge/*)
- [x] **Database layer boundaries** (section 5, database/*)
- [x] **Shared/Core boundaries** (section 5, shared/core/)

### ✅ File Responsibilities Locked

- [x] **Backend files** (section 6)
- [x] **Frontend files** (section 6)
- [x] **Knowledge files** (section 6)
- [x] **LangGraph files** (section 6)
- [x] **Database files** (section 6)
- [x] **Test files** (section 6)
- [x] **Scripts & tools** (section 6)
- [x] **Documentation files** (section 6, immutable)

### ✅ Clarification Questions Logged

- [x] **All CQ items from CPRS + MIF Bible captured** (section 8)
- [x] **CQ blocking analysis** (which sections depend on each CQ)
- [x] **No CQs resolved** (all preserved)

### ✅ Deferred Items Documented

- [x] **All Phase-2+ items listed** (section 9)
- [x] **Target phases assigned** (when each deferred item is expected)

### ⚠️ Pending Before Implementation

- [ ] CQ-14 resolved (prod topic path)
- [ ] CQ-15 resolved (target repo identity)
- [ ] CQ-01 resolved (field editability)
- [ ] Database schema created from migration scripts (pending CQ-08 on table list finalization)
- [ ] GitHub OAuth app registration (env vars: GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET)
- [ ] PostgreSQL connection string verified (.env)
- [ ] Redis connection verified (.env)

### ⚠️ Verification Before Phase 2

- [ ] Run `scripts/validate_architecture.py` to enforce import rules
- [ ] All existing files confirmed present (test-path checks from session context showed all created files exist)
- [ ] Folder structure validated (no missing or extra top-level folders)
- [ ] Knowledge registries validated (JSON well-formed)

---

## 11. USAGE GUIDELINES FOR THIS DOCUMENT

### When to Read This Document

1. **Before writing any code** — ensure you understand layer responsibilities and dependencies
2. **Before adding a new import** — check section 5 to confirm it's allowed
3. **Before creating a new service** — verify it fits in section 3 and doesn't violate SRP
4. **When resolving a CQ** — check section 8 to understand which sections unblock
5. **During code review** — use section 7 (frozen decisions) and §18.5 (review checklist) to guide feedback

### When to Update This Document

1. **CQ resolution** — move from section 8 to section 7 (frozen decisions) with rationale
2. **New architectural decision** — add to section 7 with references to authoritative sources
3. **Scope changes** — update section 9 (deferred items) with new target phases

**Never update this document without:**
- [ ] Consensus from architecture team
- [ ] Traceability to authoritative sources (CPRS, MIF Bible, TAS, Backend Module Architecture)
- [ ] Impact analysis (which layers affected?)

### Enforcement Points

| Gate | Check | Tool/Script |
|------|-------|-----------|
| Commit pre-hook | Import rules | `scripts/validate_architecture.py` (linter) |
| PR review | Section 7 alignment | Manual (code review checklist §18.5) |
| Phase gate | CQ resolutions | Manual (roadmap review) |
| Deployment | Dependency graph | SBOM + static analysis |

---

## 12. REFERENCES TO AUTHORITATIVE SOURCES

All sections reference the following frozen sources:

| Source | URL / Path | Version | Last verified |
|--------|-----------|---------|----------------|
| CPRS v1.0 | doc/CPRS_v1.0.md | 1.0 | 2026-06-28 |
| Repository Master Structure | doc/01_REPOSITORY_MASTER_STRUCTURE.md | 2.0 | 2026-06-28 |
| Backend Module Architecture | doc/02_BACKEND_MODULE_ARCHITECTURE.md | Per spec | 2026-06-28 |
| Implementation Bible | doc/MIF_Implementation_Bible.md | 1.0 FINAL DRAFT | 2026-06-28 |
| TAS Reference | doc/TAS_reference.md | Per spec | 2026-06-28 |
| Glue Job Process | doc/mif-glue-job-creation-terraform-script-process.md | 1.0 | 2026-06-28 |
| Terraform Reference Repo | saptcc/, saptce/, confluent_minerva_dev/ | Current | 2026-06-28 |

---

**END OF ARCHITECTURE DECISIONS DOCUMENT**

**Status:** FROZEN  
**Next action:** Await CQ resolutions before proceeding to Phase-2 implementation.

