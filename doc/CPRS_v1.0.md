# Canonical Product Requirements Specification (CPRS)
## MIF Infrastructure Copilot — Enterprise AI Agent Platform

**Version:** 1.0 — READY FOR APPROVAL
**Document type:** Product Requirements Specification (product behavior only)
**Companion document:** Technical Architecture Specification (TAS) — holds all implementation detail; non-binding until product spec is approved.
**Inputs consolidated:** `imp_cell` (primary), `mif-glue-job-creation-terraform-script-process.md` (workflow).
**On approval:** this CPRS becomes the single source of truth. The two input documents are retired as direct inputs.

**Status tags**
- **[C]** CANONICAL — consolidated and internally consistent (or resolved on explicit evidence).
- **[U]** UNRESOLVED — sources conflict with no settling evidence; an open Clarification Question (CQ) is attached. Not guessed.
- **[O]** OUT OF SCOPE for Phase-1 (explicitly deferred by the source).

**ID scheme:** `<TYPE>-<GROUP>-<n>` — FR functional, BR business rule, UX experience, CON constraint, SEC security, NFR non-functional, SCOPE.

---

## 0. Product Identity

- **PI-1 [C]** Product: *MIF Infrastructure Copilot*, an enterprise AI Agent Platform.
- **PI-2 [C]** Purpose: let engineers create and modify Terraform infrastructure entries (flagship: AWS Glue Kafka→Iceberg ingestion jobs) in a GitHub repository through a ChatGPT-style conversational agent, with minimum questions and maximum automation.
- **PI-3 [C]** Users: engineers who create/modify MIF Glue ingestion jobs, authenticated via GitHub; pull requests are raised under the user's own GitHub identity.
- **PI-4 [C]** Scale intent: production-grade for 10,000+ users; explicitly not a POC.
- **PI-5 [C]** Product character: a guided, knowledge-driven automation agent — not a free-form chatbot and not a rigid step-by-step form wizard.

---

## 1. Scope

**In scope (Phase-1)**
- **SCOPE-1 [C]** Create a Glue Job from a Kafka source — full capability.
- **SCOPE-2 [C]** Modify existing repository files via conversational navigation.
- **SCOPE-3 [C]** Multiple operations in one session (several jobs and/or file edits, across multiple source systems) delivered as one pull request.
- **SCOPE-4 [C]** GitHub sign-in, saved sessions, session history, and recovery of in-progress work.
- **SCOPE-5 [C]** Repository-based validation and a final Terraform validation before the pull request.
- **SCOPE-6 [C]** A working area where changes accumulate and can be undone before the pull request.
- **SCOPE-7 [C]** A review step with a single confirmation before the pull request is raised.

**Placeholder only (Phase-1: offered but not functional)**
- **SCOPE-8 [C]** JDBC, Flat File, and API source types are presented as options but respond "need to implement."

**Out of scope (Phase-1)**
- **SCOPE-9 [O]** Validating Kafka brokers or the Schema Registry.
- **SCOPE-10 [O]** Merging the PR, auto-applying, or deploying the generated Terraform.
- **SCOPE-11 [O]** Role-based access control, secret vaulting/rotation, multi-tenant features.
- **SCOPE-12 [U]** A full visual change/diff comparison engine — Phase-1 vs deferred is unsettled. See **CQ-09**.

**Non-goals**
- **SCOPE-13 [C]** Direct merge, auto-apply, production deployment, and a UX wireframe deliverable are explicitly non-goals.

---

## 2. Workflow A — Create Glue Job (Kafka)

### 2.1 What the user is asked
- **FR-A-1 [C]** The user is asked for exactly three things to begin: **environment**, **source system**, **schema grain**. Nothing else is requested up front.
- **FR-A-2 [C]** Environment is chosen first (`dev` / `prod`). No work can begin before environment is selected, and every artifact produced in the session belongs to that environment.
- **FR-A-3 [C]** Source system is chosen from a list that reflects the current repository; the user may instead enter a brand-new source system.
- **FR-A-4 [C]** Schema grain is typed in freely (not a list), e.g., `multi-1`.

