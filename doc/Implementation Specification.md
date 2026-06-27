MIF Infrastructure Copilot — Master Implementation Specification
Version: 1.0 Status: FROZEN FOR IMPLEMENTATION Last Updated: 2026-06-27 Role: Principal Enterprise Architect — Final Architecture Completion Authoritative (frozen) inputs: CPRS v1.0, TAS Reference, MIF Implementation Bible, Repository Master Structure, Backend Module Architecture, MIF Glue Job Creation Process

Rule of this document: Extends — never redesigns — the frozen documents. Every unresolved item from the source corpus is carried forward as IMPLEMENTATION GAP — requires clarification (CQ-xx), never silently resolved.

MASTER TABLE OF CONTENTS
Doc	Title
1	Knowledge Base Specification
2	LangGraph Node Specification
3	Graph State Specification
4	Prompt Library Specification
5	DTO Mapping Specification
6	Exception Architecture
7	Logging & Observability Specification
Cross-cutting gap register (carried into every document): CQ-01 (field editability), CQ-02 (topic editability), CQ-03 (enterprise function set), CQ-04 (max workers/default), CQ-05 (run mode default), CQ-06 (draft state names), CQ-07 (node count), CQ-08 (table count), CQ-09 (diff engine), CQ-13b (TF gate), CQ-14 (prod topic path), CQ-15 (target repo), CQ-A1 (new-source concretes + LH DB pattern), CQ-A4 (conflict depth), CQ-A5 (transformer settings), CQ-A6 (modify guardrails), CQ-A7 (token encryption/pydantic), CQ-A8 (NFR targets), CQ-A2 (project_information/cell1–cell8).

DOCUMENT 1 — KNOWLEDGE BASE SPECIFICATION
Version: 1.0 | Status: FROZEN | Owner: Knowledge Owner References: Bible §5, TAS T5/T10, Process doc, Repository Master Structure §1.5

1.1 Knowledge Folder Structure
Reconciling Repository Master Structure §1.5 (knowledge/) with the gap-fill needs of this spec. The canonical tree is the §1.5 tree extended (never replaced) with provider/, loader/, version/, priority/ as explicit subfolders.



knowledge/
├── __init__.py
├── service.py                         # KnowledgeBaseService (orchestrator)
├── provider/
│   ├── __init__.py
│   ├── repository_knowledge_provider.py
│   └── fact_model.py                  # RepositoryFacts dataclasses
├── registries/
│   ├── __init__.py
│   ├── loader.py                      # delegates to loader/ lifecycle
│   ├── source_systems_registry.py
│   ├── validation_rules_registry.py
│   ├── terraform_templates.py
│   ├── repo_patterns_registry.py
│   ├── defaults_registry.py
│   ├── constants_registry.py
│   ├── environment_rules_registry.py
│   ├── worker_defaults_registry.py
│   ├── job_defaults_registry.py
│   ├── naming_rules_registry.py
│   └── repository_mapping_registry.py
├── derivers/
│   ├── __init__.py
│   ├── base_deriver.py
│   ├── job_name_deriver.py
│   ├── iam_role_deriver.py
│   ├── kafka_secret_deriver.py
│   ├── glue_version_deriver.py
│   ├── worker_config_deriver.py
│   ├── database_deriver.py
│   ├── s3_paths_deriver.py
│   ├── schedule_deriver.py
│   ├── enterprise_function_deriver.py
│   ├── subgroup_deriver.py
│   ├── template_resolver.py
│   └── priority_resolver.py
├── validators/
│   ├── __init__.py
│   ├── validation_engine.py
│   ├── topic_validator.py
│   ├── job_name_validator.py
│   ├── source_system_validator.py
│   ├── schema_grain_validator.py
│   └── terraform_validator.py
├── parsers/
│   ├── __init__.py
│   ├── terraform_hcl_parser.py        # base HCL parser
│   ├── topic_tf_parser.py
│   ├── locals_tf_parser.py
│   ├── glue_tf_parser.py
│   ├── repository_tree_parser.py
│   ├── module_reference_parser.py
│   ├── variable_parser.py
│   └── output_parser.py
├── templates/
│   ├── __init__.py
│   ├── locals_tf_template.py
│   ├── glue_tf_template.py
│   └── template_engine.py
├── cache/
│   ├── __init__.py
│   ├── cache_manager.py
│   └── invalidation.py
├── loader/
│   ├── __init__.py
│   └── registry_loader.py             # startup + hot reload lifecycle
├── version/
│   ├── __init__.py
│   └── versioning.py
├── priority/
│   ├── __init__.py
│   └── priority_matrix.py             # encodes §1.7 matrix
└── exceptions.py
Folder responsibilities:

Folder	Single responsibility	Consumes	Forbidden to import
provider/	GitHub → structured facts (sole knowledge GitHub reader)	github_service, parsers/	services, repositories
registries/	Typed access to one JSON each	loader/	derivers, validators
derivers/	One value per deriver	registries, provider facts, priority	persistence, api
validators/	Apply rules → result+ID	registries	derivers, drafts
parsers/	.tf text → structured data	none	everything
templates/	Render locals.tf/glue.tf	registries	persistence
cache/	TTL + invalidation	core	derivers
loader/	Load/validate/hot-reload registries	filesystem	derivers
version/	Stamp + check registry versions	none	derivers
priority/	Encode precedence matrix	none	persistence
1.2 Every Registry — Complete JSON Schema
For each: Purpose | Owner | Version | Schema | Example | Validation Rules | Relationships | Load Order | Caching Rules.

1.2.1 validation_rules.json
Purpose: All validation rules with stable IDs. Owner: Knowledge Owner. Version: semver in version.
Schema:
json


{
  "version": "1.0.0",
  "rules": [
    {
      "id": "TR-001",
      "category": "topic",
      "field": "topics_file",
      "condition": "file_exists",
      "message_key": "TR-001",
      "severity": "block"
    },
    {
      "id": "TR-002",
      "category": "topic",
      "field": "schema_grain",
      "condition": "grain_present_in_topics_file",
      "message_key": "TR-002",
      "severity": "block"
    },
    {
      "id": "JR-001",
      "category": "job",
      "field": "glue_job_name",
      "condition": "job_key_absent_in_locals",
      "message_key": "JR-001",
      "severity": "block"
    },
    { "id": "TF-001", "category": "terraform", "field": "init",     "condition": "terraform_init_succeeds",  "message_key": "TF-001", "severity": "block" },
    { "id": "TF-002", "category": "terraform", "field": "fmt",      "condition": "terraform_fmt_clean",      "message_key": "TF-002", "severity": "block" },
    { "id": "TF-003", "category": "terraform", "field": "validate", "condition": "terraform_validate_clean", "message_key": "TF-003", "severity": "block" }
  ]
}
Validation: unique id; category ∈ {topic,job,terraform,file}; message_key must exist in validation_messages.json.
Relationships: message_key → validation_messages.json. Load order: 3 (after messages). Caching: app lifetime, hot-reload.
1.2.2 validation_messages.json
Purpose: User-facing strings (Bible §9.6). Owner: Knowledge Owner.
json


{
  "version": "1.0.0",
  "messages": {
    "TR-001": "Source system not configured.",
    "TR-002": "Please create the topic first.",
    "JR-001": "Glue Job already exists.",
    "TF-001": "Terraform initialization failed: {detail}",
    "TF-002": "Terraform formatting issues detected in {file}",
    "TF-003": "Terraform validation failed: {detail}"
  }
}
Validation: every message_key referenced by validation_rules.json present. Load order: 2.
1.2.3 defaults.json
Purpose: Default scalar values for derivation. Owner: Knowledge Owner.
json


