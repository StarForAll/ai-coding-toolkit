/**
 * Trellis project state resolution: project root, workflow-state blocks,
 * active task pointer, and status mapping.
 *
 * Pure logic with an injectable filesystem shim so unit tests run without
 * touching a real Trellis project.
 *
 * @module dsh-trellis/workflow
 */
import { join, dirname, isAbsolute, relative, resolve, sep } from "node:path";
import { createHash } from "node:crypto";
import { parseSection, topLevelScalar } from "./trellis-config.js";

/**
 * Workflow-state block charset, mirrored from Trellis's workflow.md contract.
 *
 * The `\s*\n` after the opening tag is load-bearing: Trellis's own
 * `[workflow-state:STATUS]` blocks always open on their own line, while
 * workflow.md also *mentions* tags inline (for example inside the
 * breadcrumb-contract HTML comment). Without the newline constraint a mention
 * such as `[workflow-state:no_task] → no active task` opens a match that runs
 * to the next real closing tag, injecting the whole comment into the prompt.
 */
const STATUS_RE =
  /\[workflow-state:([A-Za-z0-9_-]+)\]\s*\n([\s\S]*?)\n\s*\[\/workflow-state:\1\]/g;

/** Workflow variants live under `.trellis/workflows/<id>.md`. */
const WORKFLOWS_DIR = "workflows";
const WORKFLOW_ID_RE = /^[A-Za-z0-9_-]+$/;

/** Same sanitization Trellis task.py applies to context keys. */
export function sanitizeContextKey(value) {
  return String(value)
    .replace(/[^A-Za-z0-9._-]+/g, "_")
    .replace(/^[._-]+|[._-]+$/g, "");
}

/**
 * Mode banner appended whenever the project selects `dsh.dispatch_mode: inline`,
 * independent of which workflow-state block was chosen. The `*-inline` blocks
 * come from Trellis and are marked Codex-only; their phase contract is
 * platform-neutral, but they do not mention DSH-specific mechanics. This banner
 * restores exactly those mechanics for inline mode without forking the workflow
 * file, and it is the only signal that survives when a custom workflow variant
 * has no `*-inline` block.
 */
export const DSH_INLINE_NOTE =
  "<dsh-mode>\n" +
  "inline: the main session implements and checks directly. Do not dispatch " +
  "trellis-agent-implement / trellis-agent-check sub-agents; the trellis_wait " +
  "tool is not needed in this mode. Verify with the trellis-check skill, update " +
  "specs with trellis-update-spec, then commit (Phase 3.4) and run " +
  "/trellis-finish-work.\n" +
  "</dsh-mode>";

/** The degrading fallback when workflow.md lacks a block for the resolved status. */
export const FALLBACK_BREADCRUMB =
  "Refer to `.trellis/workflow.md` for the current workflow step (no matching [workflow-state] block found).";

/** Old workflows may not yet define task_error; never turn a bad record into no_task. */
export const TASK_ERROR_BREADCRUMB =
  "The active task record could not be read. Do not create or activate another task. " +
  "Inspect the active task directory and repair its task.json (a JSON object with a non-empty status). " +
  "Preserve existing fields and artifacts; ask the user if the correct status is uncertain.";

/**
 * Parse every `[workflow-state:STATUS] ... [/workflow-state:STATUS]` block.
 *
 * A block whose body is empty (or whitespace-only) is not a usable template:
 * Trellis's own `load_breadcrumbs` drops it (`if body: result[status] = body`),
 * so the hook degrades to its generic line instead of injecting nothing. Keeping
 * such a block here would render an empty breadcrumb body and let an empty
 * `planning-inline` / `in_progress-inline` shadow the populated base block.
 *
 * @param {string} content - workflow.md content.
 * @returns {Map<string, string>} status → trimmed, non-empty body.
 */
export function parseWorkflowStateBlocks(content) {
  const blocks = new Map();
  for (const match of content.matchAll(STATUS_RE)) {
    const body = match[2].trim();
    if (body !== "") blocks.set(match[1], body);
  }
  return blocks;
}

/**
 * Resolve a workflow variant id to `.trellis/workflows/<id>.md`.
 *
 * Trellis rejects ids containing path separators or dots so a task record can
 * never escape the variant directory; a missing file falls through to the next
 * layer, exactly like `common/workflow_selection.py`.
 *
 * @param {string} root
 * @param {string | null} id
 * @param {object} fs
 * @returns {Promise<string | null>}
 */
