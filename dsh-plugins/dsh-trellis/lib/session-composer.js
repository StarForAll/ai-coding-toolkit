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
 * @module dsh-trellis/session-composer
 */
import { join } from "node:path";
import { breadcrumbMessage, hasSkipKeyword } from "./breadcrumb.js";
import { bootstrapMessage } from "./bootstrap.js";
import { nodeFs } from "./node-fs.js";
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
 * @returns {{compose(agent: any, messages: any[], signal?: AbortSignal): Promise<any[]>}}
 */
export function createSessionComposer(resolved, ctx, dependencies = {}) {
  const fs = dependencies.fs ?? nodeFs;
  const cache = new Map();

  const compose = async (agent, messages, signal) => {
    if (resolved.maxBytes <= 0 || !Number.isFinite(resolved.maxBytes)) return [];
    const cwd = await resolveWorkingDirectory(ctx, agent, signal);
    const subagent = isSubagentSession(agent);
    const sessionId = agent.session.header.id ?? "";
    const contextKey =
      sessionId === "" ? "" : `dsh_${sanitizeContextKey(sessionId)}`;
    signal?.throwIfAborted();
    const state = await resolveTrellisState({
      cwd,
      markers: resolved.projectRootMarkers,
      contextKey,
      fs,
      cache,
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
    if (hasSkipKeyword(messages, keyword)) return [];
    // A delegated child without a task of its own has nothing truthful to say
    // here: its task context, when it has one, is the push message. Silence is
    // the only state that cannot contradict that push.
    if (subagent && state.status === "no_task") return [];
    const composed = [breadcrumbMessage(state, resolved.maxBytes)];
    if (!subagent && state.status === "no_task") composed.push(bootstrapMessage());
    return composed;
  };

  return { compose };
}
