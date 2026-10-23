/**
 * Host-side upstream lookup for the settings page.
 *
 * GitHub's Atom feeds (`commits.atom`, `releases.atom`) carry the same commit
 * and release facts as the REST API without its unauthenticated quota, but
 * they do **not** send CORS headers, so a browser cannot read them directly.
 * The Host can: Node's fetch has no origin restriction. This module performs
 * the fetch here and exposes one same-origin JSON route to the client.
 *
 * Only two shapes are ever fetched, and both are derived from validated input
 * rather than taken from the request:
 *
 * - `https://github.com/<owner>/<repo>/commits.atom` (plus `releases.atom`),
 * - `https://registry.npmjs.org/-/package/<name>/dist-tags`.
 *
 * That keeps the route from becoming an arbitrary-URL proxy.
 *
 * @module dsh-trellis/upstream
 */

import { probeLocalVersions } from "./local-version.js";

export const ROUTE_PATH = "/dsh-trellis/version-check";
/** The feeds are small; refuse anything that is not. */
export const MAX_FEED_CHARS = 512 * 1024;

const REPO_RE = /^https?:\/\/(?:www\.)?github\.com\/([A-Za-z0-9_.-]+)\/([A-Za-z0-9_.-]+?)(?:\.git)?\/?$/;
const PACKAGE_RE = /^(@[a-z0-9-_.]+\/)?[a-z0-9-_.]+$/i;

/** Error carrying the HTTP status the route should answer with. */
export class UpstreamError extends Error {
  constructor(message, status = 502) {
    super(message);
    this.name = "UpstreamError";
    this.status = status;
  }
}

/**
 * Validate a GitHub repository URL (a full github.com URL, `.git` optional).
 * @param {unknown} input
 * @returns {{owner: string, repo: string} | null}
 */
export function parseRepoUrl(input) {
  if (typeof input !== "string") return null;
  const match = REPO_RE.exec(input.trim());
  if (match === null) return null;
  const [, owner, repo] = match;
  // Paths that are not repositories.
  if (["orgs", "users", "topics", "settings"].includes(owner)) return null;
  if (repo === "") return null;
  return { owner, repo };
}

/**
 * Validate an npm package name.
 * @param {unknown} input
 * @returns {string | null}
 */
export function parsePackageName(input) {
  if (typeof input !== "string") return null;
  const text = input.trim();
  return PACKAGE_RE.test(text) ? text : null;
}

/**
 * Decode the XML entities GitHub's feeds actually use.
 * @param {string} text
 * @returns {string}
 */
export function decodeXml(text) {
  return String(text)
    .replace(/&#(\d+);/g, (_match, code) => String.fromCodePoint(Number(code)))
    .replace(/&#x([0-9a-f]+);/gi, (_match, code) => String.fromCodePoint(Number.parseInt(code, 16)))
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, "\"")
    .replace(/&apos;/g, "'")
    .replace(/&amp;/g, "&");
}

/**
 * Parse the first entry of a `commits.atom` feed.
 * @param {string} xml
 * @returns {{sha: string, shortSha: string, date: string | null, message: string,
 *   url: string} | null}
 */
export function parseCommitFeed(xml) {
  const entry = /<entry>([\s\S]*?)<\/entry>/.exec(String(xml))?.[1];
  if (entry === undefined) return null;
  const sha = /Grit::Commit\/([0-9a-f]{7,40})/.exec(entry)?.[1]
    ?? /\/commit\/([0-9a-f]{7,40})/.exec(entry)?.[1];
  if (sha === undefined) return null;
  const title = /<title>([\s\S]*?)<\/title>/.exec(entry)?.[1];
  const date = /<updated>([^<]+)<\/updated>/.exec(entry)?.[1] ?? null;
  const link = /<link[^>]*href="([^"]*\/commit\/[0-9a-f]+)"/.exec(entry)?.[1];
  return {
    sha,
    shortSha: sha.slice(0, 7),
    date,
    message: title === undefined
      ? ""
      : decodeXml(title).replace(/\s+/g, " ").trim().slice(0, 120),
    url: link === undefined
      ? `https://github.com/${sha}`
      : decodeXml(link),
  };
}