### 2.2 Topic and validation (user-visible behavior)
- **FR-A-5 [C]** The agent forms the topic as `{env}.{source}.{grain}.raw` (e.g., `dev.saptcc.multi-1.raw`) and shows it.
- **BR-A-1 [C]** The topic is produced by the agent from the three inputs; the user does not type the topic.
- **BR-A-2 [U]** Whether the topic can be changed by asking the agent, or only by changing the three inputs, is unsettled. See **CQ-02**.
- **FR-A-6 [C]** The agent confirms the topic exists in the repository before proceeding:
  - **BR-A-3 [C]** Topic present → continue.
  - **BR-A-4 [C]** Topic file present but this grain absent → stop with "Please create the topic first."
  - **BR-A-5 [C]** Topic file absent → stop with "Source system not configured."
  - **BR-A-6 [C]** On a stop, the agent shows no schema list, no suggestions, and no extra controls.
- **BR-A-7 [U]** Which repository location is checked when environment is `prod` is not stated (only the dev location is named). See **CQ-14**.
- **FR-A-7 [C]** Before creating the job, the agent confirms the same job does not already exist for that source; if it does, it stops with "Glue Job already exists."
- **BR-A-8 [C]** Repository checks (topic, then duplicate job) always happen before the agent derives values or creates a draft.

### 2.3 Derivation and presentation
- **FR-A-8 [C]** After checks pass, the agent automatically determines all remaining configuration and presents it to the user for review.
- **FR-A-9 [C]** Values determined for the user: Kafka Secret Name, Glue Job Name, IAM Role, Worker Type, Glue Version, Number of Workers, Scheduling Mode, Job Type, Job Version, Lakehouse DB, and S3 paths.
- **BR-A-9 [C]** Source of truth for these values:
  - Existing source system → the repository is authoritative.
  - New source system → the documented MIF rules are authoritative until the PR merges, after which the repository becomes authoritative.
- **BR-A-10 [C]** If the repository and the knowledge base disagree, the repository wins.

### 2.4 What gets written
- **BR-A-11 [C]** Job name follows `kafka-to-iceberg-batch-<source>-<grain>` and must be unique for that source.
- **BR-A-12 [C]** Existing source system → only the source's `locals.tf` is modified; its `glue.tf` is never touched.
- **BR-A-13 [C]** New source system → both `locals.tf` and `glue.tf` are created for that source.
- **BR-A-14 [C]** "Source already exists" means the source's folder is present in the repository. *(Resolved on explicit evidence: the source repeatedly defines existence by repo folder/file presence and states "GitHub wins.")*

### 2.5 Source-type choice
- **FR-A-10 [C]** When creating a job, the agent asks the source type: Kafka / JDBC / Flat File / API.
- **FR-A-11 [C]** Only Kafka is functional; the others reply "need to implement."
- **BR-A-15 [C]** "Kafka" here means only that the derived topic is verified against the repository; the product never connects to a Kafka broker.

---

## 3. Workflow B — Modify Existing Files

- **FR-B-1 [C]** The user chooses "Modify Existing Files" and the agent guides them through the repository conversationally.
- **FR-B-2 [C]** The agent shows the contents of a named folder, asks whether to go deeper, and continues until the user reaches the file they want, then lets them edit it by describing the change.
- **FR-B-3 [C]** After an edit, the agent asks whether to change anything else; when the user is done, it proceeds toward validation and the pull request (only after the user approves).
- **BR-B-1 [C]** In this mode the agent changes only what the user explicitly asks for; it does not make changes the user did not request (for example, it will edit `glue.tf` only on request).
- **FR-B-4 [U]** The limits on what may be edited (which files/folders, and any checks beyond Terraform validation) are not defined. See **CQ-A6**.

---

## 4. Multi-Operation Session and the Pull Request

- **FR-S-1 [C]** A single session may contain several Glue Jobs and several file edits, spanning multiple source systems.
- **FR-S-2 [C]** The agent never asks "how many jobs?" After each completed operation it asks only "What would you like to do next?"
- **FR-S-3 [C]** The "What would you like to do next?" options are:
  - Before any change exists: **Create Glue Job**, **Modify Existing Files**.
  - After at least one change: **Create Another Glue Job**, **Modify Existing Files**, **Review Draft Workspace**, **Discard Last Change**, **Create Pull Request**.
  - "Create Another Glue Job" is hidden if the user has only modified files and created no job.
