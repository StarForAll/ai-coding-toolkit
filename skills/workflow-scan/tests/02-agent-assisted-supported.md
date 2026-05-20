# 02 Agent-Assisted Supported

## Purpose

Verify that `workflow-scan` may use bounded helper agents only when `--agent`
is explicitly requested and the current session is truly agent-capable.

## Input

User input:

> Run `/workflow-scan --agent` against the temp project. This session can invoke helper agents, pass explicit read-only ownership boundaries, and receive distinct handoffs back from each helper.

## Expected Mode

Agent-assisted scan with the current CLI session kept as coordinator.

## Expected Key Behaviors

- confirm that the runtime really supports helper invocation, bounded ownership,
  and distinct handoff return paths
- split only non-overlapping evidence-gathering slices across a small number of
  helper agents
- require helper handoffs to follow the reusable handoff template
- keep overwrite prompts, conflict resolution, final finding judgment, report
  writing, and read-back validation in the coordinator session
- emit the same `WORKFLOW_QUESTIONS.md` contract used by inline scans

## Must Not

- must not let helper agents write `WORKFLOW_QUESTIONS.md`
- must not let helper agents finalize severity or deduplicate findings
- must not widen helper fan-out just because agent execution is available
- must not change the shared scan/repair report schema when `--agent` is used
