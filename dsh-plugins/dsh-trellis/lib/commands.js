/**
 * Human-facing /trellis commands: status and finish.
 *
 * Command names follow the dsh grammar (lowercase letters, digits, `_`, `-`;
 * no `:`), and deliberately avoid the skill names (`trellis-start`,
 * `trellis-continue`, `trellis-finish-work`): a command sharing a skill name
 * would shadow the skill's slash-pipeline injection. The Trellis session
 * rituals stay on the skill surface; these commands cover the deterministic,
 * zero-token side — pointer inspection and wrap-up.
 *
 * @module dsh-trellis/commands
 */
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { join } from "node:path";
import { findProjectRoot } from "./workflow.js";
import { nodeFs } from "./node-fs.js";
import { dshContextKey } from "./session-env.js";
import { resolveWorkingDirectory } from "./working-directory.js";

const execFileAsync = promisify(execFile);

/** Platform-aware Python launch candidates. An explicit config disables fallback. */
export function pythonCandidates(config, platform = process.platform) {
  if (config.pythonCmd) return [{ command: config.pythonCmd, prefixArgs: [] }];
  if (platform === "win32") {
    return [
      { command: "py", prefixArgs: ["-3"] },
      { command: "python", prefixArgs: [] },
    ];
  }
  return [
    { command: "python3", prefixArgs: [] },
    { command: "python", prefixArgs: [] },
  ];
}

/** Run a project Trellis script with bounded time and output. */
export async function runTrellisScript(
  config,
  root,
  sessionId,
  scriptArgs,
  dependencies = {},
) {
  const execute = dependencies.execFile ?? execFileAsync;
  const platform = dependencies.platform ?? process.platform;
  const signal = dependencies.signal;
  const contextKey = dshContextKey(sessionId);
  const env = {
    ...process.env,
    ...(contextKey
      ? {
          TRELLIS_CONTEXT_ID: contextKey,
          DSH_TRELLIS_CONTEXT_ID: contextKey,
          DSH_SHELL: "1",
          DSH_SESSION_ID: sessionId,
        }
      : {}),
  };
  const script = join(root, ".trellis", "scripts", "task.py");
  const candidates = pythonCandidates(config, platform);
  for (const [index, candidate] of candidates.entries()) {
    const args = [...candidate.prefixArgs, script, ...scriptArgs];
    try {
      const { stdout, stderr } = await execute(candidate.command, args, {
        cwd: root,
        env,
        windowsHide: true,
        timeout: 15_000,
        maxBuffer: 256 * 1024,
        ...(signal ? { signal } : {}),
      });
      const text = `${stdout}${stderr ? `\n${stderr}` : ""}`.trim();
      return { kind: "success", text, code: 0, stdout, stderr };
    } catch (error) {
      if (signal?.aborted || error?.name === "AbortError") {
        return {
          kind: "error",
          text: "Trellis command cancelled.",
          code: null,
          stdout: "",
          stderr: "",
        };
      }
      // Keep the child's output even on a non-zero exit: Trellis's `current`
      // documents exit 1 for "no active task" and still prints its payload to
      // stdout, so the caller must be able to inspect it.
      const stdout = typeof error?.stdout === "string" ? error.stdout : "";
      const stderr = typeof error?.stderr === "string" ? error.stderr : "";
      const code = Number.isInteger(error?.code) ? error.code : null;
      const missing = error?.code === "ENOENT";
      if (missing && index < candidates.length - 1) continue;
      const attempted = candidates
        .slice(0, index + 1)
        .map(({ command, prefixArgs }) => [command, ...prefixArgs].join(" "))
        .join(", ");
      let message;
      if (missing) {
        message = `Python command not found (tried: ${attempted}). Set the plugin's pythonCmd config to a Python 3 executable.`;
      } else {
        const detail = [stderr.trim(), stdout.trim()].filter(Boolean).join("\n");
        message = `Trellis script failed via ${[candidate.command, ...candidate.prefixArgs].join(" ")}: ${error?.message ?? String(error)}`;
        if (detail !== "") message += `\n${detail}`;
      }
      return { kind: "error", text: message, code, stdout, stderr };
    }
  }
  return {
    kind: "error",
    text: "No Python command candidates are configured.",
    code: null,
    stdout: "",
    stderr: "",
  };
}

/**
 * Parse the machine-readable `task.py current --json` payload.
 *
 * Trellis has returned this shape since at least 0.6.17: `current_task` is
 * either `null` or an object with a non-empty `dir`, alongside `source` and
 * `stale`. Anything else is not the contract this command set understands.
 *
 * @param {string} stdout
 * @returns {{current_task: object | null, source?: string, stale?: boolean, error?: object} | null}
 */