{
  "version": "1.0.0",
  "defaults": {
    "worker_type": "G.1X",
    "glue_version": "5.1",
    "job_type": "unified",
    "job_version": "0.3.0",
    "sink_type": "iceberg",
    "sink_catalog_type": "glue",
    "sink_trigger": "availableNow",
    "stop_before_start": true,
    "assume_session_name": "mif-glue-iceberg",
    "enterprise_function": "AGTR",
    "subgroup": "APAC",
    "transformer1": "timestamp",
    "transformer1_column": "processing_timestamp",
    "transformer1_value_format": "json",
    "transformer2": "kafka_unpack",
    "transformer2_metadata_column": "__metadata__",
    "sink_transformer1": "kafka_split"
  }
}
IMPLEMENTATION GAP (CQ-04): number_of_workers default — Process doc says 1, examples use 4. NOT placed in defaults.json until resolved. IMPLEMENTATION GAP (CQ-05): scheduling_mode default — Process: Manual; CPRS narrative: daily 1AM. NOT placed until resolved.

Validation: worker_type ∈ worker_defaults.allowed. Load order: 4.
1.2.4 repo_patterns.json
Purpose: Repository path patterns. Owner: Knowledge Owner.
json


{
  "version": "1.0.0",
  "patterns": {
    "topic_file_dev": "confluent_minerva_dev/topics_{source}.tf",
    "topic_file_prod": "IMPLEMENTATION_GAP_CQ-14",
    "source_locals": "{source}/locals.tf",
    "source_glue": "{source}/glue.tf"
  }
}
IMPLEMENTATION GAP (CQ-14): topic_file_prod — no confluent_minerva_prod/ exists in the target repo; pattern undefined. Value held as literal gap token; loader rejects use until set.

Load order: 5.
1.2.5 terraform_templates.json
Purpose: Shapes for generated locals.tf entry + glue.tf module block (must match Process §11–12 / TAS T10 exactly). Owner: Knowledge Owner.
json


{
  "version": "1.0.0",
  "locals_glue_jobs_entry": {
    "job_type": "{job_type}",
    "job_version": "{job_version}",
    "glue_version": "{glue_version}",
    "number_of_workers": "{number_of_workers}",
    "worker_type": "{worker_type}",
    "stop_before_start": true,
    "trigger_schedule_optional": "{trigger_schedule}",
    "glue_job_arguments": {
      "--source": "kafka",
      "--source_kafka_endpoint": "local.kafka_bootstrap_endpoint[local.env]",
      "--source_kafka_secret_name": "{kafka_secret_name}",
      "--source_kafka_topic": "{topic_name}",
      "--transformer1": "timestamp",
      "--transformer1_column": "processing_timestamp",
      "--transformer1_value_format": "json",
      "--transformer2": "kafka_unpack",
      "--transformer2_metadata_column": "__metadata__",
      "--sink_transformer1": "kafka_split",
      "--sink_transformer1_schema_registry_endpoint": "local.schema_registry_endpoint[local.env]",
      "--sink_transformer1_secret_name": "{kafka_secret_name}",
      "--sink": "iceberg",
      "--sink_iceberg_catalog_type": "glue",
      "--sink_iceberg_catalog_id": "local.miw_account_id[local.env]",
      "--sink_iceberg_database": "{lh_database}",
      "--sink_iceberg_warehouse": "{s3_warehouse}",
      "--sink_iceberg_checkpoint_dir": "{s3_checkpoint}",
      "--sink_iceberg_assume_role_arn": "{assume_role_arn}",
      "--sink_iceberg_assume_session_name": "mif-glue-iceberg",
      "--sink_trigger": "availableNow"
    }
  },
  "glue_tf_module_block": {
    "for_each": "local.glue_jobs",
    "source": "git::https://git.cglcloud.com/mayank/mif-ingest-to-lakehouse-infra-dev.git/mayank/glue_job?ref=main",
    "lookups": ["glue_version","job_type","job_version","topic_name","stop_before_start","number_of_workers","worker_type","extra_py_files","trigger_schedule","glue_job_arguments","secretsmanager_secret_name"]
  }
}
IMPLEMENTATION GAP (CQ-A1): {assume_role_arn}, the catalog account id, bootstrap/schema-registry endpoints for NEW sources have no defined origin. Template variables exist but their source is unspecified. Load order: 6.

1.2.6 source_systems.json
Purpose: Cached catalog (supplementary; repo wins). Owner: Knowledge Owner.
json


{
  "version": "1.0.0",
  "sources": {
    "saptcc": { "known_grains": ["multi-1"], "discovered_from": "repo_scan" },
    "saptce": { "known_grains": [], "discovered_from": "repo_scan" }
  }
}
Authority: supplementary; BR-A-10 repo wins. Load order: 7 (or rebuilt at session start).
1.2.7 constants.json
json


{
  "version": "1.0.0",
  "constants": {
    "kafka_secret_pattern": "minerva-${env}-corp-mif-{source}-gluejob-sa-cc-api-creds",
    "topic_format": "{env}.{source}.{grain}.raw",
    "job_name_format": "kafka-to-iceberg-batch-{source}-{grain}",
    "sink_type": "iceberg",
    "catalog_type": "glue"
  }
}
IMPLEMENTATION GAP (CQ-A1): literal corp in the secret pattern vs enterprise function — unresolved. Load order: 1 (foundational).

1.2.8 environment_rules.json
json


{
  "version": "1.0.0",
  "environments": {
    "dev": { "allowed": true, "topic_path_key": "topic_file_dev" },
    "prod": { "allowed": true, "topic_path_key": "topic_file_prod" }
  }
}
IMPLEMENTATION GAP (CQ-14): prod.topic_path_key resolves to gap token. Load order: 5.

1.2.9 worker_defaults.json
json


{
  "version": "1.0.0",
  "worker_type": { "allowed": ["G.1X","G.2X","G.4X"], "default": "G.1X" },
  "number_of_workers": { "allowed_max": 10, "default": "IMPLEMENTATION_GAP_CQ-04" }
}
IMPLEMENTATION GAP (CQ-04): default 1 (Process) vs 4 (examples).

1.2.10 job_defaults.json
json


{
  "version": "1.0.0",
  "job_type": { "allowed": ["unified","unified_batch","kafka_to_iceberg"], "default": "unified" },
  "job_version": { "default": "0.3.0" },
  "glue_version": { "default": "5.1" },
  "sink_trigger": { "default": "availableNow" },
  "stop_before_start": { "default": true }
}
1.2.11 naming_rules.json
json


{
  "version": "1.0.0",
  "topic": "{env}.{source}.{grain}.raw",
  "job_name": "kafka-to-iceberg-batch-{source}-{grain}",
  "kafka_secret": "minerva-${env}-corp-mif-{source}-gluejob-sa-cc-api-creds",
  "lh_database": "IMPLEMENTATION_GAP_CQ-A1"
}
IMPLEMENTATION GAP (CQ-A1): LH DB pattern conflict — lh_<source_hyphenated>_raw_{env} (Process header) vs minerva_dev_src_agtr_saptce_prd_raw_db / lh_cdp_sap_tc1_raw_dev (Process §8 examples).

1.2.12 enterprise_functions.json
json


{
  "version": "1.0.0",
  "allowed": "IMPLEMENTATION_GAP_CQ-03",
  "default": "AGTR",
  "subgroup": { "allowed": ["APAC","NA","LATAM"], "default": "APAC" }
}
IMPLEMENTATION GAP (CQ-03): AGTR/FOOD/SPEC (Process) vs AGTR/FOOD/CORP (CPRS).

