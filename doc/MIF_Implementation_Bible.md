# MIF Infrastructure Copilot — Implementation Documentation Package
## The Implementation Bible

**Version:** 1.0
**Status:** FINAL DRAFT — Ready for engineering consumption after CPRS approval
**Authoritative inputs (frozen):** CPRS v1.0, TAS Reference
**Rule:** This document does NOT modify CPRS or TAS. Where information is missing, a Clarification Question is cited rather than assumed. Every specification traces to a CPRS requirement ID or TAS section.

---

## Master Table of Contents

| Section | Title | Page |
|---------|-------|------|
| 1 | System Context | §1 |
| 2 | Detailed Functional Specification | §2 |
| 3 | Complete LangGraph Specification | §3 |
| 4 | Complete State Machine Specification | §4 |
| 5 | Knowledge Layer Specification | §5 |
| 6 | Repository Navigation Specification | §6 |
| 7 | Draft Workspace Specification | §7 |
| 8 | Review Workspace Specification | §8 |
| 9 | Validation Specification | §9 |
| 10 | GitHub Integration Specification | §10 |
| 11 | Database Specification | §11 |
| 12 | API Specification | §12 |
| 13 | Frontend Specification | §13 |
| 14 | Prompt Engineering Specification | §14 |
| 15 | Testing Specification | §15 |
| 16 | Implementation Roadmap | §16 |
| 17 | Production Readiness | §17 |
| 18 | Developer Handbook | §18 |
| A | Consolidated Clarification Questions | Appendix A |

---

# SECTION 1 — System Context Document

## 1.1 Product Boundary

The MIF Infrastructure Copilot is a self-contained web application that automates creation and modification of Terraform infrastructure entries in an external GitHub repository. It does not execute Terraform, deploy infrastructure, merge pull requests, or connect to Kafka/Schema Registry. Its outputs are pull requests containing Terraform code; its inputs are user conversations and repository state.

**References:** PI-1, PI-2, PI-5, SCOPE-9, SCOPE-10, SCOPE-13

## 1.2 External Systems

| System | Role | Integration Type | Direction | Auth |
|--------|------|-----------------|-----------|------|
| GitHub (Repository) | Target repository for navigation, validation, PR creation | REST API (GitHub API v3/GraphQL) | Read + Write | OAuth token (user identity) |
| GitHub (OAuth Provider) | User authentication | OAuth 2.0 Authorization Code flow | Inbound redirect | Client ID/Secret |
| Terraform CLI | Syntax/structure validation of generated code | Local CLI execution (`init`, `fmt`, `validate`) | Outbound (local) | None (CLI) |
| PostgreSQL | Persistent storage: users, sessions, drafts, snapshots, validations, PR metadata | Database connection (async) | Read + Write | Connection credentials |
| Redis | Caching, session state, distributed locking, LangGraph checkpointing | Redis protocol | Read + Write | Connection credentials |
| LLM Provider | Natural language understanding and generation for conversational nodes | API | Outbound | API key |

**References:** TAS T1, FR-H-1, FR-A-6, FR-Q-2

## 1.3 Internal System Boundaries

| Component | Boundary | Owns | Does NOT Own |
|-----------|----------|------|--------------|
| Frontend (React+Vite) | User interface only | Rendering, user input capture, display | Business logic, validation, state persistence |
| Agent API (FastAPI) | Single entry point for frontend | Message routing to LangGraph | Direct DB queries from frontend |
| LangGraph Orchestrator | Workflow execution | Node sequencing, state transitions, interrupt management | Data persistence, external API calls |
| Service Layer | Business logic | Validation, derivation, draft management, PR creation | Direct database access |
| Repository Layer | Data access | CRUD, transactions, optimistic locking | Business rules |
| Knowledge Layer | Configuration intelligence | Registries, derivation rules, templates, validation rules | Persistence, UI |

**References:** TAS T2, CON-API-1, CON-API-2

## 1.4 Source of Truth Hierarchy

Conflicts between sources are resolved by this precedence (highest first):

| Priority | Source | Governs |
|----------|--------|---------|
| 1 | GitHub Repository (live) | Source system existence, topic existence, duplicate job detection, file contents |
| 2 | Draft Workspace (PostgreSQL) | Current working state of user changes, PR generation |
| 3 | Knowledge Base Registries (JSON) | Default values, derivation rules, validation rules, templates |
| 4 | LangGraph State (Redis/checkpoints) | Workflow position references only (never business data) |

**Rule:** If GitHub says a source does not exist but the knowledge base says it does, GitHub wins. The draft workspace is the sole input for PR generation — never LangGraph memory or transient state.

**References:** BR-A-10, BR-A-14, FR-W-1, TAS T4

## 1.5 User Journey (high-level)

```
User opens application
       │
       ▼
GitHub OAuth sign-in ──────────► Token stored; session created
       │
       ▼
Session restored (if returning) ► Draft + navigation + conversation restored
       │
       ▼
Environment selection (dev/prod) ► Mandatory gate; nothing proceeds without this
       │
       ▼
Operation choice ──────────────► "Create Glue Job" or "Modify Existing Files"
       │
       ├──► Create Glue Job ──► Source type ──► Kafka flow ──► 3 inputs ──► Validation ──► Derivation ──► Draft
       │
       ├──► Modify Files ──────► Repository navigation ──► File edit ──► Draft
       │
       ▼
"What would you like to do next?" ──► Loop (more jobs, more edits, review, undo, or PR)
       │
       ▼
Review Workspace ──► All changes visible, editable (per CQ-01), diff view
       │
       ▼
Terraform Validation ──► PASS/FAIL shown to user
       │
       ▼
Single confirmation: "Raise Pull Request?"
       │
       ▼
PR created (one commit, one PR) ──► Session saved
```

**References:** FR-A-1 through FR-A-11, FR-B-1 through FR-B-3, FR-S-1 through FR-S-4, FR-W-5 through FR-W-8, FR-Q-2, BR-S-1

## 1.6 Data Flow Boundaries

| Flow | Source | Destination | Content | Trigger |
|------|--------|-------------|---------|---------|
| User input | Frontend | Agent API | Chat message | User sends message |
| Agent response | LangGraph node | Frontend | Chat message + UI widgets | Node execution completes |
| Repository read | GitHub API | Knowledge/Validation services | File contents, folder listings | Validation or navigation |
| Draft persistence | Service layer | PostgreSQL | Draft files, glue jobs, snapshots | Every mutation |
| PR creation | Service layer | GitHub API | Branch, commit, PR | User confirms "Create PR" |
| Session recovery | PostgreSQL + Redis | Frontend | Restored session state | User returns / refresh |

**References:** FR-H-4, FR-W-1, BR-S-1, TAS T9



---

# SECTION 2 — Detailed Functional Specification

Each CPRS functional requirement is expanded below into implementation-ready detail. Business rules (BR-*) and UX requirements (UX-*) are woven into the relevant function rather than duplicated.

---

## 2.1 Environment Selection

**CPRS refs:** FR-A-2, AC-11

| Field | Detail |
|-------|--------|
| **Purpose** | Gate all workflows behind a mandatory environment choice |
| **Inputs** | User selection: `dev` or `prod` |
| **Outputs** | Environment stored in session state; all subsequent artifacts inherit this value |
| **Preconditions** | User is authenticated via GitHub OAuth (FR-H-1) |
| **Postconditions** | Session.environment is set; no workflow node may execute before this is non-null |
| **Business rules** | BR-A-2 requires env before any workflow; environment cannot be changed mid-session without starting over (FR-H-5) |
| **Failure cases** | User attempts to proceed without selecting → agent re-prompts; system never defaults silently |
| **Acceptance criteria** | AC-11: Given no environment selected, no other step is permitted |

---

## 2.2 Create Glue Job — User Input Collection

**CPRS refs:** FR-A-1, FR-A-3, FR-A-4, FR-A-10, FR-A-11

| Field | Detail |
|-------|--------|
| **Purpose** | Collect the three mandatory inputs for Glue Job creation and the source type |
| **Inputs** | (1) Source type: Kafka/JDBC/Flat File/API; (2) Source system: from repo-derived list or free-text new; (3) Schema grain: free-text |
| **Outputs** | `source_type`, `source_system`, `schema_grain` stored in workflow state |
| **Preconditions** | Environment selected; user chose "Create Glue Job" |
| **Postconditions** | If Kafka: flow continues to topic derivation. If JDBC/FlatFile/API: agent responds "need to implement" and returns to operation menu (AC-12) |
| **Business rules** | Only three values are asked up front (FR-A-1); source system list is dynamically populated from the target repository (FR-A-3, BR-A-14 — **PENDING CQ-15** for which repository); schema grain is never a dropdown (FR-A-4) |
| **Failure cases** | Source type not Kafka → placeholder response; Source system invalid characters → agent prompts for correction |
| **Acceptance criteria** | AC-12: JDBC/Flat File/API responds "need to implement"; Only 3 inputs collected before derivation |

---

## 2.3 Topic Derivation and Display

**CPRS refs:** FR-A-5, BR-A-1, BR-V-1

| Field | Detail |
|-------|--------|
| **Purpose** | Generate and display the Kafka topic name from user inputs |
| **Inputs** | `environment`, `source_system`, `schema_grain` |
| **Outputs** | `topic_name` = `{env}.{source_system}.{schema_grain}.raw` displayed to user |
| **Preconditions** | All three inputs collected |
| **Postconditions** | Topic name is stored in draft state; displayed to user in chat |
| **Business rules** | Agent produces the topic, user does not type it (BR-A-1); topic format is fixed (BR-V-1). Editability of the derived topic: **PENDING CQ-02** |
| **Failure cases** | None at this step; validation occurs next |
| **Acceptance criteria** | Topic is displayed in the exact format `{env}.{source}.{grain}.raw` |

---

## 2.4 Topic Validation

**CPRS refs:** FR-A-6, BR-A-3, BR-A-4, BR-A-5, BR-A-6, BR-A-8, BR-A-15, AC-3, AC-4

| Field | Detail |
|-------|--------|
| **Purpose** | Verify the derived topic exists in the repository before proceeding |
| **Inputs** | `source_system`, `schema_grain`, `environment` |
| **Outputs** | PASS (continue) or HARD BLOCK (stop with message) |
| **Preconditions** | Topic has been derived (§2.3) |
| **Postconditions** | On PASS: flow continues to duplicate-job validation. On BLOCK: user is stopped; must change inputs or abandon |
| **Business rules** | The agent checks `confluent_minerva_<env>/topics_<source_system>.tf` in the target repository (**PENDING CQ-14** for prod path, **PENDING CQ-15** for target repo). Repository is authoritative (BR-A-10). No broker connection ever (BR-A-15, SCOPE-9). Validation runs BEFORE derivation (BR-A-8) |
| **Failure cases** | (1) File `topics_<source>.tf` not found → "Source system not configured" (BR-A-5, AC-4); (2) File found but grain not present → "Please create the topic first" (BR-A-4, AC-3); (3) GitHub API unreachable → agent reports connectivity error, does not assume pass or fail |
| **Acceptance criteria** | AC-3 (grain absent → block), AC-4 (file absent → block); on any block: no schema list, no suggestions, no extra controls (BR-A-6) |

---

## 2.5 Duplicate Job Validation

**CPRS refs:** FR-A-7, BR-A-8, BR-A-11, AC-5

| Field | Detail |
|-------|--------|
| **Purpose** | Prevent creation of a Glue Job that already exists |
| **Inputs** | Derived `glue_job_name` (from BR-A-11 pattern), `source_system` |
| **Outputs** | PASS (continue) or HARD BLOCK ("Glue Job already exists") |
| **Preconditions** | Topic validation passed |
| **Postconditions** | On PASS: flow continues to knowledge derivation |
| **Business rules** | Check `<source_system>/locals.tf` in the target repository for the derived job key in the `glue_jobs` map. Job name pattern: `kafka-to-iceberg-batch-<source>-<grain>` (BR-A-11). Runs after topic validation, before derivation (BR-A-8) |
| **Failure cases** | Job name already present → "Glue Job already exists" (AC-5); `locals.tf` does not exist for existing source → this is a logic contradiction (source exists = folder exists = locals.tf should exist); if encountered, treat as system error |
| **Acceptance criteria** | AC-5: Given existing job name → flow stops with "Glue Job already exists" |

---

## 2.6 Knowledge Derivation

**CPRS refs:** FR-A-8, FR-A-9, BR-A-9, BR-A-10, BR-A-12, BR-A-13

| Field | Detail |
|-------|--------|
| **Purpose** | Automatically determine all Glue Job configuration values and present them |
| **Inputs** | `environment`, `source_system`, `schema_grain`, `topic_name`, source-exists flag |
| **Outputs** | Complete set of derived values (FR-A-9): Kafka Secret Name, Glue Job Name, IAM Role, Worker Type, Glue Version, Workers, Scheduling Mode, Job Type, Job Version, LH DB, S3 paths; plus file-operation plan (which files to create/modify per BR-A-12/BR-A-13) |
| **Preconditions** | Topic validation and duplicate-job validation both passed |
| **Postconditions** | Values stored in draft; presented to user in chat or review panel; file plan (create/modify) determined |
| **Business rules** | Existing source → repo is SoT for derivation (BR-A-9); new source → MIF rules/templates are SoT (BR-A-9); repo always wins on conflict (BR-A-10); existing source → modify `locals.tf` only (BR-A-12); new source → create both `locals.tf` and `glue.tf` (BR-A-13). Values for Enterprise Function: **PENDING CQ-03**; default schedule: **PENDING CQ-05**; max workers: **PENDING CQ-04**; LH DB pattern: **PENDING CQ-A1**; new-source concretes origin: **PENDING CQ-A1** |
| **Failure cases** | Repository read failure → agent reports error; Knowledge base missing/corrupt → agent reports error; derivation produces invalid value → caught by validation engine before persisting |
| **Acceptance criteria** | AC-1 (existing source → draft modifies only `locals.tf`), AC-2 (new source → both files created) |

---

## 2.7 Modify Existing Files — Navigation and Edit

**CPRS refs:** FR-B-1, FR-B-2, FR-B-3, FR-B-4, BR-B-1

| Field | Detail |
|-------|--------|
| **Purpose** | Let the user conversationally navigate the repository and edit files |
| **Inputs** | User's textual instructions (folder names, file names, edit descriptions) |
| **Outputs** | Modified file content stored in draft workspace |
| **Preconditions** | Environment selected; user chose "Modify Existing Files" |
| **Postconditions** | File changes saved to draft; snapshot created |
| **Business rules** | Agent changes only what user explicitly requests (BR-B-1); navigation is conversational, not wizard-style; guardrails on which files/folders are editable: **PENDING CQ-A6** |
| **Failure cases** | Folder/file does not exist → agent informs user; user requests edit outside scope → depends on CQ-A6; GitHub API error → agent reports connectivity issue |
| **Acceptance criteria** | User can navigate to any file in the repo, describe a change, and see it applied in the draft |

---

## 2.8 Multi-Operation Loop

**CPRS refs:** FR-S-1, FR-S-2, FR-S-3, FR-S-4, AC-8