export function parseCurrentTaskPayload(stdout) {
  if (typeof stdout !== "string" || stdout.trim() === "") return null;
  let payload;
  try {
    payload = JSON.parse(stdout);
  } catch {
    return null;
  }
  if (payload === null || typeof payload !== "object" || Array.isArray(payload)) {
    return null;
  }
  if (!Object.hasOwn(payload, "current_task")) return null;
  const task = payload.current_task;
  if (task !== null) {
    if (typeof task !== "object" || Array.isArray(task)) return null;
    if (typeof task.dir !== "string" || task.dir.trim() === "") return null;
  }
  return payload;
}

/**
 * Render the parsed current-task payload for humans without inventing state.
 * @param {ReturnType<typeof parseCurrentTaskPayload>} payload
 */
export function formatCurrentTask(payload) {
  const source =
    typeof payload?.source === "string" && payload.source !== ""
      ? payload.source
      : "none";
  const task = payload?.current_task ?? null;
  if (task === null) {
    return {
      kind: "success",
      noTask: true,
      task: null,
      text: `Current task: (none)\nSource: ${source}`,
    };
  }
  const lines = [`Current task: ${task.dir}`];
  if (typeof task.status === "string" && task.status !== "") {
    lines.push(`Status: ${task.status}`);
  }
  if (typeof task.title === "string" && task.title !== "") {
    lines.push(`Title: ${task.title}`);
  }
  lines.push(`Source: ${source}`);
  if (payload.stale === true) lines.push("State: stale");
  if (typeof payload.error?.message === "string" && payload.error.message !== "") {
    lines.push(`Task record error: ${payload.error.message}`);
  }
  return { kind: "success", noTask: false, task, text: lines.join("\n") };
}

/** Trellis releases before 0.6.10 have no `current --json`; argparse exits 2. */
const LEGACY_JSON_REJECTED = /unrecognized arguments:\s*--json\b/i;

/**
 * Parse the documented `task.py current --source` output.
 *
 * This is the compatibility contract for Trellis releases whose `current`
 * predates `--json` (verified absent in 0.6.5 and earlier, present in 0.6.10+).
 * Only the documented `Current task: <path>` line is accepted; anything else
 * stays an error rather than inventing a task state.
 *
 * @param {string} stdout
 * @returns {{kind: "success", noTask: boolean, task: object | null, text: string} | null}
 */
export function parseLegacyCurrentTask(stdout) {
  if (typeof stdout !== "string") return null;
  const match = /^Current task:[ \t]*(.*)$/m.exec(stdout);
  if (match === null) return null;
  const value = match[1].trim();
  if (value === "") return null;
  const noTask = value === "(none)";
  return {
    kind: "success",
    noTask,
    task: noTask ? null : { dir: value },
    text: stdout.trim(),
  };
}

async function readLegacyCurrentTask(config, root, sessionId, dependencies) {
  const result = await runTrellisScript(
    config,
    root,
    sessionId,
    ["current", "--source"],
    dependencies,
  );
  if (result.kind === "success") {
    const parsed = parseLegacyCurrentTask(result.stdout);
    return parsed ?? {
      kind: "error",
      text: "Trellis returned an unreadable current-task output (expected `task.py current --source` text).",
    };
  }
  if (result.code === 1) {
    const parsed = parseLegacyCurrentTask(result.stdout);
    if (parsed !== null && parsed.noTask) return parsed;
  }
  return result;
}

/**
 * Read the session's active task through Trellis's machine-readable contract.
 *
 * `task.py current` exits 1 when there is no active task, which is a valid
 * answer, not a script failure. The only accepted exit-1 shape is a parseable
 * payload whose `current_task` is null; a Python traceback that also exits 1
 * stays an error.
 *
 * Trellis releases before 0.6.10 only have `current --source`. When the script
 * rejects `--json` as an unknown argument, fall back to that documented text
 * contract instead of failing the command.
 *
 * @param {object} config
 * @param {string} root
 * @param {string} sessionId
 * @param {object} [dependencies]
 * @returns {Promise<{kind: "success" | "error", noTask?: boolean, task?: object | null, text: string}>}
 */
export async function readCurrentTask(
  config,
  root,
  sessionId,
  dependencies = {},
) {
  const result = await runTrellisScript(
    config,
    root,
    sessionId,
    ["current", "--json"],
    dependencies,
  );
  if (result.kind === "success") {
    const payload = parseCurrentTaskPayload(result.stdout);
    return payload === null
      ? {
          kind: "error",
          text: "Trellis returned an unreadable current-task payload (expected `task.py current --json` JSON).",
        }
      : formatCurrentTask(payload);
  }
  const payload =
    result.code === 1 ? parseCurrentTaskPayload(result.stdout) : null;
  if (payload !== null && payload.current_task === null) {
    return formatCurrentTask(payload);
  }
  if (
    result.code === 2 &&
    LEGACY_JSON_REJECTED.test(result.stderr || result.text)
  ) {
    return readLegacyCurrentTask(config, root, sessionId, dependencies);
  }
  return result;
}

