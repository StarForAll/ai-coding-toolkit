/**
 * Path-scoped spec injection at the tool boundary.
 *
 * DSH exposes two hooks the Codex wiring does not have in the same shape:
 *
 * - `tools/pre-execute` can `deny` a call with a model-visible reason, which is
 *   how Codex's deny-once gate is reproduced: the edit/write is refused once,
 *   the governing spec arrives in the error result, and the retry is allowed.
 * - `tools/post-execute` can attach `additionalContexts`, delivered with the
 *   next request. Tickets (a cheap reminder for an unchanged spec) use this
 *   path, so a ticket never blocks the call.
 *
 * A read-only tool has no deny path — it only ever receives post-execute
 * context. `read` is therefore opt-in via `spec_injection.tools`.
 *
 * The authority is `.trellis/config.yaml` (`spec_injection:`), exactly as on
 * other platforms: an explicit `enabled: false` disables the feature, a missing
 * section keeps Trellis's default of enabled.
 *
 * The decision records persist per project + session in
 * `.trellis/.runtime/spec-inject/` (see `spec-state.js`). A restart therefore
 * keeps "already taught" state; `compaction/end` deletes both the in-memory map
 * and the shard so the next touch re-teaches.
 *
 * @module dsh-trellis/spec-policy
 */
import { isAbsolute } from "node:path";
import { createUserMessage } from "@deepseek-ai/dsh-llm";
import { nodeFs } from "./node-fs.js";
import { resolveTrellisProject } from "./project.js";
import {
  decide,
  assemblePayload,
  RETRY_NOTICE,
} from "./spec-inject.js";
import { matchSpecsForFile, readSpecBody } from "./spec-index.js";
import {
  compareSpecificity,
  normalizeRepoRelative,
  normalizeRepoRelativeFrom,
} from "./spec-glob.js";
import { findProjectRoot } from "./workflow.js";
import { resolveWorkingDirectory } from "./working-directory.js";
import {
  clearSpecState,
  loadSpecState,
  saveSpecState,
} from "./spec-state.js";
import {
  normalizeToolName,
  specInjectionSettings,
} from "./trellis-config.js";

export const SOURCE_KIND = "dsh-trellis";
export const SOURCE_FORM = "spec-context";

/** A read-only tool may never be denied; it only receives post-execute context. */
const MUTATING_TOOLS = new Set(["edit", "write"]);

/**
 * Resolve a tool's `file_path` into every plausible repo-relative path.
 *
 * DSH resolves a relative `file_path` against the agent's current working
 * directory, which may be a subdirectory of the Trellis project. The same
 * argument may also be written repo-relative by a model that has the project
 * root as cwd. Both interpretations are candidates; callers union their spec
 * matches (over-injection is the safe side of the asymmetry).
 *
 * @param {string} root - absolute project root.
 * @param {string} cwd - absolute agent working directory.
 * @param {string} filePath - raw tool argument.
 * @returns {string[]} deduplicated repo-relative candidates, cwd-relative first.
 */
export function candidateRepoPaths(root, cwd, filePath) {
  const candidates = [];
  const add = (value) => {
    if (typeof value === "string" && value !== "" && !candidates.includes(value)) {
      candidates.push(value);
    }
  };
  if (typeof filePath !== "string" || filePath.trim() === "") return candidates;
  if (isAbsolute(filePath)) {
    add(normalizeRepoRelative(root, filePath));
    return candidates;
  }
  add(normalizeRepoRelativeFrom(root, cwd, filePath));
  add(normalizeRepoRelative(root, filePath));
  return candidates;
}

/**
 * Build the message attached after a ticket-only tool call.
 * @param {string} payload
 * @param {string[]} specs
 * @returns {ReturnType<typeof createUserMessage>}
 */
export function specContextMessage(payload, specs) {
  return createUserMessage({
    content: [{ type: "text", text: payload }],
    source: {
      kind: SOURCE_KIND,
      form: SOURCE_FORM,
      specs,
    },
  });
}

/**
 * Plan one injection without mutating session state.
 *
 * Exported for tests: the tool-policy registration below only adds IO and
 * state bookkeeping around this function.
 *
 * @param {object} options
 * @param {string} options.root
 * @param {string[]} options.filePaths - repo-relative candidates (cwd first).
 *   `filePath` is still accepted for callers/tests that have one canonical path.
 * @param {string} [options.filePath]
 * @param {string} options.toolName
 * @param {string} options.sessionKey - empty means stateless (ticket-only).
 * @param {Map<string, Record<string, unknown>>} options.store - per-session records.
 * @param {Map<string, unknown>} options.indexCache
 * @param {ReturnType<typeof specInjectionSettings>} options.settings
 * @param {number} options.nowSeconds
 * @returns {Promise<{kind: "none"} | {kind: "full" | "context", payload: string,
 *   records: Array<Record<string, unknown>>, editedRel: string}>}
 */
