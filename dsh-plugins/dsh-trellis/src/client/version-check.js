/**
 * Upstream version monitoring for the settings page — client half.
 *
 * The Host owns the outbound request (`lib/upstream.js`): GitHub's Atom feeds
 * have no CORS headers and the REST API's unauthenticated quota is what made a
 * browser check return 403. The client calls one same-origin route, compares
 * what it receives with what this browser recorded last time, and raises the
 * desktop notification.
 *
 * Three external dependencies can require updating this plugin or break it:
 * the plugin's upstream fork (watched by commit), and the Trellis and DSH npm
 * packages (watched by their published dist-tags — the same data `npm view
 * <pkg> dist-tags` prints).
 *
 * @module dsh-trellis/client/version-check
 */

export const ROUTE_PATH = "/dsh-trellis/version-check";
export const LAST_CHECK_KEY = "dsh-trellis:version-check:last";
export const SEEN_PREFIX = "dsh-trellis:version-check:";

/** Upstream sources, in display order. */
export const SOURCES = Object.freeze([
  {
    id: "plugin",
    kind: "commits",
    labelKey: "monitor.source.plugin",
    field: "versionCheckPluginRepo",
    defaultUrl: "https://github.com/SajoLuo/dsh-trellis",
  },
  {
    id: "trellis",
    kind: "npm",
    labelKey: "monitor.source.trellis",
    field: "versionCheckTrellisPackage",
    defaultUrl: "@mindfoldhq/trellis",
  },
  {
    id: "dsh",
    kind: "npm",
    labelKey: "monitor.source.dsh",
    field: "versionCheckDshPackage",
    defaultUrl: "@deepseek-ai/dsh",
  },
]);

/**
 * Same-origin route URL for one source.
 * @param {{id: string, kind: string}} source
 * @param {string} value - configured repository URL or package name.
 * @returns {string}
 */
export function checkRouteUrl(source, value) {
  const params = new URLSearchParams({
    source: source.kind === "npm" ? "npm" : "plugin",
  });
  if (source.kind === "npm") params.set("name", value);
  else params.set("url", value);
  return `${ROUTE_PATH}?${params.toString()}`;
}

/**
 * Ask the Host to look up one source.
 *
 * A failed check rejects with the Host's message so each source can report its
 * own error without taking the others down.
 *
 * @param {object} options
 * @param {{id: string, kind: string}} options.source
 * @param {string} options.value
 * @param {typeof fetch} [options.fetchImpl]
 * @returns {Promise<{commit?: object, release?: object | null, tags?: Record<string, string>}>}
 */
export async function requestUpstream({ source, value, fetchImpl = globalThis.fetch }) {
  if (typeof fetchImpl !== "function") throw new Error("fetch is not available");
  const response = await fetchImpl(checkRouteUrl(source, value), {
    headers: { accept: "application/json" },
  });
  let payload;
  try {
    payload = await response.json();
  } catch {
    throw new Error(`version-check route returned ${response.status}`);
  }
  if (payload?.ok !== true) {
    throw new Error(payload?.error ?? `version-check route returned ${response.status}`);
  }
  return payload;
}

/** In-memory storage used when `localStorage` is unavailable (SSR, tests). */
export function memoryStorage(initial = {}) {
  const map = new Map(Object.entries(initial));
  return {
    getItem: (key) => map.get(key) ?? null,
    setItem: (key, value) => { map.set(key, String(value)); },
    removeItem: (key) => { map.delete(key); },
  };
}

/** `localStorage` when reachable, otherwise a per-process fallback. */
export function defaultStorage() {
  try {
    if (typeof localStorage !== "undefined") {
      const probe = "dsh-trellis:probe";
      localStorage.setItem(probe, "1");
      localStorage.removeItem(probe);
      return localStorage;
    }
  } catch {
    // Private mode / disabled storage: keep the monitor working in memory.
  }
  return memoryStorage();
}

/**
 * True when an automatic check is due.
 * @param {{versionCheck?: boolean, versionCheckIntervalMinutes?: number}} config
 * @param {{getItem(key: string): string | null}} storage
 * @param {number} now - epoch milliseconds.
 * @returns {boolean}
 */
export function isCheckDue(config, storage, now) {
  if (config?.versionCheck === false) return false;
  const minutes = Number(config?.versionCheckIntervalMinutes ?? 1440);
  if (!(minutes > 0)) return false;
  const last = Number(storage.getItem(LAST_CHECK_KEY) ?? 0);
  return !(last > 0 && now - last < minutes * 60_000);
}

/** Browser notification when permitted; returns whether one was shown. */
export function notifyDesktop(title, body, tag) {
  if (typeof Notification === "undefined") return false;
  if (Notification.permission !== "granted") return false;
  try {
    new Notification(title, { body, tag });
    return true;
  } catch {
    return false;
  }
}

/** Ask for notification permission when the browser still allows the prompt. */
export async function requestNotificationPermission() {
  if (typeof Notification === "undefined") return "unsupported";
  if (Notification.permission !== "default") return Notification.permission;
  try {
    return await Notification.requestPermission();
  } catch {
    return "denied";
  }
}

