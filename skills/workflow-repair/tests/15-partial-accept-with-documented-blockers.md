# 15 Partial Accept With Documented Blockers

## Purpose

Verify that `workflow-repair --auto` may still continue after partial
acceptance when some blocked or manual-decision items remain unresolved, but
those items are documented clearly enough that the resulting commit does not
misrepresent the repair as fully complete.

## Input

User input:

> Run `/workflow-repair --auto` in analysis-first mode. After the correction plan is shown, the user accepts only the safe adopted fixes. Those accepted fixes succeed, while some blocked/manual-decision items remain and are recorded clearly in the correction plan and repair log.

## Expected Mode

Partial execution with auto follow-through allowed after documented unresolved
items.

## Expected Key Behaviors

- preserve the blocked/manual-decision records in the correction plan and repair log
- allow auto follow-through only because the unresolved items are documented
  clearly enough to avoid misleading the commit
- keep the unresolved items visible instead of implying that the repair is
  fully complete

## Must Not

- must not silently drop blocked or manual-decision items from the record
- must not continue auto follow-through if the unresolved items would make the
  commit misleading
- must not restate the partial repair as a fully complete closure