| Field | Detail |
|-------|--------|
| **Purpose** | Allow unlimited sequential operations before a single PR |
| **Inputs** | User's choice from the "What would you like to do next?" menu |
| **Outputs** | Routing to the chosen operation, or to review/PR |
| **Preconditions** | At least one operation completed (or initial state for first-time menu) |
| **Postconditions** | Next operation begins, or flow moves to review/PR |
| **Business rules** | Menu composition rules per FR-S-3: initial = {Create Glue Job, Modify Existing Files}; after ≥1 change = full menu; "Create Another Glue Job" hidden if no job was created (AC-8). Never ask "how many jobs?" (FR-S-2). Never ask "do you want to continue?" (FR-S-4). One confirmation total: before PR (FR-S-4) |
| **Failure cases** | User types unrecognized intent → OutOfScope node handles gracefully (UX-E-6) |
| **Acceptance criteria** | AC-8: "Create Another Glue Job" visible only after ≥1 job created; multiple jobs + edits across systems accumulate in one draft |

---

## 2.9 Draft Workspace Mutation and Undo

**CPRS refs:** FR-W-1, FR-W-2, FR-W-3, FR-W-4, FR-W-6, FR-W-7

| Field | Detail |
|-------|--------|
| **Purpose** | Accumulate changes, support undo, freeze during PR creation |
| **Inputs** | File additions/modifications/deletions, Glue Job additions, value edits |
| **Outputs** | Updated draft state; snapshot created per mutation |
| **Preconditions** | Draft is in editable state (not frozen for PR creation) |
| **Postconditions** | Change persisted; snapshot recorded; undo available |
| **Business rules** | One session = one active draft (FR-W-2); undo = "Discard Last Change" only, no snapshot IDs exposed (FR-W-3); editable values scope **PENDING CQ-01**; freeze on PR confirmation (FR-W-6); duplicate PR prevention (FR-W-7) |
| **Failure cases** | Edit attempted during PR freeze → rejected with message; Snapshot creation failure → mutation must be rolled back (atomic operation) |
| **Acceptance criteria** | AC-7: repeated "Create PR" produces one PR; draft frozen during creation |

---

## 2.10 Review and PR Creation

**CPRS refs:** FR-W-5, FR-W-8, UX-R-1 through UX-R-5, FR-Q-2, BR-S-1, AC-6, AC-10

| Field | Detail |
|-------|--------|
| **Purpose** | Present all changes for final review, validate, get confirmation, create PR |
| **Inputs** | Complete draft state (all files, jobs, metadata) |
| **Outputs** | Validated review; single confirmation; one PR with one commit |
| **Preconditions** | At least one change exists in draft; user selected "Create Pull Request" or "Review Draft Workspace" |
| **Postconditions** | PR created on GitHub under user's identity; session marked complete |
| **Business rules** | PR generated only from reviewed workspace (FR-W-5); diff view with green/red (FR-W-8); field visibility per UX-R-1/R-3; validation outcomes shown, rules hidden (UX-R-4, AC-10); one commit, one PR (BR-S-1, AC-6); editability **PENDING CQ-01**; Terraform gate **PENDING CQ-13b** |
| **Failure cases** | Terraform validation fails → show failure reason (AC-10), offer to fix; PR creation fails (GitHub error) → unfreeze draft, report error; conflict detected → enter conflict resolution (FR-C-1) |
| **Acceptance criteria** | AC-6 (one PR, one commit), AC-10 (failure reasons visible), AC-7 (duplicate prevention) |

---

## 2.11 Conflict Resolution

**CPRS refs:** FR-C-1 through FR-C-5

| Field | Detail |
|-------|--------|
| **Purpose** | Handle merge conflicts when the target branch has changed since the draft was based |
| **Inputs** | Conflict details from git rebase attempt |
| **Outputs** | Resolved files; PR created with single commit |
| **Preconditions** | PR creation attempted; conflict detected |
| **Postconditions** | Conflict resolved; PR created; still one commit (BR-S-2) |
| **Business rules** | Auto-attempt rebase first (FR-C-2); show incoming vs current (FR-C-3); options: Accept Incoming, Accept Current, Accept Both, Manual Edit; resolution stays in same session (FR-C-4); result is still one commit (BR-S-2). Phase-1 depth: **PENDING CQ-A4** |
| **Failure cases** | Auto-rebase succeeds → no user action needed; Auto-rebase fails → user must resolve; User abandons resolution → draft returns to editable state |
| **Acceptance criteria** | After resolution, PR has exactly one commit |

---

## 2.12 Session History and Recovery

**CPRS refs:** FR-H-1 through FR-H-5, AC-9

| Field | Detail |
|-------|--------|
| **Purpose** | Persist sessions, provide ChatGPT-style history, recover on interruption |
| **Inputs** | GitHub identity; session data; draft state; navigation position |
| **Outputs** | Restored session with conversation, draft, and navigation intact |
| **Preconditions** | User previously authenticated; session exists in database |
| **Postconditions** | User continues exactly where they left off |
| **Business rules** | History grouped Today/Yesterday/Previous per user (FR-H-2); reopen restores conversation + draft + navigation (FR-H-3); refresh/disconnect resumes (FR-H-4, AC-9); "Start Over" clears state (FR-H-5) |
| **Failure cases** | Session data corrupt → offer "Start Over"; PostgreSQL/Redis unavailable → show error, retry |
| **Acceptance criteria** | AC-9: interrupted session fully restored |

---

## 2.13 Out-of-Scope Question Handling

**CPRS refs:** UX-E-6, CON-LG-2 (TAS)

| Field | Detail |
|-------|--------|
| **Purpose** | Handle user questions that fall outside the supported workflow |
| **Inputs** | User message that does not match any workflow intent |
| **Outputs** | Graceful response explaining scope; redirect to supported actions |
| **Preconditions** | None — can occur at any point in conversation |
| **Postconditions** | Workflow state unchanged; user returned to appropriate context |
| **Business rules** | Must handle gracefully, never fail (UX-E-6); dedicated node (TAS T3); must not modify draft or session state |
| **Failure cases** | Misclassification (scope question treated as out-of-scope) → acceptable but should be minimized through prompt engineering |
| **Acceptance criteria** | Non-workflow questions receive a helpful response without breaking the flow |



---

# SECTION 3 — Complete LangGraph Specification

**References:** TAS T2, T3, T4; CON-LG-1 (one node = one responsibility); CON-LG-2 (OutOfScope node mandatory)
**PENDING:** CQ-07 (exact node list and count). The specification below documents the consolidated node sequence from TAS T3. Nodes flagged as uncertain are marked.

## 3.1 Graph Topology

```
GitHubOAuthNode
       │
       ▼
SessionManagerNode
       │
       ▼
EnvironmentNode ◄────────── (re-entry for "Start Over")
       │
       ▼
OperationNode ◄──────────── (re-entry from multi-operation loop)
       │
       ├──────────────────► ModifyFileFlow (FR-B-*)
       │
       ▼
IntentRouterNode ─────────► (routes by source type)
       │
       ├──► SourceTypeNode
       │         │
       │    ┌────┴─────┬──────────┬──────────┐
       │    ▼          ▼          ▼          ▼
       │  KafkaFlow  JDBCNode  FlatFileNode APINode
       │    │       (placeholder) (placeholder) (placeholder)
       │    ▼
       │  SourceSystemNode
       │    │
       │    ▼
       │  SchemaGrainNode
       │    │
       │    ▼
       │  TopicValidationNode
       │    │
       │    ▼
       │  DuplicateJobValidationNode
       │    │
       │    ▼
       │  KnowledgeDerivationNode
       │    │
       ▼    ▼
DraftWorkspaceNode ◄──────── (both flows converge here)
       │
       ▼
(Multi-operation loop: return to OperationNode or continue below)
       │
       ▼
ReviewWorkspaceNode
       │
       ▼
TerraformValidationNode
       │
       ▼
ApprovalNode (single confirmation)
       │
       ▼
PRCreationNode
       │
       ▼
SessionPersistNode (UNCERTAIN — CQ-07)

OutOfScopeNode ◄──────────── (reachable from any node via intent detection)
```

## 3.2 Node Specifications

### 3.2.1 GitHubOAuthNode

| Field | Detail |
|-------|--------|
| **Purpose** | Authenticate user via GitHub OAuth and obtain access token |
| **Owner** | Auth Service |
| **Input state** | Empty/initial state or returning-user state |
| **Output state** | `user_id`, `github_username`, `github_token_ref` (reference, never raw token), `is_authenticated=true` |
| **Entry conditions** | User has opened the application |
| **Exit conditions** | Valid GitHub token obtained and persisted |
| **Interrupt points** | Yes — waits for OAuth callback redirect |
| **Retry logic** | OAuth flow restartable; token refresh if expired |
| **Failure handling** | OAuth denied → show error, re-prompt login; OAuth provider unreachable → show connectivity error |
| **State changes** | Sets authentication fields; creates or updates `users` record |
| **Called services** | GitHubOAuthService, UserRepository |
| **Never calls** | DraftService, KnowledgeService, TerraformService |
| **Allowed transitions** | → SessionManagerNode |
| **Forbidden transitions** | → Any workflow node without authentication |

**References:** FR-H-1, SEC-1, SEC-4

---

### 3.2.2 SessionManagerNode

| Field | Detail |
|-------|--------|
| **Purpose** | Create new session or restore existing session |
| **Owner** | Session Service |
| **Input state** | `user_id`, `is_authenticated=true` |
| **Output state** | `session_id`, `draft_id` (if restoring), `conversation_history` (if restoring), `navigator_state` (if restoring) |
| **Entry conditions** | User authenticated |
| **Exit conditions** | Session active in database; if restoring: draft, conversation, and navigation position loaded |
| **Interrupt points** | No |
| **Retry logic** | Database retry on transient failure |
| **Failure handling** | DB unavailable → error message; corrupt session → offer "Start Over" (FR-H-5) |
| **State changes** | Sets session context; loads or creates draft reference |
| **Called services** | SessionRepository, DraftRepository |
| **Never calls** | GitHubService, TerraformService |
| **Allowed transitions** | → EnvironmentNode |
| **Forbidden transitions** | → Any node that requires environment without passing through EnvironmentNode |

**References:** FR-H-2, FR-H-3, FR-H-4, AC-9

---

### 3.2.3 EnvironmentNode

| Field | Detail |
|-------|--------|
| **Purpose** | Collect and store the target environment |
| **Owner** | Session Service |
| **Input state** | `session_id` |
| **Output state** | `environment` = `dev` or `prod` |
| **Entry conditions** | Session active; environment not yet selected (or "Start Over" resets) |
| **Exit conditions** | `environment` is set and stored in session |
| **Interrupt points** | Yes — waits for user selection |
| **Retry logic** | Re-prompt if input invalid |
| **Failure handling** | Non-dev/non-prod input → re-prompt |
| **State changes** | Sets `session.environment` |
| **Called services** | SessionRepository |
| **Never calls** | GitHubService, KnowledgeService |
| **Allowed transitions** | → OperationNode |
| **Forbidden transitions** | → Any workflow node; environment must be set first (AC-11) |

**References:** FR-A-2, AC-11

---

### 3.2.4 OperationNode

| Field | Detail |
|-------|--------|
| **Purpose** | Present operation choices and route user intent |
| **Owner** | Orchestrator |
| **Input state** | `environment`, `draft_change_count`, `draft_job_count` |
| **Output state** | `selected_operation` |
| **Entry conditions** | Environment selected; may be re-entered from multi-operation loop |
| **Exit conditions** | User has chosen an operation |
| **Interrupt points** | Yes — waits for user choice |
| **Retry logic** | Re-prompt on unrecognized intent |
| **Failure handling** | Unrecognized → OutOfScopeNode |
| **State changes** | Sets `selected_operation` |
| **Called services** | None (routing only) |
| **Never calls** | Any persistence or external service |
| **Allowed transitions** | → SourceTypeNode (Create Glue Job), → ModifyFileFlow entry, → ReviewWorkspaceNode, → DraftWorkspaceNode (Discard), → PRCreationNode |
| **Forbidden transitions** | → PRCreationNode or ReviewWorkspaceNode when draft is empty |
| **Menu visibility rules** | Initial: {Create Glue Job, Modify Existing Files}. After ≥1 change: full menu. "Create Another Glue Job" only if `draft_job_count > 0` (AC-8) |

**References:** FR-S-2, FR-S-3, FR-S-4, AC-8

---

### 3.2.5 SourceTypeNode

| Field | Detail |
|-------|--------|
| **Purpose** | Ask user for the data source type |
| **Owner** | Orchestrator |
| **Input state** | `selected_operation = create_glue_job` |
| **Output state** | `source_type` (kafka / jdbc / flatfile / api) |
| **Entry conditions** | User chose "Create Glue Job" |
| **Exit conditions** | Source type selected |
| **Interrupt points** | Yes — waits for user choice |
| **Retry logic** | Re-prompt on invalid selection |
| **Failure handling** | Non-Kafka → respond "need to implement" (AC-12), return to OperationNode |
| **State changes** | Sets `source_type` |
| **Called services** | None |
| **Never calls** | Any external service |
| **Allowed transitions** | → SourceSystemNode (Kafka), → OperationNode (non-Kafka placeholder) |
| **Forbidden transitions** | → KnowledgeDerivation without passing through validation nodes |

**References:** FR-A-10, FR-A-11, AC-12, SCOPE-8

---

### 3.2.6 SourceSystemNode

| Field | Detail |
|-------|--------|
| **Purpose** | Present source system dropdown and collect selection |
| **Owner** | Knowledge Service |
| **Input state** | `source_type = kafka`, `environment` |
| **Output state** | `source_system`, `source_exists` (boolean) |
| **Entry conditions** | Source type is Kafka |
| **Exit conditions** | Source system selected or entered |
| **Interrupt points** | Yes — waits for user selection |
| **Retry logic** | Re-prompt on empty input |
| **Failure handling** | GitHub API failure → show error, offer retry; empty repo → show empty list + allow new entry |
| **State changes** | Sets `source_system`, `source_exists` |
| **Called services** | GitHubService (list repo folders), KnowledgeService (cached list) |
| **Never calls** | DraftService, TerraformService |
| **Allowed transitions** | → SchemaGrainNode |
| **Forbidden transitions** | → TopicValidation without schema grain |

**References:** FR-A-3, BR-A-14

---

### 3.2.7 SchemaGrainNode

| Field | Detail |
|-------|--------|
| **Purpose** | Collect free-text schema grain input |
| **Owner** | Orchestrator |
| **Input state** | `source_system` |
| **Output state** | `schema_grain` |
| **Entry conditions** | Source system selected |
| **Exit conditions** | Schema grain entered (non-empty) |
| **Interrupt points** | Yes — waits for user text input |
| **Retry logic** | Re-prompt if empty |
| **Failure handling** | Invalid characters → re-prompt with guidance |
| **State changes** | Sets `schema_grain`; triggers topic derivation (`topic_name = {env}.{source}.{grain}.raw`) |
| **Called services** | None (pure derivation) |
| **Never calls** | Any external service |
| **Allowed transitions** | → TopicValidationNode |
| **Forbidden transitions** | → KnowledgeDerivation without validation |

**References:** FR-A-4, FR-A-5, BR-A-1, BR-V-1

---

### 3.2.8 TopicValidationNode