1.2.13 repository_mapping.json
json


{
  "version": "1.0.0",
  "target_repository": "IMPLEMENTATION_GAP_CQ-15",
  "org": "IMPLEMENTATION_GAP_CQ-15",
  "base_branch": "main",
  "branch_pattern": "draft/{draft_id}"
}
IMPLEMENTATION GAP (CQ-15): target repo identity; whether _v3 is target or separate. IMPLEMENTATION GAP (CQ-06): branch key (session_id vs draft_id) — draft_id adopted as working position per Bible §10.3, flagged.

1.2.14 Registry Load Order (authoritative)


1. constants.json
2. validation_messages.json
3. validation_rules.json
4. defaults.json / worker_defaults.json / job_defaults.json
5. repo_patterns.json / environment_rules.json / naming_rules.json
6. terraform_templates.json
7. source_systems.json (or rebuilt from repo scan)
8. enterprise_functions.json / repository_mapping.json
1.3 Knowledge Derivers
Each: Purpose | Input | Output | Repository Usage | Registry Usage | Priority Rules | Failure Behaviour | Example.

Deriver	Purpose	Input	Output	Repo usage	Registry usage	Priority	Failure	Example
JobNameDeriver	Build job key	source, grain	kafka-to-iceberg-batch-{source}-{grain}	uniqueness check (existing)	naming_rules	repo wins on uniqueness	duplicate → block JR-001	kafka-to-iceberg-batch-saptce-multi-1
IAMRoleDeriver	Resolve IAM role	source, env, source_exists	role/arn	existing→locals.tf	naming_rules	repo > registry	new + unspecified → GAP CQ-A1	from saptcc/locals.tf
KafkaSecretDeriver	Secret name	source, env	secret name	existing→locals.tf	constants.kafka_secret_pattern	repo > pattern	n/a	minerva-dev-corp-mif-saptce-gluejob-sa-cc-api-creds
GlueVersionDeriver	Glue version	source, source_exists	5.1	existing→locals.tf	job_defaults	repo > default	n/a	5.1
WorkerConfigDeriver	worker type+count	source, source_exists	type, count	existing→locals.tf	worker_defaults	repo > default	count default GAP CQ-04	G.1X, ?
DatabaseDeriver	LH DB name	source, env	db name	existing→locals.tf	naming_rules.lh_database	repo > pattern	pattern GAP CQ-A1	gap
S3PathDeriver	warehouse+checkpoint	source, env	two S3 prefixes (end /)	existing→locals.tf	terraform_templates	repo > pattern	new concretes GAP CQ-A1	s3://minerva-dev-src-dev/current/prd/raw/sap_tce/
ScheduleDeriver	mode + cron	NL answer	mode, cron(...)	n/a	scheduling_defaults	user > default	default GAP CQ-05	"every day 1 AM" → cron(0 1 * * ? *)
EnterpriseFunctionDeriver	EF value	user/dropdown	EF	n/a	enterprise_functions	user > default	set GAP CQ-03	AGTR
SubGroupDeriver	subgroup	user/dropdown	subgroup	n/a	enterprise_functions.subgroup	user > default	n/a	APAC
TemplateResolver	select+populate template	derived values, source_exists	rendered TF	n/a	terraform_templates	n/a	missing var → KnowledgeException	locals entry
PriorityResolver	apply precedence	candidate values from all sources	resolved value	provider facts	priority_matrix	§1.7	unresolved → raise	repo overrides registry
BaseDeriver contract: pure function; derive(context) -> value; no persistence; raises DerivationException (subclass of KnowledgeException) on missing inputs; never fabricates values flagged as gaps.

1.4 Repository Knowledge Provider
Aspect	Specification
Repository Scan	List root folders via github_service.list_source_systems; a folder = a source (BR-A-14). Read confluent_minerva_{env}/topics_{source}.tf, {source}/locals.tf, {source}/glue.tf on demand.
Caching	Source list cached per-session; file contents NEVER cached across validations (freshness critical, Bible §5.3).
Normalization	Parsers convert HCL → RepositoryFacts dataclasses (fact_model.py).
Fact Model	RepositoryFacts{ sources: list[str], existing_jobs: dict[source, list[job_key]], topic_grains: dict[source, list[grain]], file_contents: dict[path,str], base_sha: str }.
Fact Ownership	Provider is the sole knowledge GitHub reader; NavigationService reads separately for browsing.
Refresh Strategy	Source list refreshed on session start / explicit refresh; validation-time reads always fresh.
Invalidation	New session, "Start Over", manual refresh invalidate source-list cache.
1.5 Repository Parsers
For each: Input | Output | Supported Objects | Error Handling | Validation | Example.

Parser	Input	Output	Supported objects	Error handling	Validation	Example
TerraformHCLParser (base)	.tf text	AST/dict	blocks, maps, attrs	malformed → ParserException	balanced braces	generic
TopicTFParser	topics_<src>.tf	list of topic names+grains	topic strings	missing → caller blocks	.raw suffix	dev.saptcc.multi-1.raw
LocalsTFParser	locals.tf	glue_jobs map + locals	job keys, per-job values	invalid map → ParserException	unique keys	extract worker_type
GlueTFParser	glue.tf	module block + lookups	for_each, source URL, lookups	n/a (read-only)	module present	module wiring
RepositoryTreeParser	folder listing JSON	tree nodes (folder/file)	dirs, files	partial → mark incomplete	path normalization	saptcc/
ModuleReferenceParser	glue.tf module block	source URL + ref	git source, ref	bad URL → ParserException	URL scheme	?ref=main
VariableParser	interpolations	resolved/lookup refs	local.x[local.env]	unknown ref → keep literal	known locals	local.env
OutputParser	terraform CLI stdout/stderr	structured findings	errors, warnings, file refs	non-zero exit → FAIL findings	rule-id mapping	TF-003 detail
1.6 Registry Loader
Lifecycle phase	Specification
Startup	Load all registries in §1.2.14 order; validate schema + cross-references; stamp versions into provenance. Fail-fast on any gap token used in an enabled path.
Cache lifecycle	Parsed objects held for app lifetime (Bible §5.3).
Reload	Manual reload endpoint (internal); re-runs validation.
Hot reload	File-change detection triggers reload without restart.
Version checking	Each load records registry_version, rule_set_version, template_version, kb_version (TAS T4).
Backward compatibility	Semver; major bump → compatibility check; mismatch → KnowledgeException.
Registry validation	Unique IDs, message-key resolution, allowed-set membership, no unresolved gap tokens in active paths.
Failure strategy	Startup load failure = fatal (app does not serve). Hot-reload failure = keep previous good version + alert.
1.7 Knowledge Priority Matrix
Precedence (Bible §1.4, BR-A-9/10): Repository(1) > Draft(2) > Registry(3) > Graph state(4); user input governs the three inputs + dropdown fields.

