/**
 * Path-scoped spec index: frontmatter parsing, scanning and matching.
 *
 * A spec is prose that happens to carry a routing hint, so the parser is
 * deliberately tolerant. Only what would make routing wrong is an error: a
 * `paths:` key that is not a list, or a frontmatter block still open when the
 * bounded head read ends. Both skip the file instead of routing on half a
 * block.
 *
 * @module dsh-trellis/spec-index
 */
import { createHash } from "node:crypto";
import { readdir, readFile, stat } from "node:fs/promises";
import { join } from "node:path";
import {
  compareSpecificity,
  globToRegex,
  normalizeRepoRelative,
  specificityRank,
  validateGlob,
} from "./spec-glob.js";

/** Bounded head read for frontmatter scanning, mirrored from Trellis. */
export const HEAD_MAX_BYTES = 16384;
export const HEAD_MAX_LINES = 200;

/** Upper bound on a spec body we are willing to read and hash (10 MiB). */
export const MAX_SPEC_SOURCE_BYTES = 10 * 1024 * 1024;

/** Rebuild the index at most this often even when the directory mtime agrees. */
export const INDEX_TTL_MS = 5000;

const KNOWN_KEYS = new Set(["paths", "name", "description"]);
const KEY_RE = /^([A-Za-z_][A-Za-z0-9_-]*):(.*)$/;
const BLOCK_SCALARS = new Set(["|", ">", "|-", ">-", "|+", ">+"]);

/**
 * Strip an inline YAML comment, respecting quotes.
 * @param {string} value
 * @returns {string}
 */
function stripComment(value) {
  let quote = "";
  for (let index = 0; index < value.length; index += 1) {
    const char = value[index];
    if (quote !== "") {
      if (char === quote) quote = "";
      continue;
    }
    if (char === '"' || char === "'") {
      quote = char;
      continue;
    }
    if (char === "#" && (index === 0 || /\s/.test(value[index - 1]))) {
      return value.slice(0, index);
    }
  }
  return value;
}

/**
 * Remove one layer of matching quotes.
 * @param {string} value
 * @returns {string}
 */
function unquote(value) {
  const trimmed = value.trim();
  if (trimmed.length < 2) return trimmed;
  const first = trimmed[0];
  const last = trimmed[trimmed.length - 1];
  if ((first === '"' && last === '"') || (first === "'" && last === "'")) {
    return trimmed.slice(1, -1);
  }
  return trimmed;
}

/**
 * Split a YAML flow sequence body (`[a, b]`) into unquoted items.
 * @param {string} value
 * @returns {string[]}
 */
function parseFlowSequence(value) {
  const inner = value.slice(1, -1);
  if (inner.trim() === "") return [];
  return inner
    .split(",")
    .map((part) => unquote(stripComment(part)))
    .filter((part) => part !== "");
}

/**
 * Parse the optional frontmatter block from a spec file's head.
 *
 * @param {string} headText - at least the first {@link HEAD_MAX_LINES} lines.
 * @returns {{paths: string[] | null, name: string | null, description: string | null} | null}
 * @throws {Error} on a malformed `paths:` value or an unclosed block.
 */
export function parseSpecFrontmatter(headText) {
  const lines = String(headText ?? "").split(/\r?\n/).slice(0, HEAD_MAX_LINES);
  if (lines.length === 0) return null;
  if (lines[0].replace(/^\uFEFF/, "") !== "---") return null;

  let paths = null;
  let name = null;
  let description = null;
  let pendingKey = null;
  let blockIndent = null;
  let sawKnownKey = false;
  let closed = false;

  for (const line of lines.slice(1)) {
    const stripped = line.trim();
    const indent = line.length - line.trimStart().length;

    if (blockIndent !== null) {
      if (stripped === "" || indent > blockIndent) continue;
      blockIndent = null;
    }
    if (stripped === "---") {
      closed = true;
      break;
    }
    if (stripped === "" || stripped.startsWith("#")) continue;

    if (stripped === "-" || stripped.startsWith("- ")) {
      if (pendingKey === "paths" && paths !== null) {
        const item = unquote(stripComment(stripped.slice(1).trim()));
        paths.push(item);
      }
      continue;
    }

    const keyMatch = KEY_RE.exec(stripped);
    if (keyMatch === null) continue;
    const key = keyMatch[1];
    sawKnownKey ||= KNOWN_KEYS.has(key);
    const rawValue = keyMatch[2].trim();

    if (BLOCK_SCALARS.has(rawValue)) {
      if (key === "paths") throw new Error("'paths' must be a list of globs");
      pendingKey = null;
      blockIndent = indent;
      continue;
    }

    const value = unquote(stripComment(rawValue));
    if (value !== "") {
      pendingKey = null;
      if (key === "paths") {
        if (!(value.startsWith("[") && value.endsWith("]"))) {
          throw new Error("'paths' must be a list of globs");
        }
        paths = parseFlowSequence(value);
      } else if (key === "name") {
        name = value;
      } else if (key === "description") {
        description = value;
      }
    } else {
      pendingKey = key;
      if (key === "paths") paths = [];
    }
  }

  if (!sawKnownKey) return null;
  if (!closed) {
    throw new Error(
      `frontmatter block never closed within the head bound (${HEAD_MAX_BYTES} bytes / ${HEAD_MAX_LINES} lines)`,
    );
  }
  return { paths, name, description };
}

