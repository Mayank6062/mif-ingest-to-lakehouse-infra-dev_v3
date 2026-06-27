BACKEND_MODULE_ARCHITECTURE.md
Version: 2.0 (merged) | Status: FROZEN FOR IMPLEMENTATION Last Updated: 2026-06-27 Authoritative inputs (frozen): CPRS v1.0, TAS Reference, MIF Implementation Bible, MIF Glue Job Creation Process Supersedes: Backend Module Architecture v1.0, Final Engineering Package Deliverables 2–8 & Master Implementation Spec Principle: Hexagonal, SRP, DDD-friendly. One module = one responsibility. Services hold ALL business logic; repositories hold ZERO.

2.1 Layer Model (Hexagonal)


   Frontend ──► api/ (HTTP adapter) ──► langgraph/ (orchestration) ──► services/ (business logic)
                                                                          │
                                          ┌───────────────┬──────────────┼───────────────┐
                                          ▼               ▼              ▼               ▼
                                     knowledge/      github_service   repositories/   terraform CLI
                                          │           (outbound)           │
                                     registries/                       models/ → database/
                                          all ──► shared/ + core/ (leaves)
Module	Purpose	May depend on	Must NOT depend on	Lifecycle
core/shared	primitives	nothing	everything else	app singleton
schemas	wire DTOs	core	models, repositories	per-request
api	HTTP boundary	services, schemas, langgraph.graph	repositories, models, database	per-request
langgraph	orchestration	services, state, shared	repositories, database, api	per-session graph
services	business logic	repositories, knowledge, github	api, langgraph	per-request (DI)
knowledge	config intelligence	github_service, registries, shared	api, langgraph, repositories	singleton + per-call
repositories	data access	models, database, core	services, api, langgraph	per-UoW
models	ORM	core	everything else	app lifetime
database	connectivity	core	services, api	app lifetime
2.2 API Layer
2.2.1 Endpoints


POST   /api/v1/agent/message      Single agent message endpoint (primary, CON-API-1)
GET    /api/v1/agent/stream       WebSocket/SSE streaming
GET    /api/v1/auth/github/login  Initiate OAuth
GET    /api/v1/auth/github/callback  OAuth callback (code exchange)
POST   /api/v1/auth/logout        Invalidate session
GET    /api/v1/auth/me            Current user
GET    /api/v1/sessions           List sessions (Today/Yesterday/Previous, FR-H-2)
GET    /api/v1/sessions/{id}      Session detail + draft info
DELETE /api/v1/sessions/{id}      Abandon/archive
GET    /api/v1/internal/drafts/{id}        (service token only — CON-API-2)
POST   /api/v1/internal/validation/run     (service token only)
POST   /api/v1/internal/pr/create          (service token only)
GET    /api/v1/health             Liveness
GET    /api/v1/health/ready       Readiness (DB + Redis)
POST /api/v1/agent/message — request/response

Field	Type	Required	Notes
session_id	UUID	after first message	active session
user_message	string	yes	user text
context.selected_option	string	no	menu selection
context.form_data	object	no	structured input
Response field	Type	Notes
session_id	UUID	
messages[].type	enum	TEXT, FORM, SUMMARY, VALIDATION, CODE_PREVIEW, APPROVAL, PR_SUCCESS
messages[].content	string/object	
messages[].actions[]	array	buttons
draft_summary	object	change_count, job_count, status
navigation_state	object	current path (modify flow)
user_input_required	bool	
Error codes: 400 INVALID_INPUT · 401 UNAUTHORIZED · 404 SESSION_NOT_FOUND · 409 DRAFT_FROZEN (FR-W-6) · 429 RATE_LIMITED · 500 INTERNAL_ERROR · 503 SERVICE_UNAVAILABLE.

2.2.2 Middleware Stack (order)
correlation_middleware — assign/propagate correlation_id + request_id
auth_middleware — validate GitHub token, enrich context (user_id, session_id), 401 on invalid
ratelimit_middleware — per-user (100 req/min on agent endpoint)
LoggingMiddleware — structured req/resp, mask secrets
error_middleware — exception → HTTP per §2.10
CORS
2.2.3 Dependency Injection (dependencies.py)
DIContainer — singleton services (knowledge_base_service, draft_service, github_service, validation_service, terraform_service, …) + repository factories (per-request, scoped to a UoW). Rules: singletons at startup; repositories injected into services; services injected into routes; registries loaded+cached at startup; initialize()/shutdown() lifecycle hooks.

