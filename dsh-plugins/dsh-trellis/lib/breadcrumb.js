/**
 * Per-turn workflow-state breadcrumb message: payload shape and ownership.
 *
 * Composition (which states produce which messages) lives in
 * `session-composer.js`; this module only owns the breadcrumb payload itself.
 *
 * @module dsh-trellis/breadcrumb
 */
import { createUserMessage } from "@deepseek-ai/dsh-llm";
import { truncateUtf8 } from "./text.js";

export const SOURCE_KIND = "dsh-trellis";
export const SOURCE_FORM = "breadcrumb";

// Kept as a re-export: callers and tests historically reached the helper here.
export { truncateUtf8 };

/**
 * Compose the model-visible breadcrumb message for a resolved state.
 * @param {{status: string, taskPath: string | null, body: string, digest: string}} state
 * @param {number} maxBytes
 * @returns {ReturnType<typeof createUserMessage>}
 */
export function breadcrumbMessage(state, maxBytes) {
  const taskLine =
    state.taskPath === null ? "" : `\nActive task: ${state.taskPath}`;
  const text = truncateUtf8(
    `<system-reminder>\nTrellis workflow state: ${state.status}${taskLine}\n\n${state.body}\n</system-reminder>`,
    maxBytes,
  );
  return createUserMessage({
    content: [{ type: "text", text }],
    source: {
      kind: SOURCE_KIND,
      form: SOURCE_FORM,
      status: state.status,
      task: state.taskPath,
      digest: state.digest,
    },
  });
}

/** Whether a user message carries our breadcrumb source. */
export function isBreadcrumbMessage(message) {
  const source = message?.source;
  return (
    typeof source === "object" &&
    source !== null &&
    source.kind === SOURCE_KIND &&
    source.form === SOURCE_FORM
  );
}

/**
 * Does the claimed prompt batch contain the skip keyword as a standalone word?
 *
 * Boundary rule mirrors Trellis's `prompt_has_skip_keyword`
 * (`.codex/hooks/inject-workflow-state.py`), the authority the project-level
 * `prompt_injection.skip_keyword` comes from:
 *
 *     (?<![\w-])keyword(?![\w-])   # re.IGNORECASE
 *
 * A hyphen counts as a word character, so `foo-no-trellis` is *not* a
 * standalone hit, while punctuation/whitespace boundaries are. Python's `\w`
 * is Unicode-aware, hence the `\p{L}\p{N}_` classes rather than the ASCII-only
 * `\b`, which also never matches a keyword that starts or ends with
 * punctuation (e.g. `#skip`, `skip.`).
 *
 * @param {Array<{content?: unknown}>} messages
 * @param {string} keyword
 */
export function hasSkipKeyword(messages, keyword) {
  if (!keyword) return false;
  const pattern = new RegExp(
    `(?<![\\p{L}\\p{N}_-])${keyword.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}(?![\\p{L}\\p{N}_-])`,
    "iu",
  );
  for (const message of messages) {
    const content = message?.content;
    const parts = Array.isArray(content)
      ? content
      : [{ type: "text", text: String(content ?? "") }];
    for (const part of parts) {
      if (typeof part?.text === "string" && pattern.test(part.text))
        return true;
    }
  }
  return false;
}