| Field | Detail |
|-------|--------|
| **Purpose** | Verify derived topic exists in repository |
| **Owner** | Validation Service |
| **Input state** | `topic_name`, `source_system`, `schema_grain`, `environment` |
| **Output state** | `topic_validation_result` (PASS/FAIL), `topic_validation_message` |
| **Entry conditions** | Topic name derived |
| **Exit conditions** | Validation result determined |
| **Interrupt points** | No |
| **Retry logic** | GitHub API retry on transient failure (up to 3 attempts with backoff) |
| **Failure handling** | File not found → HARD BLOCK "Source system not configured" (BR-A-5); grain not found → HARD BLOCK "Please create the topic first" (BR-A-4); GitHub API persistent failure → report error |
| **State changes** | Sets validation result; records validation attempt in history (FR-Q-5) |
| **Called services** | GitHubService (file content read), ValidationService |
| **Never calls** | KnowledgeService, DraftService |
| **Allowed transitions** | → DuplicateJobValidationNode (PASS), → OperationNode (FAIL — user may choose different inputs) |
| **Forbidden transitions** | → KnowledgeDerivation on FAIL |

**Repository path checked:** `confluent_minerva_<env>/topics_<source_system>.tf` — **PENDING CQ-14** for prod path

**References:** FR-A-6, BR-A-3 through BR-A-6, BR-A-8, AC-3, AC-4

---

### 3.2.9 DuplicateJobValidationNode

| Field | Detail |
|-------|--------|
| **Purpose** | Verify the derived Glue Job does not already exist |
| **Owner** | Validation Service |
| **Input state** | `source_system`, `schema_grain`, derived `glue_job_name` |
| **Output state** | `duplicate_validation_result` (PASS/FAIL) |
| **Entry conditions** | Topic validation passed |
| **Exit conditions** | Validation result determined |
| **Interrupt points** | No |
| **Retry logic** | GitHub API retry on transient failure |
| **Failure handling** | Job exists → HARD BLOCK "Glue Job already exists" (AC-5); `locals.tf` missing for supposedly existing source → system error |
| **State changes** | Records validation result |
| **Called services** | GitHubService (read `<source>/locals.tf`), ValidationService |
| **Never calls** | KnowledgeService, DraftService |
| **Allowed transitions** | → KnowledgeDerivationNode (PASS), → OperationNode (FAIL) |
| **Forbidden transitions** | → DraftWorkspace on FAIL |

**References:** FR-A-7, BR-A-8, BR-A-11, AC-5

---

### 3.2.10 KnowledgeDerivationNode

| Field | Detail |
|-------|--------|
| **Purpose** | Derive all Glue Job configuration values using knowledge layer |
| **Owner** | Knowledge Service |
| **Input state** | `environment`, `source_system`, `schema_grain`, `source_exists` |
| **Output state** | `derived_values` (complete set per FR-A-9), `file_plan` (create/modify decisions per BR-A-12/BR-A-13) |
| **Entry conditions** | Both repository validations passed |
| **Exit conditions** | All values derived; file plan determined |
| **Interrupt points** | No |
| **Retry logic** | Knowledge registry load retry; GitHub read retry |
| **Failure handling** | Registry missing → critical error; derivation produces invalid value → validation engine catches |
| **State changes** | Stores `derived_values` in state; records provenance reference |
| **Called services** | KnowledgeBaseService, RepositoryKnowledgeProvider, DerivedValueEngine |
| **Never calls** | DraftService (derivation only, not persistence), GitHubService (for PR), TerraformService |
| **Allowed transitions** | → DraftWorkspaceNode |
| **Forbidden transitions** | → PRCreation, → ReviewWorkspace (must go through Draft first) |

**References:** FR-A-8, FR-A-9, BR-A-9, BR-A-10, BR-A-12, BR-A-13, AC-1, AC-2; TAS T5

---

### 3.2.11 DraftWorkspaceNode

| Field | Detail |
|-------|--------|
| **Purpose** | Persist derived values and file plan into the draft workspace |
| **Owner** | Draft Service |
| **Input state** | `derived_values`, `file_plan` (from creation flow) OR modified file content (from modify flow) |
| **Output state** | `draft_id`, `draft_change_count`, `draft_job_count`, `snapshot_id` |
| **Entry conditions** | Values derived (creation) or file edited (modify) |
| **Exit conditions** | Draft updated; snapshot created |
| **Interrupt points** | No |
| **Retry logic** | Database transaction retry |
| **Failure handling** | Transaction failure → rollback, report error; snapshot failure → mutation must also roll back |
| **State changes** | Creates/updates draft records; creates immutable snapshot; increments counters |
| **Called services** | DraftRepository, SnapshotService, DraftGlueJobRepository, DraftFileRepository |
| **Never calls** | GitHubService, TerraformService, KnowledgeService |
| **Allowed transitions** | → OperationNode (multi-operation loop) |
| **Forbidden transitions** | → PRCreation directly (must go through Review and Validation) |

**References:** FR-W-1, FR-W-2, FR-W-3; TAS T6

---

### 3.2.12 ReviewWorkspaceNode

| Field | Detail |
|-------|--------|
| **Purpose** | Present all accumulated changes for review |
| **Owner** | Review Service |
| **Input state** | `draft_id` with all accumulated changes |
| **Output state** | `review_presented = true`, user edits (if any) |
| **Entry conditions** | User selected "Review Draft Workspace" or "Create Pull Request" |
| **Exit conditions** | User has reviewed and made any desired edits |
| **Interrupt points** | Yes — user may edit fields, make changes, or confirm |
| **Retry logic** | N/A (interactive) |
| **Failure handling** | Draft load failure → show error |
| **State changes** | May update draft if user edits values (scope per CQ-01) |
| **Called services** | DraftRepository, DraftGlueJobRepository, DraftFileRepository |
| **Never calls** | GitHubService, TerraformService |
| **Allowed transitions** | → TerraformValidationNode, → OperationNode (user wants more changes) |
| **Forbidden transitions** | → PRCreation without passing TerraformValidation |

**References:** FR-W-5, FR-W-8, UX-R-1 through UX-R-5

---

### 3.2.13 TerraformValidationNode

| Field | Detail |
|-------|--------|
| **Purpose** | Run Terraform validation on generated/modified files |
| **Owner** | Terraform Service |
| **Input state** | `draft_id`, all draft files materialized |
| **Output state** | `terraform_validation_status` (PASS/FAIL), `validation_messages[]` |
| **Entry conditions** | Review presented; user proceeding toward PR |
| **Exit conditions** | Validation result recorded |
| **Interrupt points** | No (automated) |
| **Retry logic** | CLI retry on transient failure |
| **Failure handling** | FAIL → show reason to user (UX-R-4, AC-10); user may edit and re-validate or proceed (**PENDING CQ-13b** for mandatory gate) |
| **State changes** | Records validation result and history (FR-Q-5) |
| **Called services** | TerraformValidationService (CLI: `init`, `fmt`, `validate`) |
| **Never calls** | GitHubService, KnowledgeService, DraftService |
| **Allowed transitions** | → ReviewWorkspaceNode (on FAIL, user wants to fix), → ApprovalNode (on PASS or per CQ-13b) |
| **Forbidden transitions** | → PRCreation without passing through Approval |

**References:** FR-Q-2, FR-Q-3, UX-R-4, AC-10; TAS T10

---

### 3.2.14 ApprovalNode

| Field | Detail |
|-------|--------|
| **Purpose** | Present single final confirmation before PR creation |
| **Owner** | Orchestrator |
| **Input state** | `terraform_validation_status`, complete draft state |
| **Output state** | `user_approved = true/false` |
| **Entry conditions** | Terraform validation complete |
| **Exit conditions** | User confirms or declines |
| **Interrupt points** | Yes — waits for user confirmation |
| **Retry logic** | N/A |
| **Failure handling** | User declines → return to ReviewWorkspace or OperationNode |
| **State changes** | Sets approval status |
| **Called services** | None (pure user interaction) |
| **Never calls** | Any service |
| **Allowed transitions** | → PRCreationNode (approved), → ReviewWorkspaceNode (declined), → OperationNode (declined, wants more changes) |
| **Forbidden transitions** | → PRCreation without explicit approval (FR-S-4) |

**References:** FR-S-4, FR-W-6

---

### 3.2.15 PRCreationNode

| Field | Detail |
|-------|--------|
| **Purpose** | Create branch, single commit, and pull request on GitHub |
| **Owner** | PR Service |
| **Input state** | `draft_id` (frozen), `user_approved = true`, `github_token_ref` |
| **Output state** | `pr_url`, `pr_number`, `commit_sha`, `branch_name` |
| **Entry conditions** | User approved; draft frozen (FR-W-6) |
| **Exit conditions** | PR created successfully |
| **Interrupt points** | No |
| **Retry logic** | GitHub API retry; idempotency check prevents duplicate PR (FR-W-7) |
| **Failure handling** | Conflict detected → enter conflict resolution (FR-C-1); GitHub error → unfreeze draft, report error; duplicate prevention: if PR already exists for this draft, return existing PR info |
| **State changes** | Freezes draft; creates PR metadata record; updates session status |
| **Called services** | GitHubService (branch, commit, PR), DraftRepository, PRMetadataRepository |
| **Never calls** | KnowledgeService, TerraformService |
| **Allowed transitions** | → ConflictResolutionFlow (on conflict), → SessionComplete |
| **Forbidden transitions** | → Any edit node while PR is being created |

**References:** BR-S-1, BR-S-2, FR-W-6, FR-W-7, AC-6, AC-7; TAS T10, T11

---

### 3.2.16 OutOfScopeNode

| Field | Detail |
|-------|--------|
| **Purpose** | Handle user questions/requests outside the supported workflow |
| **Owner** | Orchestrator |
| **Input state** | User message classified as out-of-scope |
| **Output state** | Helpful response; workflow state unchanged |
| **Entry conditions** | Intent classifier routes here |
| **Exit conditions** | Response delivered |
| **Interrupt points** | No |
| **Retry logic** | N/A |
| **Failure handling** | LLM failure → generic "I can help with Glue Job creation and file modification" |
| **State changes** | None — must not modify draft, session, or workflow state |
| **Called services** | LLM (for response generation) |
| **Never calls** | GitHubService, DraftService, any persistence service |
| **Allowed transitions** | → Return to previous node context |
| **Forbidden transitions** | → Any workflow-advancing node |

**References:** UX-E-6, CON-LG-2 (TAS T3)

---

### 3.2.17 Placeholder Nodes (JDBC, FlatFile, API)

| Field | Detail |
|-------|--------|
| **Purpose** | Acknowledge unsupported source types gracefully |
| **Owner** | Orchestrator |
| **Input state** | `source_type` = jdbc/flatfile/api |
| **Output state** | Placeholder message delivered |
| **Entry conditions** | User selected a non-Kafka source type |
| **Exit conditions** | Message delivered; flow returns to OperationNode |
| **All other fields** | No retry, no failure handling, no state changes, no services called |
| **Allowed transitions** | → OperationNode |

**References:** FR-A-11, AC-12, SCOPE-8

---

## 3.3 Uncertain Nodes (PENDING CQ-07)

The following nodes appear in some source lists but not others. Their inclusion depends on CQ-07 resolution:

| Node | Possible purpose | Appears in |
|------|-----------------|------------|
| TopicGenerationNode | Separate node for deriving topic string | Some node lists |
| SessionPersistNode | Final node to persist session after PR | Some node lists |
| IntentRouterNode vs OperationNode | May be separate or combined | Varies |

Until CQ-07 is answered, implementations should treat TopicGeneration as part of SchemaGrainNode and session persistence as part of PRCreationNode.



---

# SECTION 4 — Complete State Machine Specification

**References:** TAS T7, T4; FR-W-6, FR-W-7, FR-H-4, FR-H-5

## 4.1 Draft Lifecycle State Machine

**PENDING CQ-06:** Four candidate state sets exist. The specification below uses the most frequently recurring set and notes alternatives. Confirm before implementation.

### Working model (pending confirmation)

```
DRAFT_EDITING ──────► REVIEW_READY ──────► PR_CREATING ──────► PR_CREATED
      │                    │                    │
      │                    │                    ├──► PR_FAILED → DRAFT_EDITING
      │                    │                    │
      ▼                    ▼                    ▼
 ABANDONED            DRAFT_EDITING       CONFLICT_DETECTED → DRAFT_EDITING (after resolution)
                     (user wants changes)
```

| State | Description | Allowed actions | Forbidden actions |
|-------|-------------|----------------|-------------------|
| DRAFT_EDITING | Active editing; mutations create snapshots | Add/edit/delete files; add/edit jobs; undo; value changes | Create PR |
| REVIEW_READY | Draft presented in review workspace | Edit reviewed fields (per CQ-01); return to editing; proceed to validation | Add new jobs or files directly |
| PR_CREATING | Draft frozen; PR being created on GitHub | None — all mutations blocked (FR-W-6) | Any edit, undo, add, or delete |
| PR_CREATED | Terminal success state | View PR link; start new session | Any mutation |
| PR_FAILED | PR creation failed (not conflict) | Return to editing; retry PR | N/A |
| CONFLICT_DETECTED | Merge conflict found during PR creation | Conflict resolution actions (per CQ-A4) | Unrelated edits |
| ABANDONED | User explicitly abandoned draft or session expired | Start new session | Any mutation |

### Transition rules

| From | To | Trigger | Guard |
|------|-----|---------|-------|
| DRAFT_EDITING | REVIEW_READY | User selects "Review" or "Create PR" | `draft_change_count > 0` |
| REVIEW_READY | DRAFT_EDITING | User requests changes | Always allowed |
| REVIEW_READY | PR_CREATING | User confirms "Create PR" after validation | Approval confirmed; Terraform validation status checked (per CQ-13b) |
| PR_CREATING | PR_CREATED | GitHub PR created successfully | Exactly one commit, one PR |
| PR_CREATING | PR_FAILED | GitHub API error (non-conflict) | N/A |
| PR_CREATING | CONFLICT_DETECTED | Merge conflict during push | N/A |
| CONFLICT_DETECTED | DRAFT_EDITING | Conflict resolved | Resolution applied, still one commit |
| PR_FAILED | DRAFT_EDITING | Auto-transition; draft unfrozen | N/A |
| Any editable state | ABANDONED | User "Start Over" or session timeout | N/A |

---

## 4.2 Session Lifecycle

```
UNAUTHENTICATED ──► AUTHENTICATING ──► ACTIVE ──► COMPLETED
                                         │              │
                                         ▼              ▼
                                      SUSPENDED      ARCHIVED
                                         │
                                         ▼
                                       ACTIVE (restored)
```

| State | Description | References |
|-------|-------------|------------|
| UNAUTHENTICATED | User not signed in | FR-H-1 |
| AUTHENTICATING | OAuth flow in progress | FR-H-1 |
| ACTIVE | User working; session persisted | FR-H-2, FR-H-4 |
| SUSPENDED | Browser closed / connection lost; session persisted | FR-H-4, AC-9 |
| COMPLETED | PR created; session saved for history | FR-H-2 |
| ARCHIVED | Old session in history view | FR-H-2 |

### Recovery rules (FR-H-4, AC-9)

| Scenario | Behavior |
|----------|----------|
| Browser refresh | Session restored from PostgreSQL; conversation, draft, and navigation position intact |
| WebSocket disconnect | Automatic reconnection attempt; state restored from persistent store |
| Backend restart | Session restored from PostgreSQL (token must persist — SEC-4, CQ-A7); Redis state rebuilt from checkpoints |
| "Start Over" | Session state cleared; new draft created; old session archived (FR-H-5) |

---

## 4.3 PR Lifecycle (within a session)