Field	Repository	Draft	Registry	User input	Default	Conflict resolution
Environment	—	held	—	authoritative	—	user
Source system	existence authoritative	held	supplementary list	provides value	—	repo wins existence
Schema grain	—	held	—	authoritative	—	user
Topic	—	derived	format	derived (not typed)	—	format fixed; edit GAP CQ-02
Job Name	uniqueness authoritative	held	pattern	—	—	repo wins uniqueness
Worker Type	existing→authoritative	held	worker_defaults	editable	G.1X	repo > user > default
Workers	existing→authoritative	held	worker_defaults	editable	GAP CQ-04	repo > user > default
Glue Version	existing→authoritative	held	job_defaults	GAP CQ-01	5.1	repo > default
Job Type	existing→authoritative	held	job_defaults	GAP CQ-01	unified	repo > default
Job Version	existing→authoritative	held	job_defaults	GAP CQ-01	0.3.0	repo > default
IAM Role	existing→authoritative	held	naming	GAP CQ-01	new→GAP CQ-A1	repo > registry
Kafka Secret	existing→authoritative	held	constants pattern	GAP CQ-01	pattern	repo > pattern
LH Database	existing→authoritative	held	naming GAP CQ-A1	GAP CQ-01	GAP CQ-A1	repo > pattern
S3 Warehouse	existing→authoritative	held	template	GAP CQ-01	new→GAP CQ-A1	repo > pattern
S3 Checkpoint	existing→authoritative	held	template	GAP CQ-01	new→GAP CQ-A1	repo > pattern
Schedule	existing→authoritative	held	scheduling_defaults	editable	GAP CQ-05	user > default
Enterprise Function	existing→authoritative	held	enterprise_functions	editable dropdown	AGTR (GAP CQ-03 set)	user > default
Subgroup	existing→authoritative	held	enterprise_functions.subgroup	editable dropdown	APAC	user > default
Sink type	—	held	constants	—	iceberg	fixed
Catalog id / endpoints / assume-role	existing→authoritative	held	template	—	new→GAP CQ-A1	repo; new = gap
Commit/PR text	—	held	agent-generated default	editable	generated	user > generated
1.8 Knowledge Cache
Layer	Cached	TTL	Refresh	Version	Invalidation	Consistency
Memory (registries)	parsed JSON	app lifetime	hot-reload	stamped	file change	single source per process
Memory (source list)	folder listing	per-session	session start	n/a	new session/Start Over	per-session snapshot
Redis (optional, shared)	source list across nodes	per-session	n/a	n/a	session end	last-write-wins per session
File contents	— (never cached across validations)	none	every read	n/a	always fresh	repo authoritative
1.9 Knowledge Exceptions


KnowledgeException (base)
├── RegistryLoadException        # load/parse/version failure
├── RegistryValidationException  # cross-reference/allowed-set failure
├── DerivationException          # missing input / cannot derive
├── TemplateRenderException      # missing template variable
├── ParserException              # HCL parse failure
└── PriorityResolutionException  # unresolved precedence conflict
(Full mapping in Document 6.)

DOCUMENT 2 — LANGGRAPH NODE SPECIFICATION
Version: 1.0 | Status: FROZEN | Owner: Orchestration Owner References: Bible §3, TAS T3, Repository Master Structure §1.4

IMPLEMENTATION GAP (CQ-07): TAS/Repo §1.4 state "18 nodes". This spec enumerates the explicit node set; IntentRouter is included as a distinct node per Repo §1.4 (it lists intent_router.py). Final count confirmation pending. The node files in Repo §1.4 are authoritative for file placement.

2.1 Node Roster (18 nodes per §1.4 + OutOfScope already counted)
GitHubOAuth, SessionManager, Environment, Operation, IntentRouter, SourceType, SourceSystem, SchemaGrain, TopicValidation, DuplicateJobValidation, KnowledgeDerivation, DraftWorkspace, ReviewWorkspace, TerraformValidation, Approval, PRCreation, OutOfScope — plus the ModifyFiles/ConflictResolution workflows (Repo §1.4 workflows/) and JDBC/FlatFile/API placeholder behavior inside SourceType routing.

2.2 Per-Node Specification
Template applied to all (fields: Purpose, Responsibility, Owner, Input State, Output State, Entry, Exit, Interrupt, Resume, Retry, Failure, Recovery, Human Interaction, Services Called, Repositories Called, Knowledge Used, State Updated, Events, Validation, Transitions, Example, Timing, Metrics, Logging, Prompt, Variables). Where Bible §3.2 already specifies a node, this document inherits it verbatim and lists only deltas/gap-fills.

2.2.1 GitHubOAuthNode
Purpose: Authenticate, obtain token ref. Owner: Auth Service.
Input: initial/returning. Output: user_id, github_username, github_token_ref, is_authenticated.
Entry: app opened. Exit: valid token persisted. Interrupt: yes (OAuth callback). Resume: from callback. Retry: restartable; refresh expired.
Failure: denied→re-prompt; provider down→connectivity error. Recovery: re-auth.
Services: github_oauth_service, (UserRepository via auth service). Repositories called: none directly (via service). Knowledge: none.
State updated: auth fields. Events: auth.success/auth.failed.
Transitions: → SessionManager. Forbidden: → any workflow node without auth.
Timing: OAuth round-trip dependent (GAP CQ-A8). Metrics: auth_attempts_total, auth_failures_total.
Logging: mask token. Prompt: none. Variables: none.
2.2.2 SessionManagerNode
Purpose: Create/restore session. Owner: Session Service.
Input: user_id, is_authenticated. Output: session_id, draft_id?, conversation_history_ref?, navigator_state?.
Interrupt: no. Retry: DB transient. Failure: DB down→error; corrupt→offer Start Over.
Services: session_service. Knowledge: none. Transitions: → Environment.
Recovery: restore conversation+draft+navigation (AC-9). Prompt: recovery.txt. Variables: {summary},{path}.
Metrics: sessions_created_total, sessions_restored_total.
2.2.3 EnvironmentNode
Purpose: Collect env gate. Output: environment ∈ {dev,prod}.
Interrupt: yes (selection). Failure: non-dev/prod→re-prompt. Transitions: → Operation. Forbidden: any workflow before env (AC-11).
Knowledge used: environment_rules.json. Prompt: environment_selection.txt.
2.2.4 OperationNode
Purpose: Present menu + route. Input: environment, draft_change_count, draft_job_count. Output: selected_operation.
Menu rules: initial {Create Glue Job, Modify Existing Files}; after ≥1 change full menu; "Create Another Glue Job" only if draft_job_count>0 (AC-8).
Interrupt: yes. Failure: unrecognized→OutOfScope. Services: none (routing).
Transitions: → IntentRouter/SourceType (create), → ModifyFiles workflow, → ReviewWorkspace, → DraftWorkspace (discard), → PRCreation. Forbidden: → PR/Review when draft empty.
Prompt: operation_choice.txt. Variables: {draft_change_count},{draft_job_count}.
2.2.5 IntentRouterNode
Purpose: Classify intent and route (Repo §1.4). Input: user message + selected_operation. Output: routing decision.
Interrupt: no. Services: none. Knowledge: none. Failure: ambiguous→OutOfScope.
Transitions: → SourceType / ModifyFiles / OutOfScope. Prompt: intent_router.txt.
IMPLEMENTATION GAP (CQ-07): overlap between Operation and IntentRouter responsibilities — both present in §1.4; kept distinct here per the frozen file list.

2.2.6 SourceTypeNode
Purpose: Collect source type. Output: source_type.
Failure/placeholder: non-Kafka → "need to implement" (AC-12), → Operation.
Transitions: → SourceSystem (kafka), → Operation (placeholder). Prompt: source_type widget.
2.2.7 SourceSystemNode
Purpose: Collect source + existence. Output: source_system, source_exists.
Services: github_service (list), KnowledgeBaseService (cached). Knowledge: source_systems.json, repo scan.
Failure: API failure→error+retry; empty repo→empty list+allow new. Transitions: → SchemaGrain. Prompt: source_system_selection.txt.
2.2.8 SchemaGrainNode
Purpose: Free-text grain + derive topic. Output: schema_grain, topic_name.
Must NOT present a list/suggestions (FR-A-4). Knowledge: naming_rules.topic. Transitions: → TopicValidation. Prompt: schema_grain_input.txt.
IMPLEMENTATION GAP (CQ-02): topic editability by asking the agent.

