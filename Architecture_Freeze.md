# ARCHITECTURE FREEZE — FINAL & PERMANENT
## MIF Infrastructure Copilot — Phase 1 Bootstrap

**Status:** PERMANENTLY FROZEN (2026-06-28)  
**Signed:** Architect Lead  
**Authority:** Final Authority Council  
**Scope:** This document is the constitutional law of the MIF Copilot architecture. No modification is permitted. Implementation must not violate any frozen decision.

---

## 1. PURPOSE

This document permanently freezes the architecture of the MIF Infrastructure Copilot before Phase-2 implementation begins.

**Why This Matters:**
- Prevents architectural drift during implementation
- Ensures all developers follow identical design rules
- Protects against unintended redesigns
- Creates a permanent reference for future maintenance
- Establishes the authority hierarchy for conflict resolution

**This document is read-only after publication. No AI, no engineer, no stakeholder may alter these frozen decisions.**

---

## 2. ARCHITECTURE AUTHORITY — PERMANENT HIERARCHY

When multiple sources speak, resolve conflicts by this **immutable precedence order**:

1. **doc/CPRS_v1.0.md** (v1.0 FINAL)
   - Product and functional requirements
   - Acceptance criteria (AC-1 through AC-14)
   - Authoritative on scope and user-facing behavior

2. **doc/01_REPOSITORY_MASTER_STRUCTURE.md** (v2.0 FROZEN)
   - Authoritative repository topology
   - Folder structure, file ownership, naming conventions
   - Frozen project organization

3. **doc/02_BACKEND_MODULE_ARCHITECTURE.md** (v2.0 FROZEN)
   - Layer responsibilities and module boundaries
   - Dependency rules (import restrictions)
   - Service contracts and data flow

4. **doc/MIF_Implementation_Bible.md** (v1.0 FINAL DRAFT)
   - 18-section implementation specification
   - Detailed workflows, state machines, node specifications
   - Authoritative interpretation of requirements

5. **doc/TAS_reference.md** (v1.0)
   - Technical architecture summary
   - Phases (T1–T14), technology decisions
   - Reference implementation patterns

6. **doc/mif-glue-job-creation-terraform-script-process.md** (v1.0)
   - Glue job configuration patterns
   - Terraform template shapes and rules
   - Domain-specific example values

7. **Terraform Reference Repositories** (current state)
   - saptcc/, saptce/, confluent_minerva_dev/ folders
   - Read-only reference for patterns
   - Current state is authoritative, not a source for new rules

8. **Decisions.md** (created 2026-06-28)
   - Architecture decision summary
   - Dependency graph documentation
   - CQ preservation and gap tracking

**Conflict Resolution Rule:**  
If two sources disagree, the higher-numbered source wins. If the conflict is unresolvable, escalate as a **Clarification Question (CQ)** — never invent a decision unilaterally.

---

## 3. ARCHITECTURE FREEZE DECLARATION

### 3.1 What Is Frozen

✅ **The hexagonal architecture pattern is frozen.**  
- Frontend → API (HTTP adapter) → LangGraph (orchestrator) → Services (business logic) → Repositories (data) → Database
- No deviation permitted. No redesigns allowed.

✅ **The seven-layer model is frozen.**  
- Shared/Core (leaves) → Database → Repositories → Services → Knowledge → LangGraph → API → Frontend
- Each layer has fixed responsibilities (see §4).
- No layer may merge with another. No layer may be removed.

✅ **The single-responsibility principle (SRP) is frozen.**  
- Every class, file, and module has exactly one reason to change.
- A service cannot also be a repository. A repository cannot contain business logic.
- SRP violations = architectural violation = must be reverted.

✅ **The dependency graph is frozen.**  
- Services depend on repositories + knowledge + github. Not reverse.
- Repositories depend on models + database. Never services.
- Models depend on core only. Never anything else.
- All dependencies documented in Decisions.md §4 & §5.

