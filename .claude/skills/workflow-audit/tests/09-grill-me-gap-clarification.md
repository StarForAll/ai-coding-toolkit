# 09 grill-me Gap Clarification

## Purpose

Verify that `workflow-audit` may use `grill-me` only as an internal clarification submode during gap analysis when key branches remain unresolved and continuing would require guessing.

## Input

User input:

> Audit `docs/workflows/新项目开发工作流/`, but stop me and question my assumptions if the candidate issues depend on facts you cannot safely infer from the current repo state.

## Expected Mode

Gap-analysis clarification path inside Step 2C.

## Expected Key Behaviors

- execute Step 2A and 2B first
- reach Step 2C and recognize that key branches remain unresolved
- use `grill-me` only as a clarification submode inside the audit
- resume the evidence mainline after clarification instead of treating `grill-me` as the audit result

## Must Not

- must not recommend `grill-me` as the post-audit next step
- must not use `grill-me` before reaching gap analysis
- must not guess past unresolved branches when clarification is required