2.2.9 TopicValidationNode
Purpose: Verify topic in repo. Output: topic_validation_result, topic_validation_message.
Path: confluent_minerva_<env>/topics_<source>.tf (GAP CQ-14 prod). Retry: GitHub 3x backoff.
Failure: file missing→block TR-001; grain missing→block TR-002; persistent API→error. On block: no list/suggestions (BR-A-6).
Services: github_service, validation_service. Knowledge: validation_rules, repo_patterns, parsers. Repos: validation_report (record).
Transitions: → DuplicateJobValidation (PASS), → Operation (FAIL). Metrics: topic_validation_total{result}.
2.2.10 DuplicateJobValidationNode
Purpose: Verify job not present. Path: <source>/locals.tf. Output: duplicate_validation_result.
Failure: present→block JR-001; locals.tf missing for existing source→system error.
Transitions: → KnowledgeDerivation (PASS), → Operation (FAIL). Knowledge: LocalsTFParser, validation_rules.
2.2.11 KnowledgeDerivationNode
Purpose: Derive all values + file plan. Output: derived_values, file_plan, knowledge refs.
Services: KnowledgeBaseService (and GlueJobService.derive_all_values per Backend §2.3.2). Never: persistence, terraform, github-for-PR.
Failure: registry missing→critical; new-source concretes→GAP CQ-A1. Transitions: → DraftWorkspace.
Knowledge: all derivers + priority matrix. Prompt: derivation (present values, no per-field confirm).
2.2.12 DraftWorkspaceNode
Purpose: Persist draft + snapshot. Output: draft_id, draft_change_count, draft_job_count, snapshot_id, draft_status.
Services: draft_service, snapshot_service. Repos (via service): draft, draft_file, draft_glue_job, snapshot.
Failure: tx failure→rollback; snapshot failure→rollback mutation (atomic). Transitions: → Operation (loop). Forbidden: → PR directly.
Knowledge: TemplateEngine (materialize). Metrics: draft_mutations_total.
2.2.13 ReviewWorkspaceNode
Purpose: Present review + accept edits. Output: review_presented, user edits.
Interrupt: yes (edit/confirm). Services: draft_service (get_draft_for_review), review_service. Knowledge: none.
Edits scope: GAP CQ-01. Diff: green/red, Files Changed:N (FR-W-8); engine scope GAP CQ-09.
Transitions: → TerraformValidation, → Operation (more changes). Prompt: review_workspace.txt.
2.2.14 TerraformValidationNode
Purpose: Run TF validation once before PR. Output: terraform_validation_status, validation_messages[].
Services: terraform_validation_service (init/fmt/validate via draft_service.materialize_files). Interrupt: no.
Failure: FAIL→show reason (UX-R-4, AC-10), offer fix→re-validate. Gate strictness GAP CQ-13b.
Transitions: → ReviewWorkspace (FAIL), → Approval (PASS or per CQ-13b). Knowledge: OutputParser, validation_messages.
2.2.15 ApprovalNode
Purpose: Single confirmation. Output: user_approved. Interrupt: yes.
Services: none. Transitions: → PRCreation (yes), → Review/Operation (no). Forbidden: → PR without approval (FR-S-4). Prompt: approval.
2.2.16 PRCreationNode
Purpose: Branch + single commit + PR (+ session persist). Output: pr_url, pr_number, commit_sha, branch_name.
Services: github_service (Git Data API), pr_service; repos: draft, pr_metadata. Idempotent: duplicate→return existing (FR-W-7).
Failure: conflict→ConflictResolution; GitHub error→unfreeze draft+report. Freeze: draft frozen during (FR-W-6).
Transitions: → ConflictResolution (conflict), → END (success). Knowledge: none. Metrics: prs_created_total, pr_creation_seconds.
IMPLEMENTATION GAP (CQ-15): target repo. (CQ-06): branch key. (CQ-A4): conflict depth.

2.2.17 OutOfScopeNode
Purpose: Graceful off-workflow handling. Output: helpful response; state unchanged.
Services: LLM only. Never: github/draft/persistence. Transitions: → return to prior context. Prompt: out_of_scope.txt.
2.2.18 Workflows (ModifyFiles, ConflictResolution) — Repo §1.4 workflows/
ModifyFiles: NavigationService + DraftService; edit only what user asks (BR-B-1); guardrails GAP CQ-A6; → DraftWorkspace.
ConflictResolution: ConflictService; auto-rebase then incoming/current options; one commit (BR-S-2); depth GAP CQ-A4; → PRCreation.
2.3 Graph-Level Specifications
Complete flow:



OAuth→Session→Environment→Operation→IntentRouter
  ├─create→SourceType→[non-kafka→Placeholder→Operation]
  │         └kafka→SourceSystem→SchemaGrain→TopicValidation
  │                 ├FAIL→Operation
  │                 └PASS→DuplicateJobValidation
  │                          ├FAIL→Operation
  │                          └PASS→KnowledgeDerivation→DraftWorkspace→Operation
  └─modify→ModifyFiles→DraftWorkspace→Operation
Operation──review/PR──►ReviewWorkspace→TerraformValidation
  ├FAIL→ReviewWorkspace
  └PASS(|CQ-13b)→Approval──yes──►PRCreation
                              ├conflict→ConflictResolution→PRCreation
                              └success→END
OutOfScope◄any node intent►return
Concern	Specification
Node dependency graph	Linear with a multi-operation loop back to Operation; validations gate derivation; review→validation→approval→PR.
Conditional branches	source_type (kafka vs placeholder); validation PASS/FAIL; approval yes/no; PR success/conflict.
Human-in-the-loop	interrupt_before at: Environment, Operation, SourceType, SourceSystem, SchemaGrain, ReviewWorkspace, Approval, OAuth callback, ConflictResolution manual.
Loop handling	Multi-operation loop returns to Operation; counters drive menu (FR-S-3). No "continue?" prompts (FR-S-4).
Recovery flow	SessionManager restores current_step + draft + navigation (TAS T4, AC-9).
Parallel execution	None in Phase-1 (sequential conversation).
Error propagation	Node failures surface as typed messages; never crash graph; OutOfScope catches off-workflow.
Cancellation	"Start Over" (FR-H-5) clears state → Environment.
Resume logic	Redis checkpointer + current_step; AsyncSession never in state (TAS T4).
State persistence	Business data → Postgres; workflow position → checkpoint.
DOCUMENT 3 — GRAPH STATE SPECIFICATION
Version: 1.0 | Status: FROZEN | Owner: Orchestration Owner References: TAS T4, Bible §3/§4, Backend §2.5

IMPLEMENTATION GAP (CQ-11): KnowledgeState removal — adopted (references only). (CQ-12): workspace.defaults → derived_values rename — adopted. Both flagged per TAS T4.

3.1 State Composition (nested objects)


GraphState
├── session: SessionState
├── conversation: ConversationState
├── workflow: WorkflowState
├── operation: OperationState
├── repository: RepositoryState
├── knowledge: KnowledgeRefState
├── draft: DraftRefState
├── review: ReviewState
├── validation: ValidationState
├── pr: PRState
├── conflict: ConflictState
├── ui: UIState
├── history: HistoryState
├── metrics: MetricsState
├── audit: AuditState
└── system: SystemState
3.2 Per-Section Field Tables
Each field: Purpose | Type | Owner | Default | Who modifies | When updated | Persistence | Recovery | Validation.