✅ **The repository structure is frozen.**  
```
MIF-INGEST-TO-LAKEHOUSE-INFRA-DEV_V3/
├── backend/       (FastAPI + services + repositories + models)
├── frontend/      (React + Vite SPA)
├── langgraph/     (Orchestration nodes + state + routing)
├── knowledge/     (Registries + derivers + validators + templates)
├── database/      (Engine + migrations + session factory)
├── prompts/       (System + node prompts)
├── shared/        (Types, constants, exceptions, validators)
├── tests/         (Unit + integration + contract + e2e + recovery + failure)
├── config/        (Settings, logging, redis, alembic)
├── docker/        (Dockerfiles, docker-compose, nginx)
├── scripts/       (Setup, validation, CI/CD helpers)
├── docs/          (Engineering documentation)
├── .github/       (CI/CD workflows)
└── [Terraform reference folders]
    ├── confluent_minerva_dev/
    ├── project_information/
    ├── saptcc/
    └── saptce/
```
- **No new top-level folders without architectural review.**
- **No folder renames without architectural review.**
- **No folder merges without architectural review.**
- **No folder deletions without architectural review.**

✅ **File ownership is frozen.**  
Every file belongs to exactly one owner (see Repository Master Structure §1.15).  
File reassignments require architectural approval.

✅ **Import restrictions are frozen.**  
- Repositories may NOT import services.
- Models may NOT import anything except core.
- Core/Shared may NOT import anything.
- API may NOT import repositories directly.
- All restrictions documented in Decisions.md §5.
- Enforced by `scripts/validate_architecture.py` (import linter).

✅ **The 8-table data model is frozen** (pending CQ-08 clarification on naming).
- users, sessions, drafts, draft_files, draft_glue_jobs, snapshots, validation_reports, pr_metadata
- Entities defined in backend/models/
- Schema in database/migrations/

✅ **The 18-node LangGraph structure is frozen** (per Backend Module Architecture §2.6).
- Node list: OAuth, SessionManager, Environment, Operation, SourceType, SourceSystem, SchemaGrain, TopicValidation, DuplicateJobValidation, KnowledgeDerivation, DraftWorkspace, ModifyFile, ReviewWorkspace, TerraformValidation, Approval, PRCreation, ConflictResolution, OutOfScope (+ Placeholder for non-Kafka).
- Transition matrix documented in Backend Module Architecture §2.6.
- No node additions without architectural review.
- No node merges without architectural review.
- No node removals without architectural review.

✅ **The knowledge layer is frozen.**  
- All intelligence in registries (JSON), derivers, validators, templates.
- No hardcoded business logic.
- No hardcoded defaults.
- All rules additive (no code changes for new rules).

✅ **The API contract is frozen.**  
- `/api/v1/agent/message` (primary endpoint)
- `/api/v1/auth/*` (OAuth)
- `/api/v1/sessions` (session management)
- `/api/v1/internal/*` (service-only)
- `/api/v1/health*` (monitoring)
- All endpoint signatures defined in Backend Module Architecture §2.2.

✅ **The Terraform output format is frozen.**  
- locals.tf entry structure matches glue-job-creation-process.md §11.
- glue.tf module block matches §12.
- No deviation permitted.

✅ **One commit, one PR rule is frozen** (BR-S-1, BR-S-2).
- Every pull request must contain exactly one Git commit.
- Multi-file changes are squashed before PR creation.
- Enforced in PRCreationNode.

✅ **One user = one session = one draft rule is frozen** (FR-W-2).
- Concurrent edits not supported.
- Session restoration takes precedence over session re-creation.
- Draft mutations are atomic (snapshot created before mutation).

✅ **Validation-before-derivation rule is frozen** (BR-A-8).
- Topic validation runs first.
- Duplicate-job validation runs second.
- Knowledge derivation runs third.
- No exceptions to this order.

✅ **Source-of-truth hierarchy is frozen** (BR-A-10).
1. GitHub repository (live) — always correct for existence/naming.
2. Draft workspace (PostgreSQL) — user's current working state.
3. Knowledge registries (JSON) — defaults, rules, patterns.
4. LangGraph state (Redis) — workflow position only.

---

### 3.2 What AI Must NEVER Do

🚫 **Never redesign the architecture.**  
You may not change the hexagonal pattern, split layers, merge responsibilities, or introduce new layers. The architecture is locked.

🚫 **Never move folders or rename packages.**  
All top-level folders are assigned. Renames require architectural review.

🚫 **Never merge unrelated responsibilities.**  
One service = one responsibility. One repository = one entity set. One node = one workflow step.

🚫 **Never split responsibilities without design review.**  
If a file grows complex, refactor within its layer using helper classes, but maintain single responsibility at the public interface.