async function variantWorkflowPath(root, id, fs) {
  if (typeof id !== "string" || !WORKFLOW_ID_RE.test(id)) return null;
  const path = join(root, ".trellis", WORKFLOWS_DIR, `${id}.md`);
  return (await fs.exists(path)) ? path : null;
}

/**
 * Personal override from the gitignored `.trellis/.developer` file.
 * @param {string | null | undefined} text - file content.
 * @returns {string | null}
 */
function developerWorkflowId(text) {
  if (typeof text !== "string") return null;
  for (const line of text.split(/\r?\n/)) {
    if (line.startsWith("workflow=")) {
      return line.slice("workflow=".length).trim() || null;
    }
  }
  return null;
}

/**
 * Normalize `dsh.dispatch_mode` to `"auto"` or `"inline"`.
 *
 * This is the DSH counterpart of Trellis's `codex.dispatch_mode` and is read
 * only from `.trellis/config.yaml` `dsh.dispatch_mode`. `auto` (the default)
 * keeps the base blocks and the sub-agent dispatch protocol; `inline` selects
 * the platform-neutral `*-inline` phase block plus the DSH mode banner.
 * Unknown values fall back to `auto` instead of silently changing how the main
 * session works.
 *
 * @param {string | null | undefined} configText
 * @returns {"auto" | "inline"}
 */
export function dshDispatchMode(configText) {
  const section = parseSection(configText, "dsh");
  if (section === null) return "auto";
  const raw = section.get("dispatch_mode");
  if (raw === undefined) return "auto";
  const mode = String(raw).trim().toLowerCase();
  return mode === "inline" ? "inline" : "auto";
}

/**
 * Pick the workflow file for this turn.
 *
 * Precedence is Trellis's own (`common/workflow_selection.py`):
 * per-task `task.json workflow` → `.developer workflow=` → config.yaml
 * `default_workflow` → global `.trellis/workflow.md`. Every layer falls
 * through when its id is invalid or names a missing file.
 *
 * @param {object} options
 * @param {string} options.root
 * @param {string | null} [options.taskWorkflow]
 * @param {object} options.fs
 * @param {Map<string, {mtimeMs: number, content: string | null}>} [options.cache]
 * @returns {Promise<string>}
 */
export async function resolveWorkflowPath({ root, taskWorkflow = null, fs, cache }) {
  const shared = cache ?? new Map();
  const candidates = [
    taskWorkflow,
    developerWorkflowId(
      await readCached(join(root, ".trellis", ".developer"), fs, shared),
    ),
    topLevelScalar(
      await readCached(join(root, ".trellis", "config.yaml"), fs, shared),
      "default_workflow",
    ),
  ];
  for (const id of candidates) {
    const variant = await variantWorkflowPath(root, id, fs);
    if (variant !== null) return variant;
  }
  return join(root, ".trellis", "workflow.md");
}

/**
 * Walk upward from cwd to the first directory containing one of the markers.
 * @param {string} cwd - absolute starting directory.
 * @param {string[]} markers - child names that identify a project root.
 * @param {{exists(path: string): Promise<boolean>}} fs - filesystem shim.
 * @returns {Promise<string | null>}
 */
export async function findProjectRoot(cwd, markers, fs) {
  let current = resolve(cwd);
  for (;;) {
    for (const marker of markers) {
      if (await fs.exists(join(current, marker))) return current;
    }
    const parent = dirname(current);
    if (parent === current) return null;
    current = parent;
  }
}

/**
 * Read a file, returning null when absent. Cache by (path, mtimeMs) so the
 * per-turn hot path does not re-read workflow.md on every step.
 * @param {string} path
 * @param {{readFile(path: string): Promise<string | null>, stat(path: string): Promise<{mtimeMs: number} | null>}} fs
 * @param {Map<string, {mtimeMs: number, content: string | null}>} cache
 * @returns {Promise<string | null>}
 */
export async function readCached(path, fs, cache) {
  try {
    const info = await fs.stat(path);
    if (info === null) return null;
    const hit = cache.get(path);
    if (hit !== undefined && hit.mtimeMs === info.mtimeMs) return hit.content;
    const content = await fs.readFile(path);
    cache.set(path, { mtimeMs: info.mtimeMs, content });
    return content;
  } catch {
    return null;
  }
}

/**
 * Normalize a session pointer's task reference the way Trellis does
 * (`common/active_task.py normalize_task_ref`): trim, forward slashes, drop
 * leading `./`, keep absolute paths, and expand the legacy `tasks/<slug>`
 * form to `.trellis/tasks/<slug>`.
 *
 * @param {unknown} taskRef
 * @returns {string}
 */