SessionState
Field	Type	Owner	Default	Modifier	When	Persist	Recovery	Validation
user_id	str	OAuth	—	OAuth	login	Postgres	reload	uuid
github_username	str	OAuth	—	OAuth	login	Postgres	reload	non-empty
github_token_ref	secret ref	OAuth	—	OAuth	login	Postgres (SEC-4)	reload	ref only (GAP CQ-A7 encryption)
is_authenticated	bool	OAuth	false	OAuth	login	checkpoint	re-auth	—
session_id	uuid	Session	—	Session	create	Postgres	reload	uuid
environment	enum	Environment	null	Environment	env step	Postgres	reload	dev/prod
ConversationState
| conversation_history_ref | ref | Session | — | nodes | each turn | Postgres | reload | ref | | current_step | str | all | start | active node | each node | checkpoint | resume | known node | | last_message_preview | str | Session | "" | nodes | each turn | Postgres | reload | — |

WorkflowState
| selected_operation | enum | Operation | null | Operation | menu | checkpoint | resume | enum | | source_type | enum | SourceType | null | SourceType | step | checkpoint | resume | kafka/jdbc/flatfile/api | | source_system | str | SourceSystem | null | SourceSystem | step | checkpoint | resume | repo/new | | source_exists | bool | SourceSystem | null | SourceSystem | step | checkpoint | resume | — | | schema_grain | str | SchemaGrain | null | SchemaGrain | step | checkpoint | resume | non-empty | | topic_name | str | SchemaGrain | derived | SchemaGrain | step | checkpoint | resume | format |

OperationState
| draft_change_count | int | DraftWorkspace | 0 | DraftWorkspace | mutation | Postgres | reload | ≥0 | | draft_job_count | int | DraftWorkspace | 0 | DraftWorkspace | mutation | Postgres | reload | ≥0 |

RepositoryState
| navigator_state | obj | SourceSystem/Modify | {} | nav nodes | navigation | Postgres | reload | path valid | | base_sha | str | Provider | — | Provider | scan | Postgres | reload | sha | | source_list | list | SourceSystem | [] | SourceSystem | scan | session cache | rescan | — |

KnowledgeRefState (references only — TAS T4)
| kb_version, rule_set_version, template_version, registry_version, provenance_reference, knowledge_context_id | refs | KnowledgeDerivation | — | KnowledgeDerivation | derive | checkpoint | resume | present |

Immutable rule: KB contents never stored here (CQ-11 confirms removal of KnowledgeState object).

DraftRefState
| draft_id | uuid | DraftWorkspace | null | DraftWorkspace | create | Postgres | reload | uuid | | draft_status | enum | DraftWorkspace | OPEN | DraftWorkspace | transition | Postgres | reload | (GAP CQ-06 state names) | | snapshot_id | uuid | DraftWorkspace | — | DraftWorkspace | mutation | Postgres | reload | uuid | | derived_values | obj | KnowledgeDerivation | {} | KnowledgeDerivation | derive | draft(Postgres) | reload | schema | | file_plan | obj | KnowledgeDerivation | {} | KnowledgeDerivation | derive | draft | reload | create/modify |

ReviewState
| review_presented | bool | Review | false | Review | review | checkpoint | resume | — | | field_edits | obj | Review | {} | Review | edit | draft | reload | scope GAP CQ-01 |

ValidationState
| topic_validation_result | enum | TopicValidation | — | node | validate | Postgres | reload | PASS/FAIL | | duplicate_validation_result | enum | DuplicateJob | — | node | validate | Postgres | reload | PASS/FAIL | | terraform_validation_status | enum | TerraformValidation | — | node | validate | Postgres | reload | PASS/FAIL | | validation_messages | list | validation nodes | [] | nodes | validate | Postgres | reload | — |

PRState
| user_approved | bool | Approval | false | Approval | confirm | checkpoint | resume | — | | pr_url, pr_number, commit_sha, branch_name | str/int | PRCreation | — | PRCreation | create | Postgres | reload | — |

ConflictState
| draft_base_sha, repo_head_sha | str | PRCreation | — | PRCreation | PR attempt | Postgres | reload | sha | | conflict_files | list | Conflict | [] | Conflict | detect | Postgres | reload | — | | user_resolution | obj | Conflict | {} | Conflict | resolve | draft | reload | depth GAP CQ-A4 |

UIState (local only — not persisted to graph)
| active_pane, loading_states, modals | obj | Frontend | — | Frontend | UI | none | n/a | — |

HistoryState
| node_history | list (simplified per TAS T4) | all | [] | nodes | each node | checkpoint | resume | — |

MetricsState
| node_timings | obj | all | {} | nodes | each node | metrics sink | n/a | — |

AuditState
| created_by, updated_by, pr_created_by | str | all | — | nodes | mutations | Postgres | reload | (SEC-2) |

SystemState
| correlation_id | str | middleware | — | middleware | request | logs | n/a | uuid | | graph_version | str | system | — | system | build | checkpoint | resume | semver |

3.3 Lifecycle / Serialization / Recovery / Migration / Security
Concern	Specification
Serialization	JSON-serializable; secret refs only; AsyncSession forbidden (TAS T4).
Persistence split	Business data→Postgres; workflow position→Redis checkpoint.
Recovery	Restore from Postgres (draft/session) + Redis (current_step); rebuild Redis from Postgres if lost (Bible §4.2).
Snapshots	Draft snapshots in Postgres (immutable); graph state checkpointed per interrupt.
Interrupt/Resume	interrupt_before at HITL points; resume from current_step.
Versioning	graph_version; checkpoint compatibility checked on resume.
Migration	State schema migrations versioned with graph_version; incompatible→Start Over fallback.
State validation	On load: required fields by step; env non-null before workflow (AC-11).
Immutable fields	session_id, user_id, draft_id, snapshot_id, knowledge version refs once set.
Mutable fields	counts, validation results, navigator_state, derived_values (pre-freeze).
Forbidden mutations	any draft mutation while draft_status frozen (FR-W-6); KB contents into state; raw token into state.
Audit rules	created_by/updated_by on every mutation (SEC-2).
Security rules	token masked; secrets never serialized (SEC-1).
3.4 State Transition Rules (draft) — GAP CQ-06
Adopted working set (Backend §2.5 model uses OPEN/REVIEW/PR_CREATED/ABANDONED; Bible §4.1 uses DRAFT_EDITING/REVIEW_READY/...). Conflict flagged. Working position = Backend model names (matches Draft.status default OPEN):



OPEN → REVIEW (guard: change_count>0)
REVIEW → OPEN (user wants changes)
REVIEW → PR_CREATING (approval + TF status per CQ-13b)
PR_CREATING → PR_CREATED | PR_FAILED→OPEN | CONFLICT_DETECTED→OPEN(after resolve)
any editable → ABANDONED (Start Over/timeout)
IMPLEMENTATION GAP (CQ-06): Backend §2.5 (OPEN/REVIEW/PR_CREATED/ABANDONED) vs Bible §4.1 (DRAFT_EDITING/REVIEW_READY/PR_CREATING/...). Two frozen documents disagree. Must be reconciled before the CHECK drafts.status constraint is finalized.

DOCUMENT 4 — PROMPT LIBRARY SPECIFICATION
Version: 1.0 | Status: FROZEN | Owner: Architecture Owner (system), Node Owners (node prompts) References: Bible §14, Repository Master Structure §1.8