🚫 **Never hardcode business logic, defaults, or rules.**  
All intelligence lives in the knowledge layer (registries, derivers, validators, templates). Services orchestrate; they don't decide.

🚫 **Never introduce new modules without approval.**  
Want a new service? Ask. New repository? Ask. New LangGraph node? Ask. New folder at top level? Ask.

🚫 **Never bypass validation or security gates.**  
Topic validation, duplicate-job validation, Terraform validation, approval confirmation — these are not optional.

🚫 **Never let business logic live in repositories.**  
Repositories do CRUD only. Business rules move to services.

🚫 **Never let business logic live in API endpoints.**  
API routes are thin wrappers. Business logic moves to services.

🚫 **Never let business logic live in LangGraph nodes.**  
Nodes orchestrate. Business logic moves to services.

🚫 **Never let business logic live in the knowledge layer.**  
Knowledge provides configuration and rules. Services apply them.

🚫 **Never import models directly into services.**  
Services receive/return domain objects (shared/types), not ORM instances.

🚫 **Never import repositories into LangGraph nodes.**  
All persistence goes through services. Nodes never touch repositories directly.

🚫 **Never leave unresolved CQ items as assumptions.**  
If a CQ blocks your work, escalate it. Never invent a resolution.

🚫 **Never skip reading the authoritative documents.**  
Before writing any code, read the specification. Do not assume. Do not guess.

🚫 **Never ignore import-linter violations.**  
If `scripts/validate_architecture.py` fails, fix the import. Do not work around it.

🚫 **Never replace frozen patterns.**  
Hexagonal architecture, SRP, repository pattern, service layer, knowledge layer — these are non-negotiable.

---

### 3.3 What AI Must ALWAYS Do

✅ **Always read the authoritative documents first.**  
Before any task, read the relevant sections of CPRS, Repository Master Structure, Backend Module Architecture, Implementation Bible, or TAS.

✅ **Always read Decisions.md and Architecture_Freeze.md before implementation.**  
These documents define your constraints.

✅ **Always follow the frozen repository structure.**  
No new top-level folders. No renames. No merges.

✅ **Always respect dependency rules.**  
Services depend on repositories, not reverse. Use the import-linter script to verify.

✅ **Always respect Single Responsibility Principle.**  
One file = one reason to change. One service = one responsibility. One repository = one entity set.

✅ **Always respect hexagonal architecture.**  
Frontend → API → LangGraph → Services → Repositories → Database.  
No shortcuts. No bypasses. No exceptions.

✅ **Always preserve all CQ items exactly as stated.**  
If you resolve a CQ, move it from Decisions.md §8 to §7 with full rationale and traceability.  
Never assume a CQ resolution.

✅ **Always follow the implementation order (see §5).**  
Build in order: Shared → Config → Database → Models → Repositories → Knowledge → Services → LangGraph → API → Frontend.  
Do not skip layers.

✅ **Always maintain immutable snapshots for draft history.**  
Every mutation creates a snapshot. Snapshots are never modified; only restored.

✅ **Always enforce one-commit-one-PR rule.**  
Squash all file changes into a single Git commit before PR creation.

✅ **Always validate before deriving.**  
Topic validation → Duplicate job → Knowledge derivation. Immutable order.

✅ **Always mask secrets in logs.**  
GitHub tokens, database passwords, API keys are never logged. Use SecretStr.

✅ **Always run validation gates before PR creation.**  
Topic exists? → Job doesn't exist? → Terraform valid? → User approved? All mandatory.

✅ **Always use the source-of-truth hierarchy.**  
GitHub wins over KB. Draft wins over registries. Never invert precedence.

✅ **Always trace requirements to source documents.**  
Every decision must trace back to CPRS, MIF Bible, TAS, or an explicit CQ.

✅ **Always enforce import-linter rules.**  
Run `scripts/validate_architecture.py` on every commit. No violations permitted.

✅ **Always document architectural decisions with citations.**  
If you make a choice, cite the authoritative source. If no source supports it, it's probably a CQ.

---

## 4. LAYER RESPONSIBILITIES — FROZEN

