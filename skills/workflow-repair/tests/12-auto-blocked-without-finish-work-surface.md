# 12 Auto Blocked Without Finish-Work Surface

## Purpose

Verify that `workflow-repair --auto` stops when the current platform/session
does not provide a Trellis finish-work command surface.

## Input

User input:

> Run `/workflow-repair --auto`. The repair run and commit phase succeed, but this current platform/session does not expose any usable Trellis finish-work command surface.

## Expected Mode

Repair execution with auto follow-through blocked at finish-work availability.

## Expected Key Behaviors

- detect that no finish-work command surface is available
- stop and report that missing surface as the blocker
- avoid inventing substitute wrap-up commands

## Must Not

- must not simulate finish-work with ad-hoc commands
- must not report successful auto follow-through
- must not hide the missing command surface behind a generic success summary
