/**
 * Pushed role-contract normalization.
 *
 * Trellis role skills serve two paths:
 *
 * - pull: a class-2 child loads the installed SKILL.md and resolves its own
 *   task context;
 * - push: dsh-trellis includes the role instructions in the child's first
 *   step, with the curated task context already materialized.
 *
 * The pull-only paragraphs must not survive into the pushed copy: they tell
 * the child to run `task.py current` and to ask the user for a task path,
 * directly contradicting the push preamble. This module removes only those
 * paragraphs from the PUSHED copy; the on-disk skill stays untouched so the
 * pull path still works.
 *
 * @module dsh-trellis/role-contract
 */

/** Role spellings a dispatch label may carry: `trellis-agent-<role>` / `trellis-<role>`. */
const LABEL_ROLE_RE = /^(?:trellis-agent-|trellis-)(implement|check|research)$/;

/**
 * Decide whether a dispatch `description` / descriptor `label` *is* a role.
 *
 * The label is a short display string supplied by the caller, so a substring
 * match is not evidence: "研究 trellis-agent-implement 插件的 README" or
 * "about trellis-agent-check plugin docs" talk about a role rather than select
 * one. Only a whole-label role name (ignoring wrapping quotes/punctuation and
 * case) selects the role; anything longer stays generic, exactly like a
 * dispatch with no role at all.
 *
 * @param {unknown} label
 * @returns {"implement" | "check" | "research" | null}
 */
export function roleFromLabel(label) {
  if (typeof label !== "string") return null;
  const stripped = label
    .trim()
    .replace(/^[\s`'"\u201c\u201d\u2018\u2019(\[{<]+/, "")
    .replace(/[\s`'"\u201c\u201d\u2018\u2019)\]}>,.;:!?\uff0c\u3002\uff1b\uff1a\uff01\uff1f\u3001]+$/, "")
    .toLowerCase();
  return LABEL_ROLE_RE.exec(stripped)?.[1] ?? null;
}

export const TASK_CONTEXT_SECTION = `## Task Context

The curated task context is included at the end of this message under
\`## Curated Context\`.

`;

const PULL_HEADING_RE =
  /^## Required: Load Trellis Context First[ \t]*\r?\n[\s\S]*?(?=^## )/m;
const PULL_SENTENCE_RE =
  /^dsh does not auto-inject SessionStart task context\.[^\r\n]*(?:\r?\n)?/m;
const RESEARCH_STEP_RE =
  /^### Step 1: Resolve Current Task[ \t]*\r?\n[\s\S]*?(?=^### Step 2:)/m;
const RESEARCH_STEP_REPLACEMENT = `### Step 1: Prepare Output Directory

Use the Active task path from the dispatch context above. Ensure
\`{TASK_DIR}/research/\` exists before writing findings.

`;

/**
 * Remove pull-only task-discovery instructions from one pushed role contract.
 *
 * Returns the input unchanged when the expected section is absent, which keeps
 * older Trellis role-skill versions working without guessing at their layout.
 *
 * @param {string} body - role skill body after frontmatter stripping.
 * @param {"implement" | "check" | "research" | string} role
 * @returns {string}
 */
export function stripPullOnlyContext(body, role) {
  const source = String(body ?? "");
  if (source.trim() === "") return source;
  if (role === "research") {
    return source.replace(RESEARCH_STEP_RE, RESEARCH_STEP_REPLACEMENT);
  }
  if (role !== "implement" && role !== "check") return source;
  return source
    .replace(PULL_HEADING_RE, TASK_CONTEXT_SECTION)
    .replace(PULL_SENTENCE_RE, "");
}