export async function planSpecInjection({
  root,
  filePath,
  filePaths,
  toolName,
  sessionKey,
  store,
  indexCache,
  settings,
  nowSeconds,
}) {
  if (!settings.enabled) return { kind: "none" };
  if (!settings.tools.includes(normalizeToolName(toolName))) return { kind: "none" };

  const candidatePaths = Array.isArray(filePaths)
    ? filePaths.filter((value) => typeof value === "string" && value !== "")
    : typeof filePath === "string" && filePath !== ""
      ? [filePath]
      : [];
  if (candidatePaths.length === 0) return { kind: "none" };

  // Union matches from every plausible path interpretation, keeping the most
  // specific match when two candidates reach the same spec.
  const matchesBySpec = new Map();
  for (const path of candidatePaths) {
    const matches = await matchSpecsForFile(root, path, indexCache, nowSeconds * 1000);
    for (const match of matches) {
      const previous = matchesBySpec.get(match.specRel);
      if (previous === undefined ||
          compareSpecificity(match.rank, previous.rank) > 0) {
        matchesBySpec.set(match.specRel, match);
      }
    }
  }
  const matches = [...matchesBySpec.values()].sort((left, right) => {
    const byRank = compareSpecificity(left.rank, right.rank);
    return byRank !== 0 ? byRank : left.specRel < right.specRel ? -1 : 1;
  });
  if (matches.length === 0) return { kind: "none" };

  const stateless = sessionKey === "";
  const candidates = [];
  for (const match of matches) {
    const spec = await readSpecBody(match.absPath);
    if (spec === null) continue;
    const last = stateless ? null : (store.get(match.specRel) ?? null);
    const mode = decide({
      stateless,
      last,
      sha256: spec.sha256,
      nowSeconds,
      winSeconds: settings.refreshWindowSeconds,
    });
    candidates.push({
      specRel: match.specRel,
      description: match.description,
      sha256: spec.sha256,
      sha12: spec.sha256.slice(0, 12),
      body: spec.body,
      mode,
    });
  }
  if (candidates.length === 0) return { kind: "none" };

  const { payload, records } = assemblePayload({
    editedRel: matches[0].relPath,
    candidates,
    maxSpecChars: settings.maxSpecChars,
    maxTotalChars: settings.maxTotalChars,
    stateless,
    nowSeconds,
  });
  if (payload === "") return { kind: "none" };
  return {
    kind: records.some((record) => record.mode === "full") ? "full" : "context",
    payload,
    records,
    editedRel: matches[0].relPath,
  };
}

/**
 * Register the pre/post-execute policy for one plugin runtime.
 *
 * @param {import("@deepseek-ai/cordis").Context} ctx
 * @param {{projectRootMarkers: string[]}} resolved
 * @returns {() => void} disposer.
 */