2.3 Schemas (DTOs)
Schema	Purpose	Editable subset
AgentMessageRequest	endpoint input	n/a
AgentMessageResponse	endpoint output	n/a
DraftReviewRequest	review edits {field: value}	per CQ-01
DraftReviewResponse	files[], glue_jobs[], metadata	n/a
GlueJobConfigView	UX-R-1 fields only	hidden fields excluded (UX-R-3)
ValidationResult	status, messages[], rule_id (rule_id never serialized to frontend)	n/a
PRResponse	pr_number, pr_url, commit_sha	n/a
Serialization rules: SecretStr never serialized (SEC-1); bootstrap servers / schema-registry / rule IDs / internal TF values never cross to frontend (UX-R-3); datetimes ISO-8601 UTC; IDs UUID strings.

2.4 Service Layer
Golden rule: Services hold ALL business logic; return domain objects (never ORM); no HTTP semantics; orchestrate repositories + knowledge + github. (Merged note: the Backend-v1 rule "services never call other services" is relaxed to the Final-Package matrix where explicit delegation is required — e.g., validation_service→glue_job_service, conflict_service→draft_service. Allowed delegations are enumerated below; all others forbidden.)

Service Ownership & Allowed Delegation Matrix
Service	Single responsibility	Owns	May call	Forbidden
auth_service	token validation, user binding	user identity	user_repository	drafts, github writes
session_service	session create/restore/archive	session lifecycle, env	session/draft repos	github, terraform
glue_job_service	derivation orchestration + repo validations	derived config, file plan	knowledge_base_service, github_service	draft_service, pr_service
draft_service	draft mutation, undo, materialize, freeze	draft state	draft/file/job repos, snapshot_service, template_engine	github, terraform, knowledge
snapshot_service	immutable snapshot create/restore	snapshots	snapshot_repository	github
navigation_service	conversational repo browse (read)	navigator state	github_service	drafts, derivation
review_service	assemble review payload + diffs	review presentation	draft repos, github_service (diff)	mutation logic
validation_service	orchestrate validations + history	validation outcomes	glue_job_service, terraform_service, validation_repository	draft mutation, pr
terraform_service	CLI init/fmt/validate	TF outcomes	terraform CLI	github, drafts
github_service	all GitHub I/O (read+write)	API calls, retries	(external client)	business rules, repositories
github_oauth_service	OAuth code exchange	tokens	(external)	drafts
pr_service	branch + single commit + PR	PR creation	github_service, draft/pr_metadata repos	derivation, validation rules
conflict_service	rebase / resolution	conflict mechanics	github_service, draft_service, terraform_service	pr_service
2.4.1 GlueJobService — contract


validate_topic_exists(env, source, grain) -> ValidationResult
validate_duplicate_job(env, source, derived_job_name) -> ValidationResult
check_source_exists(env, source) -> bool
derive_all_values(env, source, grain, topic_name, source_exists) -> DerivedGlueJobConfig
plan_file_operations(env, source, source_exists) -> FileOperationPlan
Flow (existing): read <source>/locals.tf (authoritative) + glue.tf (read-only) → fill gaps from KB, repo wins (BR-A-10) → modify locals.tf only (BR-A-12). Flow (new): templates/registries authoritative → create both locals.tf + glue.tf (BR-A-13). Errors: GitHubException→ValidationException(user msg); KnowledgeException→ValidationException("Configuration rules missing").

IMPLEMENTATION GAP (CQ-A1): new-source per-env concretes (bootstrap/schema-registry endpoints, catalog account IDs, assume-role ARNs) + LH DB pattern have no defined origin. New-source derive_all_values cannot complete until resolved — must raise DerivationException, never fabricate.

2.4.2 DraftService — contract


create_or_get_draft(session_id, env) -> Draft
add_glue_job_to_draft(draft_id, config) -> Draft          # atomic: job + files + snapshot + count++
add_file_changes_to_draft(draft_id, path, content, op) -> Draft   # atomic
discard_last_change(draft_id) -> Draft                    # restore previous snapshot → new snapshot
get_draft_for_review(draft_id) -> DraftReviewState        # green/red diffs (FR-W-8)
freeze_draft(draft_id) / unfreeze_draft(draft_id)         # FR-W-6/7
materialize_files(draft_id) -> Dict[path, content]        # for TF validation
Atomicity: snapshot failure rolls back the mutation. Undo exposes no snapshot IDs (FR-W-3).

