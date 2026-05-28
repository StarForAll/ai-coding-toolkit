# 64 Closure Runtime-Patch Requires Behavior Verification

## Purpose

Verify that `workflow-repair` does not declare closure clean for a
runtime-patch repair family when closure only proves marker/text presence but
does not execute at least one behavior-level assertion against the installed
carrier path.

## Input

User input:

> Run `/workflow-repair`. The confirmed repair changes an installed runtime
> carrier's blocked/deny/route-stop behavior. Closure runs only static string
> checks on the patched carrier and does not execute any behavior-level
> assertion for that carrier path.

## Expected Mode

Bounded closure verification with runtime-patch behavior gate.

## Expected Key Behaviors

- refuse to treat the runtime-patch closure round as `clean`
- record the missing behavior-level verification as a closure problem or
  blocker rather than as a mere note
- stop close-out / version bump until at least one installed-carrier behavior
  assertion is included for that repair family

## Must Not

- must not declare closure converged solely because required marker/text
  fragments exist
- must not treat runtime stop/deny semantics as equivalent to source-only text
  presence