| Layer | Purpose | Responsibilities | May depend on | Forbidden |
|-------|---------|------------------|---------------|-----------|
| **Frontend** | User interaction | UI rendering, input capture, state display | API contract (HTTP) | Business logic, DB access, backend internals |
| **API** | HTTP boundary | Endpoint routing, request validation, response serialization | Services, LangGraph builder, Schemas | Repositories, models (directly), database |
| **LangGraph** | Orchestration | Node sequencing, state transitions, interrupt handling | Services, state model, shared/core | Repositories, database, API logic |
| **Services** | Business logic | Derivation, validation, draft mgmt, PR creation, GitHub I/O | Repositories, knowledge, shared | API (reverse), LangGraph (reverse) |
| **Knowledge** | Configuration intelligence | Registries, derivers, validators, templates, repo analysis | Registries (JSON), GitHub (via service), shared | Repositories, services, API, LangGraph (reverse) |
| **Repositories** | Data access | CRUD, transactions, optimistic locking | Models, database, core | Services (reverse), API, LangGraph |
| **Models** | ORM definitions | Entity definitions, field validation | Core only | Everything else |
| **Database** | Connectivity | Engine factory, session factory, migrations | Core only | Services, API, business logic |
| **Shared/Core** | Primitives | Types, exceptions, constants, validators | Nothing | Everything |

**Enforcement:** Every layer respects these boundaries. Import-linter enforces at commit time.

---

## 5. IMPLEMENTATION ORDER — MANDATORY

The implementation must follow this sequence **exactly**. No skipping layers. No reordering.

| Phase | Layer | Deliverables | Gate condition | Reference |
|-------|-------|--------------|----------------|-----------|
| **P1** | Shared + Core | Types, exceptions, constants, logging | Passed | §doc/01 §1.9, §doc/02 §2.1 |
| **P2** | Config + Database | Settings, engine, session factory, migrations | Schema created | §doc/01 §1.11, §doc/02 §2.8 |
| **P3** | Models + Repositories | ORM definitions, CRUD stubs | Tests pass | §doc/02 §2.8, §2.9 |
| **P4** | Knowledge | Registries, loaders, derivers, validators, templates | Registries well-formed | §doc/01 §1.6, §doc/02 §2.5 |
| **P5** | Services | Business logic (validation, draft, derivation, GitHub, TF) | Services tested in isolation | §doc/02 §2.4 |
| **P6** | LangGraph | Nodes, state model, routing, transitions | Graph executes end-to-end | §doc/02 §2.6, §doc/01 §1.5 |
| **P7** | API | Endpoints, middleware, DTO serialization | Contract tests pass | §doc/02 §2.2, §doc/01 §1.3 |
| **P8** | Frontend | Pages, components, hooks, stores, API client | Flows render, state persists | §doc/01 §1.4 |
| **P9** | Testing | Unit, integration, contract, e2e, recovery, failure | Coverage >90% | §doc/01 §1.10 |
| **P10** | Performance | Load testing, cache tuning, monitoring setup | p50<100ms, p95<500ms | §doc/02 §2.11 |
| **P11** | Production | Security hardening, deployment automation, runbooks | All gates pass | §doc/02 §2.13–2.14 |

**Rules:**
- Phase P(n) cannot begin until P(n-1) exits its gate condition.
- No phase may depend on code from a later phase.
- Each phase has ownership assigned (§doc/01 §1.15).

---

## 6. FROZEN DEPENDENCY RULES

### 6.1 Allowed Imports (Complete List)

```
SHARED/CORE (leaves — no outbound dependencies)
  ↑
  
MODELS (depends on CORE only)
  ↑
  
REPOSITORIES (depends on MODELS + CORE + DATABASE)
  ↑
  
KNOWLEDGE (depends on SHARED + CORE, reads GitHub via SERVICE)
  ↑
  
SERVICES (depends on REPOSITORIES + KNOWLEDGE + SHARED + GITHUB_SERVICE)
  ↑
  
LANGGRAPH NODES (depends on SERVICES + STATE + SHARED)
  ↑
  
API (depends on SERVICES + SCHEMAS + LANGGRAPH.BUILDER + SHARED)
  ↑
  
FRONTEND (depends on API contract only — HTTP)
```

### 6.2 Forbidden Imports (Absolute)

- ✗ Repositories → Services (inversion)
- ✗ Knowledge → Services (read-only)
- ✗ Knowledge → Repositories (no side effects)
- ✗ Knowledge → API (configuration, not HTTP)
- ✗ LangGraph → Repositories (via services only)
- ✗ LangGraph → Database (via services only)
- ✗ API → Repositories (via services only)
- ✗ Frontend → Backend internals (HTTP only)
- ✗ Models → anything except CORE
- ✗ CORE → anything
- ✗ Circular imports (enforced by linter)