export function registerSpecPolicy(ctx, resolved) {
  const stores = new Map();
  const loading = new Map();
  const saves = new Map();
  const sessionRoots = new Map();
  const indexCache = new Map();
  const fileCache = new Map();
  const pending = new Map();
  let disposed = false;

  const warn = (error) => {
    ctx.logger?.warn?.("dsh-trellis spec injection failed: %o", error);
  };

  const storeKey = (root, sessionKey) => `${root}\u0000${sessionKey}`;

  const trackRoot = (sessionKey, root) => {
    let roots = sessionRoots.get(sessionKey);
    if (roots === undefined) {
      roots = new Set();
      sessionRoots.set(sessionKey, roots);
    }
    roots.add(root);
  };

  const storeFor = async (root, sessionKey) => {
    if (sessionKey === "") return new Map();
    const key = storeKey(root, sessionKey);
    const cached = stores.get(key);
    if (cached !== undefined) return cached;
    const inFlight = loading.get(key);
    if (inFlight !== undefined) return inFlight;
    trackRoot(sessionKey, root);
    const promise = loadSpecState(root, sessionKey)
      .then((store) => {
        stores.set(key, store);
        loading.delete(key);
        return store;
      })
      .catch((error) => {
        loading.delete(key);
        warn(error);
        const store = new Map();
        stores.set(key, store);
        return store;
      });
    loading.set(key, promise);
    return promise;
  };

  const flushState = (root, sessionKey, store) => {
    const key = storeKey(root, sessionKey);
    const previous = saves.get(key) ?? Promise.resolve();
    const next = previous
      .catch(() => {})
      .then(async () => {
        const ok = await saveSpecState(root, sessionKey, store);
        if (!ok) {
          warn(new Error(`spec state could not be persisted for ${sessionKey}`));
        }
      })
      .catch((error) => warn(error));
    saves.set(key, next);
    return next;
  };

  const flushClear = (root, sessionKey) => {
    const key = storeKey(root, sessionKey);
    const previous = saves.get(key) ?? Promise.resolve();
    const next = previous
      .catch(() => {})
      .then(() => clearSpecState(root, sessionKey))
      .catch((error) => warn(error));
    saves.set(key, next);
    return next;
  };

  const sessionKeyOf = (agent) => agent?.session?.header?.id ?? "";

  const disposePre = ctx.on("tools/pre-execute", async (exec, next) => {
    const decision = await next();
    if (disposed || decision.kind !== "allow") return decision;
    try {
      const filePath = exec.arguments?.file_path;
      if (typeof filePath !== "string" || filePath.trim() === "") return decision;
      const project = await resolveTrellisProject({
        ctx,
        agent: exec.agent,
        signal: exec.signal,
        fs: resolved.fs,
        cache: fileCache,
      });
      if (project === null) return decision;
      const settings = specInjectionSettings(project.configText);
      if (!settings.enabled) return decision;
      const toolName = normalizeToolName(exec.name);
      if (!settings.tools.includes(toolName)) return decision;
      let cwd = project.root;
      try {
        cwd = await resolveWorkingDirectory(ctx, exec.agent, exec.signal);
      } catch (error) {
        // A broken working-directory service must not silently skip spec
        // injection; fall back to the project root (the old interpretation).
        warn(error);
      }
      const filePaths = candidateRepoPaths(project.root, cwd, filePath);
      if (filePaths.length === 0) return decision;
      const sessionKey = sessionKeyOf(exec.agent);
      const store = await storeFor(project.root, sessionKey);
      const plan = await planSpecInjection({
        root: project.root,
        filePaths,
        toolName,
        sessionKey,
        store,
        indexCache,
        settings,
        nowSeconds: Math.floor(Date.now() / 1000),
      });
      if (plan.kind === "none") return decision;
      for (const record of plan.records) store.set(record.spec, record);
      if (sessionKey !== "" && plan.records.length > 0) {
        await flushState(project.root, sessionKey, store);
      }
      if (plan.kind === "full" && MUTATING_TOOLS.has(toolName)) {
        // Deny-once: the model reads the spec in the error result and retries;
        // the recorded FULL makes the retry silent for the refresh window.
        return { kind: "deny", reason: `${RETRY_NOTICE}\n\n${plan.payload}` };
      }
      // Read-only tools have no deny path, so their payload travels with the
      // next request through post-execute instead.
      pending.set(exec.callId, {
        payload: plan.payload,
        specs: plan.records.map((record) => record.spec),
      });
      return decision;
    } catch (error) {
      warn(error);
      return decision;
    }
  });

  const disposePost = ctx.on("tools/post-execute", async (exec, result, next) => {
    const decision = await next();
    const parked = pending.get(exec.callId);
    if (parked === undefined) return decision;
    pending.delete(exec.callId);
    if (disposed) return decision;
    const message = specContextMessage(parked.payload, parked.specs);
    const additionalContexts = [...(decision.additionalContexts ?? []), message];
    return { ...decision, additionalContexts };
  });

  // A compacted session lost the spec text, so the next touch of a matching
  // file must re-teach it in full. Dropping the in-memory map and the persisted
  // shard is required: keeping either would let the next process stay silent
  // about text the model no longer has.
  const disposeSession = ctx.on("session/event", async (session, event) => {
    if (event?.type !== "compaction/end") return;
    const roots = new Set(sessionRoots.get(session.id) ?? []);
    // A restarted plugin has not seen a tool call yet, so sessionRoots may be
    // empty. Resolve the project root from the session header instead of
    // leaving a stale shard behind that would silence the next touch.
    const cwd = session?.header?.cwd ?? session?.cwd;
    if (typeof cwd === "string" && cwd !== "") {
      try {
        const root = await findProjectRoot(cwd, [".trellis"], nodeFs);
        if (root !== null) roots.add(root);
      } catch (error) {
        warn(error);
      }
    }
    if (roots.size === 0) return;
    for (const root of roots) {
      const key = storeKey(root, session.id);
      stores.delete(key);
      loading.delete(key);
    }
    sessionRoots.delete(session.id);
    await Promise.all(
      [...roots].map((root) => flushClear(root, session.id)),
    );
  });

  return () => {
    disposed = true;
    disposePre();
    disposePost();
    disposeSession?.();
    pending.clear();
    stores.clear();
    loading.clear();
    saves.clear();
    sessionRoots.clear();
    indexCache.clear();
    fileCache.clear();
  };
}