```
NOT_STARTED ──► VALIDATING ──► VALIDATION_PASSED ──► CREATING ──► CREATED
                    │                                     │
                    ▼                                     ▼
              VALIDATION_FAILED ──► VALIDATING       CREATION_FAILED
              (user fixes, re-run)                   (unfreezes draft)
                                                          │
                                                          ▼
                                                    CONFLICT_DETECTED
                                                          │
                                                          ▼
                                                    RESOLVING ──► CREATING
```

**References:** FR-Q-2, FR-Q-3, FR-W-6, FR-W-7, FR-C-1 through FR-C-5, BR-S-1

---

## 4.4 Validation Lifecycle

```
NOT_RUN ──► RUNNING ──► PASSED
                │
                ▼
             FAILED ──► (user edits) ──► RUNNING (re-run)
```

| Field | Detail |
|-------|--------|
| Validation types | Topic (§9.1), Duplicate Job (§9.2), Terraform (§9.3) |
| History | Every run is recorded with timestamp, rule IDs, and result (FR-Q-5) |
| Visibility | Outcomes shown to user; rules hidden (UX-R-4, AC-10) |

---

# SECTION 5 — Knowledge Layer Specification

**References:** TAS T5; FR-A-8, FR-A-9, BR-A-9, BR-A-10

## 5.1 Component Architecture

| Component | Purpose | Input | Output | Owner |
|-----------|---------|-------|--------|-------|
| **RepositoryKnowledgeProvider** | Extract facts from GitHub repository | GitHub API responses (folder listings, file contents) | Structured facts: existing sources, existing jobs, file contents, patterns | Knowledge Service |
| **KnowledgeBaseService** | Orchestrate derivation and validation using registries + repo facts | User inputs + repo facts + registry data | Derived values, validation results, template selections | Knowledge Service |
| **RegistryLoader** | Load and cache JSON registries | File system / embedded resources | Parsed registry objects with version info | Knowledge Service |
| **ValidationEngine** | Apply validation rules to inputs and derived values | Values to validate + validation_rules.json | Pass/fail with rule IDs and messages | Validation Service |
| **DerivedValueEngine** | Compute configuration values from inputs + rules + patterns | User inputs + repo facts + repo_patterns.json + terraform_templates.json | Complete derived value set | Knowledge Service |
| **TemplateEngine** | Select and populate Terraform templates | Derived values + terraform_templates.json | Rendered `locals.tf` entries, `glue.tf` module blocks | Knowledge Service |
| **ProvenanceService** | Track which registry versions and repo states produced each derivation | Derivation context | Provenance record (versions, timestamps, sources) | Knowledge Service |

## 5.2 Registry Specifications

### 5.2.1 `source_systems.json`

| Field | Detail |
|-------|--------|
| **Purpose** | Cached catalog of known source systems with their properties |
| **Contents** | Source system name, known schema grains, default worker config, IAM patterns, S3 patterns |
| **Refresh strategy** | Rebuilt from repository scan on session start or cache miss; cache TTL configurable |
| **Authority** | Supplementary to live repository scan; repo always wins (BR-A-10) |
| **Versioning** | Each load produces a `registry_version` stored in state (TAS T4) |

### 5.2.2 `validation_rules.json`

| Field | Detail |
|-------|--------|
| **Purpose** | Define all validation rules with stable IDs |
| **Contents** | Rule ID (e.g., `TR-001`), rule type, field, condition, error message template, severity |
| **Rule categories** | Topic validation (`TR-*`), Job validation (`JR-*`), Terraform validation (`TF-*`), File validation (`FR-*`) |
| **Extensibility** | New rules added to JSON without code changes (TAS T5) |
| **Versioning** | `rule_set_version` tracked in state |

### 5.2.3 `terraform_templates.json`

| Field | Detail |
|-------|--------|
| **Purpose** | Define the shape of generated Terraform output |
| **Contents** | `locals.tf` glue_jobs entry template, `glue.tf` module block template, variable interpolation patterns |
| **Template variables** | `{env}`, `{source}`, `{grain}`, `{job_key}`, `{secret_name}`, `{worker_type}`, etc. |
| **Authority** | Must match TAS T10 output shapes exactly |

### 5.2.4 `repo_patterns.json`

| Field | Detail |
|-------|--------|
| **Purpose** | Define repository structure patterns for navigation, validation, and derivation |
| **Contents** | Topic file path pattern (`confluent_minerva_{env}/topics_{source}.tf`), source folder pattern (`{source}/locals.tf`, `{source}/glue.tf`), naming conventions |
| **PENDING** | Prod path pattern requires CQ-14; target repo requires CQ-15 |

## 5.3 Caching Strategy

| Cache layer | What is cached | TTL | Invalidation |
|-------------|---------------|-----|--------------|
| Source system list | Folder listing from GitHub | Per-session (loaded once) | Manual refresh; new session |
| Registry data | Parsed JSON registries | Application lifetime (hot-reloadable) | Registry file change detection |
| File contents | Individual file reads from GitHub | Per-operation (validated fresh each time) | Not cached across validations — freshness critical for validation |

## 5.4 Ownership Rules

| Rule | Detail |
|------|--------|
| Only KnowledgeDerivationNode calls KnowledgeBaseService for derivation | No other node derives values |
| Only ValidationNodes call ValidationEngine | No other node validates |
| TemplateEngine is called only by DraftWorkspaceNode (to materialize) | KnowledgeDerivation derives values; DraftWorkspace materializes templates |
| RepositoryKnowledgeProvider is the ONLY component that reads GitHub for knowledge facts | Navigation reads are separate (GitHubService via NavigationService) |

---

# SECTION 6 — Repository Navigation Specification

**References:** FR-B-1, FR-B-2, FR-B-3, BR-B-1, FR-H-3

## 6.1 Navigation Model

| Field | Detail |
|-------|--------|
| **Purpose** | Let users conversationally browse the target repository tree |
| **Entry** | User selects "Modify Existing Files" |
| **Target repository** | **PENDING CQ-15** |
| **Root** | Repository root of the target repo |

## 6.2 Tree Loading Strategy

| Strategy | Detail |
|----------|--------|
| **Initial load** | Load root-level folders and files (single API call) |
| **Lazy loading** | Subfolder contents loaded only when user navigates into them |
| **Depth limit** | No hard limit; follows user navigation |
| **Caching** | Per-session cache of loaded tree nodes; cleared on new session or "Start Over" |

## 6.3 Navigation Flow

```
User says: "change saptcc"
Agent: Shows contents of saptcc/
       ├── locals.tf
       ├── glue.tf
       └── ...
User says: "open locals.tf"
Agent: Shows file (or summary); asks "What changes would you like to make?"
User describes change
Agent: Applies change, saves to draft, shows result
Agent: "Want to change anything else in this folder?"
```

## 6.4 Navigation State (persisted for recovery)

| Field | Purpose | References |
|-------|---------|------------|
| `current_path` | Current folder/file the user is viewing | FR-H-3 |
| `breadcrumb[]` | Path history for context | FR-H-3 |
| `visited_paths[]` | All paths visited in this session | Recovery |
| `open_file` | Currently open file (if any) | FR-B-2 |

## 6.5 File Discovery and Filtering

| Behavior | Detail |
|----------|--------|
| Show all files | Agent lists all files in the current directory |
| No filtering by default | All `.tf` and other files visible |
| Folder vs file distinction | Agent clearly indicates which entries are folders vs files |
| File content display | On "open", show file content or a meaningful summary |
| Guardrails | **PENDING CQ-A6** (which files/folders are editable, and extra checks) |

## 6.6 Permissions

| Rule | Detail |
|------|--------|
| Read | All repository files readable via GitHub API using user's OAuth token |
| Write | Changes are NOT written directly to the repo; they go to the draft workspace only |
| User scope | User can only access repos their GitHub token grants access to |



---

# SECTION 7 — Draft Workspace Specification

**References:** FR-W-1 through FR-W-8; TAS T6, T7

## 7.1 Draft Lifecycle

| Phase | Description | Allowed mutations | Snapshot behavior |
|-------|-------------|-------------------|-------------------|
| **Creation** | Draft created when first operation begins | N/A | Initial snapshot created |
| **Editing** | Active accumulation of changes | Add file, edit file, delete file, add job, edit job values, undo | Every mutation creates immutable snapshot |
| **Review** | Draft presented for final review | Field edits (per CQ-01), return to editing | Edits create snapshots |
| **Frozen** | PR creation in progress | None — all mutations blocked | No snapshots |
| **Complete** | PR created successfully | None — read-only | No snapshots |
| **Abandoned** | User started over or session expired | None — archived | No snapshots |

## 7.2 Snapshot System

| Property | Detail | References |
|----------|--------|------------|
| **Immutability** | Snapshots are never modified after creation | FR-W-3 (TAS concept) |
| **Auto-creation** | Every mutation triggers a new snapshot before the mutation is applied | FR-W-3 |
| **Content** | Complete draft state at that point: all files, all jobs, all metadata | TAS T6 |
| **Restore** | "Discard Last Change" creates a NEW state from the previous snapshot; does not edit the snapshot | FR-W-3 |
| **User visibility** | User sees only "Discard Last Change"; never snapshot IDs, version numbers, or internal state | FR-W-3 |
| **Storage** | PostgreSQL `snapshots` table, keyed by (draft_id, created_at) | TAS T6 |
| **Retention** | Snapshots retained for the life of the session; cleanup policy **PENDING CQ-10** |

## 7.3 Undo Behavior

| Action | User says | System does |
|--------|----------|-------------|
| **Undo last** | "Discard Last Change" | Load previous snapshot → create new draft state from it → new snapshot |
| **No redo** | Not specified in CPRS | Redo is NOT a requirement; only undo (one level at a time) |
| **Undo scope** | Reverses exactly one mutation | If user added a job, undo removes that job; if user edited a file, undo restores previous version |
| **Undo limit** | Can undo back to initial empty draft | Each undo creates its own snapshot, so the undo history itself is preserved |

## 7.4 Change Stack

| Change type | How it enters the draft | References |
|-------------|------------------------|------------|
| **New Glue Job** | KnowledgeDerivation → DraftWorkspace; job added to `draft_glue_jobs` | FR-A-8, AC-1, AC-2 |
| **New file** (new source) | Template materialization; files added to `draft_files` | BR-A-13 |
| **Modified file** (existing source) | Template injection into existing file content; file added to `draft_files` | BR-A-12 |
| **Manual file edit** | User's described change applied to file content; stored in `draft_files` | FR-B-2 |
| **Value edit** | User changes a derived value; `draft_glue_jobs` updated, file re-materialized | FR-W-4 (scope per CQ-01) |
| **Discard** | Previous snapshot restored | FR-W-3 |

## 7.5 File Ownership

| Rule | Detail |
|------|--------|
| Draft owns all file changes | No file change exists outside the draft |
| File identified by path | `draft_files` keyed by `(draft_id, path)` |
| File content stored in draft | Content stored as text (TAS T6); no external pointer in Phase-1 |
| Original content reference | Store the base version (from GitHub) alongside the modified version for diff generation |

## 7.6 Conflict Metadata

| Field | Purpose | Populated when |
|-------|---------|----------------|
| `draft_base_sha` | The commit SHA the draft was based on | Draft creation (read from repo HEAD) |
| `repo_head_sha` | Current repo HEAD at PR creation time | PR creation attempt |
| `conflict_files[]` | List of files with merge conflicts | Conflict detection during rebase |

**References:** TAS T6, FR-C-1

## 7.7 Review Preparation

When user selects "Review" or "Create PR," the draft workspace prepares:

| Artifact | Content | Display |
|----------|---------|---------|
| File diff list | All files added/modified/deleted with before/after | Green (added), Red (deleted), Red+Green (modified) per FR-W-8 |
| Glue Job summary | All jobs with their derived values | Table per UX-R-1 |
| PR metadata | Commit message, PR title, PR description | Editable text fields |
| Statistics | Files changed count, jobs created count | Summary line |

---

# SECTION 8 — Review Workspace Specification

**References:** FR-W-5, FR-W-8, UX-R-1 through UX-R-5

## 8.1 Field Classification

**PENDING CQ-01** for definitive per-field editability. Working model based on latest consolidated guidance:

### Glue Job fields

| Field | Displayed | Editable? (working model) | Source |
|-------|-----------|--------------------------|--------|
| Topic Name | Yes (UX-R-1) | Read-only (derived) — **PENDING CQ-02** | Agent-derived from 3 inputs |
| Kafka Secret Name | Yes | **PENDING CQ-01** | Agent-derived |
| Glue Job Name | Yes | **PENDING CQ-01** | Agent-derived |
| IAM Role | Yes | **PENDING CQ-01** | Agent-derived |
| Worker Type | Yes | Editable (dropdown: G.1X/G.2X/G.4X) | Default from KB |
| Glue Version | Yes | **PENDING CQ-01** | Agent-derived |
| Workers | Yes | Editable (number input; max **PENDING CQ-04**) | Default from KB |
| Scheduling Mode | Yes | Editable (text → cron conversion) | Default **PENDING CQ-05** |
| Job Type | Yes | **PENDING CQ-01** | Agent-derived |
| Job Version | Yes | **PENDING CQ-01** | Agent-derived |
| Enterprise Function | Yes | Editable (dropdown + new; values **PENDING CQ-03**) | Default AGTR |
| Subgroup | Yes | Editable (dropdown + new: APAC/NA/LATAM) | Default APAC |
| Lakehouse DB | Yes | **PENDING CQ-01** | Agent-derived |
| S3 Paths | Yes | **PENDING CQ-01** | Agent-derived |

### PR metadata fields

| Field | Displayed | Editable? | Source |
|-------|-----------|-----------|--------|
| Commit Message | Yes | Editable | Agent-generated default |
| PR Title | Yes | Editable | Agent-generated default |
| PR Description | Yes | Editable | Agent-generated default |

### Hidden fields (UX-R-3)

| Field | Reason |
|-------|--------|
| Validation rules | Backend-only (UX-R-3) |
| Kafka bootstrap servers | Internal infrastructure (UX-R-3) |
| Schema Registry endpoints | Internal infrastructure (UX-R-3) |
| Terraform internal values | Backend-only (UX-R-3) |
| Derived internal metadata | Backend-only (UX-R-3) |
| Transformer configuration | **PENDING CQ-A5** (always defaulted, never shown) |

## 8.2 Validation Display

| Element | Visibility | Content | References |
|---------|-----------|---------|------------|
| Validation outcome (PASS) | Shown | "Terraform validation passed" with green indicator | UX-R-4, AC-10 |
| Validation outcome (FAIL) | Shown | Failure reason + affected files/rules in user-friendly language | UX-R-4, AC-10 |
| Validation rule IDs | Hidden | e.g., `TR-001` not shown to user | UX-R-3 |
| Validation rule logic | Hidden | The condition that was evaluated | UX-R-3 |
| Validation history | Shown (summary) | "Attempt 1: Failed → Attempt 2: Passed" | FR-Q-5 |

## 8.3 Diff Rendering

| Element | Detail | References |
|---------|--------|------------|
| Format | GitHub-style unified diff | FR-W-8 |
| Added lines | Green background with `+` prefix | FR-W-8 |
| Removed lines | Red background with `-` prefix | FR-W-8 |
| Modified lines | Old in red, new in green | FR-W-8 |
| File summary | "Files Changed: N" with list | FR-W-8 |
| Expandable | Each file expandable to see full diff | FR-W-8 |
| Full diff engine | **PENDING CQ-09** (Phase-1 vs deferred) |

