# 55 Stale Scan Report Is Rejected Before Repair

## Purpose

Verify that `workflow-repair` does not consume a `WORKFLOW_QUESTIONS.md`
produced for an older workflow version after the source workflow version has
already advanced.

## Input

User input:

> Run `/workflow-repair` on a validated report whose `workflow-version` is
> `0.1.2800`, while the current source workflow version and the temp-project
> install record both now resolve to `0.1.2801`.

## Expected Mode

Version-gated repair intake that stops before verification or source edits.

## Expected Key Behaviors

- compare report workflow version, temp-project install-record workflow version,
  and current source `WORKFLOW_VERSION`
- stop as `Blocked / Stale Scan Report`
- tell the user to re-embed and re-run `workflow-scan`
- do not create a correction plan
- do not modify workflow source files

## Must Not

- must not consume the stale report "carefully anyway"
- must not downgrade this case to a warning
