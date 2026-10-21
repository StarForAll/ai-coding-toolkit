/**
 * Persistent spec-injection state.
 *
 * The decision engine in `spec-inject.js` is stateless: it needs the last
 * emission per spec to choose FULL / TICKET / silent. `spec-policy.js` used to
 * keep that record map only in process memory, so every DSH restart re-taught
 * every matched spec and denied the first edit again.
 *
 * This module stores one small JSON shard per project + session under
 * `.trellis/.runtime/spec-inject/` (already ignored by Trellis' own
 * `.gitignore`). Writes are atomic (temp file + rename); a missing, corrupt, or
 * unreadable shard is treated as "no history", which re-teaches rather than
 * silently skipping a spec. The state is advisory: a failed write never blocks
 * a tool call.
 *
 * @module dsh-trellis/spec-state
 */
import { mkdir, readFile, rename, rm, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { STATE_VERSION } from "./spec-inject.js";
import { sanitizeContextKey } from "./workflow.js";

/** Bump when the persisted shard envelope changes; older shards are ignored. */
export const SPEC_STATE_VERSION = 1;

/** Record schema version shared with the in-memory decision engine. */
export const SPEC_RECORD_VERSION = STATE_VERSION;

/** Relative state directory inside a Trellis project. */
export const SPEC_STATE_DIR = Object.freeze([".trellis", ".runtime", "spec-inject"]);

const SHA256_RE = /^[a-f0-9]{64}$/;
const MODES = new Set(["full", "ticket"]);

/**
 * Absolute shard path for one root + session, or null when the session has no
 * stable identity (stateless calls must not create shared state).
 *
 * @param {string} root
 * @param {string} sessionKey
 * @returns {string | null}
 */
export function specStatePath(root, sessionKey) {
  const safe = sanitizeContextKey(sessionKey);
  if (safe === "") return null;
  return join(root, ...SPEC_STATE_DIR, `${safe}.json`);
}

/**
 * Validate one persisted record. Unknown extra keys are dropped; malformed
 * records are skipped without discarding the rest of the shard.
 *
 * @param {unknown} value
 * @returns {Record<string, unknown> | null}
 */
export function normalizeSpecRecord(value) {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }
  const record = /** @type {Record<string, unknown>} */ (value);
  if (record.v !== SPEC_RECORD_VERSION) return null;
  if (typeof record.spec !== "string" || record.spec.trim() === "") return null;
  if (typeof record.sha256 !== "string" || !SHA256_RE.test(record.sha256)) return null;
  if (typeof record.ts !== "number" || !Number.isFinite(record.ts)) return null;
  if (typeof record.mode !== "string" || !MODES.has(record.mode)) return null;
  if (record.reset !== undefined && typeof record.reset !== "string") return null;
  if (record.complete !== undefined && typeof record.complete !== "boolean") {
    return null;
  }
  const normalized = {
    v: record.v,
    spec: record.spec,
    sha256: record.sha256,
    mode: record.mode,
    ts: record.ts,
  };
  if (record.reset !== undefined) normalized.reset = record.reset;
  if (record.complete !== undefined) normalized.complete = record.complete;
  return normalized;
}

/**
 * Load one session's shard. Missing/corrupt/version-mismatched files return an
 * empty map so the next touch re-teaches instead of silently staying silent.
 *
 * @param {string} root
 * @param {string} sessionKey
 * @returns {Promise<Map<string, Record<string, unknown>>>}
 */
export async function loadSpecState(root, sessionKey) {
  const path = specStatePath(root, sessionKey);
  if (path === null) return new Map();
  let parsed;
  try {
    parsed = JSON.parse(await readFile(path, "utf8"));
  } catch {
    return new Map();
  }
  if (
    parsed === null ||
    typeof parsed !== "object" ||
    Array.isArray(parsed) ||
    parsed.version !== SPEC_STATE_VERSION ||
    !Array.isArray(parsed.records)
  ) {
    return new Map();
  }
  const store = new Map();
  for (const value of parsed.records) {
    const record = normalizeSpecRecord(value);
    if (record !== null) store.set(record.spec, record);
  }
  return store;
}

/**
 * Persist one session's shard atomically. Returns false (without throwing) when
 * the project is read-only or the write fails; the caller keeps its in-memory
 * map and the next touch re-teaches on a future process.
 *
 * @param {string} root
 * @param {string} sessionKey
 * @param {Map<string, Record<string, unknown>>} store
 * @returns {Promise<boolean>}
 */
export async function saveSpecState(root, sessionKey, store) {
  const path = specStatePath(root, sessionKey);
  if (path === null) return false;
  const records = [];
  for (const value of store.values()) {
    const record = normalizeSpecRecord(value);
    if (record !== null) records.push(record);
  }
  if (records.length === 0) {
    await clearSpecState(root, sessionKey);
    return true;
  }
  const temp = `${path}.${process.pid}.${Date.now()}.tmp`;
  try {
    await mkdir(dirname(path), { recursive: true });
    await writeFile(
      temp,
      `${JSON.stringify({
        version: SPEC_STATE_VERSION,
        updatedAt: new Date().toISOString(),
        records,
      }, null, 2)}\n`,
      "utf8",
    );
    await rename(temp, path);
    return true;
  } catch {
    try {
      await rm(temp, { force: true });
    } catch {
      // Best-effort cleanup; the rename may already have consumed the temp file.
    }
    return false;
  }
}

/**
 * Remove one session's shard (compaction/clear, or an empty store).
 *
 * @param {string} root
 * @param {string} sessionKey
 * @returns {Promise<void>}
 */
export async function clearSpecState(root, sessionKey) {
  const path = specStatePath(root, sessionKey);
  if (path === null) return;
  try {
    await rm(path, { force: true });
  } catch {
    // Advisory state; a failed delete must not break the tool call.
  }
}