- **FR-S-4 [C]** The agent never asks "do you want to continue?" and never repeats a confirmation it already has. There is exactly one confirmation in the entire flow: immediately before creating the pull request.
- **BR-S-1 [C]** Everything done in a session becomes one pull request containing one commit — never multiple commits.
- **BR-S-2 [C]** Even after conflict resolution, the result remains one commit in one pull request.

---

## 5. Working Area, Undo, and Review (user-visible)

- **FR-W-1 [C]** Changes accumulate in a working area that is the basis for the pull request; the PR reflects exactly what is in that working area at confirmation time.
- **FR-W-2 [C]** A session has one active working set of changes at a time.
- **FR-W-3 [C]** The user can undo via "Discard Last Change." The user never sees internal version numbers or snapshot identifiers — only this single undo control.
- **FR-W-4 [C]** Until the pull request is created, the user may change values the agent generated simply by telling the agent (e.g., "change worker count to 20"); no navigation is needed and the working area updates immediately. *(Scope of which fields this applies to is governed by CQ-01; see §6.)*
- **FR-W-5 [C]** A review step presents the final set of changes; the pull request is generated only from this reviewed set.
- **FR-W-6 [C]** Once the user confirms "Create Pull Request," the working area is frozen — no further edits, additions, or undo — until the PR is created or the attempt fails.
- **FR-W-7 [C]** Repeated "Create Pull Request" clicks result in only one pull request.
- **FR-W-8 [C]** The review shows changes in a familiar diff style: additions in green, deletions in red, modifications shown as both; a "Files Changed: N" summary with each file expandable.

---

## 6. Field Visibility and Editability in Review

- **UX-R-1 [C]** The review presents: Topic Name, Kafka Secret Name, Glue Job Name, IAM Role, Worker Type, Glue Version, Workers, Scheduling Mode, Job Type, Job Version, Enterprise Function, Subgroup, Lakehouse DB, S3 Paths, Commit Message, PR Title, PR Description.
- **UX-R-2 [C]** Enterprise Function and Subgroup are shown as dropdowns that also allow entering a new value.
- **UX-R-3 [C]** The user never sees internal mechanics: validation rules, internal Terraform values, Kafka bootstrap servers, backend logic, internal metadata, or Schema Registry values.
- **UX-R-4 [C]** Validation **outcomes** are shown to the user (pass/fail and the reason on failure); validation **rules** are not. *(Resolved on explicit evidence: the source criticizes hidden validation and requires findings to be visible in review, while separately requiring the rules themselves to stay backend-only.)*
- **UX-R-5 [U]** Exactly which presented fields are user-editable versus read-only is the central open decision. The latest consolidated guidance indicates user-provided and dropdown fields plus commit/PR text are editable, while agent-derived values are not editable; earlier passages conflict. See **CQ-01**.

---

## 7. Topic, Schedule, and Allowed Values (business rules)

- **BR-V-1 [C]** Topic format: `{env}.{source}.{grain}.raw`.
- **BR-V-2 [C]** Worker Type allowed: `G.1X`, `G.2X`, `G.4X`; default `G.1X`.
- **BR-V-3 [U]** Number of workers — stated maximum 10 / default 1, but examples use other numbers. See **CQ-04**.
- **BR-V-4 [U]** Default run mode — documented as Manual (no schedule) in the workflow source, but the product narrative defaults to a daily schedule and even pre-fills a daily-1-AM time; the hour (AM vs PM) also conflicts. See **CQ-05**.
- **BR-V-5 [C]** The agent generates the schedule from a plain-English answer ("run every day at 1 AM"); the schedule field is pre-filled and editable.
- **BR-V-6 [U]** Enterprise Function allowed set — `AGTR / FOOD / SPEC` vs `AGTR / FOOD / CORP`; default `AGTR`. See **CQ-03**.
- **BR-V-7 [C]** Subgroup allowed: `APAC`, `NA`, `LATAM`; default `APAC`.
- **BR-V-8 [C]** Sink/target type: `iceberg`.
- **BR-V-9 [U]** Lakehouse DB naming — two conflicting patterns appear in the source. See **CQ-A1**.
- **BR-V-10 [C]** Transformer and sink pre-processing settings are applied with standard defaults.
- **BR-V-11 [U]** Whether those transformer/sink settings are ever shown or editable in Phase-1 is unconfirmed. See **CQ-A5**.

---

## 8. Conflict Resolution (user-visible)

