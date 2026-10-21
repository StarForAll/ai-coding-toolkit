/**
 * One-time session bootstrap nudge.
 *
 * This is the DSH counterpart of the `<trellis-bootstrap>` notice Codex attaches
 * to its per-turn `UserPromptSubmit` context while a session has no active
 * task. It is a message family of its own — its own `source.form` and its own
 * projection — so it is deduped independently of the workflow breadcrumb:
 *
 *   - injected once per session, regardless of how often the workflow state
 *     changes between no_task and an active task;
 *   - injected again only when the message is no longer visible on the session
 *     surface (a compaction removed it), which is exactly when the model lost
 *     the context the nudge refers to.
 *
 * The wording stays conditional ("if you have not already loaded …") because a
 * compaction may legitimately re-deliver it.
 *
 * @module dsh-trellis/bootstrap
 */
import { createUserMessage } from "@deepseek-ai/dsh-llm";
import { createMessageProjection, registerMessageProjection } from "./message-projection.js";
import { truncateUtf8 } from "./text.js";

export const SOURCE_KIND = "dsh-trellis";
export const SOURCE_FORM = "bootstrap";
export const BOOTSTRAP_PROJECTION_KEY = "dsh-trellis.bootstrap";

/** Fixed ceiling for a pure reminder; it never competes with the spec budget. */
export const BOOTSTRAP_MAX_BYTES = 512;

export const BOOTSTRAP_NOTICE = `<trellis-bootstrap>
If you have not already loaded Trellis context this session, read the \`trellis-start\` skill once.
</trellis-bootstrap>`;

/**
 * Compose the bootstrap message.
 * @param {number} [maxBytes] - byte budget; `<= 0` keeps the full notice.
 * @returns {ReturnType<typeof createUserMessage>}
 */
export function bootstrapMessage(maxBytes = BOOTSTRAP_MAX_BYTES) {
  return createUserMessage({
    content: [{ type: "text", text: truncateUtf8(BOOTSTRAP_NOTICE, maxBytes) }],
    source: { kind: SOURCE_KIND, form: SOURCE_FORM },
  });
}

/** Whether a message belongs to the bootstrap family. */
export function isBootstrapMessage(message) {
  const source = message?.source;
  return (
    typeof source === "object" &&
    source !== null &&
    source.kind === SOURCE_KIND &&
    source.form === SOURCE_FORM
  );
}

export const bootstrapProjection = createMessageProjection({
  key: BOOTSTRAP_PROJECTION_KEY,
  isOwn: isBootstrapMessage,
});

/** Register/read the bootstrap projection on the owning runtime scope. */
export function registerBootstrapProjection(ctx) {
  return registerMessageProjection(ctx, bootstrapProjection);
}
