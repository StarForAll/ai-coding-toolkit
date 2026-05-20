# 17 Commit Succeeds But Finish-Work Fails

## Purpose

Verify that `workflow-repair --auto` records the dangerous partial-success
boundary where commit succeeds but finish-work later fails.

## Input

User input:

> Run `/workflow-repair --auto`. Repairs succeed and the current repair task commits successfully, but invoking the available finish-work command surface then fails because wrap-up conditions are not satisfied.

## Expected Mode

Auto follow-through blocked after commit but before task wrap-up completes.

## Expected Key Behaviors

- allow commit to complete
- stop auto follow-through when finish-work fails
- record in the blocker reason that commit already succeeded before finish-work failed

## Must Not

- must not report `reached-finish-work`
- must not hide the post-commit failure behind a generic blocker message
- must not invent a second close-out path after finish-work fails