/**
 * Register the /trellis command family.
 * @param {object} ctx - cordis context exposing `ctx.commands`.
 * @param {object} resolved - normalized plugin config.
 * @returns {() => void} disposer.
 */
export function registerCommands(ctx, resolved, dependencies = {}) {
  const fs = dependencies.fs ?? nodeFs;
  const execute = dependencies.execFile ?? execFileAsync;
  const platform = dependencies.platform ?? process.platform;
  const disposers = [];

  const withoutInput = (invocation, fn) => {
    const rawInput = invocation.rawInput ?? "";
    const attachments = invocation.attachments ?? [];
    if (rawInput.trim() !== "" || attachments.length > 0) {
      return {
        kind: "error",
        text: "This Trellis command does not accept arguments or image attachments.",
      };
    }
    return fn();
  };

  const withProject = async (invocation, fn) => {
    let cwd;
    try {
      cwd = await resolveWorkingDirectory(ctx, invocation.agent, invocation.signal);
    } catch (error) {
      return {
        kind: "error",
        text: invocation.signal?.aborted
          ? "Trellis command cancelled."
          : `Cannot resolve the current DSH working directory: ${error?.message ?? String(error)}`,
      };
    }
    const root = await findProjectRoot(cwd, resolved.projectRootMarkers, fs);
    if (root === null) {
      return {
        kind: "error",
        text: "No project root found from the configured markers.",
      };
    }
    const workflow = join(root, ".trellis", "workflow.md");
    const taskScript = join(root, ".trellis", "scripts", "task.py");
    if (!(await fs.exists(workflow)) || !(await fs.exists(taskScript))) {
      return {
        kind: "error",
        text: "No Trellis project found (expected .trellis/workflow.md and .trellis/scripts/task.py).",
      };
    }
    const sessionId = invocation.agent?.session?.header?.id ?? "";
    return fn(root, sessionId, invocation.signal);
  };

  disposers.push(
    ctx.commands.register({
      name: "trellis-status",
      description: "Show the Trellis active task and git status.",
      // DSH rc.8 records command lifecycle events. These commands have no
      // payload of their own, so omit empty/invalid input from the durable log.
      recordInput: false,
      handler: (invocation) =>
        withoutInput(invocation, () =>
          withProject(invocation, async (root, sessionId, signal) => {
            const task = await readCurrentTask(resolved, root, sessionId, {
              execFile: execute,
              platform,
              signal,
            });
            if (signal?.aborted) return task;
            let git = "";
            try {
              const { stdout } = await execute(
                "git",
                ["status", "--short", "--branch"],
                {
                  cwd: root,
                  windowsHide: true,
                  timeout: 10_000,
                  maxBuffer: 128 * 1024,
                  ...(signal ? { signal } : {}),
                },
              );
              git = `\n\nGit status:\n${stdout.trim()}`;
            } catch {
              git = "";
            }
            const hint =
              task.kind === "success"
                ? `\n\nSession rituals: type /trellis-start (start), /trellis-continue (resume), /trellis-finish-work (skill wrap-up).`
                : "";
            return { kind: task.kind, text: `${task.text}${git}${hint}` };
          }),
        ),
    }),
  );

  disposers.push(
    ctx.commands.register({
      name: "trellis-finish",
      description:
        "Inspect the active task and print the safe wrap-up checklist.",
      recordInput: false,
      handler: (invocation) =>
        withoutInput(invocation, () =>
          withProject(invocation, async (root, sessionId, signal) => {
            const result = await readCurrentTask(resolved, root, sessionId, {
              execFile: execute,
              platform,
              signal,
            });
            if (signal?.aborted) return result;
            const checklist = result.noTask
              ? "No active task. Nothing to archive or record for a Trellis task.\n\nIf you expected an active task, run /trellis-status or inspect the session pointer before wrapping up."
              : 'Wrap-up checklist (this command did not clear or archive anything):\n  1. Commit this task\'s changes (workflow.md Phase 3.4; do not push).\n  2. Type /trellis-finish-work so the skill can archive the task before the pointer is removed and then record the session journal.\n\nIf you must do it manually, archive first with the configured Python 3 runtime: .trellis/scripts/task.py archive <task-name>; then run .trellis/scripts/add_session.py --title "..." --commit <hash> --summary "...".';
            return { kind: result.kind, text: `${result.text}\n\n${checklist}` };
          }),
        ),
    }),
  );

  return () => {
    for (const dispose of disposers) dispose();
  };
}