2.4.3 ValidationService — contract


validate_topic_from_registry(env, source, grain) -> ValidationResult     # delegates GlueJobService; BR-A-8
validate_duplicate_job_from_registry(env, source, job_name) -> ValidationResult
validate_terraform(draft_id) -> ValidationResult                          # FR-Q-2; outcomes shown, rules hidden
get_validation_history(draft_id) -> List[ValidationReport]                # FR-Q-5
2.4.4 GitHubService — contract


list_source_systems(env) -> List[str]            # FR-A-3
read_topics_file(env, source) -> Dict            # BR-A-15 no broker
read_locals_tf(env, source) -> Dict
read_file(path, ref="main") -> str
create_branch(branch_name, base_ref="main")      # BR-S-1
create_commit(branch_name, files, message) -> sha # single commit; Git Data API
create_pull_request(branch_name, title, desc, base_ref) -> PRMetadata
get_repository_head() -> sha                      # conflict detection
handle_merge_conflict(branch_name, base_ref) -> ConflictInfo  # FR-C-2
get_file_diff(path, from_ref, to_ref) -> str      # FR-W-8
Security: token never logged; SecretStr; error messages never expose internal paths.

IMPLEMENTATION GAP (CQ-15): target repo/org from config — value unconfirmed. (CQ-14): prod topic path. (CQ-06): branch key (draft/<draft_id> adopted, flagged).

2.4.5 TerraformService — contract


validate_draft(draft_id, files) -> ValidationResult   # init, fmt -check, validate; temp dir; cleanup
format_code(files) -> Dict[path, content]
Rules TF-001 (init), TF-002 (fmt), TF-003 (validate). Runtime: Terraform CLI ≥1.0; module sources reachable.

2.4.6 ConflictService — contract


detect_conflict(draft_id, branch_name, base_ref) -> ConflictDetectionResult  # FR-C-1/2
apply_auto_resolution(draft_id, branch_name, base_ref) -> bool                # rebase only, FR-C-2
resolve_conflict(draft_id, branch_name, resolution, strategy) -> None         # FR-C-3/4/5; one commit (BR-S-2)
Strategies: incoming | current | both | manual. Finalize: commit --amend + push --force-with-lease.

IMPLEMENTATION GAP (CQ-A4): Phase-1 depth (full resolution vs detection-only).

2.4.7 KnowledgeBaseService — contract


get_derivation_rule(rule_key) -> DerivationRule
get_validation_rule(rule_key) -> ValidationRule
get_template(template_key) -> str
get_registry(registry_name) -> Dict
derive_all(context) -> DerivedGlueJobConfig          # orchestrates derivers + priority_resolver
Only KnowledgeDerivationNode (via glue_job_service) triggers derivation. KB contents never enter graph state (TAS T4) — references only.