## 8.4 Approval Rules

| Rule | Detail | References |
|------|--------|------------|
| Single confirmation | Exactly one "Raise Pull Request?" confirmation | FR-S-4 |
| Terraform gate | Must Terraform validation pass? **PENDING CQ-13b** | FR-Q-4 |
| Draft non-empty | PR cannot be created from empty draft | FR-S-3 menu rules |
| User identity | PR raised under user's GitHub identity | FR-H-1 |

## 8.5 PR Readiness Checklist (system-enforced)

| Check | Required | Auto-enforced |
|-------|----------|---------------|
| Draft has ≥1 change | Yes | Yes |
| Environment set | Yes | Yes (AC-11) |
| Terraform validation run | Yes | Yes (FR-Q-2) |
| Terraform validation passed | **PENDING CQ-13b** | Depends |
| User confirmed | Yes | Yes (FR-S-4) |
| Draft not already frozen/completed | Yes | Yes (FR-W-6) |

---

# SECTION 9 — Validation Specification

**References:** FR-Q-1 through FR-Q-5, UX-R-4; TAS T5

## 9.1 Topic Validation

| Field | Detail |
|-------|--------|
| **Validation ID prefix** | `TR-*` |
| **Trigger** | After topic derivation, before duplicate-job validation |
| **Input** | `environment`, `source_system`, `schema_grain`, derived `topic_name` |
| **Repository path** | `confluent_minerva_<env>/topics_<source_system>.tf` (**PENDING CQ-14** for prod) |
| **Rule TR-001** | File `topics_<source>.tf` must exist; failure → "Source system not configured" |
| **Rule TR-002** | Schema grain must be present in the topics file; failure → "Please create the topic first" |
| **Ordering** | Runs FIRST in the validation chain (FR-Q-1, BR-A-8) |
| **Error display** | Message shown to user; rule ID hidden (UX-R-4) |

## 9.2 Duplicate Job Validation

| Field | Detail |
|-------|--------|
| **Validation ID prefix** | `JR-*` |
| **Trigger** | After topic validation passes |
| **Input** | `source_system`, derived `glue_job_name` |
| **Repository path** | `<source_system>/locals.tf` in target repo |
| **Rule JR-001** | Derived job key must NOT exist in the `glue_jobs` map of `locals.tf`; failure → "Glue Job already exists" |
| **Ordering** | Runs AFTER topic validation, BEFORE knowledge derivation (FR-Q-1, BR-A-8) |
| **Error display** | Message shown to user; rule ID hidden |

## 9.3 Terraform Validation

| Field | Detail |
|-------|--------|
| **Validation ID prefix** | `TF-*` |
| **Trigger** | After review, before PR confirmation (FR-Q-2) |
| **Input** | All materialized draft files |
| **Method** | Execute `terraform init`, `terraform fmt -check`, `terraform validate` against materialized files |
| **Rule TF-001** | `terraform init` succeeds |
| **Rule TF-002** | `terraform fmt` reports no formatting issues |
| **Rule TF-003** | `terraform validate` reports no errors |
| **Ordering** | Runs ONCE, immediately before PR (FR-Q-2). Re-runs if user makes changes after failure |
| **Error display** | Failure details shown to user (AC-10); rule IDs hidden; user offered option to fix (FR-Q-3) |

## 9.4 Validation Ordering Summary

```
1. Topic Validation (TR-*)
   │ FAIL → Hard block
   ▼ PASS
2. Duplicate Job Validation (JR-*)
   │ FAIL → Hard block
   ▼ PASS
3. Knowledge Derivation (not a validation, but depends on 1+2 passing)
   │
   ▼
4. ... (user edits, multi-operation loop) ...
   │
   ▼
5. Terraform Validation (TF-*)
   │ FAIL → Show reason, offer fix
   ▼ PASS (or per CQ-13b)
6. PR Creation
```

**References:** FR-Q-1, BR-A-8

## 9.5 Validation Recording

| Field | Detail |
|-------|--------|
| Each validation run is recorded | Timestamp, validation type, rule IDs evaluated, result (pass/fail), error messages |
| History is per-draft | All validation attempts for a draft are retained |
| Accessible to | Backend (full); user (outcomes only per UX-R-4) |

**References:** FR-Q-5

## 9.6 Validation Error Messages (user-facing)

| Rule | User-facing message | Notes |
|------|-------------------|-------|
| TR-001 | "Source system not configured." | No suggestions, no schema list (BR-A-6) |
| TR-002 | "Please create the topic first." | No suggestions (BR-A-6) |
| JR-001 | "Glue Job already exists." | Show existing job name |
| TF-001 | "Terraform initialization failed: {detail}" | Include relevant Terraform output |
| TF-002 | "Terraform formatting issues detected in {file}" | Include file names |
| TF-003 | "Terraform validation failed: {detail}" | Include Terraform error output |



---

# SECTION 10 — GitHub Integration Specification

**References:** FR-H-1, BR-S-1, BR-S-2, FR-W-6, FR-W-7, FR-C-1 through FR-C-5; TAS T11

## 10.1 OAuth Flow

| Step | Detail |
|------|--------|
| 1. Login initiation | Frontend redirects to GitHub OAuth authorization URL with `client_id`, `redirect_uri`, `scope` |
| 2. User authorizes | User grants access on GitHub |
| 3. Callback | GitHub redirects to callback URL with authorization `code` |
| 4. Token exchange | Backend exchanges `code` for `access_token` via GitHub API |
| 5. Token storage | Token stored as a secret reference (SEC-1); persisted for recovery (SEC-4, **PENDING CQ-A7** for encryption) |
| 6. User creation/update | `users` record created/updated with GitHub username, user ID |
| **Scopes required** | `repo` (read/write repository), `user:email` (identify user) |

## 10.2 Repository Operations

| Operation | GitHub API | When used | References |
|-----------|-----------|-----------|------------|
| List folders | `GET /repos/{owner}/{repo}/contents/{path}` | Source system dropdown; repository navigation | FR-A-3, FR-B-2 |
| Read file | `GET /repos/{owner}/{repo}/contents/{path}` | Topic validation, duplicate-job validation, file editing | FR-A-6, FR-A-7, FR-B-2 |
| Get repo info | `GET /repos/{owner}/{repo}` | Initial connection, branch info | Setup |
| **Target repo** | **PENDING CQ-15** | All operations | All |

## 10.3 Branch Management

| Rule | Detail | References |
|------|--------|------------|
| Branch naming | `draft/<session_id>` or `draft/<draft_id>` (**PENDING CQ-06** for which key) | TAS T7 |
| Branch creation | Created from target branch HEAD at PR creation time | BR-S-1 |
| Base branch | Main/default branch of target repository | Standard |
| Branch per draft | One dedicated branch per draft | TAS T7 |

## 10.4 Commit Generation — One Commit Rule

| Step | Detail | References |
|------|--------|------------|
| 1. Collect files | Read all `draft_files` from the draft workspace | FR-W-1 |
| 2. Create tree | Build a single Git tree containing all file changes | BR-S-1 |
| 3. Create commit | Single commit with the user's commit message | BR-S-1 |
| 4. Update branch | Point branch to the new commit | BR-S-1 |
| 5. Create PR | Open PR from draft branch to base branch | BR-S-1 |
| **Never** | Multiple commits per PR; per-file commits; temporary commits | BR-S-1 |
| **API approach** | Use GitHub Git Data API (`POST /repos/{owner}/{repo}/git/trees`, `POST .../git/commits`, `PATCH .../git/refs`) for atomic single-commit creation | TAS T10 |

## 10.5 PR Generation

| Field | Source | Editable |
|-------|--------|----------|
| Title | Agent-generated from draft context | Yes (UX-R-1) |
| Description | Agent-generated summary of changes | Yes (UX-R-1) |
| Base branch | Default branch of target repo | No |
| Head branch | `draft/<id>` | No |
| Reviewers | Not set in Phase-1 | N/A |
| Labels | Not set in Phase-1 | N/A |

## 10.6 Conflict Handling

| Step | Detail | References |
|------|--------|------------|
| 1. Detection | During PR creation, if base branch has advanced past `draft_base_sha` | FR-C-1 |
| 2. Auto-resolution | Agent attempts `git fetch` + `git rebase` | FR-C-2 |
| 3. Manual resolution | If conflict persists, show incoming vs current diff; user picks: Accept Incoming, Accept Current, Accept Both, Manual Edit | FR-C-3 |
| 4. Finalize | After resolution: `git commit --amend` + `git push --force-with-lease` | BR-S-2 |
| 5. Result | Still one commit in one PR | BR-S-2 |
| **Phase-1 depth** | **PENDING CQ-A4** | FR-C-5 |

## 10.7 Recovery

| Scenario | Behavior |
|----------|----------|
| PR creation interrupted (network) | On retry, check if PR already exists for this branch; if yes, return existing PR info (FR-W-7 duplicate protection) |
| Branch already exists | If from same draft, reuse; if stale, delete and recreate |
| Token expired | Refresh token or re-authenticate; resume operation |

---

# SECTION 11 — Database Specification

**References:** TAS T6, T8; **PENDING CQ-08** for authoritative table count

## 11.1 Entity Relationships

**Working model based on 8 named entities (CQ-08 may expand this):**

```
users ──< sessions ──< drafts ──< draft_glue_jobs
                          │
                          ├──< draft_files
                          │
                          ├──< snapshots
                          │
                          └──< validation_reports
                          │
                          └─── pr_metadata (1:1)
```

| Relationship | Type | Detail |
|-------------|------|--------|
| users → sessions | 1:N | One user has many sessions |
| sessions → drafts | 1:1 | One session has one active draft (FR-W-2) |
| drafts → draft_glue_jobs | 1:N | One draft may have many jobs (FR-S-1) |
| drafts → draft_files | 1:N | One draft may have many file changes (FR-S-1) |
| drafts → snapshots | 1:N | One draft has many snapshots (auto-created on mutation) |
| drafts → validation_reports | 1:N | One draft may have many validation attempts (FR-Q-5) |
| drafts → pr_metadata | 1:1 | One draft produces at most one PR |

## 11.2 Table Responsibilities