4.1 Prompt Inventory (maps to Repo §1.8 prompts/)
File	Type	Owner	Frozen	Variables
system_prompt.txt	System	Architecture	Yes	none
node_prompts/environment_selection.txt	Node	Node	Yes	none
node_prompts/operation_choice.txt	Node	Node	Yes	{draft_change_count},{draft_job_count}
node_prompts/intent_router.txt	Node	Node	Yes	{user_message}
node_prompts/source_system_selection.txt	Node	Node	Yes	{source_list}
node_prompts/schema_grain_input.txt	Node	Node	Yes	none
node_prompts/review_workspace.txt	Review	Node	Yes	{draft_summary}
node_prompts/out_of_scope.txt	Out-of-scope	Node	Yes	none
node_prompts/conflict_resolution.txt	Conflict	Node	Yes	{conflict_files},{diff}
(derived) validation	Validation	Node	Yes	{outcome},{message}
(derived) recovery	Recovery	Node	Yes	{summary},{path}
(derived) clarification	Clarification	Node	Yes	{question}
(derived) approval	Approval	Node	Yes	{summary}
4.2 System Prompt (content per Bible §14.2)
Element	Content	Ref
Identity	"You are the MIF Infrastructure Copilot..."	PI-1/2
Scope	create Kafka Glue Jobs, modify files, review, create PRs	SCOPE-1/2
Constraints	minimum questions; never "how many jobs?"; never "continue?"; one confirmation before PR	FR-S-2/4, UX-E-5
Style	conversational, ChatGPT-style, not a wizard	PI-5
Boundaries	never connect to Kafka; never merge/apply/deploy	SCOPE-9/10/13
Source of truth	repository always wins	BR-A-10
4.3 Node Prompts (purpose + rules)
Prompt	Purpose	Must	Must NOT
environment_selection	ask dev/prod	be brief	explain
operation_choice	present dynamic menu	follow FR-S-3 visibility	add filler
intent_router	classify	route deterministically	answer off-domain
source_system_selection	present repo sources	include "new source"	invent sources
schema_grain_input	ask grain	accept free text	list/suggest
review_workspace	summarize changes	show diffs (FR-W-8)	expose rules (UX-R-3)
validation	translate outcome	hide rule IDs (UX-R-4)	expose rule logic
approval	single confirmation	one prompt only	re-confirm
conflict_resolution	explain conflict + 4 options	Accept Incoming/Current/Both/Manual	auto-resolve silently
recovery	resume naturally	restore context	restart
out_of_scope	redirect helpfully	stay friendly	answer out-of-domain
4.4 Prompt Variables, Templates, Versioning, Loader
Concern	Specification
Variables	template_variables.py (Repo §1.8) defines allowed variables per prompt; injection only, no business values embedded.
Templates	Plain-text with {var} placeholders; loader.py renders.
Versioning	Each prompt carries # version: x.y.z header; changes logged; frozen prompts require approval (Repo §1.8 ownership).
Loader	prompts/loader.py loads, validates variable set, caches; never inline-hardcoded.
4.5 Prompt Security / Injection Protection
Rule	Specification
Input isolation	User text inserted only into designated {user_message} slots, never into instruction sections.
Instruction precedence	System prompt boundaries cannot be overridden by user content.
Secret safety	No secrets/tokens ever placed in prompts (SEC-1).
Scope guard	Off-workflow/injection attempts route to OutOfScope (UX-E-6).
Output filtering	Validation rule IDs/logic never emitted to user (UX-R-3/4).
Determinism	Routing/validation decisions never delegated to free-form LLM where a rule exists (rules from registries).
DOCUMENT 5 — DTO MAPPING SPECIFICATION
Version: 1.0 | Status: FROZEN | Owner: Contract Owner References: Backend §2.5/§2.6, Repo §1.7 shared, TAS T9

5.1 The Mapping Chain


GitHub Repo (HCL)
   │ parsers
   ▼
RepositoryFacts (knowledge/provider/fact_model.py)
   │ derivers
   ▼
DerivedGlueJobConfig (domain object)
   │ draft_service
   ▼
