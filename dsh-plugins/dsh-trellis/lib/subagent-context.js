/**
 * Sub-agent task-context push (the DSH equivalent of Codex's `SubagentStart`).
 *
 * Codex injects a curated developer context when a `trellis-*` role starts. DSH
 * publishes `subagent/start` with the child id and the delegating parent, but
 * not the role, so the push happens at the child's first `agent/pre-step`: the
 * dispatch prompt is already one of the messages entering that step, which
 * proves the context lands before the child's first model request.
 *
 * The parent's session pointer is the fallback when a dispatch prompt carries
 * no `Active task:` prelude. The push carries the installed role contract
 * (`.dsh/skills/trellis-agent-<role>/SKILL.md`) before curated task context;
 * the child-side skills keep working either way — this layer is additive, never
 * a replacement for the pull path.
 *
 * @module dsh-trellis/subagent-context
 */
import { readFile, readdir, realpath } from "node:fs/promises";
import { isAbsolute, join, resolve, sep } from "node:path";
import { createUserMessage } from "@deepseek-ai/dsh-llm";
import { nodeFs } from "./node-fs.js";
import { contextInjectionLimits } from "./trellis-config.js";
import { roleFromLabel, stripPullOnlyContext } from "./role-contract.js";
import { registerSubagentIdentity } from "./subagent-identity.js";
import { findProjectRoot, resolveActiveTask, sanitizeContextKey } from "./workflow.js";
import { resolveWorkingDirectory } from "./working-directory.js";

export const SOURCE_KIND = "dsh-trellis";
export const SOURCE_FORM = "subagent-context";

/** `trellis-agent-<role>` first, then the bare `trellis-<role>` alias. */
const AGENT_ROLE_RE = /\btrellis-agent-(implement|check|research)\b/;
const BARE_ROLE_RE = /\btrellis-(implement|check|research)\b/;

/** @param {string} text @returns {string | null} */
function roleFrom(text) {
  return AGENT_ROLE_RE.exec(text)?.[1] ?? BARE_ROLE_RE.exec(text)?.[1] ?? null;
}

/** Role name → curated manifest file inside the task directory. */
const ROLE_MANIFEST = Object.freeze({
  implement: "implement.jsonl",
  check: "check.jsonl",
  research: "research.jsonl",
});

/** Task artifacts, in the order Trellis itself inlines them. */
const TASK_ARTIFACTS = Object.freeze([
  { file: "prd.md", label: "Requirements" },
  { file: "design.md", label: "Technical Design" },
  { file: "implement.md", label: "Execution Plan" },
]);

/** Role name → the DSH-private role skill installed by `trellis init --dsh`. */
const ROLE_SKILLS = Object.freeze({
  implement: ".dsh/skills/trellis-agent-implement/SKILL.md",
  check: ".dsh/skills/trellis-agent-check/SKILL.md",
  research: ".dsh/skills/trellis-agent-research/SKILL.md",
});

/** Hard ceiling for the role contract; task context has its own config budget. */
export const ROLE_INSTRUCTIONS_MAX_BYTES = 16384;

/**
 * Strip a leading YAML frontmatter block, leaving the Markdown body.
 * The skill's `name` / `description` fields are discovery metadata, not role
 * instructions; Codex's agent TOML also injects only `developer_instructions`.
 *
 * @param {string} text
 * @returns {string}
 */
export function stripYamlFrontmatter(text) {
  const source = String(text ?? "");
  if (!source.startsWith("---")) return source;
  const match = /^---\r?\n[\s\S]*?\r?\n---\r?\n?/.exec(source);
  return match === null ? source : source.slice(match[0].length);
}

/**
 * Read the role contract from the project's DSH role skill.
 *
 * This is intentionally sourced from the installed Trellis skill rather than a
 * second copy in the plugin: when Trellis updates the role rules, the push
 * follows. The task context is already prepared, so the message explains that
 * the skill's generic "load context yourself" step is satisfied for this push.
 *
 * @param {object} options
 * @param {string} options.root
 * @param {string} options.role
 * @param {number} [options.maxBytes]
 * @returns {Promise<string | null>}
 */