| Table | Owns | Does not own |
|-------|------|-------------|
| `users` | GitHub identity, auth metadata | Session state, draft content |
| `sessions` | Environment, session lifecycle, conversation history reference | File contents, job details |
| `drafts` | Lifecycle status, base SHA, branch name, PR metadata fields | Individual file or job records |
| `draft_glue_jobs` | All job-level config values (per TAS T6) | File content, session context |
| `draft_files` | File path, original content, modified content, operation type | Job configuration |
| `snapshots` | Immutable point-in-time draft state | Current state (that's the draft) |
| `validation_reports` | Validation type, result, rule IDs, messages, timestamp | Business rule definitions |
| `pr_metadata` | PR URL, PR number, commit SHA, creation timestamp | Draft editing state |

## 11.3 Repository Ownership

| Repository class | Owns persistence for | Transaction boundary |
|-----------------|---------------------|---------------------|
| UserRepository | `users` | Per-operation |
| SessionRepository | `sessions` | Per-operation |
| DraftRepository | `drafts` | Per-operation; coordinates with child repos |
| DraftGlueJobRepository | `draft_glue_jobs` | Within draft transaction |
| DraftFileRepository | `draft_files` | Within draft transaction |
| SnapshotRepository | `snapshots` | Within draft mutation transaction |
| ValidationReportRepository | `validation_reports` | Per-validation |
| PRMetadataRepository | `pr_metadata` | Within PR creation transaction |

## 11.4 Transaction Patterns

| Pattern | Detail | References |
|---------|--------|------------|
| **Draft mutation** | Add/edit file or job → create snapshot → update draft counters. Atomic: if snapshot fails, mutation rolls back | FR-W-3 |
| **Undo** | Load previous snapshot → create new state → new snapshot. Atomic | FR-W-3 |
| **PR creation** | Freeze draft → create PR → update pr_metadata. If PR fails, unfreeze draft | FR-W-6, FR-W-7 |
| **Session recovery** | Read session + draft + latest snapshot. Read-only transaction | FR-H-4 |

## 11.5 Optimistic Locking

| Table | Lock field | Purpose |
|-------|-----------|---------|
| `drafts` | `version` (integer, incremented on every update) | Prevent concurrent draft mutations |
| `sessions` | `version` | Prevent concurrent session updates |

**Behavior:** Update operations include `WHERE version = expected_version`; on mismatch, retry with fresh read.

## 11.6 Soft Delete

| Table | Strategy | References |
|-------|----------|------------|
| `users` | Soft delete (`deleted_at` timestamp; null = active) | Account deactivation |
| `sessions` | Soft delete | Session cleanup |
| `drafts` | Soft delete (ABANDONED state also serves as logical delete) | Draft lifecycle |
| `snapshots` | No delete in Phase-1; retention policy **PENDING CQ-10** | Immutability |

## 11.7 Indexes

| Index | Table | Columns | Purpose |
|-------|-------|---------|---------|
| `idx_sessions_user` | sessions | (user_id) | User's sessions list |
| `idx_sessions_draft` | sessions | (current_draft_id) | Session-draft lookup |
| `idx_jobs_draft` | draft_glue_jobs | (draft_id) | Jobs for a draft |
| `idx_jobs_key` | draft_glue_jobs | (draft_id, job_key) UNIQUE | Duplicate prevention |
| `idx_files_draft` | draft_files | (draft_id) | Files for a draft |
| `idx_files_path` | draft_files | (draft_id, path) UNIQUE | File uniqueness |
| `idx_snapshots` | snapshots | (draft_id, created_at) | Snapshot ordering |
| `idx_validations` | validation_reports | (draft_id, created_at) | Validation history |

**References:** TAS T6

## 11.8 Constraints

| Constraint | Table | Detail |
|-----------|-------|--------|
| FK sessions.user_id → users.id | sessions | Cascade: restrict delete |
| FK sessions.current_draft_id → drafts.id | sessions | Nullable (no draft yet) |
| FK drafts.session_id → sessions.id | drafts | Cascade: restrict |
| FK draft_glue_jobs.draft_id → drafts.id | draft_glue_jobs | Cascade: delete with draft |
| FK draft_files.draft_id → drafts.id | draft_files | Cascade: delete with draft |
| FK snapshots.draft_id → drafts.id | snapshots | Cascade: delete with draft |
| FK validation_reports.draft_id → drafts.id | validation_reports | Cascade: delete with draft |
| FK pr_metadata.draft_id → drafts.id | pr_metadata | Unique (1:1) |
| CHECK drafts.status | drafts | Must be valid lifecycle state (per CQ-06) |
| CHECK sessions.environment | sessions | Must be 'dev' or 'prod' |

## 11.9 Migration Ordering

| Order | Migration | Depends on |
|-------|-----------|------------|
| 1 | Create `users` | None |
| 2 | Create `sessions` | `users` |
| 3 | Create `drafts` | `sessions` |
| 4 | Create `draft_glue_jobs` | `drafts` |
| 5 | Create `draft_files` | `drafts` |
| 6 | Create `snapshots` | `drafts` |
| 7 | Create `validation_reports` | `drafts` |
| 8 | Create `pr_metadata` | `drafts` |
| 9 | Add indexes | All tables |
| 10 | Add audit columns to all tables | All tables |

---

# SECTION 12 — API Specification

**References:** TAS T9; CON-API-1, CON-API-2

## 12.1 Endpoint Inventory

### Primary endpoint (frontend-facing)

| Method | Path | Purpose | Auth | References |
|--------|------|---------|------|------------|
| POST | `/agent/message` | Send user message to agent; receive agent response | OAuth token | CON-API-1 |
| GET | `/agent/stream` | WebSocket/SSE for streaming agent responses | OAuth token | UX-E-1 |

### Auth endpoints

| Method | Path | Purpose | Auth |
|--------|------|---------|------|
| GET | `/auth/github/login` | Initiate GitHub OAuth flow | None |
| GET | `/auth/github/callback` | Handle OAuth callback | None (code exchange) |
| POST | `/auth/logout` | Clear session | OAuth token |
| GET | `/auth/me` | Get current user info | OAuth token |

### Session endpoints

| Method | Path | Purpose | Auth | References |
|--------|------|---------|------|------------|
| GET | `/sessions` | List user's sessions (history) | OAuth token | FR-H-2 |
| GET | `/sessions/{id}` | Get session detail with draft info | OAuth token | FR-H-3 |
| DELETE | `/sessions/{id}` | Abandon/archive session | OAuth token | FR-H-5 |

### Internal/support endpoints (NOT called directly by frontend — CON-API-2)

| Method | Path | Purpose | Auth | Notes |
|--------|------|---------|------|-------|
| GET | `/internal/drafts/{id}` | Get draft state | Service token | Agent calls internally |
| POST | `/internal/drafts/{id}/snapshot` | Create snapshot | Service token | Called by draft service |
| POST | `/internal/validation/run` | Trigger validation | Service token | Called by validation service |
| POST | `/internal/pr/create` | Create PR | Service token | Called by PR service |

### Health and operations

| Method | Path | Purpose | Auth |
|--------|------|---------|------|
| GET | `/health` | Liveness check | None |
| GET | `/health/ready` | Readiness check (DB + Redis) | None |

## 12.2 Primary Endpoint Detail — POST /agent/message

### Request

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `session_id` | string (UUID) | Yes (after first message) | Active session |
| `message` | string | Yes | User's text message |
| `context` | object | No | Additional context (selected option, form data) |
| `context.selected_option` | string | No | For menu selections (e.g., "Create Glue Job") |
| `context.form_data` | object | No | For structured inputs (e.g., environment selection) |

### Response

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | string (UUID) | Session identifier |
| `messages[]` | array | Agent response messages |
| `messages[].type` | enum | TEXT, FORM, SUMMARY, VALIDATION, CODE_PREVIEW, APPROVAL, PR_SUCCESS |
| `messages[].content` | string/object | Message content (text or structured) |
| `messages[].actions[]` | array | Available actions/buttons |
| `draft_summary` | object | Current draft state summary (change count, job count) |
| `navigation_state` | object | Current navigator position (if in modify flow) |

### Errors

| HTTP Code | Error | When |
|-----------|-------|------|
| 400 | INVALID_INPUT | Malformed request |
| 401 | UNAUTHORIZED | Missing or invalid token |
| 404 | SESSION_NOT_FOUND | Invalid session_id |
| 409 | DRAFT_FROZEN | Edit attempted during PR creation (FR-W-6) |
| 429 | RATE_LIMITED | Too many requests |
| 500 | INTERNAL_ERROR | System failure |
| 503 | SERVICE_UNAVAILABLE | Database or external service down |

## 12.3 Session List — GET /sessions

### Response

| Field | Type | Description |
|-------|------|-------------|
| `sessions[]` | array | List of user's sessions |
| `sessions[].id` | string (UUID) | Session ID |
| `sessions[].environment` | string | dev/prod |
| `sessions[].status` | string | active/completed/abandoned |
| `sessions[].created_at` | datetime | Creation time |
| `sessions[].updated_at` | datetime | Last activity |
| `sessions[].draft_summary` | object | {change_count, job_count, status} |
| `sessions[].last_message_preview` | string | Truncated last message |
| `grouping` | Grouped by Today / Yesterday / Previous (FR-H-2) |

## 12.4 Authentication Requirements

| Rule | Detail |
|------|--------|
| All endpoints except `/health*` and `/auth/github/*` | Require valid OAuth token |
| Token validation | Verify token against GitHub API; check user exists in DB |
| Token refresh | If token expired, redirect to re-auth |
| Session-user binding | Session can only be accessed by the user who created it |

## 12.5 Validation Rules for All Endpoints

| Rule | Detail |
|------|--------|
| Request body validation | All required fields present; types correct |
| Session ownership | Requesting user must own the session |
| Draft status | Mutations rejected if draft is frozen (409 DRAFT_FROZEN) |
| Rate limiting | Per-user rate limiting on `/agent/message` |



---

# SECTION 13 — Frontend Specification

**References:** UX-E-1 through UX-E-7, UX-R-1 through UX-R-5; TAS T1

## 13.1 Pages

| Page | Route | Purpose | Access | References |
|------|-------|---------|--------|------------|
| Login | `/login` | GitHub OAuth sign-in | Unauthenticated only | FR-H-1 |
| Chat | `/chat` or `/chat/:sessionId` | Main workspace: three-pane layout | Authenticated | UX-E-1, UX-E-2 |
| PR Review | (modal/panel within Chat) | Final review before PR | Authenticated, draft exists | FR-W-5, UX-R-1 |
| History | (sidebar within Chat) | Session history list | Authenticated | FR-H-2 |

## 13.2 Three-Pane Layout

```
┌──────────────┬────────────────────────┬──────────────────┐
│  LEFT PANE   │     CENTER PANE        │   RIGHT PANE     │
│              │                        │                  │
│  Sessions    │     Chat               │   Workspace      │
│  Sidebar     │     Conversation       │   Panel          │
│              │                        │                  │
│  - Today     │  - Agent messages      │  - Draft summary │
│  - Yesterday │  - User messages       │  - File list     │
│  - Previous  │  - Forms               │  - Job list      │
│              │  - Validations         │  - Diff preview  │
│  [New Chat]  │  - Approvals           │  - PR metadata   │
│              │  - Code previews       │                  │
└──────────────┴────────────────────────┴──────────────────┘
```

**References:** UX-E-2, UX-E-3

## 13.3 Component Hierarchy

### Left Pane — Session Sidebar

| Component | Purpose | Data source |
|-----------|---------|-------------|
| SessionList | Lists all sessions grouped by date | `GET /sessions` |
| SessionItem | Single session with preview | Session data |
| NewChatButton | Start new session | Creates new session |

### Center Pane — Chat

| Component | Purpose | Data source |
|-----------|---------|-------------|
| ChatContainer | Manages message list and input | Agent responses |
| MessageList | Renders all messages in order | Message array |
| UserMessage | User's text input display | User input |
| AgentMessage | Agent's response (text, forms, code, etc.) | Agent response |
| EnvironmentSelector | Dev/prod selection widget | FR-A-2 |
| OperationMenu | "What would you like to do next?" options | FR-S-3 |
| SourceTypeSelector | Kafka/JDBC/FlatFile/API choice | FR-A-10 |
| SourceSystemDropdown | Dynamic source system list + new entry | FR-A-3 |
| SchemaGrainInput | Free-text input for schema grain | FR-A-4 |
| TopicDisplay | Shows derived topic name | FR-A-5 |
| ValidationResult | Shows pass/fail with details | UX-R-4 |
| ApprovalPrompt | "Raise Pull Request?" confirmation | FR-S-4 |
| PRSuccessMessage | PR link and summary | Post-PR |
| ChatInput | Text input with send button | User interaction |

### Right Pane — Workspace

| Component | Purpose | Data source |
|-----------|---------|-------------|
| WorkspacePanel | Container for draft state | Draft data |
| DraftSummary | Change count, job count, status | Draft metadata |
| FileChangeList | List of added/modified/deleted files | `draft_files` |
| GlueJobList | List of jobs with key values | `draft_glue_jobs` |
| DiffViewer | GitHub-style diff rendering | File before/after |
| ReviewWorkspace | Full review with all fields (UX-R-1) | Draft + jobs + PR metadata |
| PRMetadataForm | Commit message, PR title, description | Editable fields |
| NavigatorPanel | Repository folder/file browser | GitHub API |

## 13.4 State Management

| State domain | What it holds | Persistence |
|-------------|--------------|-------------|
| Auth state | User identity, token status, login state | Memory + secure storage |
| Session state | Active session ID, session list | API-backed |
| Chat state | Message history for current session | API-backed + local |
| Draft state | Current draft summary (jobs, files, status) | API-backed |
| Navigation state | Current path, breadcrumb, open file | API-backed (for recovery) |
| UI state | Active pane, loading states, modals | Local only (not persisted) |

## 13.5 Chat Flow Rendering

| Message type | Rendering |
|-------------|-----------|
| TEXT | Plain text message bubble |
| FORM | Interactive form with inputs/dropdowns/buttons |
| SUMMARY | Structured summary card (job values, file list) |
| VALIDATION | Status card: green (pass) or red (fail) with details |
| CODE_PREVIEW | Syntax-highlighted code block (Terraform) |
| APPROVAL | Prominent confirmation prompt with "Create PR" / "Cancel" buttons |
| PR_SUCCESS | Success card with PR link, commit SHA, branch name |

**References:** UX-E-4 (TAS T3 message types)

## 13.6 Loading States

| Scenario | User sees |
|----------|----------|
| Agent processing | Typing indicator / loading animation in chat |
| Repository loading | Skeleton loader in navigator panel |
| Validation running | Progress indicator with "Validating..." |
| PR creating | Full-screen or modal progress: "Creating pull request..." with freeze indication |
| Session restoring | "Restoring your session..." with progress |

## 13.7 Error States

| Error | User sees | Recovery |
|-------|----------|----------|
| Network failure | "Connection lost. Retrying..." with retry button | Auto-retry + manual retry |
| Auth expired | "Session expired. Please sign in again." | Redirect to login |
| Draft frozen conflict | "Your draft is being processed. Please wait." | Auto-resolves when PR completes/fails |
| Server error | "Something went wrong. Please try again." | Retry button |
| Validation failure | Red validation card with details | "Fix and retry" option |

---

# SECTION 14 — Prompt Engineering Specification

**References:** PI-5, UX-E-5, UX-E-6, CON-LG-1; TAS T3

## 14.1 Prompt Architecture

Each LangGraph node that requires LLM interaction has a dedicated prompt. Prompts are managed as templates with variable injection — never hardcoded inline.

| Prompt category | Used by | Purpose |
|----------------|---------|---------|
| System prompt | All LLM nodes | Define agent identity, constraints, and behavior |
| Node-specific prompts | Individual nodes | Guide the LLM for that node's single responsibility |
| Validation prompts | TerraformValidation, topic/job validation | Interpret validation results for user-friendly messaging |
| Review prompts | ReviewWorkspace | Summarize changes for review |
| Recovery prompts | SessionManager | Resume conversation naturally |
| Conflict prompts | ConflictResolution | Explain conflict and options |
| Out-of-scope prompts | OutOfScopeNode | Handle gracefully, redirect |

## 14.2 System Prompt Specification

| Element | Content | References |
|---------|---------|------------|
| **Identity** | "You are the MIF Infrastructure Copilot, an AI assistant that helps engineers create and modify Terraform Glue Job infrastructure." | PI-1, PI-2 |
| **Scope** | "You help with: creating Kafka Glue Jobs, modifying existing repository files, reviewing changes, and creating pull requests." | SCOPE-1, SCOPE-2 |
| **Constraints** | "Ask only the minimum questions necessary. Never ask how many jobs to create. Never repeat confirmations. Only one confirmation: before creating the PR." | FR-S-2, FR-S-4, UX-E-5 |
| **Style** | "Be conversational, direct, and helpful. This is a ChatGPT-style experience, not a form wizard." | PI-5, UX-E-1 |
| **Boundaries** | "You never connect to Kafka brokers. You never execute Terraform in production. You never merge PRs." | SCOPE-9, SCOPE-10, SCOPE-13 |
| **Source of truth** | "The GitHub repository is always the source of truth. If your knowledge conflicts with the repository, the repository wins." | BR-A-10 |

## 14.3 Node-Specific Prompts

### EnvironmentNode prompt
- Purpose: Ask user to choose dev or prod
- Tone: Brief, friendly, no explanation needed
- Expected output: Single environment selection
- Reference: FR-A-2

### OperationNode prompt
- Purpose: Present available operations based on current draft state
- Dynamic: Menu items depend on `draft_change_count` and `draft_job_count` (FR-S-3)
- Tone: "What would you like to do next?" — no filler
- Reference: FR-S-2, FR-S-3

### SourceSystemNode prompt
- Purpose: Present source system options from repository
- Must include: option to enter a new source system
- Tone: Dropdown-like presentation
- Reference: FR-A-3

### SchemaGrainNode prompt
- Purpose: Ask for schema grain (free text)
- Must NOT: Present a list or suggestions
- Reference: FR-A-4

### KnowledgeDerivationNode prompt
- Purpose: Present all derived values to the user
- Must: Show values clearly, indicate which are derived
- Must NOT: Ask user to confirm each value individually (PI-5, no wizard)
- Reference: FR-A-8, FR-A-9

### OutOfScopeNode prompt
- Purpose: Acknowledge the question is outside scope; redirect helpfully
- Must: Be friendly, not dismissive
- Must NOT: Attempt to answer questions outside its domain
- Reference: UX-E-6

## 14.4 Validation Prompts

| Validation type | Prompt purpose |
|----------------|----------------|
| Topic not found | Translate TR-001/TR-002 result into user-friendly message without exposing rule IDs |
| Duplicate job | Translate JR-001 into clear guidance |
| Terraform failure | Summarize Terraform CLI output into actionable guidance; hide internal paths |

**References:** UX-R-4, AC-10

## 14.5 Recovery Prompts

| Scenario | Prompt behavior |
|----------|----------------|
| Session restored | "Welcome back! You were working on [summary]. Would you like to continue?" |
| Draft restored | "Your draft has [N] changes. [brief summary]. What would you like to do?" |
| Navigation restored | "You were browsing [path]. Would you like to continue here?" |

**References:** FR-H-3, FR-H-4, AC-9

## 14.6 Conflict Prompts

| Scenario | Prompt behavior |
|----------|----------------|
| Auto-resolved | "A newer change was merged, but I was able to reconcile your changes automatically." |
| Manual resolution needed | "There's a conflict in [file(s)]. Here are the differences: [diff]. Would you like to: Accept Incoming / Accept Current / Accept Both / Edit Manually?" |

**References:** FR-C-2, FR-C-3



---

# SECTION 15 — Testing Specification

**References:** TAS T13; AC-1 through AC-14

## 15.1 Test Categories and Ownership

| Category | Scope | Owner | When run |
|----------|-------|-------|----------|
| Unit | Single function/class in isolation | Developer who wrote it | Every commit |
| Integration | Service + DB or Service + GitHub API | Backend team | Every PR |
| Contract | API request/response shape | Frontend + Backend | Every PR |
| Conversation flow | End-to-end LangGraph flow for a scenario | QA / Backend | Every sprint |
| Recovery | Session/draft recovery after interruption | Backend | Every sprint |
| Failure | Graceful handling of external failures (GitHub down, DB down) | Backend | Every sprint |
| Performance | Response time, concurrent sessions | SRE / Backend | Pre-release |
| Acceptance | CPRS acceptance criteria (AC-1 through AC-14) | QA | Pre-release |

## 15.2 Unit Test Specifications

| Component | What to test | Key assertions |
|-----------|-------------|----------------|
| DerivedValueEngine | Value derivation for known inputs | Output matches expected values per TAS T10 patterns |
| ValidationEngine | Each validation rule | TR-001, TR-002, JR-001 produce correct pass/fail |
| TemplateEngine | Terraform template rendering | Output matches TAS T10 `locals.tf` / `glue.tf` shapes |
| SnapshotService | Snapshot creation and restore | Immutability; restore produces new state; undo works |
| DraftService | Draft lifecycle transitions | Valid transitions succeed; invalid transitions are rejected |
| TopicDerivation | Topic string formation | `{env}.{source}.{grain}.raw` for all input combinations |
| JobNameDerivation | Job name formation | `kafka-to-iceberg-batch-{source}-{grain}` |
| MenuVisibility | Operation menu logic | Rules from FR-S-3 correctly applied |

## 15.3 Integration Test Specifications

| Test | Components involved | Scenario | Expected result |
|------|-------------------|----------|-----------------|
| IT-01 | GitHubService + real/mock GitHub API | Read folder listing | Returns valid source system list |
| IT-02 | GitHubService + real/mock GitHub API | Read topic file | Returns file content for validation |
| IT-03 | DraftRepository + PostgreSQL | Create draft, add job, snapshot, undo | State correctly persisted and restored |
| IT-04 | ValidationService + GitHubService | Topic validation (pass case) | Returns PASS |
| IT-05 | ValidationService + GitHubService | Topic validation (fail: grain missing) | Returns FAIL with TR-002 |
| IT-06 | ValidationService + GitHubService | Topic validation (fail: file missing) | Returns FAIL with TR-001 |
| IT-07 | TerraformService + CLI | Validate good Terraform | Returns PASS |
| IT-08 | TerraformService + CLI | Validate bad Terraform | Returns FAIL with details |
| IT-09 | PRService + GitHubService | Create branch + commit + PR | One PR with one commit created |
| IT-10 | SessionService + PostgreSQL + Redis | Session save and restore | Full state recovered |

## 15.4 Contract Test Specifications

| Contract | Parties | What is tested |
|----------|---------|---------------|
| CT-01 | Frontend ↔ `/agent/message` | Request shape, response shape, all message types |
| CT-02 | Frontend ↔ `/sessions` | Session list response shape, grouping |
| CT-03 | Frontend ↔ `/auth/*` | OAuth flow, token format, error responses |
| CT-04 | Backend ↔ GitHub API | Expected API calls and responses for each operation |
| CT-05 | Agent ↔ LangGraph | State shape passed between nodes |

## 15.5 Conversation Flow Test Specifications

| Test | Scenario | Steps | Expected outcome | CPRS ref |
|------|----------|-------|-----------------|----------|
| CF-01 | Happy path: new Kafka job (existing source) | Select env → Select source type → Select source → Enter grain → Derive → Review → Validate → Approve → PR | PR created; locals.tf modified only | AC-1, AC-6 |
| CF-02 | Happy path: new Kafka job (new source) | Same but with new source system | PR created; locals.tf + glue.tf created | AC-2, AC-6 |
| CF-03 | Topic validation failure | Select env → Enter non-existent topic | Hard block with correct message | AC-3, AC-4 |
| CF-04 | Duplicate job failure | Enter existing job details | Hard block "Glue Job already exists" | AC-5 |
| CF-05 | Multiple jobs in one session | Create Job 1 → Create Job 2 → Create PR | One PR, one commit, both jobs | AC-6 |
| CF-06 | Mixed operations | Create Job → Modify File → Create PR | One PR, one commit | AC-6 |
| CF-07 | Undo | Create Job → Discard Last Change | Job removed from draft | FR-W-3 |
| CF-08 | Menu visibility | Create Job → Check menu → Modify File only → Check menu | "Create Another" appears after job; hidden if only file edits | AC-8 |
| CF-09 | JDBC placeholder | Select JDBC as source type | "Need to implement" response | AC-12 |
| CF-10 | Environment gate | Attempt operation without env | Blocked | AC-11 |
| CF-11 | Validation fail + fix | Terraform validation fails → Edit → Re-validate → Pass → PR | PR created after fix | AC-10 |
| CF-12 | Duplicate PR prevention | Click "Create PR" twice rapidly | Only one PR created | AC-7 |

## 15.6 Recovery Test Specifications

| Test | Scenario | Recovery expectation | CPRS ref |
|------|----------|---------------------|----------|
| RT-01 | Browser refresh mid-conversation | Session, draft, conversation, navigation restored | AC-9 |
| RT-02 | Backend restart with active sessions | Sessions recoverable from PostgreSQL | FR-H-4 |
| RT-03 | Redis failure during workflow | Graceful degradation; state recoverable from PostgreSQL | NFR-1 |
| RT-04 | GitHub API timeout during validation | Retry with backoff; inform user | FR-Q-3 |
| RT-05 | PR creation fails (network) | Draft unfrozen; user can retry | FR-W-6 |

## 15.7 Failure Test Specifications

| Test | Failure injected | Expected behavior |
|------|-----------------|-------------------|
| FT-01 | PostgreSQL unavailable | Error message; no data loss; retry option |
| FT-02 | Redis unavailable | Degraded operation; session state from PostgreSQL |
| FT-03 | GitHub API 500 | Retry with backoff; inform user after max retries |
| FT-04 | GitHub token expired mid-session | Prompt re-authentication; resume after |
| FT-05 | Terraform CLI not found | Clear error message; PR creation blocked |
| FT-06 | Concurrent draft mutation | Optimistic lock detects; retry with fresh state |

## 15.8 Performance Test Specifications

| Test | Metric | Target | Notes |
|------|--------|--------|-------|
| PT-01 | Agent message response time | **PENDING CQ-A8** | End-to-end including LLM call |
| PT-02 | Concurrent active sessions | **PENDING CQ-A8** | Simulate with load generator |
| PT-03 | Session restore time | **PENDING CQ-A8** | From refresh to usable state |
| PT-04 | PR creation time | **PENDING CQ-A8** | Including GitHub API calls |
| PT-05 | Knowledge derivation time | **PENDING CQ-A8** | Including GitHub reads |

## 15.9 Acceptance Test Matrix

| AC ID | Test reference(s) | Automated? |
|-------|-------------------|------------|
| AC-1 | CF-01 | Yes |
| AC-2 | CF-02 | Yes |
| AC-3 | CF-03 | Yes |
| AC-4 | CF-03 | Yes |
| AC-5 | CF-04 | Yes |
| AC-6 | CF-01, CF-02, CF-05, CF-06 | Yes |
| AC-7 | CF-12 | Yes |
| AC-8 | CF-08 | Yes |
| AC-9 | RT-01 | Yes |
| AC-10 | CF-11 | Yes |
| AC-11 | CF-10 | Yes |
| AC-12 | CF-09 | Yes |
| AC-13 | **PENDING CQ-01** | Blocked |
| AC-14 | **PENDING CQ-13b** | Blocked |

---

# SECTION 16 — Implementation Roadmap

**References:** TAS T13 (build order); all process governance from source

## 16.1 Phase Overview

| Phase | Name | Goal | Key deliverables |
|-------|------|------|-----------------|
| P1 | Foundation | Runnable skeleton with auth and DB | FastAPI app, React shell, PostgreSQL schema, Redis, OAuth |
| P2 | Database & Repository Layer | Persistence fully operational | All 8 tables, all repositories, migrations, CRUD verified |
| P3 | Knowledge Layer | Derivation and validation engine working | Registries, loaders, derivers, validation engine, templates |
| P4 | LangGraph Core | Workflow orchestration functional | All nodes, state model, routing, interrupts |
| P5 | API Layer | Frontend-backend contract operational | Agent endpoint, session endpoints, auth endpoints |
| P6 | Frontend | UI functional end-to-end | Three-pane layout, chat, workspace, review, history |
| P7 | Validation & Review | Quality gates active | Topic validation, duplicate-job, Terraform validation, review workspace |
| P8 | PR Creation | Full PR flow working | Branch, commit, PR, conflict detection |
| P9 | Recovery & Polish | Production behaviors | Session recovery, draft recovery, undo, error handling |
| P10 | Testing & Certification | Quality evidence | All test categories executed; acceptance criteria verified |

## 16.2 Dependency Graph

```
P1 Foundation
  │
  ▼
P2 Database ────────┐
  │                  │
  ▼                  ▼
P3 Knowledge    P4 LangGraph (depends on P2 for state persistence)
  │                  │
  └────────┬─────────┘
           │
           ▼
        P5 API (depends on P3 + P4)
           │
           ▼
        P6 Frontend (depends on P5)
           │
           ▼
        P7 Validation (depends on P3 + P4 + P6)
           │
           ▼
        P8 PR Creation (depends on P7)
           │
           ▼
        P9 Recovery (depends on P2 + P4 + P6)
           │
           ▼
        P10 Testing (depends on all)
```

## 16.3 Phase Details

### Phase 1 — Foundation

| Field | Detail |
|-------|--------|
| **Goal** | Runnable application skeleton with authentication |
| **Deliverables** | FastAPI app with health endpoint; React app with login page; PostgreSQL connection; Redis connection; GitHub OAuth flow; docker-compose for local dev |
| **Dependencies** | None (starting point) |
| **Entry criteria** | Development environment ready; GitHub OAuth app registered |
| **Exit criteria** | User can sign in with GitHub; health endpoint responds; DB schema empty but connectable; Redis reachable |
| **Verification** | OAuth round-trip; health check passes; DB connection verified; Redis ping |
| **Evidence required** | Running app screenshot; health endpoint response; OAuth token obtained; DB connection log |
| **Risks** | GitHub OAuth app registration; environment variable management |
| **Rollback** | N/A (first phase) |

### Phase 2 — Database & Repository Layer

| Field | Detail |
|-------|--------|
| **Goal** | All tables created; all repositories operational with CRUD |
| **Deliverables** | Migration scripts for 8 tables; repository classes; optimistic locking; audit columns; integration tests |
| **Dependencies** | P1 (PostgreSQL connection) |
| **Entry criteria** | P1 verified |
| **Exit criteria** | All tables exist; all repositories pass CRUD tests; optimistic locking verified; FK constraints verified |
| **Verification** | Fresh DB install; migration up/down; CRUD for every entity; concurrent update test |
| **Evidence required** | Migration logs; test results; DB schema dump |
| **Risks** | Schema design (CQ-08 may change table count) |
| **Rollback** | Migration down scripts |

### Phase 3 — Knowledge Layer

| Field | Detail |
|-------|--------|
| **Goal** | Knowledge registries loaded; derivation and validation engines operational |
| **Deliverables** | JSON registries; RegistryLoader; DerivedValueEngine; ValidationEngine; TemplateEngine; RepositoryKnowledgeProvider |
| **Dependencies** | P2 (for persistence of derived values) |
| **Entry criteria** | P2 verified |
| **Exit criteria** | Given inputs (env, source, grain), engine produces correct derived values matching TAS T10; validation rules TR-001/TR-002/JR-001 pass/fail correctly |
| **Verification** | Unit tests for all derivation rules; integration test with mock GitHub |
| **Evidence required** | Test results; sample derivation output; registry content |
| **Risks** | PENDING CQ-A1 (new source concretes); PENDING CQ-14 (prod path) |
| **Rollback** | Remove knowledge module; registries are configuration, not schema |

### Phase 4 — LangGraph Core

| Field | Detail |
|-------|--------|
| **Goal** | Workflow orchestration with all nodes functional |
| **Deliverables** | All node implementations; state model; graph builder; routing; interrupt handling; checkpointing |
| **Dependencies** | P2 (checkpointing, state persistence), P3 (knowledge nodes call KBS) |
| **Entry criteria** | P2 and P3 verified |
| **Exit criteria** | Happy-path conversation flow executes end-to-end; interrupts pause/resume correctly; state persists across restarts |
| **Verification** | Conversation flow tests CF-01 through CF-10 |
| **Evidence required** | Flow test results; state inspection; checkpoint verification |
| **Risks** | PENDING CQ-07 (node list); complex routing logic |
| **Rollback** | Nodes are modular; can be replaced individually |

### Phase 5 — API Layer

| Field | Detail |
|-------|--------|
| **Goal** | Frontend-backend contract operational |
| **Deliverables** | All endpoints from §12; request/response DTOs; error handling; auth middleware |
| **Dependencies** | P4 (agent endpoint wraps LangGraph) |
| **Entry criteria** | P4 verified |
| **Exit criteria** | All endpoints respond correctly; contract tests CT-01 through CT-05 pass |
| **Verification** | Contract tests; endpoint testing with Postman/httpie |
| **Evidence required** | Contract test results; API documentation |
| **Risks** | DTO shape changes from CQ resolutions |
| **Rollback** | API is a thin layer; endpoints can be versioned |

### Phase 6 — Frontend

| Field | Detail |
|-------|--------|
| **Goal** | UI fully functional end-to-end |
| **Deliverables** | All pages and components from §13; three-pane layout; chat flow; workspace panel; session sidebar |
| **Dependencies** | P5 (API endpoints) |
| **Entry criteria** | P5 verified |
| **Exit criteria** | User can complete full happy path through UI; all message types render correctly |
| **Verification** | Manual walkthrough; automated UI tests for critical paths |
| **Evidence required** | Screenshots/recordings of each flow; component test results |
| **Risks** | UX iteration; CQ-01 editability affects form design |
| **Rollback** | Frontend is independently deployable |

### Phase 7 — Validation & Review

| Field | Detail |
|-------|--------|
| **Goal** | All quality gates active in the UI flow |
| **Deliverables** | Topic validation wired; duplicate-job validation wired; Terraform validation running; review workspace with diff rendering |
| **Dependencies** | P6 (UI to show results), P3 (validation engine) |
| **Entry criteria** | P6 verified |
| **Exit criteria** | AC-3, AC-4, AC-5, AC-10 pass through the UI |
| **Verification** | Conversation flow tests CF-03, CF-04, CF-11 through UI |
| **Evidence required** | Test results; validation failure screenshots |
| **Risks** | PENDING CQ-13b (gate strictness); PENDING CQ-09 (diff engine scope) |
| **Rollback** | Validation can be disabled with feature flags |

### Phase 8 — PR Creation

| Field | Detail |
|-------|--------|
| **Goal** | Full PR flow operational |
| **Deliverables** | Branch creation; single-commit generation; PR creation; duplicate protection; draft freeze |
| **Dependencies** | P7 (validation must pass before PR) |
| **Entry criteria** | P7 verified |
| **Exit criteria** | AC-6, AC-7 pass; one commit, one PR confirmed |
| **Verification** | CF-01, CF-02, CF-05, CF-06, CF-12 through UI against a test repository |
| **Evidence required** | PR screenshots; commit history showing single commit; duplicate prevention log |
| **Risks** | PENDING CQ-15 (target repo); PENDING CQ-A4 (conflict resolution depth) |
| **Rollback** | PR creation is the final step; disabling it leaves the rest functional |

### Phase 9 — Recovery & Polish

| Field | Detail |
|-------|--------|
| **Goal** | Production-grade recovery and error handling |
| **Deliverables** | Session recovery; draft recovery; navigation recovery; undo; error states; loading states |
| **Dependencies** | P6 + P8 (recovery requires all features to be present) |
| **Entry criteria** | P8 verified |
| **Exit criteria** | RT-01 through RT-05 pass; AC-9 passes |
| **Verification** | Recovery tests; failure tests FT-01 through FT-06 |
| **Evidence required** | Recovery test results; failure scenario recordings |
| **Risks** | Edge cases in state restoration |
| **Rollback** | Recovery features are additive |

### Phase 10 — Testing & Certification

| Field | Detail |
|-------|--------|
| **Goal** | All quality evidence collected; all acceptance criteria verified |
| **Deliverables** | Complete test suite execution; AC matrix signed off; performance baseline |
| **Dependencies** | P9 (all features present) |
| **Entry criteria** | P9 verified |
| **Exit criteria** | All AC-* pass (except PENDING CQ items); all test categories executed; performance baselines established |
| **Verification** | Full test suite; AC matrix from §15.9 |
| **Evidence required** | Test reports; AC sign-off; performance numbers |
| **Risks** | PENDING CQs block some ACs |
| **Rollback** | N/A (certification phase) |



---

# SECTION 17 — Production Readiness

**References:** NFR-1, NFR-2, SEC-1 through SEC-4; TAS T12, T14

## 17.1 Security

| Area | Phase-1 requirement | Implementation | References |
|------|-------------------|----------------|------------|
| Authentication | GitHub OAuth | OAuth 2.0 Authorization Code flow | FR-H-1 |
| Token storage | Persist for recovery; never log | Secret reference abstraction; `SecretStr` | SEC-1, SEC-4 |
| Token encryption | **PENDING CQ-A7** | At-rest encryption if confirmed | SEC-4 |
| Session binding | Sessions bound to authenticated user | User ID FK on all session operations | §12.4 |
| Secret exposure | Secrets never in logs or UI | Log filtering; `SecretStr` serialization; audit masking | SEC-1 |
| Audit trail | Who/when/what for all mutations, PR creation, validation | Audit columns on all tables; audit log entries | SEC-2 |
| Authorization | Session-owner only (no RBAC in Phase-1) | Session ownership check on every request | §12.4 |
| RBAC | **OUT OF SCOPE** Phase-1 | Deferred | SCOPE-11 |
| Vault / rotation | **OUT OF SCOPE** Phase-1 | Deferred | SEC-3 |

## 17.2 Observability

| Layer | What to observe | Method |
|-------|----------------|--------|
| Application logs | All API requests/responses; all node executions; all validation results; all errors | Structured JSON logging |
| Business events | Session created/restored; draft mutation; PR created; validation pass/fail | Event log entries with correlation IDs |
| LLM interactions | Prompt sent; response received; token count; latency | Dedicated LLM log stream |
| GitHub API calls | Endpoint; response code; latency; retries | HTTP client instrumentation |

## 17.3 Monitoring

| Metric | What it measures | Alert threshold |
|--------|-----------------|-----------------|
| API response time (p50, p95, p99) | End-to-end response latency | **PENDING CQ-A8** |
| Error rate | Percentage of 5xx responses | > 1% sustained |
| Active sessions | Concurrent session count | **PENDING CQ-A8** |
| PR creation success rate | PRs created / PRs attempted | < 95% |
| Validation pass rate | Terraform validations passed / attempted | Informational (no alert) |
| GitHub API error rate | Failed GitHub calls / total calls | > 5% sustained |
| Database connection pool | Active / max connections | > 80% utilization |
| Redis memory | Used memory / max | > 80% |

## 17.4 Logging Standards

| Rule | Detail |
|------|--------|
| Format | Structured JSON; one line per event |
| Correlation | Every request gets a `correlation_id` propagated through all service calls |
| Levels | ERROR (failures), WARN (degradation), INFO (business events), DEBUG (development) |
| Sensitive data | Never log tokens, secrets, or full file contents; use `SecretStr` masking |
| Retention | **PENDING CQ-A8** |

## 17.5 Metrics

| Metric type | Examples |
|-------------|---------|
| Counter | `sessions_created_total`, `prs_created_total`, `validations_run_total` |
| Histogram | `api_response_seconds`, `pr_creation_seconds`, `validation_seconds` |
| Gauge | `active_sessions`, `draft_size_bytes` |

## 17.6 Tracing

| Rule | Detail |
|------|--------|
| Span per node | Each LangGraph node execution is a span |
| Span per service call | Each GitHub API call, DB query, and Redis operation is a child span |
| Context propagation | Trace ID propagated from frontend request through all backend layers |
| OTEL | **OUT OF SCOPE** Phase-1 (SEC-3); basic tracing with correlation IDs |

## 17.7 CI/CD

| Stage | What happens | Gate |
|-------|-------------|------|
| Build | Compile backend + frontend; lint; type check | Must pass |
| Unit test | All unit tests | Must pass (0 failures) |
| Integration test | DB + service integration tests | Must pass |
| Contract test | API contract verification | Must pass |
| Security scan | Dependency vulnerability scan | No critical/high CVEs |
| Build artifact | Docker images for backend + frontend | Must succeed |
| Deploy to dev | Automated deploy to dev environment | Build passes |
| Smoke test | Health check + basic flow | Must pass |
| Deploy to staging | Manual promotion | Dev smoke passes |
| Acceptance test | Full AC matrix | Must pass (excluding PENDING) |
| Deploy to prod | Manual promotion with approval | Staging acceptance passes |

## 17.8 Runbooks

| Runbook | Scenario | Key actions |
|---------|----------|-------------|
| RB-01 | PostgreSQL unavailable | Check connection; restart if needed; verify data integrity; sessions auto-recover on reconnect |
| RB-02 | Redis unavailable | Check connection; restart; LangGraph checkpoints may need rebuild from PostgreSQL |
| RB-03 | GitHub API outage | Monitor GitHub status; operations requiring GitHub will fail gracefully; users can resume when restored |
| RB-04 | High error rate | Check logs by correlation_id; identify failing component; scale or restart as needed |
| RB-05 | Orphaned PR branches | List draft branches older than N days; delete if no active session; never delete branches with open PRs |
| RB-06 | Session data cleanup | Archive completed sessions older than retention period; delete abandoned drafts |

## 17.9 Backup and Disaster Recovery

| Component | Backup strategy | RPO | RTO |
|-----------|----------------|-----|-----|
| PostgreSQL | Automated daily backups + WAL archiving | **PENDING CQ-A8** | **PENDING CQ-A8** |
| Redis | Persistence (AOF or RDB); can be rebuilt from PostgreSQL | Minutes | Minutes (restart) |
| Knowledge registries (JSON) | Version controlled in application repo | N/A (immutable per release) | Redeploy |
| GitHub (target repo) | GitHub's own redundancy | N/A | N/A |

---

# SECTION 18 — Developer Handbook

## 18.1 Coding Standards

| Area | Standard |
|------|----------|
| **Language** | Python 3.11+ (backend); TypeScript (frontend) |
| **Style** | Backend: PEP 8 + Black formatter; Frontend: ESLint + Prettier |
| **Type safety** | Backend: full type hints on all function signatures; Frontend: strict TypeScript (no `any`) |
| **OOP** | Classes for services, repositories, domain models. Pure functions for utilities. No god classes |
| **Design patterns** | Repository pattern (persistence); Strategy (validation rules); Factory (node creation); Observer (event logging) |
| **Error handling** | Custom exception hierarchy; never catch-and-swallow; always log and propagate or recover |
| **Imports** | Absolute imports only; no circular imports; enforce with CI linting |
| **Framework** | Pydantic for DTOs and validation (**PENDING CQ-A7** for v1 vs v2); SQLAlchemy for ORM; FastAPI for API |

## 18.2 Folder Ownership

| Folder | Owner team/person | May depend on | Must NOT depend on |
|--------|-------------------|---------------|-------------------|
| `api/` | API team | `services/`, `schemas/` | `repositories/`, `models/`, `database/` directly |
| `graph/nodes/` | LangGraph team | `services/` | `repositories/`, `database/` |
| `graph/state/` | LangGraph team | `core/` | `services/`, `repositories/` |
| `services/` | Service owners | `repositories/`, `knowledge/` | `api/`, `graph/` |
| `repositories/` | DB team | `models/`, `database/` | `services/`, `api/`, `graph/` |
| `models/` | DB team | `core/` | Everything else |
| `knowledge/` | Knowledge team | `core/` | `api/`, `graph/`, `repositories/` |
| `schemas/` | API team | `core/` | `models/`, `repositories/` |
| `core/` | Architecture lead | Nothing | Nothing (leaf dependency) |
| `frontend/` | Frontend team | API contracts only | Backend internals |

## 18.3 Import Rules

```
ALLOWED DEPENDENCY DIRECTION:

api/ ──────► services/ ──────► repositories/ ──────► models/
  │              │                   │                  │
  │              ▼                   ▼                  ▼
  │          knowledge/          database/            core/
  │              │                   │
  │              ▼                   ▼
  └──────────► core/ ◄──────────── core/

graph/nodes/ ──► services/
graph/state/ ──► core/

FORBIDDEN:
  repositories/ ──✗──► services/
  graph/ ──✗──► repositories/
  models/ ──✗──► anything except core/
  core/ ──✗──► anything
  services/ ──✗──► api/
  services/ ──✗──► graph/
```

**References:** TAS T2 (hexagonal architecture)

## 18.4 Naming Conventions

| Entity | Convention | Example |
|--------|-----------|---------|
| Python files | snake_case | `draft_repository.py` |
| Python classes | PascalCase | `DraftRepository` |
| Python functions | snake_case | `create_draft()` |
| Python constants | UPPER_SNAKE | `MAX_WORKERS` |
| DB tables | snake_case plural | `draft_glue_jobs` |
| DB columns | snake_case | `created_at` |
| API endpoints | kebab-case | `/agent/message` |
| React components | PascalCase | `ReviewWorkspace.tsx` |
| React hooks | camelCase with `use` prefix | `useDraftState()` |
| TypeScript interfaces | PascalCase with `I` prefix | `IAgentResponse` |
| CSS classes | kebab-case | `chat-message-container` |
| Environment variables | UPPER_SNAKE with prefix | `MIF_DATABASE_URL` |
| Registry files | snake_case JSON | `validation_rules.json` |
| Test files | `test_` prefix | `test_draft_repository.py` |

## 18.5 Review Checklist

Every PR must be reviewed against:

| Check | Verification |
|-------|-------------|
| ☐ CPRS alignment | Does this implement a CPRS requirement? Which ID? |
| ☐ No new behavior | Does this introduce behavior not in CPRS? (If yes, reject) |
| ☐ Import rules | Are dependency directions correct per §18.3? |
| ☐ Type safety | All functions typed; no `Any` without justification |
| ☐ Error handling | Errors logged and handled; no silent swallowing |
| ☐ Tests present | Unit tests for new logic; integration test if service boundary crossed |
| ☐ Secret safety | No tokens, secrets, or credentials in code/logs |
| ☐ Naming | Follows §18.4 conventions |
| ☐ No hardcoded values | Configuration in registries or env vars, not code |
| ☐ Optimistic locking | Concurrent-safe where needed (draft mutations) |
| ☐ Single responsibility | Each class/function does one thing (CON-LG-1 principle applied broadly) |

## 18.6 Definition of Done

A feature/phase is "done" when:

| Criterion | Detail | References |
|-----------|--------|------------|
| Code complete | All logic implemented per specification | §2-§14 |
| Tests pass | All relevant tests from §15 green | §15 |
| Review approved | PR reviewed per §18.5 checklist | §18.5 |
| Contract verified | API contracts match per §12 | CT-* tests |
| Evidence collected | Proof artifacts stored (screenshots, logs, test reports) | TAS T13 |
| No PENDING blockers | All CQs relevant to this feature are resolved | CPRS §15 |
| No regression | Existing tests still pass | CI |
| Documentation updated | Any spec changes reflected in this document | This doc |

---

# APPENDIX A — Consolidated Clarification Questions

All open CQs from CPRS v1.0 that affect implementation, with the sections they block.

## Blockers (block multiple implementation sections)

| CQ | Question | Blocks sections |
|----|----------|----------------|
| **CQ-01** | Which review fields are user-editable vs read-only? Per-field classification needed. | §8, §13, §14, §15 (AC-13) |
| **CQ-05** | Default run mode: Manual (no schedule) or Scheduled daily? 1 AM or 1 PM? Timezone? | §5 (derivation defaults), §8 (review form) |
| **CQ-14** | For `prod`, which repository folder/file is checked for topic validation? | §3 (TopicValidationNode), §5 (repo_patterns), §9 |
| **CQ-15** | Which repository does the agent navigate and raise PRs against? Is `_v3` the same repo or separate? | §3 (all GitHub-reading nodes), §6, §9, §10, §16 |

## High (block specific sections)

| CQ | Question | Blocks sections |
|----|----------|----------------|
| **CQ-02** | Topic: strictly read-only, or editable by asking the agent? | §3 (SchemaGrainNode), §8 |
| **CQ-03** | Enterprise Function: AGTR/FOOD/SPEC or AGTR/FOOD/CORP? | §5 (registry), §8 (dropdown) |
| **CQ-09** | Diff/ChangeSet engine: Phase-1 or deferred? | §7, §8, §13 |
| **CQ-13b** | Passing Terraform validation mandatory before PR? | §3 (ApprovalNode), §4 (state machine), §8, §15 (AC-14) |

## Medium (needed for completeness)

| CQ | Question | Blocks sections |
|----|----------|----------------|
| **CQ-04** | Maximum workers and true default | §5 (registry defaults) |
| **CQ-06** | Canonical draft lifecycle state names | §4, §11 (CHECK constraint) |
| **CQ-07** | Exact node list and count; uncertain nodes | §3 |
| **CQ-08** | Authoritative table list and count (8 vs 19) | §11 |
| **CQ-10** | Action cards, session export, statistics, cleanup: Phase-1? | §7, §13, §17 |
| **CQ-11** | Confirm KnowledgeState removal from graph state | §3 (state model) |
| **CQ-12** | Confirm workspace.defaults → derived_values rename | §3 (state model) |
| **CQ-A1** | New source concretes origin; LH DB name pattern | §5 (derivation), §10 |
| **CQ-A4** | Conflict resolution: full in Phase-1 or detection-only? | §3, §10, §15 |
| **CQ-A5** | Transformer/sink settings: shown or editable? | §8 |
| **CQ-A6** | Modify-existing-files guardrails | §6, §9 |
| **CQ-A7** | Pydantic version; token encryption | §17, §18 |
| **CQ-A8** | Deployment/infra targets; NFR numbers | §15 (performance), §17 |
| **CQ-A9** | Post-approval: full package or gated steps? | §16 (process) |
| **CQ-A2** | project_information cell1–cell8: needed or reference-only? | §5 (if it contains rules) |

---

**END OF IMPLEMENTATION DOCUMENTATION PACKAGE**

**Document statistics:**
- 18 sections covering all implementation domains
- 17+ LangGraph nodes fully specified
- 12 conversation flow test scenarios
- 10 implementation phases with entry/exit criteria
- 14 acceptance criteria traced to test cases
- Every specification traces to CPRS or TAS
- 25 Clarification Questions consolidated with section-level blocking impact

**This document is ready for engineering consumption once CPRS v1.0 is approved and blocker CQs are resolved.**
