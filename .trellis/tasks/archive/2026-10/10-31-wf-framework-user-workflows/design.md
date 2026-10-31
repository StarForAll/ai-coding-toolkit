# Design: User-Defined Workflows and Session-Scoped Execution

## Decision Summary

Add a bounded, project-owned workflow-definition and execution capability to the independent wf framework. Keep the existing single-user task lifecycle and one shared worktree. A session binds to one task or one workflow run and cannot switch; the project has at most one writer session at a time. Other sessions may inspect and prepare work, then acquire the writer after an explicit release or handoff.

This design is declarative and ordered. It does not add a general workflow programming language, plugin system, worktree parallelism, or scenario-specific framework implementations.

## Goals and Boundaries

- Let a user describe a workflow once in project data and run it through the framework's generic controller without changing framework code, Trellis assets, host-managed files, or adding a workflow-specific script.
- Support both steps inside one task and ordered workflows that create ordinary tasks.
- Keep normal tasks usable without selecting a workflow.
- Preserve session binding, task/flow progress, and approvals across compaction and later-session handoff using durable records.
- Keep workflow control, task status, and shared project-file validity as distinct concerns.
- Preserve the declared limits: one project worktree, serial project writes, no team scheduler, no hook-based real-time interception, and no claim of adversarial enforcement.

## Ownership Model

### Workflow definition

- Store user definitions as project data under `.wf/user-workflows/<workflow-id>.md`; they are Git-tracked and are not part of the framework release manifest or upgrade replacement set.
- A definition describes purpose/applicability, inputs, ordered steps, expected artifacts, completion conditions, required local checks, and explicit human decision points.
- The accepted first version is an ordered declarative format. A bounded parser/validator reports malformed or unsupported constructs before a run is approved.
- Framework upgrades preserve definitions. A format migration is an explicit, previewed project-data change and never silently rewrites user content.

### Workflow run

- Starting a definition creates a distinct run ID and pins the exact definition revision/hash plus supplied inputs. Editing the definition later does not mutate an existing run.
- Store durable run orchestration data under `.wf/workflow-runs/<run-id>.json`: definition identity, input snapshot/reference, current step, step outcomes, artifact references, and associated task IDs.
- The run record is not a second task lifecycle. It records only orchestration progress. Each work task's status, approval, touch paths, check result, and archive state remain authoritative in that task's single record.
- A task belongs to at most one active run. Reuse across runs is a read-only explicit reference to prior output; another run cannot advance, approve, or archive the referenced task.
- A single-task workflow uses the same run record and associates one ordinary task. A multi-task workflow advances through ordinary tasks using the existing dependency DAG. The run cursor does not override task dependencies or status.
- If orchestration can be represented entirely by a task's existing artifacts without a second competing fact, the mechanism design may reduce fields, but it must retain a stable run identity and durable cursor.

### Session binding

- A session binding is runtime routing state at `.wf/.runtime/sessions/<session-key>.json`; it contains exactly one bound object: an ordinary task ID or workflow run ID.
- The binding is immutable for that session. Completion, pause, or failure does not permit choosing another object in that same session. A new session is required for another task/run.
- Context compaction keeps the same session key and binding. A new conversation gets its own key and can explicitly start another object or request handoff of an existing object.
- Session identity resolution uses only verified host identifiers or an explicit wf-issued session token carried by the session. No guessed environment names and no project-global current-task fallback. If identity cannot be resolved, session-bound execution stops with a concrete recovery instruction.
- Runtime binding loss does not erase task/run progress. The user may explicitly reattach from a new session after the old writer is released; do not infer ownership by counting runtime files.

### Project writer ownership

- The shared worktree has one project-wide writer lease in `.wf/.runtime/writer.json`, containing owner session key, bound object, fencing generation, and last verified checkpoint.
- Acquiring/releasing/transferring ownership is an atomic generic framework operation. A writer may mutate task/workflow data or business files only while its session key and generation match the lease.
- Other sessions may inspect project files and prepare a proposal outside the project tree. They cannot create/advance persisted tasks, edit workflow definitions, change specs, or modify business files while another session owns the writer.
- Release occurs only after the owner's task/run is paused or completed and its worktree changes are committed or explicitly handled under the existing workspace-boundary rule. A handoff names the receiving session and object, validates the workspace, increments the fencing generation, then transfers ownership.
- A new session taking over an old run uses the same explicit handoff path. The former session remains bound to its original object but loses write authority; later framework-mediated actions from it fail on the stale generation.
- No time-based lease expiry or automatic stealing. If owner liveness or a partially completed write is uncertain, fail closed, inspect Git/task/run records, and require explicit human recovery.
- This lease is a workflow-discipline and entry/checkpoint gate, not a real-time tool interceptor. Direct out-of-band edits cannot be mechanically prevented without host hooks; they are treated as external changes and checked at the next gate. No stronger guarantee is claimed.

## Execution Contract

1. `wf-start` identifies the current session. If already bound, it resumes only that object; selecting a different object is rejected.
2. An unbound session may select a normal task or create/select a workflow run. It must pass the existing planning and approval gates.
3. Before the first project mutation, the session acquires the sole writer lease. If another session owns it, the command reports owner/object/checkpoint and offers read-only status or a handoff request; it does not mutate.
4. The workflow controller loads only the pinned definition revision and the specs relevant to the current task/step. It reports current step, unmet completion conditions, and the next action.
5. Advancing an ordinary task or workflow run updates the task/run records atomically through generic framework mechanisms. Human decisions remain explicit. A workflow definition cannot weaken task scope, authorization, Check, normal Finish, repair, or exception-exit rules.
6. At pause/handoff, validate the workspace boundary, persist decisions/progress/artifact references, invalidate or finish applicable checks, and release/transfer writer ownership only after the worktree is clean or the user has explicitly handled its changes.
7. On resume after compaction/new conversation, reread the durable task/run, definition snapshot, Git state, current spec hashes, and writer generation. Reuse still-valid approvals; invalidate affected checks per existing content-fingerprint rules.

## Failure and Recovery

- Missing/unsupported workflow definition: block only that run; normal tasks remain available.
- Definition edited after run creation: continue from the pinned revision; a deliberate migration creates a reviewed new run/revision rather than silently changing cursor semantics.
- Missing session identity: stop before binding or writing; ask for a supported identity path/session token. Never use a shared current pointer.
- Writer held by another session: read-only wait path; no task or source mutation.
- Stale/ambiguous writer ownership or interrupted handoff: preserve records, read back Git/task/run state, and require explicit human recovery. No TTL-based takeover and no blind retry.
- Shared file/spec changed by another task/session: preserve the external change, invalidate affected check results, and require the bound task/run to replan or recheck as existing rules dictate.
- Direct tool write bypasses the lease: detect at the next checkpoint where possible, report the conflict, preserve all edits, and do not auto-merge, stash, or discard.

## Consequences

- The framework gains one generic workflow-definition parser/validator, a run cursor, per-session binding, and project-wide writer ownership. These are framework mechanisms shared by every workflow, not per-workflow integrations.
- Multiple conversations may remain open and bound to different tasks/runs, while project mutation stays serial in one worktree.
- A waiting session cannot persist a new task/run while another writer holds the worktree. This is the cost of the user's selected serial-write boundary.
- Without hooks, isolation is reliable for compliant framework-mediated execution but cannot prevent a user or agent from issuing direct writes outside the workflow.

## Verification Boundary

Design-level validation can prove index/reference coverage and state the acceptance scenarios. It cannot prove runtime locking, host identity availability, session fencing, or behavior after actual compaction. Those remain implementation acceptance work.