/**
 * Compare two version strings numerically; a missing or non-numeric part is 0.
 * Pre-release suffixes are ignored, which is the conservative direction for a
 * "newer release exists" hint.
 * @param {string} left
 * @param {string} right
 * @returns {number}
 */
export function compareVersions(left, right) {
  const parse = (value) => String(value ?? "")
    .trim()
    .replace(/^v/i, "")
    .split("-")[0]
    .split(".")
    .map((part) => Number.parseInt(part, 10))
    .map((part) => (Number.isFinite(part) && part >= 0 ? part : 0));
  const a = parse(left);
  const b = parse(right);
  for (let index = 0; index < Math.max(a.length, b.length); index += 1) {
    const diff = (a[index] ?? 0) - (b[index] ?? 0);
    if (diff !== 0) return diff;
  }
  return 0;
}

/** Stable identity of a dist-tag map, used to detect any published change. */
export function tagSignature(tags) {
  return Object.entries(tags)
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([tag, version]) => `${tag}=${version}`)
    .join(";");
}

/** One-line tag summary for the UI and notifications. */
export function tagSummary(tags) {
  return Object.entries(tags)
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([tag, version]) => `${tag} ${version}`)
    .join(" · ");
}

/**
 * Check every configured upstream source once.
 *
 * @param {object} options
 * @param {Record<string, unknown>} options.config - settings values (draft or saved).
 * @param {typeof fetch} [options.fetchImpl] - route fetch.
 * @param {ReturnType<typeof defaultStorage>} [options.storage]
 * @param {boolean} [options.notify]
 * @param {(source: {id: string, labelKey: string}) => string} [options.labelOf]
 * @param {typeof notifyDesktop} [options.notifyImpl]
 * @param {number} [options.now]
 * @param {string} [options.localVersion] - used to flag a newer plugin release.
 * @returns {Promise<{checkedAt: number, results: Array<object>}>}
 */
export async function runVersionCheck({
  config,
  fetchImpl = globalThis.fetch,
  storage = defaultStorage(),
  notify = false,
  labelOf = (source) => source.id,
  notifyImpl = notifyDesktop,
  now = Date.now(),
  localVersion,
}) {
  const results = [];
  for (const source of SOURCES) {
    const value = String(config?.[source.field] ?? "").trim();
    if (value === "") {
      results.push({ ...source, value, ok: true, skipped: true });
      continue;
    }
    const seenKey = `${SEEN_PREFIX}${source.id}`;
    const previous = storage.getItem(seenKey);
    try {
      const payload = await requestUpstream({ source, value, fetchImpl });
      if (source.kind === "npm") {
        const tags = payload.tags ?? {};
        const signature = tagSignature(tags);
        const firstSeen = previous === null;
        const isNew = !firstSeen && previous !== signature;
        storage.setItem(seenKey, signature);
        results.push({
          ...source,
          value,
          url: `https://www.npmjs.com/package/${value}`,
          ok: true,
          npm: { name: value, tags },
          isNew,
          firstSeen,
        });
        if (notify && isNew && config?.versionCheckNotify !== false) {
          notifyImpl(
            `Trellis: ${labelOf(source)} 官方版本有变化`,
            tagSummary(tags),
            `dsh-trellis:${source.id}`,
          );
        }
        continue;
      }

      const commit = payload.commit;
      const release = payload.release ?? null;
      const errors = Array.isArray(payload.errors) ? payload.errors : [];
      if (commit === undefined || commit === null || typeof commit.sha !== "string") {
        // The Host keeps the two Atom feeds independent. A commit-feed timeout
        // is a partial answer, not a failed check: show the release (if any)
        // and a retry hint instead of the raw AbortError.
        const detail = errors
          .map((entry) => entry?.message)
          .filter((message) => typeof message === "string" && message !== "")
          .join("; ");
        results.push({
          ...source,
          value,
          ok: true,
          partial: true,
          latestRelease: release,
          errors,
          url: release?.url ?? undefined,
          error: detail || "commit feed unavailable",
        });
        continue;
      }
      const updateAvailable = release !== null && localVersion !== undefined
        ? compareVersions(release.tag, localVersion) > 0
        : false;
      const firstSeen = previous === null;
      const isNew = !firstSeen && previous !== commit.sha;
      storage.setItem(seenKey, commit.sha);
      results.push({
        ...source,
        value,
        url: release?.url ?? commit.url,
        ok: true,
        latest: commit,
        latestRelease: release,
        updateAvailable,
        warnings: errors,
        isNew,
        firstSeen,
      });
      if (notify && isNew && config?.versionCheckNotify !== false) {
        notifyImpl(
          `Trellis: ${labelOf(source)} 上游有新提交`,
          `${commit.shortSha} ${commit.message}`.trim(),
          `dsh-trellis:${source.id}:${commit.sha}`,
        );
      }
    } catch (error) {
      results.push({
        ...source,
        value,
        ok: false,
        error: error?.message ?? String(error),
      });
    }
  }
  storage.setItem(LAST_CHECK_KEY, String(now));
  return { checkedAt: now, results };
}
