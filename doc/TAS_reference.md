# Technical Architecture Specification (TAS) — Reference
## MIF Infrastructure Copilot

**Status:** Reference companion to CPRS v1.0. NON-BINDING. Not approved.
**Purpose:** Holds the implementation-flavored detail extracted from the product spec so the CPRS stays purely about product behavior. Nothing here is a design decision yet; it is a faithful capture of what the source documents asserted, to be formalized only after CPRS v1.0 is approved and the relevant Clarification Questions are answered.
**Rule:** No item here may contradict an approved CPRS requirement. Where a CQ governs behavior, the technical item inherits that CQ.

---

## T1. Technology stack (as stated in source)
- Frontend: React + Vite.
- Backend: FastAPI.
- Orchestration: LangGraph (with checkpointing).
- Datastores: PostgreSQL, Redis.
- Integrations: GitHub OAuth + GitHub API; Terraform CLI (`init`, `fmt`, `validate`).
- Knowledge registries delivered as JSON files.

## T2. Architectural style
- Hexagonal architecture; OOP and design patterns; modular/reusable throughout.
- Agent-first: frontend calls a single agent message endpoint; the agent calls internal services.
- One node = one responsibility; one agent = one responsibility.

## T3. LangGraph internals (UNVERIFIED — depends on CQ-07)
- Intended node sequence (one consolidated version):
  GitHubOAuth → SessionManager → Environment → Operation → IntentRouter → SourceType → SourceSystem → SchemaGrain → TopicValidation → DuplicateJobValidation → KnowledgeDerivation → DraftWorkspace → ReviewWorkspace → TerraformValidation → Approval → PRCreation (and, in some versions, TopicGeneration and SessionPersist nodes).
- Stated count "18 nodes" — not reconciled with the lists above. **CQ-07.**
- Validation routing: Draft → Review → TerraformValidation → Review → Approval → PR.
- Human-in-the-loop pauses via `interrupt_before` at user-input/approval points.
- Node ownership: KnowledgeDerivation derives business values only; DraftWorkspace materializes templates + persists draft files + manages snapshots; TerraformValidation validates only; PRCreation does commit + PR only.
- Source/placeholder nodes: Kafka functional; JDBC/FlatFile/API return "need to implement."
- Mandatory OutOfScope/Copilot node for off-workflow questions.

## T4. Graph state model (as stated)
- State stores references only, never the knowledge base contents: `kb_version`, `rule_set_version`, `template_version`, `registry_version`, `provenance_reference`, `knowledge_context_id`.
- Remove `KnowledgeState` (confirm — CQ-11).
- Simplify `node_history`.
- Rename `workspace.defaults` → `derived_values` (confirm — CQ-12).
- Persist `current_step` for resume.
- AsyncSession must never enter graph state.

## T5. Knowledge layer (components & registries)
- Components: RepositoryKnowledgeProvider, KnowledgeBaseService, Registry Loaders, Parsers, Derivers, ValidationEngine, ProvenanceService, DerivedValueEngine.
- Registries (JSON): `validation_rules.json`, `source_systems.json`, `terraform_templates.json`, `repo_patterns.json`.
- JSON-driven validation (no hardcoded rule logic); knowledge-driven derivation (no hardcoded values).
- Source-system list from repository scan; cached registry may supplement; repository remains authoritative.
- Validation rule IDs (e.g., `TR-001`, `JR-001`); validation history retained.
- For NEW sources, per-environment concretes (bootstrap endpoints, schema-registry endpoints, Glue catalog account IDs, assume-role ARNs) origin is unspecified; two Lakehouse-DB name patterns conflict — **CQ-A1.**

## T6. Data model (conceptual — DDL deferred)
- Core entities named in source: `users`, `sessions`, `drafts`, `draft_files`, `draft_glue_jobs`, `validation_reports`, `snapshots`, `pr_metadata` (8). Elsewhere "19 tables." **CQ-08.**
- `sessions`: environment, current_draft_id.
- `drafts`: PR metadata (commit message, PR title/description, branch name), lifecycle status.
- `draft_glue_jobs`: per-job fields incl. environment, source_system, schema_grain, topic, kafka_secret_name, glue_job_name, iam_role, worker_type, glue_version, workers, scheduling_mode, job_type, job_version, enterprise_function, subgroup, lh_db, s3_paths, timestamps. source_system/schema_grain kept at job level so multiple sources fit one draft.
- `draft_files`: keyed by (draft_id, path).
- `snapshots`: keyed by (draft_id, created_at); immutable; restore = new state from old snapshot.
- Conflict metadata: draft_base_sha, repo_head_sha, conflict_files[].
- Audit columns: created_by, updated_by, created_at, updated_at; PR audit: pr_created_by, pr_created_at.
- Constraints/indexes named in source: unique(draft_id, job_key); optimistic locking; indexes on sessions(current_draft_id), draft_glue_jobs(draft_id), draft_glue_jobs(job_key), draft_files(draft_id, path), snapshots(draft_id, created_at).
- Deferred per source (Phase-1 overengineering): secrets table, complex FK chains, object-store content pointers, large audit model.