/**
 * Parse the first entry of a `releases.atom` feed.
 * @param {string} xml
 * @returns {{tag: string, date: string | null, url: string} | null}
 */
export function parseReleaseFeed(xml) {
  const entry = /<entry>([\s\S]*?)<\/entry>/.exec(String(xml))?.[1];
  if (entry === undefined) return null;
  const url = /<link[^>]*href="([^"]*\/releases\/tag\/[^"]+)"/.exec(entry)?.[1];
  const match = url === undefined ? null : /\/releases\/tag\/([^/?#"]+)/.exec(url);
  if (match === null) return null;
  const date = /<updated>([^<]+)<\/updated>/.exec(entry)?.[1] ?? null;
  return {
    tag: decodeURIComponent(decodeXml(match[1])),
    date,
    url: decodeXml(url),
  };
}

/**
 * Fetch one upstream URL as text, bounded by both a timeout and a size cap.
 * @param {object} options
 * @param {string} options.url
 * @param {typeof fetch} [options.fetchImpl]
 * @param {number} [options.timeoutMs]
 * @returns {Promise<string>}
 */
export async function fetchText({ url, fetchImpl = globalThis.fetch, timeoutMs = 10_000, accept = "application/atom+xml, application/xml;q=0.9, */*;q=0.1" }) {
  if (typeof fetchImpl !== "function") throw new UpstreamError("fetch is not available");
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetchImpl(url, {
      headers: {
        accept,
        "user-agent": "dsh-trellis",
      },
      signal: controller.signal,
    });
    if (!response.ok) {
      throw new UpstreamError(`GET ${url} returned ${response.status}`, response.status);
    }
    const text = await response.text();
    if (text.length > MAX_FEED_CHARS) {
      throw new UpstreamError(`GET ${url} returned an oversized feed`);
    }
    return text;
  } catch (error) {
    if (error instanceof UpstreamError) throw error;
    if (controller.signal.aborted || error?.name === "AbortError") {
      throw new UpstreamError(
        `GitHub request timed out after ${timeoutMs} ms`,
        504,
      );
    }
    throw new UpstreamError(
      `GitHub request failed: ${error?.message ?? String(error)}`,
      502,
    );
  } finally {
    clearTimeout(timer);
  }
}

/**
 * Fetch and parse one GitHub REST JSON document.
 * @param {object} options
 * @param {string} options.url
 * @param {typeof fetch} [options.fetchImpl]
 * @param {number} [options.timeoutMs]
 * @returns {Promise<any>}
 */
export async function fetchGithubJson({ url, fetchImpl, timeoutMs }) {
  const text = await fetchText({
    url,
    fetchImpl,
    timeoutMs,
    accept: "application/vnd.github+json, application/json;q=0.9, */*;q=0.1",
  });
  try {
    return JSON.parse(text);
  } catch {
    throw new UpstreamError(`GET ${url} returned invalid JSON`);
  }
}

/**
 * Latest commit from the repository's Atom feed, falling back to GitHub's
 * REST API when the feed is slow or blocked.
 *
 * The Atom feed has no unauthenticated quota but is not always reachable from
 * every network; the REST fallback is limited by GitHub's public quota and is
 * therefore only contacted after the feed fails.
 *
 * @param {object} options
 * @param {{owner: string, repo: string}} options.repo
 * @param {typeof fetch} [options.fetchImpl]
 * @param {number} [options.timeoutMs]
 * @returns {Promise<{sha: string, shortSha: string, date: string | null,
 *   message: string, url: string}>}
 */
export async function fetchCommitFeed({ repo, fetchImpl, timeoutMs }) {
  try {
    const xml = await fetchText({
      url: `https://github.com/${repo.owner}/${repo.repo}/commits.atom`,
      fetchImpl,
      timeoutMs,
    });
    const commit = parseCommitFeed(xml);
    if (commit === null) throw new UpstreamError(`could not parse ${repo.owner}/${repo.repo} commits feed`);
    return commit;
  } catch (feedError) {
    try {
      const payload = await fetchGithubJson({
        url: `https://api.github.com/repos/${repo.owner}/${repo.repo}/commits?per_page=1`,
        fetchImpl,
        timeoutMs,
      });
      const first = Array.isArray(payload) ? payload[0] : null;
      const sha = typeof first?.sha === "string" ? first.sha : "";
      if (sha === "") throw new UpstreamError("REST commit response had no sha");
      const message = typeof first?.commit?.message === "string"
        ? first.commit.message.split(/\r?\n/)[0].trim().slice(0, 120)
        : "";
      const date = typeof first?.commit?.author?.date === "string"
        ? first.commit.author.date
        : null;
      return {
        sha,
        shortSha: sha.slice(0, 7),
        date,
        message,
        url: typeof first?.html_url === "string"
          ? first.html_url
          : `https://github.com/${repo.owner}/${repo.repo}/commit/${sha}`,
      };
    } catch (apiError) {
      throw new UpstreamError(
        `commits feed failed (${feedError?.message ?? feedError}); REST fallback failed (${apiError?.message ?? apiError})`,
        502,
      );
    }
  }
}

/**
 * Latest release from the repository's Atom feed, falling back to GitHub's REST
 * API. A repository without releases is a valid null; a failed feed is not.
 *
 * @param {object} options
 * @param {{owner: string, repo: string}} options.repo
 * @param {typeof fetch} [options.fetchImpl]
 * @param {number} [options.timeoutMs]
 * @returns {Promise<{tag: string, date: string | null, url: string} | null>}
 */
export async function fetchReleaseFeed({ repo, fetchImpl, timeoutMs }) {
  try {
    const xml = await fetchText({
      url: `https://github.com/${repo.owner}/${repo.repo}/releases.atom`,
      fetchImpl,
      timeoutMs,
    });
    return parseReleaseFeed(xml);
  } catch (feedError) {
    try {
      const payload = await fetchGithubJson({
        url: `https://api.github.com/repos/${repo.owner}/${repo.repo}/releases?per_page=1`,
        fetchImpl,
        timeoutMs,
      });
      const first = Array.isArray(payload) ? payload[0] : null;
      const tag = typeof first?.tag_name === "string" ? first.tag_name : "";
      if (tag === "") return null;
      return {
        tag,
        date: typeof first.published_at === "string" ? first.published_at : null,
        url: typeof first.html_url === "string"
          ? first.html_url
          : `https://github.com/${repo.owner}/${repo.repo}/releases/tag/${encodeURIComponent(tag)}`,
      };
    } catch (apiError) {
      if (apiError instanceof UpstreamError && apiError.status === 404) return null;
      throw new UpstreamError(
        `releases feed failed (${feedError?.message ?? feedError}); REST fallback failed (${apiError?.message ?? apiError})`,
        502,
      );
    }
  }
}

/**
 * Published dist-tags, the data `npm view <pkg> dist-tags` prints.
 * @param {object} options
 * @param {string} options.name
 * @param {typeof fetch} [options.fetchImpl]
 * @param {number} [options.timeoutMs]
 * @returns {Promise<Record<string, string>>}
 */
export async function fetchNpmDistTags({ name, fetchImpl = globalThis.fetch, timeoutMs = 10_000 }) {
  if (typeof fetchImpl !== "function") throw new UpstreamError("fetch is not available");
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetchImpl(
      `https://registry.npmjs.org/-/package/${name.replace("/", "%2F")}/dist-tags`,
      { headers: { accept: "application/json" }, signal: controller.signal },
    );
    if (!response.ok) {
      throw new UpstreamError(`npm registry returned ${response.status} for ${name}`);
    }
    const payload = await response.json();
    const tags = {};
    for (const [tag, version] of Object.entries(payload ?? {})) {
      if (typeof version === "string") tags[tag] = version;
    }
    if (Object.keys(tags).length === 0) {
      throw new UpstreamError(`npm registry returned no dist-tags for ${name}`);
    }
    return tags;
  } catch (error) {
    if (error instanceof UpstreamError) throw error;
    if (controller.signal.aborted || error?.name === "AbortError") {
      throw new UpstreamError(
        `npm registry request timed out after ${timeoutMs} ms`,
        504,
      );
    }
    throw new UpstreamError(
      `npm registry request failed: ${error?.message ?? String(error)}`,
      502,
    );
  } finally {
    clearTimeout(timer);
  }
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
 * Build the `/dsh-trellis/version-check` handler.
 *
 * The request selects a source and passes the configured value; the upstream
 * URL is always constructed here from the validated value, never taken
 * verbatim from the request.
 *
 * @param {{fetchImpl?: typeof fetch, timeoutMs?: number, probeImpl?: typeof probeLocalVersions, probeTimeoutMs?: number}} [options]
 * @returns {(req: import("node:http").IncomingMessage, res: import("node:http").ServerResponse) => Promise<void>}
 */
export function createVersionCheckHandler({
  fetchImpl,
  timeoutMs,
  probeImpl = probeLocalVersions,
  probeTimeoutMs,
} = {}) {
  return async (req, res) => {
    try {
      if (req.method !== "GET" && req.method !== "HEAD") {
        sendJson(res, 405, { ok: false, error: "method not allowed" });
        return;
      }
      // Browser requests carry this header; a cross-site page must not be able
      // to drive the Host's outbound lookup.
      const site = req.headers?.["sec-fetch-site"];
      if (typeof site === "string" && site !== "same-origin" && site !== "none") {
        sendJson(res, 403, { ok: false, error: "cross-site request refused" });
        return;
      }
      const url = new URL(req.url ?? "", "http://localhost");
      const source = url.searchParams.get("source");
      if (source === "local") {
        // Fixed `dsh --version` / `trellis -v` probes; nothing from the request
        // selects a command. Failures are per probe and reported, not thrown.
        const { versions, errors } = await probeImpl({ timeoutMs: probeTimeoutMs });
        sendJson(res, 200, { ok: true, local: versions, errors });
        return;
      }
      if (source === "plugin") {
        const repo = parseRepoUrl(url.searchParams.get("url") ?? "");
        if (repo === null) {
          sendJson(res, 400, { ok: false, error: "unrecognized GitHub repository URL" });
          return;
        }
        // A slow commits feed must not discard an otherwise usable release
        // feed (or vice versa). The browser renders partial results and keeps
        // the previous baseline; a raw AbortError never reaches the UI.
        const [commitResult, releaseResult] = await Promise.allSettled([
          fetchCommitFeed({ repo, fetchImpl, timeoutMs }),
          fetchReleaseFeed({ repo, fetchImpl, timeoutMs }),
        ]);
        const errors = [];
        const commit = commitResult.status === "fulfilled" ? commitResult.value : null;
        if (commitResult.status === "rejected") {
          errors.push({
            feed: "commits",
            message: commitResult.reason?.message ?? String(commitResult.reason),
          });
        }
        const release = releaseResult.status === "fulfilled" ? releaseResult.value : null;
        if (releaseResult.status === "rejected") {
          errors.push({
            feed: "releases",
            message: releaseResult.reason?.message ?? String(releaseResult.reason),
          });
        }
        sendJson(res, 200, { ok: true, commit, release, errors });
        return;
      }
      if (source === "npm") {
        const name = parsePackageName(url.searchParams.get("name") ?? "");
        if (name === null) {
          sendJson(res, 400, { ok: false, error: "unrecognized npm package name" });
          return;
        }
        const tags = await fetchNpmDistTags({ name, fetchImpl, timeoutMs });
        sendJson(res, 200, { ok: true, tags });
        return;
      }
      sendJson(res, 400, { ok: false, error: "unknown source" });
    } catch (error) {
      const status = error instanceof UpstreamError ? error.status : 500;
      sendJson(res, status, { ok: false, error: error?.message ?? String(error) });
    }
  };
}