export async function readRoleInstructions({ root, role, maxBytes = ROLE_INSTRUCTIONS_MAX_BYTES }) {
  const relativePath = ROLE_SKILLS[role];
  if (typeof relativePath !== "string") return null;
  const full = await containedPath(root, relativePath);
  if (full === null) return null;
  let text;
  try {
    text = await readFile(full, "utf8");
  } catch {
    return null;
  }
  const body = stripPullOnlyContext(
    stripYamlFrontmatter(text).trim(),
    role,
  );
  if (body === "") return null;
  if (maxBytes > 0 && Buffer.byteLength(body, "utf8") > maxBytes) {
    return `${truncateUtf8(body, maxBytes)}\n[Trellis: role instructions truncated at ${maxBytes} bytes — read ${relativePath} for the full content]`;
  }
  return body;
}

/**
 * Fallback when the project has no generated role skill. A pointer is still
 * better than silently omitting the role contract from the child's first turn.
 *
 * @param {string} role
 * @returns {string}
 */
export function roleInstructionsFallback(role) {
  return `Load \`.dsh/skills/trellis-agent-${role}/SKILL.md\` once before acting.`;
}

/**
 * Join every text part of a message batch.
 * @param {Array<{content?: unknown}>} messages
 * @returns {string}
 */
function messageText(messages) {
  const texts = [];
  for (const message of messages ?? []) {
    const content = message?.content;
    const parts = Array.isArray(content) ? content : [];
    for (const part of parts) {
      if (typeof part?.text === "string") texts.push(part.text);
    }
  }
  return texts.join("\n");
}

/**
 * Recover the Trellis role and `Active task:` path from a dispatch prompt.
 *
 * Dispatch prompts start with `Active task: <task path>` by contract, so the
 * path is present even when the parent session pointer is stale. The role comes
 * from the prompt first and from the child's descriptor `label` second: DSH
 * records the dispatch `description` argument as that label, so a user who
 * names the role only there still gets the role contract pushed.
 *
 * A missing role in both places means "not a Trellis role agent": the push
 * stays silent and the child-side skill remains the only context source,
 * matching Codex's behaviour for generic children.
 *
 * @param {Array<{content?: unknown}>} messages
 * @param {string | null} [label] - descriptor label of the child session.
 * @returns {{role: string | null, taskPath: string | null, finish: boolean}}
 */
