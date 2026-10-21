/**
 * Client half of the Trellis-plugin conflict check.
 *
 * The Host reads its loader entries and serves the result; this module fetches
 * it once per page load and decides how to make it visible. A conflict means
 * both plugins inject the same workflow messages and register overlapping
 * tools, so the user has to act — a log line would not reach them.
 *
 * @module dsh-trellis/client/conflicts
 */

export const CONFLICTS_ROUTE_PATH = "/dsh-trellis/conflicts";

/**
 * Read the Host's conflict result.
 *
 * A missing route (older Host, Electron IPC) degrades to `unavailable`: the
 * client never invents a conflict, and never claims there is none.
 *
 * @param {typeof fetch} [fetchImpl]
 * @returns {Promise<{status: string, conflicts: Array<{id: string, name: string}>}>}
 */
export async function fetchConflicts(fetchImpl = globalThis.fetch) {
  if (typeof fetchImpl !== "function") return { status: "unavailable", conflicts: [] };
  try {
    const response = await fetchImpl(CONFLICTS_ROUTE_PATH, {
      headers: { accept: "application/json" },
    });
    const payload = await response.json();
    if (payload?.ok !== true) return { status: "unavailable", conflicts: [] };
    return {
      status: typeof payload.status === "string" ? payload.status : "unavailable",
      conflicts: Array.isArray(payload.conflicts) ? payload.conflicts : [],
    };
  } catch {
    return { status: "unavailable", conflicts: [] };
  }
}

/** Stable identity of a conflict set, used to notify once per set. */
export function conflictSignature(conflicts) {
  return conflicts
    .map((conflict) => `${conflict.id}:${conflict.name}`)
    .sort()
    .join("|");
}

/** Human-readable one-line list of the conflicting plugins. */
export function conflictSummary(conflicts, separator = "、") {
  return conflicts
    .map((conflict) => `${conflict.name}（${conflict.id}）`)
    .join(separator);
}
