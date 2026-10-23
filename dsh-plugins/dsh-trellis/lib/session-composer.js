/**
 * Session message composition for one `agent/pre-step`.
 *
 * Resolves the project's Trellis state once per step and returns every
 * plugin-owned message that state calls for. Each message family is deduped by
 * its own projection in `index.js`, so state churn (no_task → planning →
 * no_task) can never re-deliver the one-time bootstrap nudge, while a
 * compaction that removes a message can.
 *
 * Child agents are not root sessions: a delegated `trellis-agent-*` child gets
 * its task context pushed by `subagent-context.js`, and a generic child has no
 * session pointer of its own. Resolving the child's own session id therefore
 * yields `no_task` for both, which would contradict the pushed `Active task:`
 * and tell the child to start a Trellis session. A child receives the
 * breadcrumb only when it has bound a task itself, and never the bootstrap
 * nudge.
 *
 * The skip keyword is decided per **turn**, not per step. `agent/pre-step`
 * hands each step only the batch it claims from the inbox, so the user prompt
 * that carried the keyword is gone by the second step of the same turn (it
 * carries tool results instead). Codex decides the same escape hatch once per
 * `UserPromptSubmit`, so the composer remembers the skipped turn and stays
 * silent for its remaining steps.
 *
 * @module dsh-trellis/session-composer
 */
import { join } from "node:path";
import { breadcrumbMessage, hasSkipKeyword } from "./breadcrumb.js";
import { bootstrapMessage } from "./bootstrap.js";
import { nodeFs } from "./node-fs.js";
import { resolveTrellisProject } from "./project.js";
import {
  readCached,
  resolveTrellisState,
  sanitizeContextKey,
} from "./workflow.js";
import { promptInjectionSkipKeyword } from "./trellis-config.js";
import { resolveWorkingDirectory } from "./working-directory.js";

/** DSH's durable marker for an in-process delegated child. */
export const SUBAGENT_ORIGIN = "subagent";

/**
 * Whether this agent is a delegated sub-agent rather than a user-facing root or
 * forked session. `parentSession` alone is not enough: a fork also records its
 * source, but remains a root session for workflow purposes. `delegationDepth`
 * is the fallback for hosts that predate the `origin` marker.
 *
 * @param {any} agent
 * @returns {boolean}
 */
export function isSubagentSession(agent) {
  const header = agent?.session?.header;
  if (header?.origin === SUBAGENT_ORIGIN) return true;
  return Number.isInteger(header?.delegationDepth) && header.delegationDepth > 0;
}

/**
 * Build the plugin's per-step composer.
 *
 * @param {object} resolved - normalized plugin config.
 * @param {import("@deepseek-ai/cordis").Context} ctx
 * @param {{fs?: typeof nodeFs}} [dependencies]
 * @returns {{compose(agent: any, messages: any[], signal?: AbortSignal, position?: {turn?: number}): Promise<any[]>}}
 */
export function createSessionComposer(resolved, ctx, dependencies = {}) {
  const fs = dependencies.fs ?? nodeFs;
  const cache = new Map();
  // Turn-scoped skip memory. Weakly keyed by the agent, which is one per
  // session, so nothing outlives the session it belongs to and no session id
  // bookkeeping is needed. Only the latest skipped turn is kept: turn numbers
  // are monotonic within one agent, so an equality check is enough.
  const skippedTurns = new WeakMap();
  const compose = async (agent, messages, signal, position = {}) => {
    const cwd = await resolveWorkingDirectory(ctx, agent, signal);
    const subagent = isSubagentSession(agent);
    const sessionId = agent.session.header.id ?? "";
    const contextKey =
      sessionId === "" ? "" : `dsh_${sanitizeContextKey(sessionId)}`;
    signal?.throwIfAborted();
    // Resolve the project once so state resolution uses the same root. This is
    // deliberately read-only: the plugin must not rewrite `.trellis/config.yaml`
    // (the project's mode is read with an inline default).
    const project = await resolveTrellisProject({
      ctx,
      agent,
      signal,
      cwd,
      fs,
      cache,
      markers: resolved.projectRootMarkers,
    });
    signal?.throwIfAborted();
    // The skip keyword was already found earlier in this turn; only the batch
    // that carried it is visible to a later step, so the decision is remembered
    // here instead of being re-derived from `messages`.
    const turn = position?.turn;
    if (Number.isInteger(turn) && skippedTurns.get(agent) === turn) return [];
    // A zero budget disables every composed message. This is a rendering
    // decision only; the plugin never normalizes or writes the project config.
    if (resolved.maxBytes <= 0 || !Number.isFinite(resolved.maxBytes)) return [];
    const state = await resolveTrellisState({
      cwd,
      markers: resolved.projectRootMarkers,
      contextKey,
      fs,
      cache,
      root: project?.root ?? null,
    });
    signal?.throwIfAborted();
    if (state === null) return [];
    // The project's own `prompt_injection.skip_keyword` is the Trellis
    // authority every platform hook reads; the plugin-level `skipKeyword`
    // stays the fallback for projects that do not configure it.
    const configText = await readCached(
      join(state.root, ".trellis", "config.yaml"),
      fs,
      cache,
    );
    const keyword = promptInjectionSkipKeyword(configText) ?? resolved.skipKeyword;
    if (hasSkipKeyword(messages, keyword)) {
      // One decision per turn, like Codex's per-prompt hook: the steps that
      // follow a skipped prompt stay silent even though their batch only holds
      // tool results.
      if (Number.isInteger(turn)) skippedTurns.set(agent, turn);
      return [];
    }
    // A delegated child without a task of its own has nothing truthful to say
    // here: its task context, when it has one, is the push message. Silence is
    // the only state that cannot contradict that push.
    if (subagent && state.status === "no_task") return [];
    const composed = [breadcrumbMessage(state, resolved.maxBytes)];
    // A stale pointer means "no usable active task" for this turn, so it gets
    // the same one-time bootstrap nudge as no_task. Codex keeps its
    // `stale_session` label and emits no bootstrap (its notice is appended only
    // when the task is absent), so this nudge is a DSH enhancement, not parity.
    if (!subagent && (state.status === "no_task" || state.status === "stale")) {
      composed.push(bootstrapMessage());
    }
    return composed;
  };

  return { compose };
}
