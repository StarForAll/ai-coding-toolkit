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
 * <pkg> dist-tags` prints). The npm rows also compare the installed CLIs
 * (`dsh --version`, `trellis -v`, probed by the Host) with the channel that
 * matches the local version: DSH always against `latest`, Trellis against
 * `beta` / `rc` when the local version is on that channel, otherwise `latest`.
 *
 * @module dsh-trellis/client/version-check
 */

export const ROUTE_PATH = "/dsh-trellis/version-check";
export const LAST_CHECK_KEY = "dsh-trellis:version-check:last";
export const SEEN_PREFIX = "dsh-trellis:version-check:";
/**
 * Acknowledged upstream snapshot ("checked, no merge needed") for one source.
 * This is the manually set baseline: it suppresses the commit hint and the
 * release badge until upstream moves past it.
 */
export const ACK_PREFIX = "dsh-trellis:version-check:ack:";

/** Upstream sources, in display order. The local CLI probe is not a source row. */
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

/** Same-origin URL for the local CLI probe. */
export function localRouteUrl() {
  return `${ROUTE_PATH}?source=local`;
}

/**
 * Ask the Host for the installed CLI versions.
 *
 * The Host runs fixed `dsh --version` / `trellis -v` commands; a failed probe is
 * reported per source and never rejects the whole check.
 *
 * @param {object} [options]
 * @param {typeof fetch} [options.fetchImpl]
 * @returns {Promise<{versions: Record<string, string>, errors: Array<{id: string, message: string}>}>}
 */
export async function requestLocalVersions({ fetchImpl = globalThis.fetch } = {}) {
  if (typeof fetchImpl !== "function") throw new Error("fetch is not available");
  const response = await fetchImpl(localRouteUrl(), {
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
  const probed = payload.local !== null && typeof payload.local === "object" && !Array.isArray(payload.local)
    ? payload.local
    : {};
  const versions = {};
  for (const id of ["dsh", "trellis"]) {
    if (typeof probed[id] === "string" && probed[id] !== "") versions[id] = probed[id];
  }
  return { versions, errors: Array.isArray(payload.errors) ? payload.errors : [] };
}

/**
 * Dist-tag channel to compare for a local Trellis version.
 *
 * A stable local version compares against `latest`; a local `-beta.N` / `-rc.N`
 * version compares against that same channel instead of a stable release it has
 * already moved past. Any other prerelease falls back to `latest`.
 *
 * @param {string | null | undefined} version
 * @returns {"latest" | "beta" | "rc"}
 */
export function trellisTagChannel(version) {
  const text = String(version ?? "").trim().replace(/^v/i, "");
  if (/^\d+\.\d+\.\d+-beta(?:[-.]\d+)?$/i.test(text)) return "beta";
  if (/^\d+\.\d+\.\d+-rc(?:[-.]\d+)?$/i.test(text)) return "rc";
  return "latest";
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
 * Read the acknowledged snapshot for one source.
 *
 * A corrupt record is treated as "no acknowledgement" instead of throwing: the
 * monitor must keep reporting rather than fail because one stored value is bad.
 *
 * @param {{getItem(key: string): string | null}} storage
 * @param {string} id - source id.
 * @returns {{sha: string | null, tag: string | null, signature: string | null} | undefined}
 */
export function readAck(storage, id) {
  let raw;
  try {
    raw = storage.getItem(`${ACK_PREFIX}${id}`);
  } catch {
    return undefined;
  }
  if (raw === null || raw === undefined) return undefined;
  let parsed;
  try {
    parsed = JSON.parse(raw);
  } catch {
    return undefined;
  }
  if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) return undefined;
  const sha = typeof parsed.sha === "string" && parsed.sha !== "" ? parsed.sha : null;
  const tag = typeof parsed.tag === "string" && parsed.tag !== "" ? parsed.tag : null;
  const signature = typeof parsed.signature === "string" && parsed.signature !== ""
    ? parsed.signature
    : null;
  if (sha === null && tag === null && signature === null) return undefined;
  return { sha, tag, signature };
}

/**
 * Record that the current upstream snapshot was reviewed and needs no merge.
 *
 * @param {{setItem(key: string, value: string): void}} storage
 * @param {string} id - source id.
 * @param {{sha?: string | null, tag?: string | null, signature?: string | null}} snapshot
 */
export function writeAck(storage, id, { sha, tag, signature }) {
  const record = {
    sha: typeof sha === "string" && sha !== "" ? sha : null,
    tag: typeof tag === "string" && tag !== "" ? tag : null,
    signature: typeof signature === "string" && signature !== "" ? signature : null,
  };
  storage.setItem(`${ACK_PREFIX}${id}`, JSON.stringify(record));
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

/** Split a release tag into numeric core and prerelease identifiers. */
function parseReleaseTag(value) {
  const text = String(value ?? "").trim().replace(/^v/i, "");
  const dash = text.indexOf("-");
  const core = dash === -1 ? text : text.slice(0, dash);
  const pre = dash === -1 ? [] : text.slice(dash + 1).split(".");
  const nums = core.split(".").map((part) => {
    const parsed = Number.parseInt(part, 10);
    return Number.isFinite(parsed) && parsed >= 0 ? parsed : 0;
  });
  return { nums, pre };
}

/** Semver ordering for the prerelease suffix; an absent suffix is the stable one. */
function comparePrerelease(left, right) {
  if (left.length === 0 && right.length === 0) return 0;
  if (left.length === 0) return 1;
  if (right.length === 0) return -1;
  for (let index = 0; index < Math.max(left.length, right.length); index += 1) {
    const a = left[index];
    const b = right[index];
    if (a === undefined) return -1;
    if (b === undefined) return 1;
    const aNumeric = /^\d+$/.test(a);
    const bNumeric = /^\d+$/.test(b);
    if (aNumeric && bNumeric) {
      const diff = Number(a) - Number(b);
      if (diff !== 0) return diff > 0 ? 1 : -1;
    } else if (aNumeric !== bNumeric) {
      return aNumeric ? -1 : 1;
    } else if (a !== b) {
      return a.localeCompare(b) > 0 ? 1 : -1;
    }
  }
  return 0;
}

/**
 * Order two upstream release tags, keeping prerelease precedence.
 *
 * `compareVersions` drops prerelease suffixes (conservative for "a newer
 * release exists"), but an acknowledged baseline needs the finer rule: after
 * acking `0.2.0-rc.1`, the stable `0.2.0` is still newer, while acking `0.2.0`
 * must not be re-flagged by a later `0.2.0-rc.2` tag.
 *
 * @param {string} left
 * @param {string} right
 * @returns {-1 | 0 | 1}
 */
export function compareReleaseTags(left, right) {
  const a = parseReleaseTag(left);
  const b = parseReleaseTag(right);
  for (let index = 0; index < Math.max(a.nums.length, b.nums.length); index += 1) {
    const diff = (a.nums[index] ?? 0) - (b.nums[index] ?? 0);
    if (diff !== 0) return diff > 0 ? 1 : -1;
  }
  return comparePrerelease(a.pre, b.pre);
}

/**
 * True when `candidate` is a later upstream release tag than `baseline`.
 * @param {string} candidate
 * @param {string} baseline
 * @returns {boolean}
 */
export function isNewerReleaseTag(candidate, baseline) {
  return compareReleaseTags(candidate, baseline) > 0;
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
 * @param {Record<string, string>} [options.localVersions] - pre-resolved local CLI versions; probing is skipped when provided.
 * @param {typeof requestLocalVersions} [options.localProbe] - Host probe implementation.
 * @returns {Promise<{checkedAt: number, results: Array<object>, local: {versions: Record<string, string>, errors: Array<object>}}>}
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
  localVersions,
  localProbe = requestLocalVersions,
}) {
  const results = [];
  // The npm rows compare the installed CLIs with the published channel. Probe
  // once per check, only when a package source is configured and the switch is
  // on; a failed probe degrades to "local version unknown", never to a guess.
  const npmConfigured = SOURCES.some((source) => source.kind === "npm"
    && String(config?.[source.field] ?? "").trim() !== "");
  let probedLocal = localVersions;
  let localErrors = [];
  if (probedLocal === undefined && npmConfigured && config?.versionCheckLocalProbe !== false) {
    try {
      const probed = await localProbe({ fetchImpl });
      probedLocal = probed.versions;
      localErrors = probed.errors;
    } catch (error) {
      probedLocal = {};
      localErrors = [{ id: "local", message: error?.message ?? String(error) }];
    }
  }
  const local = probedLocal ?? {};
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
        // DSH is compared against the published `latest`; Trellis follows the
        // channel its local version is already on (beta / rc), else `latest`.
        const channel = source.id === "trellis" ? trellisTagChannel(local[source.id]) : "latest";
        const targetVersion = typeof tags[channel] === "string" && tags[channel] !== ""
          ? tags[channel]
          : null;
        const installed = typeof local[source.id] === "string" && local[source.id] !== ""
          ? local[source.id]
          : null;
        const ack = readAck(storage, source.id);
        const acknowledged = ack !== undefined && ack.signature !== null
          && ack.signature === signature;
        const firstSeen = previous === null;
        const isNew = !firstSeen && previous !== signature && !acknowledged;
        // Ack only raises the baseline; a recorded tag below the installed
        // version must not resurrect releases this machine already superseded.
        let baseline = installed;
        if (ack?.tag !== null && ack?.tag !== undefined
          && (baseline === null || isNewerReleaseTag(ack.tag, baseline))) {
          baseline = ack.tag;
        }
        const updateAvailable = targetVersion !== null && baseline !== null
          && isNewerReleaseTag(targetVersion, baseline);
        storage.setItem(seenKey, signature);
        results.push({
          ...source,
          value,
          url: `https://www.npmjs.com/package/${value}`,
          ok: true,
          npm: { name: value, tags },
          signature,
          channel,
          targetVersion,
          localVersion: installed,
          updateAvailable,
          acknowledged,
          ack,
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
      const ack = readAck(storage, source.id);
      // A manual acknowledgement replaces the compiled-in version as the
      // release baseline, but never lowers it: acknowledging an older release
      // must not resurrect versions this local build already supersedes.
      let baselineTag = ack?.tag ?? null;
      if (baselineTag !== null && localVersion !== undefined
        && isNewerReleaseTag(localVersion, baselineTag)) {
        baselineTag = localVersion;
      }
      let updateAvailable = false;
      if (release !== null) {
        updateAvailable = baselineTag !== null
          ? isNewerReleaseTag(release.tag, baselineTag)
          : localVersion !== undefined && compareVersions(release.tag, localVersion) > 0;
      }
      const firstSeen = previous === null;
      // The acknowledged snapshot is reviewed already: it must not re-notify.
      const acknowledged = ack !== undefined && ack.sha !== null && ack.sha === commit.sha;
      const isNew = !firstSeen && previous !== commit.sha && !acknowledged;
      storage.setItem(seenKey, commit.sha);
      results.push({
        ...source,
        value,
        url: release?.url ?? commit.url,
        ok: true,
        latest: commit,
        latestRelease: release,
        updateAvailable,
        acknowledged,
        ack,
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
  return { checkedAt: now, results, local: { versions: local, errors: localErrors } };
}
