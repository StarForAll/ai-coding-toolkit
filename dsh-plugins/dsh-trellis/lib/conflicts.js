/**
 * Detection of another enabled Trellis plugin for the same DSH profile.
 *
 * Two plugins that both inject workflow messages, register `trellis_wait`, and
 * claim the shell's Trellis identity would silently double every message and
 * collide on command/tool names. This copy cannot coexist with another
 * `dsh-trellis*` package, so the Host reports the conflict — as data for the
 * browser, not as a log line nobody reads.
 *
 * The loader entry list is the only honest source: it reflects what is actually
 * loaded, not what a `package.json` declares. The plugin's own entry is
 * identified by `Loader.locate(fiber)` or fiber identity, because a duplicate
 * simply has a different id. When the loader API is unreachable — or does not
 * expose our own entry, so "self" cannot be excluded — the result is
 * `unavailable` / `unverified` rather than a fabricated "no conflict".
 *
 * @module dsh-trellis/conflicts
 */

/** Same-origin route the browser reads the detection result from. */
export const CONFLICTS_ROUTE_PATH = "/dsh-trellis/conflicts";

/**
 * Any plugin whose package name or loader id mentions Trellis.
 *
 * Deliberately broad: a fork or wrapper can be published as `trellis-*`,
 * `@scope/trellis-*`, or something like `my-trellis`, and two Trellis
 * integrations in one profile double every workflow message. The cost is that
 * an unrelated package that happens to carry the word is also reported — the
 * safer direction than missing a real collision.
 */
export const TRELLIS_PLUGIN_RE = /trellis/i;

/**
 * @param {import("@deepseek-ai/cordis").Context} ctx
 * @returns {{status: "checked" | "unverified" | "unavailable",
 *   conflicts: Array<{id: string, name: string}>}}
 */
export function detectTrellisConflicts(ctx) {
  let loader;
  try {
    loader = typeof ctx?.get === "function" ? ctx.get("loader") : ctx?.loader;
  } catch {
    loader = undefined;
  }
  if (loader === undefined || loader === null || typeof loader.entries !== "function") {
    return { status: "unavailable", conflicts: [] };
  }

  const selfFiber = ctx?.fiber;
  // `Loader.locate(fiber)` is the documented owner lookup; the fiber comparison
  // is the fallback for loaders that predate it.
  let selfId;
  try {
    selfId = typeof loader.locate === "function" && selfFiber !== undefined
      ? loader.locate(selfFiber)
      : undefined;
  } catch {
    selfId = undefined;
  }
  const conflicts = [];
  let matches = 0;
  let selfResolved = false;
  for (const entry of loader.entries()) {
    const entryId = String(entry?.options?.id ?? entry?.id ?? "");
    const name = typeof entry?.options?.name === "string"
      ? entry.options.name
      : entryId;
    if (!TRELLIS_PLUGIN_RE.test(name) && !TRELLIS_PLUGIN_RE.test(entryId)) continue;
    matches += 1;
    const isSelf =
      (selfId !== undefined && entry?.id === selfId) ||
      (selfFiber !== undefined && entry?.fiber === selfFiber);
    if (isSelf) {
      selfResolved = true;
      continue;
    }
    if (entry?.disabled === true || entry?.options?.disabled === true) continue;
    conflicts.push({ id: entryId === "" ? name : entryId, name });
  }
  if (matches === 0) {
    // The loader exposed no Trellis entry at all: it is not describing this
    // plugin's tree, so it cannot prove anything either way.
    return { status: "unavailable", conflicts: [] };
  }
  // Without a way to exclude self, the entries cannot be attributed to another
  // plugin; report the uncertainty instead of naming this plugin as a conflict.
  if (!selfResolved) return { status: "unverified", conflicts: [] };
  return { status: "checked", conflicts };
}

/** Write one JSON response; the route owns the whole response lifecycle. */
function sendJson(res, status, payload) {
  const body = JSON.stringify(payload);
  res.writeHead(status, {
    "content-type": "application/json; charset=utf-8",
    "content-length": Buffer.byteLength(body),
    "cache-control": "no-store",
    "x-content-type-options": "nosniff",
  });
  res.end(body);
}

/**
 * Build the `/dsh-trellis/conflicts` handler.
 *
 * Detection runs per request, so a plugin enabled after this page loaded is
 * still seen. The browser decides how to surface the result; the Host no longer
 * writes a log line for it.
 *
 * @param {() => ReturnType<typeof detectTrellisConflicts>} detect
 * @returns {(req: import("node:http").IncomingMessage, res: import("node:http").ServerResponse) => Promise<void>}
 */
export function createConflictsHandler(detect) {
  return async (req, res) => {
    try {
      if (req.method !== "GET" && req.method !== "HEAD") {
        sendJson(res, 405, { ok: false, error: "method not allowed" });
        return;
      }
      const site = req.headers?.["sec-fetch-site"];
      if (typeof site === "string" && site !== "same-origin" && site !== "none") {
        sendJson(res, 403, { ok: false, error: "cross-site request refused" });
        return;
      }
      const result = detect();
      sendJson(res, 200, {
        ok: true,
        status: result.status,
        conflicts: result.conflicts,
      });
    } catch (error) {
      sendJson(res, 500, { ok: false, error: error?.message ?? String(error) });
    }
  };
}
