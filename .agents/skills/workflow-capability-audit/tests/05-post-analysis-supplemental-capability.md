# 05 Post-analysis Supplemental Capability

## Purpose

Verify that an omitted capability pointed out by the user after one discovery pass is validated within the same audit round, using the same A/B fixtures and the same `capability-report.md`.

## Input

User input:

> You missed one Trellis capability in your analysis. Please verify whether it is real and, if so, add it.

## Expected Mode

In-round supplemental validation.

## Expected Key Behaviors

- reuse existing A/B fixtures
- reuse the same `capability-report.md`
- treat the point as a hypothesis
- if confirmed:
  - insert it into the logical matrix position
  - set `Discovery Source = supplemental-confirmed`
  - keep existing capability IDs stable
- if not confirmed:
  - record it under `Rejected / Unconfirmed Supplemental Points`

## Must Not

- must not restart a new full audit
- must not renumber existing capability IDs
- must not append every confirmed supplemental capability blindly to the end