/**
 * Read at most {@link HEAD_MAX_BYTES} of a spec file as UTF-8 text.
 * @param {string} absPath
 * @returns {Promise<string | null>}
 */
async function readHead(absPath) {
  try {
    const buffer = await readFile(absPath);
    if (buffer.length > MAX_SPEC_SOURCE_BYTES) return null;
    return buffer.subarray(0, HEAD_MAX_BYTES).toString("utf8");
  } catch {
    return null;
  }
}

/**
 * Recursively list `*.md` files under a directory, POSIX-separated.
 * @param {string} dir
 * @returns {Promise<string[]>}
 */
async function listMarkdown(dir) {
  try {
    const entries = await readdir(dir, { recursive: true, withFileTypes: true });
    return entries
      .filter((entry) => entry.isFile() && entry.name.endsWith(".md"))
      .map((entry) => join(entry.parentPath ?? entry.path, entry.name));
  } catch {
    return [];
  }
}

/**
 * Build the spec index for a project root.
 * @param {string} root
 * @returns {Promise<{entries: Array<{specRel: string, absPath: string,
 *   description: string | null, globs: string[], patterns: RegExp[]}>}>}
 */
export async function scanSpecIndex(root) {
  const specDir = join(root, ".trellis", "spec");
  const files = await listMarkdown(specDir);
  const entries = [];
  for (const absPath of files.sort()) {
    const rel = normalizeRepoRelative(root, absPath);
    if (rel === null) continue;
    const head = await readHead(absPath);
    if (head === null) continue;
    let frontmatter;
    try {
      frontmatter = parseSpecFrontmatter(head);
    } catch {
      // Malformed routing metadata: skip this spec instead of routing on a
      // half-read block. The index stays usable for every other spec.
      continue;
    }
    if (frontmatter === null || frontmatter.paths === null) continue;
    const globs = [];
    const patterns = [];
    for (const glob of frontmatter.paths) {
      if (validateGlob(glob) !== null) continue;
      globs.push(glob);
      patterns.push(globToRegex(glob));
    }
    if (patterns.length === 0) continue;
    entries.push({
      specRel: rel,
      absPath,
      description: frontmatter.description,
      globs,
      patterns,
    });
  }
  return { entries };
}

/**
 * Load (or reuse) the cached index for a project root.
 *
 * The cache is invalidated by the spec directory's mtime and by an inexpensive
 * TTL, so a newly added or renamed spec directory is picked up without
 * stat-ing every spec file on each tool call.
 *
 * @param {string} root
 * @param {Map<string, {entries: unknown[], builtAt: number, dirMtimeMs: number}>} cache
 * @param {number} now - epoch milliseconds.
 * @returns {Promise<Array<{specRel: string, absPath: string, description: string | null, globs: string[], patterns: RegExp[]}>>}
 */
export async function loadSpecIndex(root, cache, now = Date.now()) {
  const specDir = join(root, ".trellis", "spec");
  let dirMtimeMs = 0;
  try {
    dirMtimeMs = (await stat(specDir)).mtimeMs;
  } catch {
    cache.delete(root);
    return [];
  }
  const hit = cache.get(root);
  if (
    hit !== undefined &&
    hit.dirMtimeMs === dirMtimeMs &&
    now - hit.builtAt < INDEX_TTL_MS
  ) {
    return hit.entries;
  }
  const built = await scanSpecIndex(root);
  cache.set(root, { ...built, builtAt: now, dirMtimeMs });
  return built.entries;
}

/**
 * Return the specs whose globs match a touched file, most specific first.
 *
 * `filePath` may be absolute or repo-relative; a path outside the repository,
 * or a project without `.trellis/spec`, yields an empty list.
 *
 * @param {string} root - absolute repository root.
 * @param {string} filePath - path handed to the tool.
 * @param {Map<string, {entries: unknown[], builtAt: number, dirMtimeMs: number}>} cache
 * @param {number} [now]
 * @returns {Promise<Array<{specRel: string, absPath: string, description: string | null, relPath: string}>>}
 */
export async function matchSpecsForFile(root, filePath, cache, now = Date.now()) {
  const relPath = normalizeRepoRelative(root, filePath);
  if (relPath === null) return [];
  const entries = await loadSpecIndex(root, cache, now);
  const matches = [];
  for (const entry of entries) {
    let matchedGlob = null;
    for (let index = 0; index < entry.patterns.length; index += 1) {
      if (entry.patterns[index].test(relPath)) {
        matchedGlob = entry.globs[index];
        break;
      }
    }
    if (matchedGlob === null) continue;
    matches.push({
      specRel: entry.specRel,
      absPath: entry.absPath,
      description: entry.description,
      relPath,
      rank: specificityRank(matchedGlob),
    });
  }
  matches.sort((left, right) => {
    const byRank = compareSpecificity(left.rank, right.rank);
    return byRank !== 0 ? byRank : left.specRel < right.specRel ? -1 : 1;
  });
  return matches;
}

/**
 * Read a spec body and its content hash.
 * @param {string} absPath
 * @returns {Promise<{body: string, sha256: string} | null>}
 */
export async function readSpecBody(absPath) {
  try {
    const buffer = await readFile(absPath);
    if (buffer.length > MAX_SPEC_SOURCE_BYTES) return null;
    const body = buffer.toString("utf8");
    return { body, sha256: createHash("sha256").update(buffer).digest("hex") };
  } catch {
    return null;
  }
}