export function parseDispatchPrompt(messages, label = null) {
  const text = messageText(messages);
  const labelText = typeof label === "string" ? label : "";
  const taskMatch = /Active task:\s*([^\s`'"<>]+)/.exec(text);
  let taskPath = taskMatch?.[1] ?? null;
  if (taskPath !== null) taskPath = taskPath.replace(/[.,;:]+$/, "");
  return {
    role: roleFrom(text) ?? roleFromLabel(labelText),
    taskPath,
    finish: /\[finish\]/i.test(text),
  };
}

/**
 * Truncate UTF-8 text to a byte budget without splitting a code point.
 * @param {string} value
 * @param {number} maxBytes
 * @returns {string}
 */
export function truncateUtf8(value, maxBytes) {
  const bytes = Buffer.from(value, "utf8");
  if (maxBytes <= 0 || bytes.length <= maxBytes) return value;
  let end = Math.trunc(maxBytes);
  while (end > 0 && (bytes.readUInt8(end) & 0xc0) === 0x80) end -= 1;
  return bytes.subarray(0, end).toString("utf8");
}

/**
 * Resolve a repo-relative path, refusing anything that escapes the repository.
 *
 * `.trellis` may itself be a symlink into a store outside the repo, so its real
 * location is accepted as a second legitimate containment base.
 *
 * @param {string} root
 * @param {string} relativePath
 * @returns {Promise<string | null>}
 */
export async function containedPath(root, relativePath) {
  if (typeof relativePath !== "string" || relativePath.trim() === "") return null;
  if (isAbsolute(relativePath)) return null;
  const full = resolve(root, relativePath);
  try {
    const rootReal = await realpath(root);
    const workflowReal = await realpath(join(root, ".trellis"));
    const targetReal = await realpath(full);
    return targetReal === rootReal ||
      targetReal.startsWith(rootReal + sep) ||
      targetReal.startsWith(workflowReal + sep)
      ? targetReal
      : null;
  } catch {
    return null;
  }
}

/** Byte-budget accumulator shared by every block of one payload. */
class Budget {
  constructor(maxTotalBytes) {
    this.maxTotalBytes = maxTotalBytes;
    this.used = 0;
  }

  hasRoom(size) {
    return this.maxTotalBytes <= 0 || this.used + size <= this.maxTotalBytes;
  }

  add(size) {
    this.used += size;
  }
}

/**
 * Build a portable source-location notice instead of a platform-specific path.
 * @param {string} path
 * @param {number} size
 * @param {string} reason
 * @returns {string}
 */
function indexNotice(path, size, reason) {
  return `[Trellis: not inlined (total context limit reached) — ${path} (${size} bytes): ${reason}]`;
}

/**
 * Render one inlined block, degrading to an index line once the budget ends.
 * @param {Budget} budget
 * @param {string} header
 * @param {string} path
 * @param {string} content
 * @param {string} reason
 * @param {number} size
 * @returns {string}
 */
function budgetedBlock(budget, header, path, content, reason, size) {
  const block = `=== ${header} ===\n${content}`;
  const bytes = Buffer.byteLength(block);
  if (!budget.hasRoom(bytes)) {
    const notice = indexNotice(path, size, reason);
    budget.add(Buffer.byteLength(notice));
    return notice;
  }
  budget.add(bytes);
  return block;
}

/**
 * Materialize one repo file, applying the per-file cap and total budget.
 * @param {object} options
 * @param {string} options.root
 * @param {string} options.filePath - repo-relative.
 * @param {string} options.reason
 * @param {{maxFileBytes: number}} options.limits
 * @param {Budget} options.budget
 * @returns {Promise<string | null>}
 */
async function materializeFile({ root, filePath, reason, limits, budget }) {
  const full = await containedPath(root, filePath);
  if (full === null) return null;
  let bytes;
  try {
    bytes = await readFile(full);
  } catch {
    return null;
  }
  if (bytes.includes(0)) {
    const notice = `[Trellis: not inlined (binary file) — ${filePath} (${bytes.length} bytes): ${reason}]`;
    budget.add(Buffer.byteLength(notice));
    return notice;
  }
  const cap = limits.maxFileBytes;
  const truncated = cap > 0 && bytes.length > cap;
  const content = truncated
    ? `${truncateUtf8(bytes.toString("utf8"), cap)}\n[Trellis: truncated at ${cap} bytes — read ${filePath} for the full content]`
    : bytes.toString("utf8");
  return budgetedBlock(budget, filePath, filePath, content, reason, bytes.length);
}

/**
 * Materialize a directory entry: its `.md` files, capped by budget.
 * @param {object} options
 * @param {string} options.root
 * @param {string} options.dirPath
 * @param {string} options.reason
 * @param {{maxFileBytes: number}} options.limits
 * @param {Budget} options.budget
 * @returns {Promise<string[]>}
 */
async function materializeDirectory({ root, dirPath, reason, limits, budget }) {
  const full = await containedPath(root, dirPath);
  if (full === null) return [];
  let names;
  try {
    names = (await readdir(full))
      .filter((name) => name.endsWith(".md"))
      .sort()
      .slice(0, 20);
  } catch {
    return [];
  }
  const blocks = [];
  for (const name of names) {
    const block = await materializeFile({
      root,
      filePath: `${dirPath.replace(/\/+$/, "")}/${name}`,
      reason,
      limits,
      budget,
    });
    if (block !== null) blocks.push(block);
  }
  return blocks;
}

/**
 * Parse a task manifest (`<role>.jsonl`).
 *
 * Rows without a `file` are seed/placeholder lines and are skipped silently;
 * a manifest with no real entry is reported in the prompt itself so the child
 * does not mistake an empty context for "nothing governs this work".
 *
 * @param {string} root
 * @param {string} manifestPath
 * @returns {Promise<Array<{file: string, type: string, reason: string}>>}
 */
export async function readManifest(root, manifestPath) {
  const full = await containedPath(root, manifestPath);
  if (full === null) return [];
  let text;
  try {
    text = await readFile(full, "utf8");
  } catch {
    return [];
  }
  const entries = [];
  for (const line of text.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (trimmed === "") continue;
    let item;
    try {
      item = JSON.parse(trimmed);
    } catch {
      continue;
    }
    const filePath = item?.file ?? item?.path;
    if (typeof filePath !== "string" || filePath.trim() === "") continue;
    entries.push({
      file: filePath.trim(),
      type: item.type === "directory" ? "directory" : "file",
      reason: typeof item.reason === "string" ? item.reason : "-",
    });
  }
  return entries;
}

/**
 * Build the project-structure overview Codex gives a research sub-agent.
 *
 * Research is a discovery role: the useful context is where specs live and how
 * to enumerate packages/layers, not the task's implementation artifacts. The
 * on-disk `research.jsonl` is optional legacy input; when it has real entries
 * they are still materialized, but an empty manifest is not turned into a
 * misleading "no context was injected" notice.
 *
 * @param {string} root
 * @returns {Promise<string>}
 */
export async function buildSpecDirectoryOverview(root) {
  const specRoot = join(root, ".trellis", "spec");
  const lines = [".trellis/spec/"];
  let packages = [];
  try {
    packages = (await readdir(specRoot, { withFileTypes: true }))
      .filter((entry) => entry.isDirectory())
      .map((entry) => entry.name)
      .sort();
  } catch {
    // A project without a spec tree still gets the search contract below.
  }
  for (let index = 0; index < packages.length; index += 1) {
    const name = packages[index];
    let layers = [];
    try {
      layers = (await readdir(join(specRoot, name), { withFileTypes: true }))
        .filter((entry) => entry.isDirectory())
        .map((entry) => entry.name)
        .sort();
    } catch {
      // A package directory that cannot be listed is still named.
    }
    const prefix = index === packages.length - 1 ? "└── " : "├── ";
    lines.push(`${prefix}${name}/${layers.length > 0 ? ` (${layers.join(", ")})` : ""}`);
  }
  return [
    "## Project Spec Directory Structure",
    "",
    "```",
    ...lines,
    "```",
    "",
    "To get structured package info, run: `python3 ./.trellis/scripts/get_context.py --mode packages`",
    "",
    "## Search Tips",
    "",
    "- Spec files: `.trellis/spec/**/*.md`",
    "- Code search: Use Glob and Grep tools",
    "- Tech solutions: use the available web/code search tools",
  ].join("\n");
}

/**
 * Research context: project spec overview first, optional curated research
 * entries second. Task artifacts are intentionally not inlined — Codex's
 * research hook does not inject them, and the role's job is discovery.
 *
 * @param {object} options
 * @param {string} options.root
 * @param {string} options.taskPath
 * @param {{maxFileBytes: number, maxArtifactBytes: number, maxTotalBytes: number}} options.limits
 * @returns {Promise<string | null>}
 */
export async function buildResearchContext({ root, taskPath, limits }) {
  if ((await containedPath(root, taskPath)) === null) return null;
  const parts = [await buildSpecDirectoryOverview(root)];
  const budget = new Budget(limits.maxTotalBytes);
  const manifestPath = `${taskPath.replace(/\/+$/, "")}/research.jsonl`;
  const entries = await readManifest(root, manifestPath);
  if (entries.length > 0) {
    for (const entry of entries) {
      if (entry.type === "directory") {
        parts.push(
          ...(await materializeDirectory({
            root,
            dirPath: entry.file,
            reason: entry.reason,
            limits,
            budget,
          })),
        );
        continue;
      }
      const block = await materializeFile({
        root,
        filePath: entry.file,
        reason: entry.reason,
        limits,
        budget,
      });
      if (block !== null) parts.push(block);
    }
  }
  return parts.join("\n\n");
}

/**
 * Build the curated context for one role.
 * @param {object} options
 * @param {string} options.root
 * @param {string} options.taskPath - repo-relative task directory.
 * @param {string} options.role
 * @param {{maxFileBytes: number, maxArtifactBytes: number, maxTotalBytes: number}} options.limits
 * @returns {Promise<string | null>}
 */
export async function buildSubagentContext({ root, taskPath, role, limits }) {
  if (role === "research") {
    return buildResearchContext({ root, taskPath, limits });
  }
  const taskDir = await containedPath(root, taskPath);
  if (taskDir === null) return null;
  const budget = new Budget(limits.maxTotalBytes);
  const parts = [];
  const manifest = ROLE_MANIFEST[role] ?? ROLE_MANIFEST.implement;
  const manifestPath = `${taskPath.replace(/\/+$/, "")}/${manifest}`;
  const entries = await readManifest(root, manifestPath);

  if (entries.length === 0) {
    parts.push(
      `[Trellis] ${manifestPath} has no curated entries, so no spec/research ` +
        "context was injected. Before working, read the guidelines relevant to " +
        "the code you will touch under .trellis/spec/, and treat the task " +
        "artifacts below as the only prepared context.",
    );
  } else {
    for (const entry of entries) {
      if (entry.type === "directory") {
        parts.push(
          ...(await materializeDirectory({
            root,
            dirPath: entry.file,
            reason: entry.reason,
            limits,
            budget,
          })),
        );
        continue;
      }
      const block = await materializeFile({
        root,
        filePath: entry.file,
        reason: entry.reason,
        limits,
        budget,
      });
      if (block !== null) parts.push(block);
    }
  }

  for (const artifact of TASK_ARTIFACTS) {
    const filePath = `${taskPath.replace(/\/+$/, "")}/${artifact.file}`;
    const cap = limits.maxArtifactBytes;
    const full = await containedPath(root, filePath);
    if (full === null) continue;
    let bytes;
    try {
      bytes = await readFile(full);
    } catch {
      continue;
    }
    const truncated = cap > 0 && bytes.length > cap;
    const content = truncated
      ? `${truncateUtf8(bytes.toString("utf8"), cap)}\n[Trellis: truncated at ${cap} bytes — read ${filePath} for the full content]`
      : bytes.toString("utf8");
    parts.push(
      budgetedBlock(
        budget,
        `${filePath} (${artifact.label})`,
        filePath,
        content,
        artifact.label,
        bytes.length,
      ),
    );
  }

  return parts.length === 0 ? null : parts.join("\n\n");
}

/**
 * Render the pushed message: role contract first, curated task context second.
 * This is the DSH equivalent of Codex's agent TOML `developer_instructions`
 * plus `SubagentStart` context in one child-visible message.
 *
 * The preamble is the single authoritative statement about where the task
 * context comes from. When the role skill is inlined, the message also tells
 * the child not to load that skill again: the dispatch prompt and the on-disk
 * skill both say "load the role skill", and following them would both waste
 * tokens and re-read artifacts this message already carries.
 *
 * @param {object} options
 * @param {string} options.role
 * @param {string} options.taskPath
 * @param {string} options.context
 * @param {string | null} [options.roleInstructions]
 * @returns {ReturnType<typeof createUserMessage>}
 */
export function subagentContextMessage({ role, taskPath, context, roleInstructions = null }) {
  const inlined = roleInstructions !== null;
  const contract = inlined ? roleInstructions : roleInstructionsFallback(role);
  const skillPrecedence = inlined
    ? `The complete \`trellis-agent-${role}\` role skill is included immediately below. ` +
      `Do not load \`.dsh/skills/trellis-agent-${role}/SKILL.md\` again, and ignore any ` +
      "\"load the task context yourself\" step inside it — this message already carries " +
      "the task context."
    : contract;
  const text = [
    "<!-- trellis-hook-injected -->",
    `# Trellis Native ${role[0].toUpperCase()}${role.slice(1)} Subagent`,
    "",
    `You are the dispatched \`trellis-${role}\` role for this task. Perform that role`,
    "directly; do not follow main-session dispatch or wait instructions, and do not",
    "spawn another Trellis subagent.",
    "",
    `Active task: ${taskPath}`,
    "",
    "## Role Instructions",
    "",
    "The task context was prepared by dsh-trellis before this message: do not run",
    "`task.py current`, do not ask the user for a task path, and do not re-read task",
    "artifacts to discover the task — they are included below.",
    "",
    skillPrecedence,
    "",
    ...(inlined ? [contract, ""] : []),
    "Apply the role instructions as written, and still read any additional specs",
    "they name.",
    "",
    "## Curated Context",
    "",
    context,
  ].join("\n");
  return createUserMessage({
    content: [{ type: "text", text }],
    source: { kind: SOURCE_KIND, form: SOURCE_FORM, role, task: taskPath },
  });
}

/**
 * Resolve the active task from the delegating parent's session pointer.
 * @param {string} root
 * @param {string} parentSessionId
 * @returns {Promise<string | null>}
 */
export async function parentTaskPath(root, parentSessionId) {
  if (typeof parentSessionId !== "string" || parentSessionId === "") return null;
  const contextKey = `dsh_${sanitizeContextKey(parentSessionId)}`;
  const task = await resolveActiveTask(root, contextKey, nodeFs);
  // A stale pointer names a directory that no longer exists; there is no task
  // context to push for it.
  if (task === null || task.status === "task_error" || task.status === "stale") {
    return null;
  }
  return task.path;
}

/**
 * Register the first-step push for Trellis role sub-agents.
 *
 * @param {import("@deepseek-ai/cordis").Context} ctx
 * @param {{projectRootMarkers: string[]}} resolved
 * @returns {() => void} disposer.
 */
export function registerSubagentContext(ctx, resolved) {
  const injected = new Set();
  const identity = registerSubagentIdentity(ctx);
  let disposed = false;
  const warn = (error) => {
    ctx.logger?.warn?.("dsh-trellis subagent context push failed: %o", error);
  };

  const disposeStep = ctx.on("agent/pre-step", async (payload, next) => {
    const decision = await next();
    if (disposed || decision.kind === "reject") return decision;
    if (payload.step !== 1) return decision;
    const agent = payload.agent;
    const header = agent?.session?.header;
    if (!header?.parentSession) return decision;
    const id = agent.session.id ?? header.id ?? "";
    if (id === "" || injected.has(id)) return decision;
    try {
      const parsed = parseDispatchPrompt(
        decision.messages,
        identity.labelOf(agent.session),
      );
      if (parsed.role === null) return decision;
      const cwd = await resolveWorkingDirectory(ctx, agent, payload.signal);
      const root = await findProjectRoot(cwd, [".trellis"], nodeFs);
      if (root === null) return decision;
      const taskPath =
        parsed.taskPath ?? (await parentTaskPath(root, header.parentSession));
      if (taskPath === null) return decision;
      const configText = await nodeFs.readFile(join(root, ".trellis", "config.yaml"));
      const limits = contextInjectionLimits(configText);
      const context = await buildSubagentContext({
        root,
        taskPath,
        role: parsed.role,
        limits,
      });
      if (context === null) return decision;
      const roleInstructions = await readRoleInstructions({
        root,
        role: parsed.role,
      });
      injected.add(id);
      const message = subagentContextMessage({
        role: parsed.role,
        taskPath,
        context,
        roleInstructions,
      });
      return { ...decision, messages: [...decision.messages, message] };
    } catch (error) {
      warn(error);
      return decision;
    }
  });

  return () => {
    disposed = true;
    disposeStep();
    injected.clear();
    identity.dispose();
  };
}