ORM Models (backend/models/*) — DraftGlueJob, DraftFile, Draft...
   │ repositories
   ▼
Domain Models (shared/types.py) — GlueJobConfig, DraftState
   │ services
   ▼
Graph State (derived_values, draft refs)
   │ api
   ▼
API DTO (backend/schemas/*) — AgentMessageResponse, DraftReviewResponse
   │ HTTP
   ▼
Frontend DTO (frontend/src/types/*) — IAgentResponse, Draft
   │ store/hooks
   ▼
React Component props
5.2 Layer Mapping Rules
From → To	Rule	Serialization	Validation
HCL → RepositoryFacts	parsers normalize; no business logic	dataclass	balanced HCL, .raw topics
RepositoryFacts → DerivedGlueJobConfig	derivers + priority matrix; repo wins	dataclass	all FR-A-9 fields present
DerivedGlueJobConfig → ORM	draft_service maps field-by-field	SQLAlchemy	unique(draft_id, job_key)
ORM → Domain	repositories return domain objects, never ORM (Backend §2.3.1)	to-domain mapper	type-safe
Domain → Graph State	only draft_id+counters+derived_values; never ORM/AsyncSession	JSON	TAS T4 rules
Graph State → API DTO	api maps state→AgentMessageResponse	Pydantic	schema §2.6
API DTO → Frontend DTO	TypeScript interfaces mirror Pydantic	JSON	strict TS, no any
Frontend DTO → Component	props typed	—	runtime guard
5.3 Field-Level Example — Glue Job
Stage	Representation
HCL	"kafka-to-iceberg-batch-saptce-multi-1" = { worker_type="G.1X" ... }
RepositoryFacts	existing_jobs["saptce"] = ["kafka-to-iceberg-batch-saptce-multi-1"]
DerivedGlueJobConfig	job_key=..., worker_type="G.1X", topic_name="dev.saptce.multi-1.raw"
ORM DraftGlueJob	columns per Backend §2.5
Domain GlueJobConfig	shared/types.py dataclass
Graph State	derived_values["jobs"][job_key] = {...}
API DTO GlueJobConfigView	JSON in DraftReviewResponse.glue_jobs[]
Frontend Draft.jobs[]	TS interface
Component	<JobSummary job={job} />
5.4 Serialization / Deserialization
Rule	Detail
Secrets	SecretStr; never serialized to API/Frontend (SEC-1, UX-R-3).
Hidden fields	bootstrap servers, schema registry, rule IDs, internal TF values never cross to API DTO (UX-R-3).
Editable subset	only fields per GAP CQ-01 marked editable in API DTO.
Datetime	ISO-8601 UTC.
IDs	UUID strings.
Diff	computed server-side (review_service), sent as structured green/red (FR-W-8); engine scope GAP CQ-09.
DOCUMENT 6 — EXCEPTION ARCHITECTURE
Version: 1.0 | Status: FROZEN | Owner: Architecture Owner References: Repo §1.7 (shared/exceptions.py), Backend error-handling sections, Bible §12 API errors

6.1 Hierarchy


ApplicationException (CopilotException — shared/exceptions.py base)
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
├── RepositoryException        # persistence/data-access
├── DraftException
├── GitHubException
├── TerraformException
├── PRException
└── ConflictException
(Repo §1.7 names CopilotException as base; ApplicationException is its alias — single base, no duplication.)

6.2 Per-Exception Specification
Exception	Cause	Recovery	User Message	Developer Message	Log Level	Retry	HTTP
AuthenticationException	invalid/expired token	re-auth	"Session expired. Please sign in again."	token validation detail	WARN	re-auth	401
SessionException	corrupt/missing session	Start Over	"We couldn't restore your session."	session id + cause	ERROR	no	404/500
RegistryLoadException	registry load/parse fail	fatal at startup	"Service unavailable."	file+version	ERROR	no	503
RegistryValidationException	bad cross-ref/allowed-set	fix registry	"Service unavailable."	rule/message detail	ERROR	no	503
DerivationException	missing input/concrete (CQ-A1)	inform/block	"We need more information to continue."	missing field	ERROR	no	500
TemplateRenderException	missing template var	block	"Could not generate configuration."	var name	ERROR	no	500
ParserException	malformed .tf	report	"We couldn't read a repository file."	path+parse error	ERROR	no	502
PriorityResolutionException	unresolved precedence	block	"Configuration conflict detected."	field+sources	ERROR	no	500
ValidationException	rule fail (TR/JR/TF)	offer fix	rule message (TR-001 etc.)	rule id + context	INFO	re-validate	422
RepositoryException	DB error/constraint	retry	"Something went wrong. Please try again."	constraint+query	ERROR	tx retry	500
DraftException	draft op fail / frozen	retry/wait	"Your draft is being processed."	draft id+state	WARN	optimistic retry	409
GitHubException	API error/rate/auth	backoff/re-auth	"GitHub is unavailable. Retrying..."	endpoint+code	WARN	3x backoff	502/429
TerraformException	CLI fail/not found/timeout	report+block PR	"Validation could not run."	stderr	ERROR	CLI retry	500
PRException	PR creation fail	unfreeze+retry	"Could not create the pull request."	github detail	ERROR	idempotent retry	502
ConflictException	merge conflict/resolution fail	resolve	"There's a conflict to resolve."	conflict files	WARN	re-resolve	409
6.3 Rules
Never catch-and-swallow (Bible §18.1); always log+propagate or recover.
All exceptions carry correlation_id.
User messages never expose internal paths, rule logic, or secrets (UX-R-3, SEC-1).
ErrorHandlerMiddleware (Backend §2.2.2) maps exceptions → HTTP per the table.
DOCUMENT 7 — LOGGING & OBSERVABILITY SPECIFICATION
Version: 1.0 | Status: FROZEN | Owner: SRE + Architecture References: Bible §17.2–§17.6, TAS T12, SEC-1/2, NFR-1/2

7.1 Identifiers (always present)
ID	Source	Scope	Propagation
correlation_id	correlation middleware	request→all layers	header + log field
request_id	API	single HTTP request	per request
trace_id	tracing	distributed trace	frontend→backend
node_id	graph	per node span	per node
session_id	session	conversation	all session events
draft_id	draft	draft lifecycle	draft events
pr_id	PR	PR lifecycle	PR events
user_id	auth	actor	all (audit)
7.2 Log Categories
Category	Content	Level(s)	Notes
Structured	every API req/resp, node exec	INFO/DEBUG	JSON one-line
Business	session created/restored, draft mutation, PR created, validation pass/fail	INFO	correlation id
Audit	who/when/what (mutations, PR, validation failures)	INFO	SEC-2; immutable
Security	auth success/failure, token refresh, denied access	WARN	masked
Knowledge	registry load/version, derivation provenance	INFO/DEBUG	versions stamped
Parser	HCL parse outcomes	DEBUG/ERROR	path + result
GitHub	endpoint, code, latency, retries	INFO/WARN	no token
Terraform	init/fmt/validate outcomes	INFO/ERROR	stderr to DEBUG
LLM	prompt sent (masked), response meta, tokens, latency	DEBUG	no secrets
7.3 Metrics
Type	Examples
Counter	sessions_created_total, prs_created_total, validations_run_total, auth_failures_total
Histogram	api_response_seconds, pr_creation_seconds, validation_seconds, node_exec_seconds
Gauge	active_sessions, draft_size_bytes, db_pool_active, redis_memory_used
Alert thresholds: error rate >1%, PR success <95%, GitHub error >5%, DB pool >80%, Redis >80%. Latency targets GAP CQ-A8.

7.4 Tracing / OTEL Readiness
Rule	Specification
Span per node	each LangGraph node = a span (Bible §17.6)
Span per external call	each GitHub/DB/Redis op = child span
Context propagation	trace id frontend→backend→services
OTEL	OUT OF SCOPE Phase-1 (SEC-3); correlation-id tracing now; structure OTEL-ready
7.5 Sensitive Data Masking
Rule	Detail
Tokens/secrets	never logged; SecretStr masking (SEC-1)
File contents	never log full file contents (Bible §17.4)
Validation rules	rule logic never logged at user-visible level; backend DEBUG only (UX-R-3)
PII	github_username allowed (audit); email masked in non-audit logs
7.6 Log Rotation / Retention
Concern	Specification
Format	structured JSON, one line/event
Levels	ERROR/WARN/INFO/DEBUG (Bible §17.4)
Rotation	size+time based (operational)
Retention	GAP CQ-A8 (not set in source)
MASTER GAP REGISTER (Consolidated)
Every gap surfaced across all 7 documents. None resolved — all require clarification.

CQ	Gap	Documents affected
CQ-01	Per-field review editability	1 (matrix), 3 (ReviewState), 5 (DTO)
CQ-02	Topic editable by asking agent	1, 2 (SchemaGrain)
CQ-03	Enterprise Function set SPEC vs CORP	1 (enterprise_functions.json)
CQ-04	Max workers / default (1 vs 4)	1 (defaults/worker_defaults)
CQ-05	Default run mode Manual vs daily 1AM	1 (scheduling), 2
CQ-06	Draft state names (Backend OPEN/... vs Bible DRAFT_EDITING/...)	3 (transitions), DB CHECK constraint
CQ-07	Node count (18 vs enumerated) + Operation/IntentRouter overlap	2
CQ-08	Table count 8 vs 19	(models — both frozen docs use 8)
CQ-09	Diff engine Phase-1 vs deferred	2 (Review), 5 (DTO)
CQ-13b	TF validation mandatory before PR	2 (TerraformValidation/Approval), 3
CQ-14	Prod topic path (no confluent_minerva_prod/ exists)	1 (repo_patterns/environment_rules), 2
CQ-15	Target repo identity / _v3 same-or-separate	1 (repository_mapping), 2 (PR)
CQ-A1	New-source concretes origin + LH DB pattern + secret corp literal	1 (derivers/templates/naming), 6 (DerivationException)
CQ-A4	Conflict resolution depth	2 (ConflictResolution), 3 (ConflictState)
CQ-A5	Transformer/sink settings shown/editable	1 (defaults), 5
CQ-A6	Modify-files guardrails	2 (ModifyFiles)
CQ-A7	Token encryption at rest / Pydantic version	3 (token_ref), 7
CQ-A8	NFR targets, retention, latency	7 (metrics/retention)
CQ-A2	project_information/cell1–cell8 contents	1 (may carry CQ-A1 concretes)
CLOSING STATEMENT
This Master Implementation Specification completes the seven missing engineering documents (Knowledge Base, LangGraph Nodes, Graph State, Prompt Library, DTO Mapping, Exception Architecture, Logging & Observability) by extending the frozen corpus without contradiction.

Two frozen documents conflict on draft state names (Backend §2.5 vs Bible §4.1) — surfaced as CQ-06 rather than silently resolved, because reconciling two approved sources is an architectural decision reserved for the project owners.

Implementation can proceed mechanically for the existing-source flow. The new-source flow remains blocked on CQ-A1 (concretes origin + LH DB pattern), and GitHub targeting remains blocked on CQ-14/CQ-15. All other gaps are localized and flagged inline.

No business rule was invented; no requirement was changed; every decision traces to CPRS, TAS, the Implementation Bible, the Repository Master Structure, the Backend Module Architecture, or the Process document — and every untraceable item is explicitly marked IMPLEMENTATION GAP — requires clarification.