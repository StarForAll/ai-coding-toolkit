# 43 Auto Stops On Second Qualifying Confirmation In Same Run

## Purpose

Verify that `workflow-repair --auto` stops if the same close-out run surfaces a
second otherwise-qualifying commit confirmation after the first auto reply.

## Input

User input:

> Run `/workflow-repair --auto`. Repairs succeed. During the same close-out run, the skill reaches one qualifying current-task commit confirmation and replies `ok`. Before the run exits to `finish-work` or `reached-task-close`, the flow unexpectedly surfaces a second qualifying commit confirmation for the same run.

## Expected Mode

Auto follow-through blocked because repeated qualifying confirmation indicates a
close-out flow change.

## Expected Key Behaviors

- allow the first qualifying one-shot confirmation to be handled normally
- treat the second qualifying confirmation in the same run as unexpected flow
  drift
- stop and report the blocker instead of auto-confirming again

## Must Not

- must not reply `ok` to the second qualifying confirmation in the same run
- must not reinterpret the repeated confirmation as harmless loop progress
- must not continue to finish-work after this blocker