### 6.3 Enforcement

```bash
# Run before every commit
scripts/validate_architecture.py
```

This script enforces all import restrictions. If it fails, fix the import before committing.

---

## 7. CLARIFICATION QUESTIONS — PRESERVED

All CQs from CPRS v1.0 and MIF Implementation Bible are listed exactly as stated. **These are NOT resolved.** They are preserved for future decision gates.

| CQ | Question | Tier | Status |
|----|----------|------|--------|
| **CQ-01** | Which review fields are user-editable vs read-only? | Blocker | PENDING |
| **CQ-02** | Topic name: strictly read-only, or user-editable? | Blocker | PENDING |
| **CQ-03** | Enterprise Function values: AGTR/FOOD/SPEC or others? | High-impact | PENDING |
| **CQ-04** | Max workers: exactly 10, or different per type? | High-impact | PENDING |
| **CQ-05** | Run mode default: Manual or Scheduled? | High-impact | PENDING |
| **CQ-06** | Draft status enum names (OPEN vs DRAFT_EDITING)? | Blocker | PENDING |
| **CQ-07** | Exact node count: 18 or 19? | Medium | PENDING |
| **CQ-08** | Table count: 8 or 19? | Blocker | PENDING |
| **CQ-09** | Diff rendering: Phase-1 or Phase-2+? | High-impact | PENDING |
| **CQ-13b** | TF validation: REQUIRED or informational? | High-impact | PENDING |
| **CQ-14** | Prod topic path: confluent_minerva_prod or other? | Blocker | PENDING |
| **CQ-15** | Target repo identity and GitHub org/repo? | Blocker | PENDING |
| **CQ-A1** | New-source concretes and LH DB pattern source? | High-impact | PENDING |
| **CQ-A2** | Are project_information/cell*.md required? | Medium | PENDING |
| **CQ-A4** | Conflict resolution depth in Phase-1? | Medium | PENDING |
| **CQ-A5** | Transformer settings: shown or defaulted? | Medium | PENDING |
| **CQ-A6** | Modify-files guardrails: allowlist or denylist? | Medium | PENDING |
| **CQ-A7** | Token encryption: at-rest algorithm? | High-impact | PENDING |
| **CQ-A8** | NFR targets: latency, throughput, retention? | Medium | PENDING |
| **CQ-A9** | Post-approval workflow atomicity? | Medium | PENDING |

**None of these CQs are resolved. All remain PENDING for future decision gates.**

---

## 8. FROZEN DECISIONS

The following 18 architectural decisions are permanently locked:

1. **Hexagonal Architecture** — Frontend → API → LangGraph → Services → Repositories → Database
2. **Single Responsibility Principle** — One file = one reason to change
3. **Repository Pattern** — CRUD-only, no business logic in repositories
4. **Service Layer** — ALL business logic lives in services
5. **Knowledge Layer** — ALL configuration, defaults, rules in registries/derivers/validators
6. **Source-of-Truth Hierarchy** — GitHub > Draft > Registries > State
7. **Immutable Snapshots** — Every draft mutation creates a snapshot; undo restores previous snapshot
8. **One Commit, One PR** — Every PR contains exactly one Git commit
9. **One Session = One Draft** — No concurrent edits; pessimistic locking
10. **Validation Before Derivation** — Topic → Duplicate Job → Knowledge (immutable order)
11. **Explicit Approval Gate** — User confirms before PR creation (FR-S-4)
12. **Terraform Validation** — Runs before PR; gated by CQ-13b
13. **Rate Limiting** — Per-session on /agent/message endpoint
14. **Optimistic Locking** — Drafts and sessions use version field
15. **Fail-Safe GitHub Operations** — All GitHub calls include retry + backoff
16. **No Secrets in Logs** — Tokens/passwords masked using SecretStr
17. **Async-First Architecture** — FastAPI + SQLAlchemy AsyncSession
18. **JSON-Only API** — No XML, form-encoded, or other content types

All decisions documented in Decisions.md §7 with full rationale.

---

## 9. ITEMS EXPLICITLY DEFERRED

The following capabilities are **not in Phase-1**. They remain deferred to Phase-2+ and must not be implemented in Phase-1:

- RBAC (role-based access control) — Phase-2+
- Vault / Secret rotation — Phase-3+
- OTEL (OpenTelemetry) — Phase-3+ (correlation IDs sufficient for Phase-1)
- API versioning strategy — Phase-3+ (v1.0 only)
- Frontend build optimization — Phase-2+
- Multi-repository support — Phase-2+
- Scheduled job automation (EventBridge) — Phase-2+
- Data export / statistics — Phase-2+
- Full conflict resolution UI — Phase-2+
- Mobile UI — Phase-3+
- Internationalization (i18n) — Phase-3+

**Rule:** If you find yourself implementing any deferred item, **STOP** and escalate.

---

## 10. IMPLEMENTATION GATE

**No AI agent, no engineer, no stakeholder may proceed to Phase-2 implementation until:**

1. ✅ This document has been read in full
2. ✅ Decisions.md has been read in full
3. ✅ All authoritative documents have been read
4. ✅ `scripts/validate_architecture.py` passes with zero violations
5. ✅ All repository folders exist and ownership is clear
6. ✅ All CQ items are preserved (none pre-resolved)
7. ✅ All frozen decisions are understood
8. ✅ Implementation order is agreed
9. ✅ All blockers (CQ-01, CQ-14, CQ-15, CQ-06, CQ-08) are on the decision roadmap

**Gating Officer:** Architecture Lead  
**Signed:** [Date: 2026-06-28]

---

## 11. ARCHITECTURE FREEZE CERTIFICATE

### Verification Checklist

| Item | Status | Verified by | Date |
|------|--------|-------------|------|
| **Repository Structure** | FROZEN ✅ | Arch Lead | 2026-06-28 |
| **Layer Responsibilities** | FROZEN ✅ | Arch Lead | 2026-06-28 |
| **Dependency Graph** | FROZEN ✅ | Arch Lead | 2026-06-28 |
| **Import Rules** | FROZEN ✅ | Arch Lead | 2026-06-28 |
| **File Ownership** | FROZEN ✅ | Arch Lead | 2026-06-28 |
| **Service Contracts** | FROZEN ✅ | Arch Lead | 2026-06-28 |
| **API Contract** | FROZEN ✅ | Arch Lead | 2026-06-28 |
| **LangGraph Topology** | FROZEN ✅ | Arch Lead | 2026-06-28 |
| **Database Schema (8 tables)** | FROZEN ✅ | Arch Lead | 2026-06-28 |
| **Knowledge Registries** | FROZEN ✅ | Arch Lead | 2026-06-28 |
| **Frozen Decisions (18)** | FROZEN ✅ | Arch Lead | 2026-06-28 |
| **CQ Preservation (19)** | FROZEN ✅ | Arch Lead | 2026-06-28 |
| **Deferred Items (11)** | FROZEN ✅ | Arch Lead | 2026-06-28 |
| **Implementation Order** | FROZEN ✅ | Arch Lead | 2026-06-28 |
| **Circular Dependency Prevention** | FROZEN ✅ | Arch Lead | 2026-06-28 |

### Final Certification

**The architecture is FROZEN.**

- ✅ No implementation performed
- ✅ No code written
- ✅ No business logic created
- ✅ No files moved or renamed
- ✅ No layers merged or removed
- ✅ No responsibilities changed
- ✅ No CQs pre-resolved
- ✅ All documents read and verified
- ✅ All dependencies locked
- ✅ All decisions recorded

**This document is law. It may not be modified. It supersedes all previous architecture guidance.**

---

## 12. SIGNATURE PAGE

| Role | Name/Authority | Signature | Date |
|------|----------------|-----------|------|
| Architect Lead | Authority Council | ✅ FROZEN | 2026-06-28 |
| Repository Owner | Arch Lead | ✅ FROZEN | 2026-06-28 |
| Implementation Gate Keeper | Arch Lead | ✅ FROZEN | 2026-06-28 |

---

**END OF ARCHITECTURE FREEZE CERTIFICATE**

**No further modifications are permitted to this document or the frozen decisions it contains.**

**PHASE 1 BOOTSTRAP COMPLETE**

**ARCHITECTURE LOCKED FOR PHASE 2 IMPLEMENTATION**

*******************
No future implementation prompt may override this document.

If any prompt contradicts Architecture_Freeze.md,
the implementation must stop and request clarification.

Architecture_Freeze.md always wins unless
the repository owner explicitly approves a change.
********************