export function normalizeTaskRef(taskRef) {
  if (typeof taskRef !== "string") return "";
  let normalized = taskRef.trim();
  if (normalized === "") return "";
  if (isAbsolute(normalized)) return normalized;
  normalized = normalized.replace(/\\/g, "/");
  while (normalized.startsWith("./")) normalized = normalized.slice(2);
  if (normalized.startsWith("tasks/")) return `.trellis/${normalized}`;
  return normalized;
}

/**
 * Resolve a normalized task reference to an absolute directory inside the
 * repo. Returns null when the reference is empty or escapes the project root.
 *
 * @param {string} root
 * @param {unknown} taskRef
 * @returns {string | null}
 */
export function resolveTaskRef(root, taskRef) {
  const normalized = normalizeTaskRef(taskRef);
  if (normalized === "") return null;
  let candidate;
  if (isAbsolute(normalized)) {
    candidate = resolve(normalized);
  } else if (normalized.startsWith(".trellis/")) {
    candidate = resolve(root, normalized);
  } else {
    candidate = resolve(root, ".trellis", "tasks", normalized);
  }
  const rel = relative(root, candidate);
  if (rel === "" || rel.startsWith("..") || isAbsolute(rel)) return null;
  return candidate;
}

/** Render an absolute path as a repo-relative POSIX path. */
function repoRelative(root, absolute) {
  return relative(root, absolute).split(sep).join("/");
}

/**
 * Resolve the active task for a dsh session.
 *
 * Read only this session's pointer. A sole foreign session is not proof of
 * ownership (Trellis #608). Child agents receive an explicit Active task:
 * dispatch prompt; they must not borrow arbitrary session bindings here.
 * Once bound, an unreadable task record is task_error, not an absent task.
 *
 * @param {string} root - project root.
 * @param {string} contextKey - sanitized `dsh_<session-id>` key for this agent.
 * @param {{readFile(path: string): Promise<string | null>}} fs
 * @returns {Promise<{path: string, status: string} | null>} task dir-relative path + status.
 */
export async function resolveActiveTask(root, contextKey, fs) {
  if (!contextKey) return null;
  const pointer = join(
    root, ".trellis", ".runtime", "sessions", `${contextKey}.json`,
  );
  let data = null;
  try {
    data = JSON.parse((await fs.readFile(pointer)) ?? "null");
  } catch {
    return null;
  }
  if (
    data === null ||
    typeof data !== "object" ||
    Array.isArray(data) ||
    typeof data.current_task !== "string" ||
    data.current_task.trim() === ""
  ) {
    return null;
  }
  const taskPath = data.current_task;
  const absolute = resolveTaskRef(root, taskPath);
  if (absolute === null) {
    // Unnormalizable or outside the project root: Trellis rejects the
    // reference, so this cannot be a live task either.
    return { path: taskPath, status: "stale", workflow: null };
  }
  const relativePath = repoRelative(root, absolute);
  // A pointer to something that is gone (or is not a directory) is `stale`,
  // not `task_error`: Trellis distinguishes the two and prompts a different
  // repair path. `task_error` means the directory exists but task.json does
  // not.
  const info = await fs.stat(absolute);
  if (info === null || info.isDirectory === false) {
    return { path: relativePath, status: "stale", workflow: null };
  }
  const record = await readTaskRecord(root, relativePath, fs);
  return {
    path: relativePath,
    status: record?.status ?? "task_error",
    workflow: record?.workflow ?? null,
  };
}

/**
 * Read a task record's status and optional workflow pin.
 * Returns null for an unreadable/invalid record (missing file, bad JSON, no
 * non-empty status).
 *
 * @param {string} root
 * @param {string} taskPath - repo-root relative task dir.
 * @param {{readFile(path: string): Promise<string | null>}} fs
 * @returns {Promise<{status: string, workflow: string | null} | null>}
 */
export async function readTaskRecord(root, taskPath, fs) {
  try {
    const data = JSON.parse(
      (await fs.readFile(join(root, taskPath, "task.json"))) ?? "null",
    );
    if (
      data === null ||
      typeof data !== "object" ||
      Array.isArray(data) ||
      typeof data.status !== "string" ||
      data.status.trim() === ""
    ) {
      return null;
    }
    const workflow =
      typeof data.workflow === "string" && data.workflow.trim() !== ""
        ? data.workflow.trim()
        : null;
    return { status: data.status.trim(), workflow };
  } catch {
    return null;
  }
}

