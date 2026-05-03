# 18 Confirmed Issue Minimum Schema

## Purpose

Verify that every confirmed issue uses the required minimum schema.

## Input

User input:

> Run a structured audit of `docs/workflows/新项目开发工作流/` and report any confirmed workflow issue in the normal audit format.

## Expected Mode

Any audit mode that reaches a confirmed issue.

## Expected Key Behaviors

- each confirmed issue includes:
  - `priority`
  - `conclusion`
  - `evidence source`
  - `validation action`
  - `impact scope`
  - `fix direction`
- the `evidence source` field keeps the required source-layer tagging

## Must Not

- must not emit a confirmed issue without one of the six required fields
- must not omit `validation action` from a confirmed issue
- must not omit source-layer tagging inside the `evidence source` field
