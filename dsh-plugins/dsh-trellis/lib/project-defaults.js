/**
 * Project bootstrap for `dsh.dispatch_mode`.
 *
 * A Trellis project that installs this plugin should start in the same mode the
 * plugin's DSH contract describes: `inline`, the main session implements and
 * checks directly. Rather than asking every user to add the key by hand, the
 * first session step in a project ensures it exists — but this is a
 * configuration migration, not a rewrite:
 *
 *   - only a *missing* `dsh.dispatch_mode` is added; an explicit `auto` (or any
 *     other value) is authoritative and never overwritten;
 *   - the rest of the file — comments, ordering, line endings — is preserved;
 *   - a missing `config.yaml` is left alone (the plugin never invents a Trellis
 *     config), and a read-only project degrades to the normal `auto` fallback
 *     with one warning;
 *   - the write is atomic (temp + rename) and guarded by a directory lock, so
 *     two sessions starting at once cannot append the section twice.
 *
 * The pure text transform (`mergeDshDispatchMode`) is separate from the IO
 * policy (`createDshDefaultsEnsurer`) so the interesting cases are unit-testable
 * without touching a real project.
 *
 * @module dsh-trellis/project-defaults
 */
import { join } from "node:path";
import { nodeFs } from "./node-fs.js";

/** The project-level default this plugin bootstraps. */
export const DEFAULT_DISPATCH_MODE = "inline";

/** A lock older than this is treated as abandoned by a crashed session. */
export const LOCK_STALE_MS = 10_000;

const LOCK_NAME = ".dsh-trellis-config.lock";
const RUNTIME_DIR = join(".trellis", ".runtime");
const DISPATCH_LINE = `  dispatch_mode: ${DEFAULT_DISPATCH_MODE}`;

const APPENDED_BLOCK = [
  "# dsh-trellis: projects default to inline execution (the main session",
  "# implements and checks directly). Set `auto` to dispatch Trellis role",
  "# sub-agents instead.",
  "dsh:",
  DISPATCH_LINE,
];

/**
 * Result of {@link mergeDshDispatchMode}.
 * @typedef {{content: string, changed: boolean, reason: string}} MergeResult
 */

/**
 * Ensure `.trellis/config.yaml` text carries `dsh.dispatch_mode`.
 *
 * @param {string | null | undefined} content - current file text.
 * @returns {MergeResult} the (possibly unchanged) text plus why.
 */
