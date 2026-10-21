/**
 * dsh-trellis: Trellis workflow integration for DeepSeek Harness.
 *
 * - Per-turn workflow-state breadcrumb: at every eligible `agent/pre-step`,
 *   resolves the project's Trellis state (.trellis/workflow.md blocks +
 *   active task) and injects the matching [workflow-state:*] body into the
 *   session, exactly where the workspace-instruction baseline lands.
 * - One-time `trellis-start` bootstrap nudge: a session with no active task
 *   receives the DSH counterpart of Codex's `<trellis-bootstrap>` notice. It is
 *   a separate message family with its own projection, so workflow state churn
 *   cannot redeliver it; only a compaction that removed it can.
 * - Path-scoped spec injection: `tools/pre-execute` denies an edit/write once
 *   when a governing `.trellis/spec` document becomes due (Codex's deny-once
 *   gate), and `tools/post-execute` delivers tickets as additional context.
 * - Sub-agent push: a Trellis role child receives curated task context before
 *   its first model request, the DSH equivalent of Codex's SubagentStart hook.
 * - `/trellis-status` and read-only `/trellis-finish` utility commands.
 *   Session rituals remain skills (`/trellis-start`, `/trellis-continue`,
 *   `/trellis-finish-work`) so command registration cannot shadow them.
 * - `trellis_wait`, an event-driven synchronization tool for a continuable
 *   role agent after the main session has exhausted independent work.
 * - A managed DSH_TRELLIS_CONTEXT_ID derived per shell execution from the
 *   native DSH session, so an outer host's inherited TRELLIS_CONTEXT_ID cannot
 *   silently claim the inner session. Utility commands set the same identity.
 *
 * In directories without a Trellis project it injects no breadcrumb; utility
 * commands validate the project only when a user explicitly invokes them.
 *
 * @module dsh-trellis
 */
import { isDeepStrictEqual } from "node:util";
import * as settingsModule from "@deepseek-ai/dsh-settings";
import { Config, hasLiveConfig, resolveConfig } from "./config.js";
import { isBootstrapMessage, registerBootstrapProjection } from "./bootstrap.js";
import { isBreadcrumbMessage } from "./breadcrumb.js";
import { registerBreadcrumbProjection } from "./breadcrumb-projection.js";
import { registerCommands } from "./commands.js";
import {
  CONFLICTS_ROUTE_PATH,
  createConflictsHandler,
  detectTrellisConflicts,
} from "./conflicts.js";
import { registerDispatchGuard } from "./dispatch-guard.js";
import { registerDoctorCommand } from "./doctor.js";
import { createSessionComposer } from "./session-composer.js";
import { registerSessionEnv } from "./session-env.js";
import { installSettingsSectionCompat } from "./settings-compat.js";
import { registerSpecPolicy } from "./spec-policy.js";
import { registerSubagentContext } from "./subagent-context.js";
import { createVersionCheckHandler, ROUTE_PATH } from "./upstream.js";
import { registerWaitTool } from "./wait-tool.js";

export const name = "dsh-trellis";
export const SETTINGS_NAMESPACE = "dsh-trellis";

/** @type {string[]} */
export const inject = ["commands", "shellEnv", "subagents", "tools", "sessionProjections"];

export { Config };

function stopAll(disposers) {
  for (const dispose of disposers.toReversed()) dispose();
}

function sameMessagePayload(left, right) {
  return (
    isDeepStrictEqual(left.content, right.content) &&
    isDeepStrictEqual(left.source, right.source)
  );
}

/** @param {import("@deepseek-ai/cordis").Context} ctx */
export function apply(ctx, config = {}) {
  let stopped = false;
  let disposeRuntime = () => {};
  let currentConfig = () => config;
  let mountedConfig;

  const mountRuntime = (nextConfig) => {
    if (stopped) return;
    disposeRuntime();
    const resolved = resolveConfig(nextConfig);
    mountedConfig = resolved;
    if (!resolved.enabled) {
      disposeRuntime = () => {};
      return;
    }

    const disposers = [];
    try {
      if (resolved.commandsEnabled) {
        disposers.push(registerCommands(ctx, resolved));
        disposers.push(registerDoctorCommand(ctx, resolved));
      }
      disposers.push(registerWaitTool(ctx));
      disposers.push(registerSessionEnv(ctx));
      disposers.push(registerSessionMessages(ctx, resolved));
      if (resolved.specInjection) {
        disposers.push(registerSpecPolicy(ctx, resolved));
      }
      if (resolved.subagentContext) {
        disposers.push(registerSubagentContext(ctx, resolved));
      }
      if (resolved.dispatchGuard) {
        disposers.push(registerDispatchGuard(ctx, resolved));
      }
    } catch (error) {
      stopAll(disposers);
      throw error;
    }
    disposeRuntime = () => stopAll(disposers);
  };

  // The settings page's upstream check runs in the Host: GitHub's Atom feeds
  // carry no CORS headers, and the REST API's unauthenticated quota is what
  // produced 403 responses. The route is same-origin and only ever fetches
  // validated GitHub/npm URLs.
  ctx.inject(["webServer"], (webCtx) => {
    const registerRoute = (path, handler, label) => {
      webCtx.effect(() => {
        try {
          return webCtx.webServer.register({ kind: "exact", path, handler });
        } catch (error) {
          // A second Trellis plugin claiming the same path must not take this
          // one down; the browser surfaces the conflict instead.
          ctx.logger?.warn?.("dsh-trellis: could not register %s: %o", path, error);
          return () => {};
        }
      }, label);
    };
    registerRoute(ROUTE_PATH, createVersionCheckHandler(), "dsh-trellis.version-route");
    // The conflict result is data the browser turns into a desktop
    // notification; the Host deliberately writes no log line for it.
    registerRoute(
      CONFLICTS_ROUTE_PATH,
      createConflictsHandler(() => detectTrellisConflicts(ctx)),
      "dsh-trellis.conflicts-route",
    );
  });

  // Keep the composition entry working when no settings provider is mounted.
  // Once the service appears, its resolved section becomes the live source and
  // a saved Web card edit remounts only this plugin's runtime.
  ctx.effect(() => {
    mountRuntime(currentConfig());
    return () => {
      stopped = true;
      disposeRuntime();
    };
  }, "dsh-trellis.runtime");

  if (hasLiveConfig(config)) {
    // Loader emits this to the owning fiber after committing every reference.
    // Unrelated profile edits must not cancel active waits or breadcrumbs.
    ctx.on("loader/volatile-update", () => {
      if (!isDeepStrictEqual(resolveConfig(config), mountedConfig)) mountRuntime(config);
    });
  }

  // Optional by design: profiles without a settings service retain the
  // loader-config behavior. The canonical bridge also distinguishes a settings
  // provider reload (fall back to config) from this plugin's own teardown
  // (leave the runtime alone until its owning effect disposes it).
  installSettingsSectionCompat(
    ctx,
    settingsModule,
    SETTINGS_NAMESPACE,
    Config,
    config,
    {
      setSource(source) {
        currentConfig = source;
      },
      onChange() {
        mountRuntime(currentConfig());
      },
    },
  );
}