- **FR-C-1 [C]** If someone else's change merges while the user is working, a conflict may surface at pull-request time.
- **FR-C-2 [C]** The agent first tries to reconcile automatically.
- **FR-C-3 [C]** If a conflict remains, the user is shown a side-by-side comparison (incoming vs current) with choices: Accept Incoming, Accept Current, Accept Both, or edit manually.
- **FR-C-4 [C]** The user resolves conflicts in the same session by instructing the agent; the pull request still ends up with a single commit.
- **FR-C-5 [U]** Whether full conflict resolution ships in Phase-1 or only detection ships now is unsettled. See **CQ-A4**.

---

## 9. Sign-in, History, and Recovery (user-visible)

- **FR-H-1 [C]** The user signs in with GitHub once; the session is saved and restored later; pull requests are raised as that GitHub user.
- **FR-H-2 [C]** Session history is presented ChatGPT-style, grouped Today / Yesterday / Previous, per user.
- **FR-H-3 [C]** Reopening a past session restores the conversation, the working area, and the user's place in repository navigation.
- **FR-H-4 [C]** If the browser refreshes or the connection drops, in-progress work resumes where it left off.
- **FR-H-5 [C]** "Start Over" clears the current work and begins a fresh conversation.

---

## 10. Conversational Experience (constraints)

- **UX-E-1 [C]** React + Vite, ChatGPT-style, dynamic conversation.
- **UX-E-2 [C]** Three areas on screen: sessions list, chat, and working area.
- **UX-E-3 [C]** Screens: Login, Chat, Working area, PR Review, History.
- **UX-E-4 [C]** No confirmations during the workflow; only one at the end ("Raise Pull Request?"). Earlier steps are grouped and not re-shown once seen.
- **UX-E-5 [C]** The agent asks the minimum number of questions and infers sensible defaults.
- **UX-E-6 [C]** Any question outside the supported workflow is still handled gracefully by the agent rather than failing.
- **UX-E-7 [U]** Whether richer review/admin extras (action buttons inside messages, session export, change statistics, cleanup of old sessions) are in Phase-1 is unsettled. See **CQ-10**.

---

## 11. Validation and Quality Gates (behavioral)

- **FR-Q-1 [C]** Repository checks come first: topic existence, then duplicate-job, before any derivation or draft.
- **FR-Q-2 [C]** A Terraform validation runs once, immediately before the pull request.
- **FR-Q-3 [C]** If validation fails, the agent tells the user what failed and offers to change it; on change it re-validates; if the user declines to change, behavior at the gate is governed by **CQ-13b**.
- **FR-Q-4 [U]** Whether a passing Terraform validation is mandatory before the PR can be created is implied but should be confirmed. See **CQ-13b**.
- **FR-Q-5 [C]** Validation outcomes are recorded so repeated attempts and their results are traceable to the user.

---

## 12. Security (user-relevant)

- **SEC-1 [C]** Secrets are referenced indirectly and never shown in logs or to the user.
- **SEC-2 [C]** The system keeps an audit trail of who did what and when (changes, PR creation, validation failures).
- **SEC-3 [O]** Vaulting, key rotation, role-based access, and full observability tooling are later-phase items.
- **SEC-4 [U]** Whether the stored GitHub token is encrypted at rest in Phase-1 needs confirmation (it must persist to enable recovery). See **CQ-A7/CQ-A8**.

---

## 13. Non-Functional Expectations

- **NFR-1 [C]** The product must be maintainable, scalable, recoverable, observable, secure, and durable for long-term operation.
- **NFR-2 [U]** Concrete targets (response times, concurrent sessions, availability, recovery objectives, rate limits, alert thresholds) are acknowledged as needed but not yet set. See **CQ-A8**.

---

## 14. Acceptance Criteria (Phase-1)

Each is phrased so it can be tested against observable behavior.

