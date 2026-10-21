/**
 * Dispatch guard for Trellis role sub-agents.
 *
 * A `trellis-agent-implement` / `trellis-agent-check` child without a task is
 * the failure mode the child-pull skills cannot recover from: it has no task
 * directory to read, so it works from whatever the dispatch prompt happened to
 * say. The guard refuses that dispatch instead.
 *
 * "Has a task" is proven by evidence, not by the word "task":
 *
 *   - the parent session's Trellis pointer resolves to a readable `task.json`,
 *     or
 *   - the dispatch prompt carries an `Active task: <path>` prelude that points
 *     at a readable `task.json`.
 *
 * Research may run without a task (it is the discovery role), so it is allowed
 * and told, after dispatch, to confirm where its findings will be persisted.
 *
 * Codex's hook silently injects nothing in this situation; failing closed here
 * is a deliberate DSH safety enhancement, not a parity claim.
 *
 * @module dsh-trellis/dispatch-guard
 */
import { createUserMessage } from "@deepseek-ai/dsh-llm";
import { resolveTrellisProject } from "./project.js";
import { nodeFs } from "./node-fs.js";
import { readTaskStatus, resolveActiveTask } from "./workflow.js";
import { dshContextKey } from "./session-env.js";

export const SOURCE_KIND = "dsh-trellis";
export const SOURCE_FORM = "dispatch-guard";

/** Dispatch tools whose prompt can select a Trellis role. */
export const GUARDED_TOOLS = Object.freeze(["subagent", "subagent_fork"]);

const ROLE_RE = /\btrellis-agent-(implement|check|research)\b/;
const TASK_PRELUDE_RE = /Active task:\s*([^\s`'"<>]+)/;

/**
 * Recover the role and task prelude from a dispatch prompt.
 * @param {unknown} prompt
 * @returns {{role: "implement" | "check" | "research" | null, taskPath: string | null}}
 */
export function parseDispatchRequest(prompt) {
  const text = typeof prompt === "string" ? prompt : "";
  const role = ROLE_RE.exec(text)?.[1] ?? null;
  const taskPath = TASK_PRELUDE_RE.exec(text)?.[1]?.replace(/[.,;:]+$/, "") ?? null;
  return { role, taskPath };
}

/**
 * Whether the dispatch has a task it can actually read.
 * @param {object} options
 * @param {string} options.root
 * @param {string | null} options.taskPath
 * @param {string} options.sessionId
 * @param {object} [options.fs]
 * @returns {Promise<boolean>}
 */
export async function hasReadableTask({ root, taskPath, sessionId, fs = nodeFs }) {
  if (taskPath !== null) {
    return (await readTaskStatus(root, taskPath, fs)) !== null;
  }
  const contextKey = dshContextKey(sessionId);
  if (contextKey === "") return false;
  const task = await resolveActiveTask(root, contextKey, fs);
  // A stale pointer names a task directory that no longer exists; the
  // dispatch would reach a child with no readable task, which is exactly what
  // this guard refuses.
  return (
    task !== null &&
    task.status !== "task_error" &&
    task.status !== "stale"
  );
}

/** Message attached after a task-less research dispatch. */
export function researchNotice() {
  return createUserMessage({
    content: [{
      type: "text",
      text:
        "<trellis-dispatch-guard>\n" +
        "Research was dispatched without a resolvable task. Confirm where its findings " +
        "will be persisted (for example `.trellis/tasks/<slug>/research/`) before relying on them.\n" +
        "</trellis-dispatch-guard>",
    }],
    source: { kind: SOURCE_KIND, form: SOURCE_FORM, role: "research" },
  });
}

/** Deny reason for a task-less implement/check dispatch. */
export function denyReason(role) {
  return (
    `Trellis dispatch guard: no readable active task for trellis-agent-${role}.\n\n` +
    "Start the workflow first (`/trellis-start`, then create/start a task), or include an " +
    "`Active task: .trellis/tasks/<slug>` prelude that points at an existing task.json.\n\n" +
    "Codex would inject nothing here and let the child run without context; this plugin fails closed."
  );
}

/**
 * Register the dispatch guard.
 *
 * @param {import("@deepseek-ai/cordis").Context} ctx
 * @param {{projectRootMarkers: string[]}} resolved
 * @returns {() => void} disposer.
 */
export function registerDispatchGuard(ctx, resolved) {
  const pending = new Map();
  const cache = new Map();
  let disposed = false;
  const warn = (error) => {
    ctx.logger?.warn?.("dsh-trellis dispatch guard failed: %o", error);
  };

  const disposePre = ctx.on("tools/pre-execute", async (exec, next) => {
    const decision = await next();
    if (disposed || decision.kind !== "allow") return decision;
    if (!GUARDED_TOOLS.includes(exec.name)) return decision;
    const { role, taskPath } = parseDispatchRequest(exec.arguments?.prompt);
    if (role === null) return decision;
    try {
      const project = await resolveTrellisProject({
        ctx,
        agent: exec.agent,
        signal: exec.signal,
        fs: resolved.fs,
        cache,
      });
      // Outside a Trellis project the guard has nothing to protect.
      if (project === null) return decision;
      const sessionId = exec.agent?.session?.header?.id ?? "";
      const readable = await hasReadableTask({
        root: project.root,
        taskPath,
        sessionId,
        fs: nodeFs,
      });
      if (readable) return decision;
      if (role === "research") {
        pending.set(exec.callId, researchNotice());
        return decision;
      }
      return { kind: "deny", reason: denyReason(role) };
    } catch (error) {
      warn(error);
      return decision;
    }
  });

  const disposePost = ctx.on("tools/post-execute", async (exec, result, next) => {
    const decision = await next();
    const notice = pending.get(exec.callId);
    if (notice === undefined) return decision;
    pending.delete(exec.callId);
    if (disposed) return decision;
    return {
      ...decision,
      additionalContexts: [...(decision.additionalContexts ?? []), notice],
    };
  });

  return () => {
    disposed = true;
    disposePre();
    disposePost();
    pending.clear();
    cache.clear();
  };
}