/**
 * Read a non-empty task.json status, or null for an unreadable/invalid record.
 * @param {string} root
 * @param {string} taskPath - repo-root relative task dir (e.g. `.trellis/tasks/04-17-foo`).
 * @param {{readFile(path: string): Promise<string | null>}} fs
 * @returns {Promise<string | null>}
 */
export async function readTaskStatus(root, taskPath, fs) {
  return (await readTaskRecord(root, taskPath, fs))?.status ?? null;
}

/**
 * Normalize a task status for breadcrumb resolution.
 *
 * Trellis statuses are free-form (`planning`, `in_progress`, `completed`,
 * `blocked`, a team-defined value, …) and the workflow file decides which of
 * them has a block. Only an absent/unreadable status degrades to `no_task`;
 * everything else passes through so `completed` and custom statuses are not
 * silently rewritten into "no active task".
 *
 * @param {string | null} status
 * @returns {string}
 */
export function mapStatus(status) {
  if (typeof status !== "string" || status.trim() === "") return "no_task";
  return status.trim();
}

/**
 * Resolve the full Trellis state for one session step.
 * @param {object} options
 * @param {string} options.cwd
 * @param {string[]} options.markers
 * @param {string} options.contextKey - sanitized session context key.
 * @param {object} options.fs - filesystem shim ({exists, readFile, stat}).
 * @param {Map<string, {mtimeMs: number, content: string | null}>} options.cache
 * @param {string | null} [options.root] - an already-resolved project root.
 *   Callers that ran a project bootstrap (for example the session composer's
 *   `dsh.dispatch_mode` migration) reuse it so both layers agree on one root
 *   and the config re-read observes the write.
 * @returns {Promise<{root: string, status: string, taskPath: string | null, body: string, digest: string} | null>}
 */
export async function resolveTrellisState({
  cwd,
  markers,
  contextKey,
  fs,
  cache,
  root: resolvedRoot = null,
}) {
  const root = resolvedRoot ?? await findProjectRoot(cwd, markers, fs);
  if (root === null) return null;
  const task = await resolveActiveTask(root, contextKey, fs);
  const workflowPath = await resolveWorkflowPath({
    root,
    taskWorkflow: task?.workflow ?? null,
    fs,
    cache,
  });
  const content = await readCached(workflowPath, fs, cache);
  if (content === null || content === undefined) return null;
  const blocks = parseWorkflowStateBlocks(content);
  if (blocks.size === 0) return null;
  // `codex.dispatch_mode` is Codex-only and is deliberately ignored here.
  // DSH has its own `dsh.dispatch_mode` switch; when it selects inline, the
  // platform-neutral `*-inline` phase block is reused when the workflow file
  // defines it, and the DSH-specific mechanics are always restored by the mode
  // banner below. The banner is the mode signal; the block is only a phase
  // wording choice.
  const configText = await readCached(
    join(root, ".trellis", "config.yaml"),
    fs,
    cache,
  );
  const rawStatus = mapStatus(task?.status ?? null);
  // Two independent decisions:
  //   1. which block to show — the `*-inline` phase block exists only for the
  //      two dispatch phases, and only when the resolved workflow file defines
  //      it (custom variants may not);
  //   2. whether this project works inline — a project-level mode that must be
  //      announced even when the variant has no `*-inline` block, otherwise a
  //      trimmed workflow would silently re-teach the auto-mode contract
  //      ("curate implement.jsonl", "dispatch implement/check") to an inline
  //      project. Codex keeps emitting `<codex-mode>inline>` in that case too;
  //      the banner, not the block choice, is what carries the mode.
  const inlineMode = dshDispatchMode(configText) === "inline";
  const inlineBlock =
    inlineMode &&
    (rawStatus === "planning" || rawStatus === "in_progress") &&
    blocks.has(`${rawStatus}-inline`);
  const status = inlineBlock ? `${rawStatus}-inline` : rawStatus;
  const block = blocks.get(status);
  let body =
    status === "task_error"
      ? blocks.get(status) || TASK_ERROR_BREADCRUMB
      : block ?? FALLBACK_BREADCRUMB;
  if (inlineMode) {
    body = `${body}\n\n${DSH_INLINE_NOTE}`;
  }
  const digest = createHash("sha1")
    .update(`${status}\n${task?.path ?? ""}\n${body}`)
    .digest("hex");
  return { root, status, taskPath: task?.path ?? null, body, digest };
}
