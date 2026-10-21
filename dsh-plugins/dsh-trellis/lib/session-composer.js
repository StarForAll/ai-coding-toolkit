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
import { resolveTrellisProject } from "./project.js";
import { createDshDefaultsEnsurer } from "./project-defaults.js";
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
  // One-time (per project, per changed state) migration: Trellis projects that
  // install this plugin start in the mode the plugin documents. The ensurer is
  // idempotent and refuses to overwrite an explicit value, so it is safe to
  // attempt on every step; the session-local cache keeps the common case at one
  // read and no writes.
  const ensureProjectDefaults = createDshDefaultsEnsurer({
    fs,
    logger: ctx.logger,
    cache,
  });

  const compose = async (agent, messages, signal) => {
    const cwd = await resolveWorkingDirectory(ctx, agent, signal);
    const subagent = isSubagentSession(agent);
    const sessionId = agent.session.header.id ?? "";
    const contextKey =
      sessionId === "" ? "" : `dsh_${sanitizeContextKey(sessionId)}`;
    signal?.throwIfAborted();
    // Bootstrap runs before state resolution so the very first turn already
    // sees `dsh.dispatch_mode: inline`; the write also invalidates the shared
    // read cache, which makes that re-read observe the new file.
    const project = await resolveTrellisProject({
      ctx,
      agent,
      signal,
      cwd,
      fs,
      cache,
      markers: resolved.projectRootMarkers,
    });
    if (project !== null) {
      try {
        await ensureProjectDefaults(project);
      } catch (error) {
        ctx.logger?.warn?.("dsh-trellis project defaults failed: %o", error);
      }
    }
    signal?.throwIfAborted();
    // The project bootstrap is about enabling the plugin, not about rendering a
    // breadcrumb: a zero byte budget still normalizes the project config.
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