2.5 Knowledge Layer (engines)
Component	Single responsibility	Calls
RepositoryKnowledgeProvider	GitHub → RepositoryFacts (sole knowledge reader)	github_service, parsers
RegistryLoader	load/validate/version/hot-reload JSON	filesystem
DerivedValueEngine	compute config values	priority_resolver, template_engine, registries
ValidationEngine	apply rules → pass/fail + rule ID	registries
RuleEngine / priority_resolver	deterministic precedence	registries, provider facts
TemplateEngine	render locals.tf/glue.tf (called only by DraftWorkspace)	registries
ProvenanceService	stamp versions/sources	—
parsers/*	.tf text → structured data	—
Derivers: JobName, KafkaSecret, IAMRole, GlueVersion, WorkerConfig, Database, S3Paths, Schedule, JobType, EnterpriseFunction, SubGroup, TemplateResolver, PriorityResolver. Each: pure function, raises DerivationException on missing input, never fabricates gap-flagged values.

Priority matrix (precedence): Repository(1) > Draft(2) > Registries(3) > Graph state(4). Repo wins on conflict (BR-A-10). User input governs env/source/grain + dropdown fields.

Registries (12)
validation_rules.json, validation_messages.json, defaults.json, repo_patterns.json, terraform_templates.json, source_systems.json, constants.json, environment_rules.json, worker_defaults.json, job_defaults.json, naming_rules.json, enterprise_functions.json, repository_mapping.json.

Load order: constants → validation_messages → validation_rules → defaults/worker/job → repo_patterns/environment/naming → terraform_templates → source_systems → enterprise_functions/repository_mapping.

Caching: registries app-lifetime (hot-reload on file change); source list per-session; file contents never cached across validations (Bible §5.3).

Confirmed values: worker_type G.1X/G.2X/G.4X default G.1X; sink iceberg; catalog glue; subgroup APAC/NA/LATAM default APAC; job_type unified; job_version 0.3.0; glue_version 5.1; stop_before_start true; sink_trigger availableNow; assume_session_name mif-glue-iceberg; topic {env}.{source}.{grain}.raw; job name kafka-to-iceberg-batch-{source}-{grain}; kafka secret minerva-${env}-corp-mif-{source}-gluejob-sa-cc-api-creds.

IMPLEMENTATION GAPS: CQ-03 (enterprise set SPEC vs CORP), CQ-04 (workers default 1 vs 4, max 10), CQ-05 (run mode Manual vs daily 1AM), CQ-A1 (LH DB pattern + new-source concretes + corp literal), CQ-14 (prod topic path). All held as gap tokens; loader rejects use until set.

2.6 LangGraph (orchestration)
Final node roster (CQ-07)
OAuth, SessionManager, Environment, Operation, SourceType, SourceSystem, SchemaGrain, TopicValidation, DuplicateJobValidation, KnowledgeDerivation, DraftWorkspace, ModifyFile, ReviewWorkspace, TerraformValidation, Approval, PRCreation, ConflictResolution, OutOfScope, Placeholder. (IntentRouter = routing module, not a node.)

Transition matrix (authoritative)


OAuth→Session→Environment→Operation
Operation──create──►SourceType──►SourceSystem──►SchemaGrain──►TopicValidation
Operation──modify──►ModifyFile──►DraftWorkspace
SourceType──non-kafka──►Placeholder──►Operation
TopicValidation──FAIL──►Operation   ──PASS──►DuplicateJobValidation
DuplicateJobValidation──FAIL──►Operation  ──PASS──►KnowledgeDerivation──►DraftWorkspace
DraftWorkspace──►Operation (multi-op loop)
Operation──review/PR──►ReviewWorkspace──►TerraformValidation
TerraformValidation──FAIL──►ReviewWorkspace  ──PASS|CQ-13b──►Approval
Approval──yes──►PRCreation ──no──►Review/Operation
PRCreation──conflict──►ConflictResolution──►PRCreation
PRCreation──success──►END
OutOfScope◄──any node intent──►return to prior context
HITL interrupts (interrupt_before): OAuth callback, Environment, Operation, SourceType, SourceSystem, SchemaGrain, ReviewWorkspace, Approval, ConflictResolution(manual). Forbidden transitions: any node→PRCreation without Approval; derivation before both validations; any edit while draft frozen (FR-W-6). Per-node specs: each node carries Purpose/Owner/Input/Output/Entry/Exit/Interrupt/Retry/Failure/Services-called/Services-forbidden/Transitions per Bible §3.2 (inherited verbatim) + gap-fills for ModifyFile and ConflictResolution.

2.7 Graph State (TAS T4)
Stores references only — never KB contents, never AsyncSession, never raw token.

Group	Key fields	Persistence	Owner
Auth	user_id, github_username, github_token_ref, is_authenticated	Postgres/checkpoint	OAuth
Session	session_id, current_step, conversation_history_ref	Postgres/checkpoint	Session
Environment	environment	Postgres	Environment
Navigation	navigator_state (current_path, breadcrumb[], visited[], open_file)	Postgres	SourceSystem/Modify
Workflow	selected_operation, source_type, source_system, source_exists, schema_grain, topic_name	checkpoint	per node
Derived	derived_values (renamed from workspace.defaults — CQ-12), file_plan	draft	KnowledgeDerivation
Knowledge refs	kb_version, rule_set_version, template_version, registry_version, provenance_reference, knowledge_context_id	checkpoint	KnowledgeDerivation
Draft	draft_id, draft_change_count, draft_job_count, snapshot_id, draft_status	Postgres	DraftWorkspace
Validation	topic/duplicate/terraform results, validation_messages[]	Postgres	validation nodes
PR	user_approved, pr_url, pr_number, commit_sha, branch_name	checkpoint/Postgres	Approval/PRCreation
Conflict	draft_base_sha, repo_head_sha, conflict_files[]	Postgres	PRCreation/Conflict
System	correlation_id, graph_version	logs/checkpoint	middleware/system
IMPLEMENTATION GAP (CQ-11): KnowledgeState object removed (references only) — confirm. (CQ-12): workspace.defaults → derived_values — confirm.

2.8 Models (ORM — 8 entities)
ORM definitions per Backend-v1 §2.5 (canonical): User, Session, Draft, DraftFile, DraftGlueJob, Snapshot, ValidationReport, PRMetadata.

String(36) UUID PKs; audit columns (created_at, updated_at, created_by); soft-delete via deleted_at (users) / status (drafts).
Constraints: UNIQUE(draft_id, file_path), UNIQUE(draft_id, job_key), pr_metadata.draft_id UNIQUE 1:1.
Indexes: sessions(user_id), sessions(current_draft_id), draft_glue_jobs(draft_id), draft_glue_jobs(draft_id, job_key), draft_files(draft_id, path), snapshots(draft_id, created_at), validation_reports(draft_id, created_at).
Optimistic locking: drafts.version, sessions.version (WHERE version = expected).
draft_glue_jobs carries source_system/schema_grain at job level so multiple sources fit one draft.
IMPLEMENTATION GAP (CQ-06): drafts.status CHECK enum — Backend OPEN/REVIEW/PR_CREATED/ABANDONED vs Bible DRAFT_EDITING/REVIEW_READY/PR_CREATING/PR_CREATED/PR_FAILED/CONFLICT_DETECTED/ABANDONED. Reconcile before constraint freeze.

2.9 Repository Layer
Golden rule: ZERO business logic; CRUD + transactions + optimistic locking only; return raw/domain data; raise repository exceptions.

BaseRepository: create, read, update, delete (soft), exists, list_by_filters. Concrete repos per Backend-v1 §2.4 (User, Session, Draft, DraftFile, DraftGlueJob, Snapshot, Validation, PRMetadata) with their listed methods.

Transaction patterns: draft mutation (job/file → snapshot → counter, atomic); undo (load prev snapshot → new state → new snapshot, atomic); PR creation (freeze → create PR → pr_metadata; on fail unfreeze); session recovery (read-only).

2.10 Exception Architecture


CopilotException (shared/exceptions.py base; ApplicationException = alias)
├── AuthenticationException
├── SessionException
├── KnowledgeException
│   ├── RegistryLoadException
│   ├── RegistryValidationException
│   ├── DerivationException
│   ├── TemplateRenderException
│   ├── ParserException
│   └── PriorityResolutionException
├── ValidationException
├── RepositoryException
├── DraftException
├── GitHubException
├── TerraformException
├── PRException
└── ConflictException
Exception	User message	Log	Retry	HTTP
AuthenticationException	"Session expired. Please sign in again."	WARN	re-auth	401
SessionException	"We couldn't restore your session."	ERROR	no	404/500
RegistryLoad/Validation	"Service unavailable."	ERROR	no (fatal startup)	503
DerivationException	"We need more information to continue."	ERROR	no	500
TemplateRenderException	"Could not generate configuration."	ERROR	no	500
ParserException	"We couldn't read a repository file."	ERROR	no	502
PriorityResolutionException	"Configuration conflict detected."	ERROR	no	500
ValidationException	rule message (TR-001 etc.)	INFO	re-validate	422
RepositoryException	"Something went wrong. Please try again."	ERROR	tx retry	500
DraftException	"Your draft is being processed."	WARN	optimistic retry	409
GitHubException	"GitHub is unavailable. Retrying..."	WARN	3× backoff	502/429
TerraformException	"Validation could not run."	ERROR	CLI retry	500
PRException	"Could not create the pull request."	ERROR	idempotent retry	502
ConflictException	"There's a conflict to resolve."	WARN	re-resolve	409
Rules: never catch-and-swallow; always log+propagate/recover; every exception carries correlation_id; user messages never expose paths/rule logic/secrets.

2.11 Logging, Observability & Security
Identifiers (always present): correlation_id, request_id, trace_id, node_id, session_id, draft_id, pr_id, user_id.

Log categories: structured (req/resp, node exec), business (session/draft/PR/validation events), audit (who/when/what — SEC-2, immutable), security (auth, token refresh — masked), knowledge (registry load/version, provenance), parser, github (endpoint/code/latency/retries, no token), terraform, LLM (masked prompt, token count, latency).

Metrics: counters (sessions_created_total, prs_created_total, validations_run_total, auth_failures_total); histograms (api_response_seconds, pr_creation_seconds, validation_seconds, node_exec_seconds); gauges (active_sessions, draft_size_bytes, db_pool_active, redis_memory_used).

Alerts: error rate >1%, PR success <95%, GitHub error >5%, DB pool >80%, Redis >80%. Latency/retention targets — IMPLEMENTATION GAP (CQ-A8).

Tracing: span per node + per external call; OTEL OUT OF SCOPE Phase-1 (correlation-id tracing now, OTEL-ready structure).

Security: OAuth 2.0 Authorization Code; session-owner binding on every request; SecretStr + masking (SEC-1); audit trail (SEC-2); RBAC/Vault deferred (SCOPE-11, SEC-3). Token encryption at rest + Pydantic v1/v2 — IMPLEMENTATION GAP (CQ-A7).

2.12 DTO Mapping Chain


HCL → parsers → RepositoryFacts → derivers/priority → DerivedGlueJobConfig
→ draft_service → ORM (DraftGlueJob/DraftFile/Draft) → repositories → Domain (shared/types)
→ services → Graph State (draft_id + counters + derived_values)
→ api → API DTO (schemas/) → Frontend DTO (types/) → React props
Rules: repositories return domain objects (never ORM); graph state holds only draft_id+counters+derived_values; secrets/hidden fields stripped before API DTO; diffs computed server-side in review_service (engine scope CQ-09); editable subset gated by CQ-01.

2.13 Production Standards (engineering)
Domain	Standard
Configuration	Pydantic Settings; env MIF_*; no hardcoded config
Retry	GitHub/DB transient backoff, max 3
Caching	per §2.5; file reads never cached across validations
Feature flags	validation toggles, diff engine (CQ-09), conflict depth (CQ-A4)
Versioning	API/DTO version-stable (/api/v1); registry versions stamped
Testing	Unit/Integration/Contract/Conversation/Recovery/Failure/Performance/Acceptance
CI gates	build, unit, integration, contract, security scan, smoke, acceptance
2.14 Backend Definition of Done
 All services unit + integration tested
 All endpoints contract-tested (CT-01…CT-05)
 Migrations frozen, up/down tested
 No unhandled exceptions; all mapped per §2.10
 Structured logging; secrets masked
 DI configured; registries loaded at startup
 Import-linter rules pass (§Repository doc 1.13)
 GitHub token handling secure (SecretStr)
 Rate limiting active
 No PENDING blocker CQ unresolved for the touched feature
2.15 Consolidated Implementation Gaps
CQ	Gap	Affects
CQ-01	Per-field review editability	schemas, review_service, frontend
CQ-02	Topic editable by asking agent	schema_grain node
CQ-03	Enterprise set SPEC vs CORP	enterprise_functions.json
CQ-04	Workers default/max	worker_defaults.json
CQ-05	Run mode default	scheduling defaults
CQ-06	Draft status enum names	drafts.status CHECK, state machine
CQ-07	Node count "18" reconciliation	langgraph
CQ-08	Table count 8 vs 19	models/migrations
CQ-09	Diff engine Phase-1	review_service, DiffViewer
CQ-13b	TF validation mandatory before PR	approval node, state machine
CQ-14	Prod topic path (no prod folder exists)	github_service, repo_patterns
CQ-15	Target repo identity	github_service config
CQ-A1	New-source concretes + LH DB pattern + corp literal	glue_job_service, derivers, templates
CQ-A4	Conflict depth	conflict_service
CQ-A5	Transformer/sink settings shown/editable	review
CQ-A6	Modify-files guardrails	navigation_service, modify_file node
CQ-A7	Token encryption / Pydantic version	core/security, config
CQ-A8	NFR targets, retention	observability
CQ-A2	project_information/cell1–cell8 contents	may carry CQ-A1 concretes
Version History
Version	Date	Status	Changes
1.0	2026-06-27	FROZEN	Two parallel backend designs existed
2.0	2026-06-27	FROZEN	Merged; Backend-v1 ORM/method detail + Final-Package services/knowledge/exceptions/state/DTO/observability folded in; service delegation matrix reconciled; conflicts flagged
STATUS: FROZEN FOR IMPLEMENTATION. No deviation without architectural review.