/**
 * Insert messages without discarding decision metadata added by DSH or another
 * pre-step participant (for example `startsRequestSeries`).
 *
 * @param {{ messages: unknown[], [key: string]: unknown }} decision
 * @param {unknown[]} claimedMessages
 * @param {unknown[]} desired
 */
export function insertMessagesDecision(decision, claimedMessages, desired) {
  const lastClaimedIndex = decision.messages.findLastIndex((message) =>
    claimedMessages.includes(message),
  );
  return {
    ...decision,
    messages: decision.messages.toSpliced(lastClaimedIndex + 1, 0, ...desired),
  };
}

/**
 * Single-message convenience wrapper around {@link insertMessagesDecision}.
 * Kept as a stable helper for callers that only add the breadcrumb.
 *
 * @param {{ messages: unknown[], [key: string]: unknown }} decision
 * @param {unknown[]} claimedMessages
 * @param {unknown} desired
 */
export function insertBreadcrumbDecision(decision, claimedMessages, desired) {
  return insertMessagesDecision(decision, claimedMessages, [desired]);
}

function registerSessionMessages(ctx, resolved) {
  const { compose } = createSessionComposer(resolved, ctx);
  const families = [];
  const isOwn = (message) => families.some((family) => family.isOwn(message));
  const isVisible = (session, message) => {
    const family = families.find((candidate) => candidate.isOwn(message));
    return family !== undefined && family.projection.isVisible(session, message);
  };
  let disposed = false;
  const pendingInboxes = new Set();

  const clearInbox = (inbox) => {
    for (const message of inbox.nextStep.filter(isOwn)) inbox.remove(message.id);
    pendingInboxes.delete(inbox);
  };

  /**
   * Keep exactly the desired messages queued, reusing an already-queued message
   * with the same payload so its identity (and the caller's reference) survives.
   */
  const syncInbox = (agent, desired) => {
    pendingInboxes.add(agent.inbox);
    const pending = agent.inbox.nextStep.filter(isOwn);
    const kept = [];
    for (const wanted of desired) {
      const reusable = pending.find(
        (message) =>
          !kept.includes(message) && sameMessagePayload(message, wanted),
      );
      kept.push(reusable ?? wanted);
    }
    for (const message of pending) agent.inbox.remove(message.id);
    for (const message of kept.toReversed()) {
      agent.inbox.prepend("next-step", message);
    }
  };

  let disposeStep;
  try {
    families.push(
      { isOwn: isBreadcrumbMessage, projection: registerBreadcrumbProjection(ctx) },
      { isOwn: isBootstrapMessage, projection: registerBootstrapProjection(ctx) },
    );
    disposeStep = ctx.on("agent/pre-step", async ({ agent, messages, step, signal }, next) => {
      const decision = await next();
      if (disposed) return decision;
      let desired;
      try {
        const composed = await compose(agent, messages, signal);
        if (disposed) return decision;
        // Each family is deduped independently: a visible breadcrumb never
        // suppresses the bootstrap nudge, and vice versa.
        desired = composed.filter(
          (message) => !isVisible(agent.session, message),
        );
      } catch (error) {
        if (signal !== undefined && signal.aborted) throw error;
        ctx.logger?.warn?.(
          "dsh-trellis session message composition failed: %o",
          error,
        );
        return decision;
      }
      signal?.throwIfAborted();
      if (desired.length === 0) {
        clearInbox(agent.inbox);
        return decision;
      }
      if (
        decision.kind === "reject" ||
        (step === 1 && decision.messages.length === 0)
      ) {
        syncInbox(agent, desired);
        return decision;
      }
      clearInbox(agent.inbox);
      const missing = desired.filter(
        (message) =>
          !decision.messages.some((candidate) =>
            sameMessagePayload(candidate, message),
          ),
      );
      if (missing.length === 0) return decision;
      return insertMessagesDecision(decision, messages, missing);
    });
  } catch (error) {
    for (const family of families) family.projection.dispose();
    throw error;
  }
  return () => {
    disposed = true;
    disposeStep();
    for (const inbox of pendingInboxes) clearInbox(inbox);
    for (const family of families) family.projection.dispose();
  };
}