## T7. Draft lifecycle state machine (UNVERIFIED — depends on CQ-06)
- Candidate state sets seen in source:
  1. OPEN → REVIEW → PR_CREATING → PR_CREATED / ABANDONED
  2. DRAFT_EDITING → REVIEW_READY → PR_CREATING → PR_CREATED
  3. OPEN → REVIEW → VALIDATED → PR_CREATING → PR_CREATED → ABANDONED
  4. OPEN → VALIDATED → READY_FOR_PR → MERGED
- One dedicated branch per draft: `draft/<session_id>` or `draft/<draft_id>` — choice open.

## T8. Repository/persistence patterns
- Repository pattern for all persistence; transaction ownership at repository layer.
- Soft-delete, unique-constraint, optimistic-locking strategies to be frozen at DB design step.
- PostgreSQL runtime/execution certification before completion.
- Future CI enforcement: LangGraph import rules; repository ownership rules; prevent AsyncSession in graph state.

## T9. API & DTO contracts
- Single agent endpoint (e.g., `/agent/message`) as the frontend's primary interface.
- Internal/support endpoints (e.g., `/drafts`, `/pr`, `/validation/request`) not called directly by the frontend.
- API and DTO contracts to be frozen and version-stable once defined.

## T10. Terraform output shapes (from MIF workflow source)
- `locals.tf` `glue_jobs` map entry shape (job_type=unified, job_version=0.3.0 default, glue_version=5.1, number_of_workers, worker_type, stop_before_start=true, optional trigger_schedule, glue_job_arguments incl. source/kafka endpoint+secret+topic, transformer1=timestamp, transformer2=kafka_unpack, sink_transformer1=kafka_split + schema-registry endpoint/secret, sink=iceberg + catalog type/id/database/warehouse/checkpoint_dir/assume_role_arn/assume_session_name=mif-glue-iceberg, sink_trigger=availableNow).
- `glue.tf` module block shape (for_each over local.glue_jobs; module source git URL; per-key lookups for glue_version, job_type, job_version, topic_name, stop_before_start, number_of_workers, worker_type, extra_py_files, trigger_schedule, glue_job_arguments, secret name).
- Kafka secret name pattern `minerva-${env}-corp-mif-<source>-gluejob-sa-cc-api-creds` (literal `corp` vs enterprise function — CQ-A1).
- Warehouse/checkpoint S3 prefixes end with `/`.

## T11. Conflict-resolution mechanics
- Auto `git fetch` + `git rebase`; on conflict show incoming/current; resolution then `git add` → `git commit --amend` → `git push --force-with-lease`; always one commit.
- Phase-1 depth open — CQ-A4.

## T12. Security mechanics
- Secret abstraction layer; secret references; SecretStr; audit logging with masking.
- Future: Vault/AWS Secrets Manager, RBAC, OTEL.
- GitHub token persistence + (encryption?) for restart recovery — CQ-A7/CQ-A8.

## T13. Testing & governance mechanics
- Test types: Unit, Integration, Contract, DTO-compatibility, Recovery, Load, Chaos; plus conversation-flow tests.
- Per-step gate process: Design Doc → Review → Freeze → Verification Checklist → PASS/FAIL → Implementation → Testing → Evidence → Certification → PASS/FAIL → next.
- Evidence required before any phase completion; no-evidence ⇒ rejection.
- Intended build order: Database → Repository → Knowledge → LangGraph → API → Frontend → Integration → Testing.

## T14. Deployment/infra (not frozen)
- Kubernetes topology, Redis HA, PostgreSQL HA, backup, secrets management, CI/CD, Dev→Test→Prod promotion — all open. NFR targets open. CQ-A8.
