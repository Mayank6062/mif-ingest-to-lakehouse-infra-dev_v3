REPOSITORY_MASTER_STRUCTURE.md
Version: 2.0 (merged) | Status: FROZEN FOR IMPLEMENTATION Last Updated: 2026-06-27 Authoritative inputs (frozen): CPRS v1.0, TAS Reference, MIF Implementation Bible, MIF Glue Job Creation Process Supersedes: Repository Master Structure v1.0, Final Engineering Package Deliverables 1 & 11–12 Rule: Single source of truth for project structure. No folder/file/ownership change without architectural review.

1.1 Repository Identity & Topology
This is the application repository MIF-INGEST-TO-LAKEHOUSE-INFRA-DEV_V3, which is separate from the Terraform target repository it operates on.

Target Terraform repo (external):  MIF-INGEST-TO-LAKEHOUSE-INFRA-DEV_V3
  ├── confluent_minerva_dev/topics_<source>.tf   ← topic validation reads
  ├── <source>/locals.tf, <source>/glue.tf       ← source folders (existence = BR-A-14)
  └── (no confluent_minerva_prod/ present)        ← IMPLEMENTATION GAP CQ-14
IMPLEMENTATION GAP (CQ-15): Whether the application lives inside _v3 or is a separate repo. Adopted working position: separate repo (mixing the agent's code into its own PR target is invalid). Confirm. IMPLEMENTATION GAP (CQ-14): No confluent_minerva_prod/ exists; prod topic-validation path undefined.

1.2 Top-Level Directory Tree
MIF-INGEST-TO-LAKEHOUSE-INFRA-DEV_V3/
├── backend/                  # FastAPI application (business logic, orchestration entry)
├── frontend/                 # React + Vite SPA
├── knowledge/                # Knowledge base layer (registries, derivers, validators, templates)
├── langgraph/                # LangGraph workflow orchestration (nodes, state, transitions)
├── database/                 # Engine, session factory, migrations, DDL reference
├── prompts/                  # System + node prompts (versioned artifacts)
├── shared/                   # Cross-layer types, constants, exceptions, validators, formatters
├── tests/                    # Unit, integration, contract, e2e, recovery, failure
├── config/                   # Pydantic settings, logging, redis, alembic config
├── docker/                   # Dockerfiles, compose, nginx
├── scripts/                  # Setup, migration, seeding, architecture lint, perf
├── docs/                     # Engineering documentation + runbooks
├── .github/                  # CI/CD workflows + templates
├── CLAUDE_RULES.md           # Binding implementation rules (see §1.20)
├── docker-compose.yml
├── .env.example
└── README.md
Top-level folder	Purpose	Owner	May depend on	Restrictions
backend/	API boundary + services + repos + models	Service/API/DB Owners	knowledge, langgraph, shared, database	No frontend imports
frontend/	UI only	Frontend Owner	API contracts only	No backend/langgraph/knowledge imports
knowledge/	Config intelligence	Knowledge Owner	shared, models (read-only)	No services/repositories/langgraph/frontend
langgraph/	Orchestration	Orchestration Owner	services, knowledge, shared, models	No repositories/frontend; no direct DB writes
database/	Connectivity + migrations	Migration/DB Owner	shared/core	No services/api
prompts/	Prompt artifacts	Prompt Owner	none	No persistence imports
shared/	Shared primitives	Arch Lead	nothing	Leaf — depends on nothing
tests/	Coverage	QA Owner	all	—
config/	Settings	Arch Lead	shared	No business logic
docker/,scripts/,docs/,.github/	Ops	DevOps/Doc Owner	—	—
1.3 Backend Structure
Purpose: FastAPI app — the single agent message endpoint + internal service orchestration.

backend/
├── __init__.py
├── main.py                           # FastAPI entry point; builds DI container + graph
├── core/                             # Shared backend primitives (leaf within backend)
│   ├── __init__.py
│   ├── config.py                     # Pydantic Settings loader
│   ├── constants.py                  # Non-business constants
│   ├── exceptions.py                 # Exception hierarchy (mirrors shared/exceptions.py)
│   ├── logging.py                    # Structured logging setup
│   ├── correlation.py                # correlation_id propagation
│   ├── security.py                   # SecretStr handling, token masking
│   └── types.py                      # Internal type aliases
├── dependencies.py                   # DIContainer (singletons + repo factories)
├── schemas/                          # Pydantic request/response DTOs
│   ├── __init__.py
│   ├── agent.py                      # AgentMessageRequest/Response
│   ├── auth.py                       # Auth/OAuth DTOs
│   ├── session.py                    # Session list/detail DTOs
│   ├── draft.py                      # Draft + review DTOs
│   ├── glue_job.py                   # GlueJobConfigView
│   ├── validation.py                 # ValidationResult DTO
│   ├── pr.py                         # PRResponse DTO
│   └── github.py                     # GitHub-related DTOs
├── api/                              # HTTP boundary
│   ├── __init__.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── agent_routes.py           # POST /api/v1/agent/message (+ stream)
│   │   ├── auth_routes.py            # GitHub OAuth login/callback/logout/me
│   │   ├── session_routes.py         # GET /sessions, /sessions/{id}, DELETE
│   │   ├── internal_routes.py        # /internal/* (service-token only)
│   │   └── health_routes.py          # /health, /health/ready
│   ├── stream/
│   │   └── agent_stream.py           # WebSocket/SSE streaming
│   └── middleware/
│       ├── __init__.py
│       ├── auth_middleware.py        # Token verify + context enrichment
│       ├── error_middleware.py       # Exception → HTTP mapping
│       ├── correlation_middleware.py # correlation/request id
│       └── ratelimit_middleware.py   # Per-user rate limiting
├── services/                         # Business logic
│   ├── __init__.py
│   ├── auth_service.py               # Token validation, user binding
│   ├── session_service.py           # Session create/restore/archive
│   ├── glue_job_service.py           # Derivation orchestration + repo validations
│   ├── draft_service.py              # Draft mutation, snapshot, undo, materialize
│   ├── snapshot_service.py           # Immutable snapshot create/restore
│   ├── navigation_service.py         # Conversational repo browse (read)
│   ├── review_service.py             # Assemble review payload + diffs
│   ├── validation_service.py         # Validation orchestration + history
│   ├── terraform_service.py          # Terraform CLI init/fmt/validate
│   ├── github_service.py             # All GitHub REST/GraphQL I/O
│   ├── github_oauth_service.py       # OAuth code exchange
│   ├── pr_service.py                 # Branch + single commit + PR
│   └── conflict_service.py           # Rebase / conflict resolution
├── repositories/                     # Data access (CRUD only)
│   ├── __init__.py
│   ├── base_repository.py
│   ├── user_repository.py
│   ├── session_repository.py
│   ├── draft_repository.py
│   ├── draft_file_repository.py
│   ├── draft_glue_job_repository.py
│   ├── snapshot_repository.py
│   ├── validation_repository.py
│   └── pr_metadata_repository.py
├── models/                           # SQLAlchemy ORM (8 entities — CQ-08)
│   ├── __init__.py
│   ├── base.py
│   ├── user.py
│   ├── session.py
│   ├── draft.py
│   ├── draft_file.py
│   ├── draft_glue_job.py
│   ├── snapshot.py
│   ├── validation_report.py
│   └── pr_metadata.py
├── utils/                            # Stateless helpers
│   ├── __init__.py
│   ├── github_utils.py
│   ├── terraform_utils.py
│   ├── secret_handler.py
│   ├── logging_utils.py
│   └── error_handlers.py
└── Dockerfile
IMPLEMENTATION GAP (CQ-08): Model/repository count assumes the 8-entity set (TAS T6). "19 tables" interpretation would expand this. Not resolved.

Backend Ownership Rules
Module	Owner	Responsibilities	May depend on	Must NOT depend on
core/	Arch Lead	config, exceptions, logging, security, correlation	nothing	everything else
schemas/	Contract Owner	wire DTO validation	core	models, repositories
api/	API Owner	HTTP routing, middleware, streaming	services, schemas, langgraph (builder)	repositories, models, database
services/	Service Owner	ALL business logic	repositories, knowledge, github, shared	api, langgraph
repositories/	Data Owner	CRUD, transactions, optimistic locking	models, database, core	services, api, langgraph
models/	DB Owner	ORM definitions	core	everything else
utils/	Service Owner	pure helpers	core, shared	api, repositories
1.4 Frontend Structure
Purpose: React + Vite SPA, ChatGPT-style three-pane conversational interface.

frontend/
├── index.html
├── package.json
├── vite.config.ts
├── tsconfig.json
├── Dockerfile
├── public/
│   ├── favicon.ico
│   └── logo.svg
└── src/
    ├── main.tsx
    ├── App.tsx
    ├── index.css
    ├── pages/
    │   ├── LoginPage.tsx             # GitHub OAuth login
    │   ├── ChatPage.tsx              # Main three-pane interface
    │   ├── ReviewPage.tsx            # Draft review (modal/panel within Chat)
    │   ├── HistoryPage.tsx           # Session history (sidebar within Chat)
    │   └── NotFound.tsx
    ├── components/
    │   ├── layout/
    │   │   └── ThreePaneLayout.tsx   # Sessions | Chat | Workspace (UX-E-2)
    │   ├── Sidebar/
    │   │   ├── SessionList.tsx       # Today/Yesterday/Previous (FR-H-2)
    │   │   ├── SessionItem.tsx
    │   │   └── NewChatButton.tsx
    │   ├── Chat/
    │   │   ├── ChatWindow.tsx
    │   │   ├── MessageList.tsx
    │   │   ├── Message.tsx
    │   │   ├── UserMessage.tsx
    │   │   ├── AgentMessage.tsx
    │   │   ├── WidgetRenderer.tsx    # Renders FORM/SUMMARY/VALIDATION/APPROVAL widgets
    │   │   ├── ChatInput.tsx
    │   │   ├── EnvironmentSelector.tsx
    │   │   ├── OperationMenu.tsx
    │   │   ├── SourceTypeSelector.tsx
    │   │   ├── SourceSystemDropdown.tsx
    │   │   ├── SchemaGrainInput.tsx
    │   │   ├── TopicDisplay.tsx
    │   │   ├── ValidationResult.tsx
    │   │   ├── ApprovalPrompt.tsx
    │   │   └── PRSuccessMessage.tsx
    │   ├── Review/
    │   │   ├── ReviewPanel.tsx
    │   │   ├── FileTreeView.tsx
    │   │   ├── DiffViewer.tsx        # Green/red diff (FR-W-8)
    │   │   ├── JobSummary.tsx
    │   │   └── PRMetadataForm.tsx
    │   ├── workspace/
    │   │   ├── WorkspacePanel.tsx
    │   │   ├── DraftSummary.tsx
    │   │   ├── FileChangeList.tsx
    │   │   ├── GlueJobList.tsx
    │   │   └── NavigatorPanel.tsx
    │   ├── Common/
    │   │   ├── Header.tsx
    │   │   ├── Button.tsx
    │   │   ├── Card.tsx
    │   │   ├── Modal.tsx
    │   │   └── LoadingSpinner.tsx
    │   └── Auth/
    │       └── ProtectedRoute.tsx
    ├── services/                     # API communication only
    │   ├── api.ts                    # Axios/fetch client + config
    │   ├── agentService.ts
    │   ├── sessionService.ts
    │   ├── draftService.ts
    │   └── authService.ts
    ├── store/                        # State management (Zustand/Redux)
    │   ├── index.ts
    │   ├── authSlice.ts
    │   ├── sessionSlice.ts
    │   ├── chatSlice.ts
    │   ├── draftSlice.ts
    │   └── uiSlice.ts
    ├── hooks/
    │   ├── useAuth.ts
    │   ├── useSession.ts
    │   ├── useDraft.ts
    │   └── useAgentStream.ts
    ├── utils/
    │   ├── format.ts
    │   ├── validation.ts
    │   ├── routing.ts
    │   └── constants.ts
    └── types/
        ├── api.ts
        ├── agent.ts
        ├── draft.ts
        └── ui.ts
Frontend Ownership Rules
Module	Owner	Responsibilities	Restrictions
pages/	Page Owner	Route-level composition	No business logic; use services/store
components/	UI Owner	Presentation only	No direct API calls; use services/hooks
services/	API Layer Owner	HTTP communication only	Never call other services
store/	State Owner	Single source of UI truth	—
hooks/	Interaction Owner	Component logic	No direct API calls
1.5 LangGraph Structure
Purpose: Workflow orchestration. Node sequencing, state transitions, interrupts, HITL.

langgraph/
├── __init__.py
├── graph.py                          # Graph builder/definition
├── config.py                         # Graph configuration
├── transitions.py                    # Transition rules + guards
├── state/
│   ├── __init__.py
│   ├── graph_state.py                # GraphState schema
│   ├── state_reducers.py             # Field reducers
│   └── state_keys.py                 # Canonical state key names
├── routing/
│   ├── __init__.py
│   ├── intent_router.py              # Intent classification routing
│   ├── menu_router.py                # Operation menu visibility logic (FR-S-3)
│   └── transition_guards.py          # Guard predicates
├── checkpoint/
│   ├── __init__.py
│   └── redis_checkpointer.py         # LangGraph checkpointing (Redis)
├── nodes/
│   ├── __init__.py
│   ├── github_oauth.py
│   ├── session_manager.py
│   ├── environment.py
│   ├── operation.py
│   ├── source_type.py
│   ├── source_system.py
│   ├── schema_grain.py
│   ├── topic_validation.py
│   ├── duplicate_job_validation.py
│   ├── knowledge_derivation.py
│   ├── draft_workspace.py
│   ├── modify_file.py
│   ├── review_workspace.py
│   ├── terraform_validation.py
│   ├── approval.py
│   ├── pr_creation.py
│   ├── conflict_resolution.py
│   ├── out_of_scope.py
│   └── placeholder.py                # JDBC/FlatFile/API "need to implement"
└── workflows/
    ├── __init__.py
    ├── create_glue_job.py
    ├── modify_files.py
    └── conflict_resolution.py
IMPLEMENTATION GAP (CQ-07): TAS states "18 nodes"; the enumerated list above (19 node files incl. placeholder + out_of_scope) reconciles by treating intent_router as a routing module (under routing/) rather than a graph node. TopicGenerationNode/SessionPersistNode folded into schema_grain/pr_creation. Final count must be confirmed.

Node Ownership (selected — full specs in BACKEND_MODULE_ARCHITECTURE.md §LangGraph)
Node	Owner	Single responsibility	Services called
EnvironmentNode	Orchestrator	Gate workflows behind env	none
OperationNode	Orchestrator	Present menu + route	none
TopicValidationNode	Validation Service	Verify topic in repo	github_service, validation_service
DuplicateJobValidationNode	Validation Service	Verify job not present	github_service, validation_service
KnowledgeDerivationNode	Knowledge Service	Derive values + file plan	knowledge_base_service / glue_job_service
DraftWorkspaceNode	Draft Service	Persist draft + snapshot	draft_service, snapshot_service
ReviewWorkspaceNode	Review Service	Present review	review_service, draft_service
TerraformValidationNode	Validation Service	Run TF validation	terraform_service
ApprovalNode	Orchestrator	Single confirmation	none
PRCreationNode	PR Service	Branch+commit+PR	github_service, pr_service
1.6 Knowledge Layer Structure
Purpose: Configuration intelligence and business-rule engine.

knowledge/
├── __init__.py
├── service.py                        # KnowledgeBaseService (orchestrator)
├── provider.py                       # RepositoryKnowledgeProvider (sole knowledge GitHub reader)
├── versioning.py                     # Registry version control
├── parsers/
│   ├── __init__.py
│   ├── terraform_hcl_parser.py       # Base HCL parser
│   ├── topics_tf_parser.py
│   ├── locals_tf_parser.py
│   ├── glue_tf_parser.py
│   ├── repository_tree_parser.py
│   ├── module_reference_parser.py
│   ├── variable_parser.py
│   └── output_parser.py              # Terraform CLI output → findings
├── registries/
│   ├── __init__.py
│   ├── loader.py                     # Registry loading orchestrator (startup + hot-reload)
│   ├── source_systems_registry.py
│   ├── validation_rules_registry.py
│   ├── validation_messages_registry.py
│   ├── terraform_templates.py
│   ├── repo_patterns_registry.py
│   ├── defaults_registry.py
│   ├── worker_defaults_registry.py
│   ├── job_defaults_registry.py
│   ├── naming_rules_registry.py
│   ├── enterprise_functions_registry.py
│   ├── repository_mapping_registry.py
│   └── constants_registry.py
├── derivers/
│   ├── __init__.py
│   ├── base_deriver.py
│   ├── job_name_deriver.py
│   ├── secret_name_deriver.py        # Kafka secret
│   ├── iam_role_deriver.py
│   ├── worker_config_deriver.py
│   ├── glue_version_deriver.py
│   ├── schedule_deriver.py
│   ├── job_type_deriver.py
│   ├── lh_database_deriver.py
│   ├── s3_paths_deriver.py
│   ├── enterprise_function_deriver.py
│   ├── subgroup_deriver.py
│   ├── template_resolver.py
│   └── priority_resolver.py          # Repo vs KB precedence
├── validators/
│   ├── __init__.py
│   ├── validation_engine.py
│   ├── topic_validator.py
│   ├── job_name_validator.py
│   ├── source_system_validator.py
│   ├── schema_grain_validator.py
│   └── terraform_validator.py        # delegates to CLI
├── templates/
│   ├── __init__.py
│   ├── locals_tf_template.py
│   ├── glue_tf_template.py
│   └── template_engine.py
└── caching/
    ├── __init__.py
    ├── cache_manager.py
    └── invalidation.py
Knowledge Layer Rules
Rule	Detail	Enforcement
No hardcoded rules	All from validation_rules.json	Code review
No hardcoded values	All defaults from registries	Code review
Repository wins	Priority resolver checks repo first (BR-A-10)	priority_resolver
Registries read-only	Immutable JSON	loader
Versioning mandatory	Version check on load	versioning.py
Caching with TTL	per-session + app-lifetime layers	cache_manager
Provider sole reader	Only provider.py reads GitHub for knowledge facts	review
1.7 Database Structure
Purpose: Persistent storage; schema, migrations, constraints.

database/
├── __init__.py
├── engine.py                         # SQLAlchemy async engine
├── session.py                        # AsyncSession factory
├── unit_of_work.py                   # Transaction boundary helper
├── base.py                           # Declarative base
├── schema.sql                        # DDL reference (documentation)
└── migrations/
    ├── env.py
    ├── script.py.mako
    └── versions/
        ├── 001_initial_schema.py     # users
        ├── 002_add_session_tables.py # sessions
        ├── 003_add_draft_tables.py   # drafts, draft_files, draft_glue_jobs
        ├── 004_add_snapshots.py
        ├── 005_add_validation_history.py
        ├── 006_add_pr_metadata.py
        └── 007_add_indexes.py
Core Tables (8 — TAS T6, CQ-08)
Table	Purpose	Key columns
users	Auth identity	id, github_id, github_username, email, created_at, deleted_at
sessions	Session state	id, user_id, environment, current_draft_id, github_token_ref, created_at, updated_at, expires_at
drafts	Draft workspace	id, session_id, environment, status, pr_* fields, is_frozen, change_count, job_count, created_by, audit
draft_files	File changes	id, draft_id, file_path, content, operation, created_at; UNIQUE(draft_id, file_path)
draft_glue_jobs	Job configs	id, draft_id, job_key, env, source_system, schema_grain, topic_name, kafka_secret_name, glue_job_name, iam_role, worker_type, glue_version, number_of_workers, scheduling_mode, job_type, job_version, enterprise_function, subgroup, lh_database, s3_warehouse, s3_checkpoint; UNIQUE(draft_id, job_key)
snapshots	Immutable history	id, draft_id, created_at, snapshot_content (JSON), description; INDEX(draft_id, created_at)
validation_reports	Validation outcomes	id, draft_id, validation_type, status, rule_id, message, internal_context, created_at
pr_metadata	PR tracking	id, draft_id (UNIQUE 1:1), pr_number, pr_url, commit_sha, branch_name, pr_created_by, pr_created_at, conflict_detected, conflict_resolved, created_at
IMPLEMENTATION GAP (CQ-06): drafts.status CHECK values. Backend model uses OPEN/REVIEW/PR_CREATED/ABANDONED; Bible uses DRAFT_EDITING/REVIEW_READY/PR_CREATING/.... Two frozen docs disagree — must reconcile before the CHECK constraint is finalized.

1.8 Prompts Structure
prompts/
├── __init__.py
├── system_prompt.txt
├── loader.py                         # Prompt loading + versioning
├── template_variables.py             # Allowed variables per prompt
└── node_prompts/
    ├── environment_selection.txt
    ├── operation_choice.txt
    ├── source_type.txt
    ├── source_system_selection.txt
    ├── schema_grain_input.txt
    ├── derivation.txt
    ├── review_workspace.txt
    ├── validation.txt
    ├── approval.txt
    ├── conflict_resolution.txt
    ├── recovery.txt
    ├── out_of_scope.txt
    └── pr_success.txt
Prompt	Owner	Modifiable	Approval required
system_prompt.txt	Architecture Owner	No (frozen)	Yes
node_prompts/*	Node Owner	No (frozen)	Yes
Prompt rules: never inline-hardcoded; variable injection only; versioned via # version: header; rule IDs/secrets never embedded.

1.9 Shared Structure
shared/
├── __init__.py
├── types.py            # DraftState, GlueJobConfig, ValidationResult, GitHubToken, PRMetadata, RepositoryFacts
├── constants.py        # ENVIRONMENTS, WORKER_TYPES, JOB_TYPES, ENTERPRISE_FUNCTIONS
├── exceptions.py       # CopilotException hierarchy (canonical — see BACKEND doc §Exceptions)
├── validators.py       # validate_topic_format, validate_job_name_format, validate_source_system_name, validate_schema_grain_format
└── formatters.py       # format_glue_job_name, format_topic_name, format_terraform_path
backend/core/exceptions.py re-exports from shared/exceptions.py — single hierarchy, no duplication.

1.10 Tests Structure
tests/
├── conftest.py
├── unit/               # test_derivers/, test_validators/, test_services/, test_utils/
├── integration/        # test_draft_workflow, test_pr_creation, test_conflict_resolution, test_session_recovery
├── contract/           # test_agent_endpoint, test_response_schemas, test_request_validation
├── e2e/                # test_create_glue_job, test_modify_files, test_multi_operation, test_pr_review_and_approval
├── recovery/           # session/draft/navigation restore
├── failure/            # GitHub down, DB down, Redis down, token expiry, TF CLI missing
├── fixtures/           # sample_repositories/, sample_glue_configs/, sample_github_responses/, database_fixtures.py
└── README.md
Layer	Test type	Coverage	Owner
Knowledge	Unit	100%	Knowledge Owner
Services	Unit + Integration	95%+	Service Owner
API	Contract	100% endpoints	API Owner
Workflows	E2E	All critical paths	Orchestration Owner
1.11 Config / Docker / Scripts / Docs / GitHub
config/
├── settings.py          # DatabaseSettings, GitHubSettings, TerraformSettings, RedisSettings, SecuritySettings, AppSettings
├── logging_config.py
├── redis_config.py
├── alembic.ini
└── .env.example

docker/
├── Dockerfile.backend
├── Dockerfile.frontend
├── docker-compose.yml
├── docker-compose.prod.yml
└── nginx.conf

scripts/
├── setup_dev.sh
├── migrate_db.sh
├── seed_registries.sh
├── validate_architecture.py   # import-linter rule enforcement
├── generate_docs.py
└── performance_test.py

docs/
├── ARCHITECTURE.md  API.md  DATABASE.md  LANGGRAPH.md  KNOWLEDGE_BASE.md
├── DEPLOYMENT.md  OPERATIONS.md  CONTRIBUTING.md  TESTING.md
└── RUNBOOKS/ (incident_response, rollback_procedures, monitoring_setup)

.github/
├── workflows/ (test, lint, security, deploy_dev, deploy_prod, docs)
└── templates/ (PULL_REQUEST_TEMPLATE, ISSUE_TEMPLATE)
1.12 Repository Communication Rules
Frontend:    pages → components → hooks → services → store
             ✗ backend / langgraph / knowledge

Backend api: api → langgraph(builder) | services → repositories → models → database
             ✗ repositories/models directly from api

LangGraph:   nodes → services ; state → shared/core
             ✗ repositories / database (writes) ; ✗ frontend

Knowledge:   provider → github_service + parsers ; engines → registries
             ✗ services / repositories / api / langgraph / frontend

All layers:  → shared / core (leaf)
1.13 Import / Dependency Rules
Allowed:

api → services, schemas, langgraph.graph
api → core
langgraph.nodes → services
langgraph.state → shared, core
services → repositories, knowledge, github_service, shared
knowledge → github_service (via provider), registries, shared, models(read-only)
repositories → models, database, core
models → core
all → shared / core
Forbidden:

repositories ─✗→ services
langgraph ─✗→ repositories / database (writes)
models ─✗→ anything but core
core/shared ─✗→ anything
services ─✗→ api / langgraph
knowledge ─✗→ api / langgraph / repositories
nodes ─✗→ repositories / database
frontend ─✗→ backend internals
AsyncSession ─✗→ graph state (TAS T4)
Circular prevention: import-linter contracts in scripts/validate_architecture.py, enforced in CI. core/shared are the only leaves.

1.14 Naming Conventions
Entity	Convention	Example
Python file	snake_case	draft_repository.py
Python class	PascalCase	DraftRepository
Python function	snake_case	create_draft()
Constant	UPPER_SNAKE	DEFAULT_WORKER_COUNT
Graph node file	snake_case (or _node suffix)	topic_validation.py
Graph state key	snake_case	draft_change_count
DB table	snake_case plural	draft_glue_jobs
DB column	snake_case	created_at
API endpoint	/api/v1/kebab-case	/api/v1/agent/message
React component	PascalCase.tsx	ReviewWorkspace.tsx
React hook	camelCase use	useDraftState()
TS interface	PascalCase (I prefix optional)	IAgentResponse
Registry file	snake_case.json	validation_rules.json
Prompt file	snake_case.txt	out_of_scope.txt
Test file	test_ prefix	test_draft_repository.py
Env var	UPPER_SNAKE MIF_	MIF_DATABASE_URL
Reconciliation note: Sources disagreed on API base (/agent/message vs /api/v1/agent/message). Adopted: /api/v1/... (versioned, more production-ready per Step-4 priority).

1.15 Ownership Model
Component	Owner	Responsibilities
backend/core/ shared/ config/	Architecture Lead	primitives, settings
backend/services/	Service Owner	business logic
backend/repositories/	Data Owner	CRUD, constraints, transactions
backend/models/ database/migrations/	DB/Migration Owner	schema, versioning
backend/api/ backend/schemas/	API/Contract Owner	HTTP contract, DTOs
langgraph/	Orchestration Owner	nodes, state, transitions
knowledge/	Knowledge Owner	registries, derivers, validators, templates
prompts/	Prompt Owner	prompt artifacts
frontend/	Frontend Owner	UI, state
tests/	QA Owner	coverage, CI gates
docs/	Documentation Owner	architecture records
1.16 Golden / Frozen Implementation Rules
SRP: one file = one responsibility. Never combine logic + persistence, or logic + HTTP.
Source of truth hierarchy: GitHub repo (1) > Draft workspace (2) > Registries (3) > Graph state (4).
No hardcoded intelligence: defaults/rules/templates/patterns all in registries.
Immutable frozen artifacts: prompts, registry schema, DB schema (migrations only), graph structure, API contracts.
One PR = one commit (BR-S-1/2).
One session = one active draft (FR-W-2).
Validation before derivation (FR-Q-1, BR-A-8).
Draft is sole PR input — never graph memory.
Untraceable decisions → mark IMPLEMENTATION GAP, never guess.
(Full 110-rule binding set: CLAUDE_RULES.md at repo root — referenced, not duplicated here.)

1.17 References
Document	Content
CPRS v1.0	Functional/product requirements
TAS Reference (T1–T14)	Technology + architecture detail
MIF Implementation Bible	Detailed specifications
MIF Glue Job Creation Process	Terraform output shapes
Version History
Version	Date	Status	Changes
1.0	2026-06-27	FROZEN	Two parallel structures existed
2.0	2026-06-27	FROZEN	Merged; Sonnet structure canonical + Opus core/graph-state/parsers folded in; conflicts flagged
STATUS: FROZEN FOR IMPLEMENTATION. No structural change without architectural review.