- **AC-1 [C]** Given a valid env/source/grain for an existing source, when the user proceeds, then the agent derives all values, shows them, and creates a draft modifying only that source's `locals.tf`.
- **AC-2 [C]** Given a brand-new source, when the user proceeds, then the draft creates both `locals.tf` and `glue.tf` for that source.
- **AC-3 [C]** Given a topic whose grain is absent from the repository, when validation runs, then the flow stops with "Please create the topic first" and offers no extra UI.
- **AC-4 [C]** Given a source folder absent from the repository, when validation runs, then the flow stops with "Source system not configured."
- **AC-5 [C]** Given a job name that already exists for the source, when the user tries to create it, then the flow stops with "Glue Job already exists."
- **AC-6 [C]** Given several jobs and file edits in one session, when the user creates the PR, then exactly one PR with one commit is produced.
- **AC-7 [C]** Given any number of repeated "Create Pull Request" actions, then only one PR is created and the working area is frozen during creation.
- **AC-8 [C]** Given a completed operation, when the agent asks what's next, then "Create Another Glue Job" appears only if at least one job was created.
- **AC-9 [C]** Given an interrupted session (refresh/disconnect), when the user returns, then the conversation, working area, and navigation position are restored.
- **AC-10 [C]** Given the review step, when validation fails, then the failure reason is visible to the user while internal rules remain hidden.
- **AC-11 [C]** Given the start of any workflow, when no environment is selected, then no other step is permitted.
- **AC-12 [C]** Given JDBC/Flat File/API is chosen, then the agent responds "need to implement" and does not proceed.
- **AC-13 [U]** Editability acceptance (which fields the user can change in review) is pending **CQ-01**.
- **AC-14 [U]** PR-gate acceptance (passing Terraform validation required) is pending **CQ-13b**.

---

## 15. Clarification Questions outstanding at v1.0

These must be answered for the spec to be fully frozen. Blockers change product behavior materially.

**Blockers**
- **CQ-01** Which review fields are user-editable vs read-only? (Latest guidance: user/dropdown + commit/PR text editable, agent-derived not editable — confirm per field.)
- **CQ-05** Default run mode: Manual (no schedule) or Scheduled daily? If scheduled, what time and zone (1 AM vs 1 PM)?
- **CQ-14** For `prod`, which repository location is checked for topic validation?
- **CQ-15** Which repository does the agent navigate and raise PRs against, and is the `_v3` repository the same as the target or a separate one?

**High**
- **CQ-02** Topic: strictly read-only (change the three inputs to change it) or also editable by asking the agent?
- **CQ-03** Enterprise Function set: `AGTR/FOOD/SPEC` or `AGTR/FOOD/CORP`?
- **CQ-09** Visual diff/change-comparison engine: Phase-1 or deferred?
- **CQ-13b** Is a passing Terraform validation mandatory before the PR can be created?

**Medium / detail**
- **CQ-04** Maximum number of workers and the true default.
- **CQ-10** Action buttons in messages, session export, change statistics, cleanup policies — Phase-1 or later?
- **CQ-A1** For new sources, where do environment-specific concrete values come from, and which Lakehouse-DB naming pattern is correct?
- **CQ-A4** Conflict resolution: full in Phase-1 or detection-only now?
- **CQ-A5** Are transformer/sink settings ever shown or editable in Phase-1?
- **CQ-A6** Modify-Existing-Files guardrails (editable scope, extra checks).
- **CQ-A7** Pydantic/version pinning for Phase-1 (relevant only if it affects validation behavior the user sees).
- **CQ-A8** Deployment/infrastructure and NFR targets: decide now or defer.

**Meta (decides what happens after approval)**
- **CQ-A9** After CPRS approval: produce the full architecture package at once, or resume the gated step-by-step freeze?

**Reference-only flag**
- **CQ-A2** A `project_information/` folder (cell1–cell8) is referenced but was not provided. Confirm it is reference-only (ignore) or share it if it carries requirements.

---

## Appendix — Evidence notes for resolved conflicts

- **UX-R-4 / validation visibility (was CQ-13):** resolved because the source explicitly criticizes hidden validation ("validation UI me dikhayi hi nahi ja rahi… Review screen me validation findings visible honi chahiye") while separately requiring validation *rules* to stay backend-only ("Validation Rules… user ki UI me nahi dikhana"). The two are about different objects (outcomes vs rules), so both hold.
- **BR-A-14 / "source exists" (was CQ-16):** resolved because existence is consistently defined by repository folder/file presence, reinforced by the "GitHub wins" rule.
- **CQ-01 (partial):** the final consolidated section lists the user-input and dropdown fields plus commit/PR text as the editable surface and states "Derived values must NOT be editable"; encoded as the working position but left open per-field because earlier sections contradict it.