export function mergeDshDispatchMode(content) {
  if (typeof content !== "string") {
    return { content: "", changed: false, reason: "no-config" };
  }
  const eol = content.includes("\r\n") ? "\r\n" : "\n";
  const lines = content.split(/\r?\n/);

  const dshIndex = lines.findIndex((line) => /^dsh\s*:\s*(?:#.*)?$/.test(line));
  const inlineDshIndex = lines.findIndex(
    (line) => /^dsh\s*:/.test(line) && !/^dsh\s*:\s*(?:#.*)?$/.test(line),
  );
  if (dshIndex === -1 && inlineDshIndex !== -1) {
    // `dsh: {…}` or `dsh: auto` — a shape this conservative migration will not
    // rewrite. The user's mapping stays authoritative.
    return { content, changed: false, reason: "dsh-not-block" };
  }

  if (dshIndex === -1) {
    const base = content.replace(/\s+$/, "");
    const block = APPENDED_BLOCK.join(eol);
    const next = base === ""
      ? `${block}${eol}`
      : `${base}${eol}${eol}${block}${eol}`;
    return { content: next, changed: true, reason: "appended" };
  }

  // The section ends at the next top-level key. A column-zero comment is the
  // start of that key's documentation, not part of the `dsh:` section, so it
  // also terminates the section; indented comments stay inside it.
  let end = dshIndex + 1;
  while (end < lines.length) {
    const line = lines[end];
    if (line.trim() === "" || /^\s/.test(line)) {
      end += 1;
      continue;
    }
    break;
  }
  const section = lines.slice(dshIndex + 1, end);
  if (section.some((line) => /^\s+dispatch_mode\s*:/.test(line))) {
    return { content, changed: false, reason: "present" };
  }

  // Insert after the section's last non-blank line so comments stay attached to
  // the key they describe; a section with no entries gets the key directly
  // under its header (an empty line is not an entry).
  let insertAt = dshIndex + 1;
  for (let index = end - 1; index > dshIndex; index -= 1) {
    if (lines[index].trim() !== "") {
      insertAt = index + 1;
      break;
    }
  }
  const next = [...lines];
  next.splice(insertAt, 0, DISPATCH_LINE);
  return { content: next.join(eol), changed: true, reason: "inserted" };
}

/**
 * Atomically write the merged config text.
 * @param {string} root
 * @param {string} content
 * @param {object} fs - filesystem shim with writeFile/rename.
 * @returns {Promise<void>}
 */
async function writeConfig(root, content, fs) {
  const target = join(root, ".trellis", "config.yaml");
  const temp = join(
    root,
    RUNTIME_DIR,
    `${LOCK_NAME}.${process.pid}.${Date.now()}.tmp`,
  );
  try {
    await fs.writeFile(temp, content, { encoding: "utf8" });
    await fs.rename(temp, target);
  } catch (error) {
    try {
      await fs.unlink?.(temp);
    } catch {
      // The temp file is best-effort cleanup; the original error is what matters.
    }
    throw error;
  }
}

/**
 * @param {object} [options]
 * @param {object} [options.fs] - filesystem shim.
 * @param {{warn?: Function}} [options.logger]
 * @param {Map<string, unknown>} [options.cache] - the resolvers' read cache.
 */
export function createDshDefaultsEnsurer({
  fs = nodeFs,
  logger,
  cache,
} = {}) {
  const warned = new Set();
  // A project that cannot accept the bootstrap (read-only checkout, immutable
  // config, failed rename) would otherwise retry the same lock/write on every
  // model step. A process-local negative cache keeps one warning and zero
  // repeated IO; a new DSH process gets one fresh attempt.
  const failedRoots = new Map();

  /**
   * @param {{root: string, configText: string | null}} project
   * @returns {Promise<MergeResult>}
   */
  return async function ensureDshDefaults({ root, configText }) {
    const cachedFailure = failedRoots.get(root);
    if (cachedFailure !== undefined) return cachedFailure;
    const merged = mergeDshDispatchMode(configText);
    if (!merged.changed) return merged;
    if (typeof fs.writeFile !== "function" || typeof fs.rename !== "function") {
      const result = { ...merged, changed: false, reason: "fs-readonly" };
      failedRoots.set(root, result);
      return result;
    }
    // Transient state lives under `.trellis/.runtime/`, which Trellis ignores;
    // a crashed session must not leave a lock file in the tracked tree.
    const runtimeDir = join(root, RUNTIME_DIR);
    const lockPath = join(runtimeDir, LOCK_NAME);
    const configPath = join(root, ".trellis", "config.yaml");
    if (typeof fs.mkdir === "function") {
      try {
        await fs.mkdir(runtimeDir, { recursive: true });
      } catch {
        // Locking is best-effort; the atomic rename still protects the file.
      }
    }
    const locked = await acquireLock(lockPath, fs);
    if (!locked) return { ...merged, changed: false, reason: "locked" };
    try {
      // The snapshot above may predate another process's write (this session
      // read before waiting on the lock). Merge against the file as it is now,
      // so a concurrent addition is never duplicated and concurrent unrelated
      // edits are not overwritten.
      const current = await fs.readFile(configPath);
      const fresh = mergeDshDispatchMode(current);
      if (!fresh.changed) {
        cache?.delete(configPath);
        return fresh;
      }
      await writeConfig(root, fresh.content, fs);
      cache?.delete(configPath);
      return fresh;
    } catch (error) {
      if (!warned.has(root)) {
        warned.add(root);
        logger?.warn?.(
          "dsh-trellis: could not add dsh.dispatch_mode to %s: %o",
          configPath,
          error,
        );
      }
      const result = { ...merged, changed: false, reason: "write-failed" };
      failedRoots.set(root, result);
      return result;
    } finally {
      await releaseLock(lockPath, fs);
    }
  };
}

/**
 * Directory lock: `mkdir` is atomic on every supported filesystem. Without it
 * (test shims, unusual hosts) the write proceeds unlocked — the atomic rename
 * still prevents torn files.
 * @returns {Promise<boolean>}
 */
async function acquireLock(lockPath, fs) {
  if (typeof fs.mkdir !== "function" || typeof fs.rmdir !== "function") {
    return true;
  }
  try {
    await fs.mkdir(lockPath);
    return true;
  } catch (error) {
    if (error?.code !== "EEXIST") return true;
  }
  const info = await fs.stat(lockPath);
  if (info !== null && Date.now() - info.mtimeMs > LOCK_STALE_MS) {
    try {
      await fs.rmdir(lockPath);
      await fs.mkdir(lockPath);
      return true;
    } catch {
      return false;
    }
  }
  return false;
}

async function releaseLock(lockPath, fs) {
  if (typeof fs.rmdir !== "function") return;
  try {
    await fs.rmdir(lockPath);
  } catch {
    // Another process may have cleaned up a stale lock first.
  }
}
