/**
 * Deterministic spec glob translation and repo-relative normalisation.
 *
 * This mirrors the grammar Trellis's `common/spec_match.py` already documents:
 * `*` never crosses `/`, `?` matches one character within a segment, `**` as a
 * whole segment spans zero or more segments, a trailing `/` is sugar for
 * `/**`, and an embedded `**` degrades to `*` because the segment translator
 * treats every `*` the same.
 *
 * The module is pure: no filesystem access, so every rule is unit-testable.
 *
 * @module dsh-trellis/spec-glob
 */
import { isAbsolute, relative, resolve, sep } from "node:path";

// eslint-disable-next-line no-control-regex
const CONTROL_RE = /[\x00-\x1f\x7f]/;

/** macOS and Windows filesystems are case-insensitive by default. */
const CASE_INSENSITIVE = process.platform === "darwin" || process.platform === "win32";

/**
 * Return an error message for an unsafe/meaningless glob, or null when valid.
 * Deny-list, not allow-list: `@scope`, `[slug]`, `(marketing)` and non-ASCII
 * directory names are all legal in real repositories.
 * @param {string} glob
 * @returns {string | null}
 */
export function validateGlob(glob) {
  if (typeof glob !== "string" || glob === "") return "empty glob";
  if (glob.startsWith("/")) return "absolute paths are not allowed";
  if (glob.split("/").includes("..")) return "'..' segments are not allowed";
  if (glob.includes("\\")) return "backslashes are not allowed";
  if (CONTROL_RE.test(glob)) return "contains control characters";
  return null;
}

/**
 * Escape one character for a regular expression that must not match `/`.
 * @param {string} char
 * @returns {string}
 */
function escapeLiteral(char) {
  return /[.*+?^${}()|[\]\\]/.test(char) ? `\\${char}` : char;
}

/**
 * Translate a validated glob into a full-match regular expression.
 * @param {string} glob
 * @returns {RegExp}
 */
export function globToRegex(glob) {
  const source = glob.endsWith("/") ? `${glob}**` : glob;
  const segments = source.split("/");
  const parts = [];
  for (let index = 0; index < segments.length; index += 1) {
    const segment = segments[index];
    const isLast = index === segments.length - 1;
    if (segment === "**") {
      parts.push(isLast ? ".*" : "(?:[^/]+/)*");
      continue;
    }
    let piece = "";
    for (const char of segment) {
      if (char === "*") piece += "[^/]*";
      else if (char === "?") piece += "[^/]";
      else piece += escapeLiteral(char);
    }
    parts.push(isLast ? piece : `${piece}/`);
  }
  return new RegExp(`^${parts.join("")}$`, CASE_INSENSITIVE ? "i" : "");
}

/**
 * Canonical repo-relative POSIX path, or null when the file sits outside the
 * repository. Relative inputs are taken as repo-relative (matching Trellis's
 * Python helper), so tool calls that pass a relative `file_path` still match.
 * @param {string} root - absolute repository root.
 * @param {string} filePath - absolute or repo-relative path.
 * @returns {string | null}
 */
export function normalizeRepoRelative(root, filePath) {
  if (typeof filePath !== "string" || filePath.trim() === "") return null;
  const rootResolved = resolve(root);
  const candidate = isAbsolute(filePath)
    ? resolve(filePath)
    : resolve(rootResolved, filePath.replace(/\\/g, "/"));
  const rel = relative(rootResolved, candidate);
  if (rel === "" || rel === ".") return null;
  if (rel === ".." || rel.startsWith(`..${sep}`) || isAbsolute(rel)) return null;
  return rel.split(sep).join("/").normalize("NFC");
}

/**
 * Specificity key used to order matches before the payload budget is spent.
 * Exact matches and narrow scopes outrank broad tree globs; the spec path is
 * the deterministic tie-break.
 * @param {string} glob
 * @returns {[number, number, number, number]}
 */
export function specificityRank(glob) {
  const scored = glob.endsWith("/") ? `${glob}**` : glob;
  const wildcards = (scored.match(/[*?]/g) ?? []).length;
  const segments = scored.split("/");
  const literalSegments = segments.filter(
    (segment) => !segment.includes("*") && !segment.includes("?"),
  ).length;
  return [
    wildcards === 0 ? 0 : 1,
    -literalSegments,
    wildcards,
    -(scored.length - wildcards),
  ];
}

/**
 * Lexicographic comparison of two specificity tuples.
 * @param {[number, number, number, number]} left
 * @param {[number, number, number, number]} right
 * @returns {number}
 */
export function compareSpecificity(left, right) {
  for (let index = 0; index < left.length; index += 1) {
    if (left[index] !== right[index]) return left[index] - right[index];
  }
  return 0;
}
