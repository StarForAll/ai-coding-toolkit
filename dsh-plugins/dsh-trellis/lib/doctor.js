/**
 * `/trellis-doctor`: a JS-only diagnostic that still works when the project's
 * Python runtime does not.
 *
 * The other two commands shell out to `.trellis/scripts/task.py`, so they fail
 * exactly when a broken Python toolchain is the problem. Doctor answers the
 * questions that need no Trellis script: is this a Trellis project, which
 * workflow is wired, which version is installed, is spec injection on, is the
 * active task readable, and is another Trellis plugin competing with this one.
 *
 * Version monitoring here is local-only: it reports the installed plugin and
 * Trellis versions and never performs a network check.
 *
 * @module dsh-trellis/doctor
 */
import { readFile } from "node:fs/promises";
import { join, relative } from "node:path";
import { detectTrellisConflicts } from "./conflicts.js";
import { nodeFs } from "./node-fs.js";
import { loadSpecIndex } from "./spec-index.js";
import { specInjectionSettings } from "./trellis-config.js";
import {
  dshDispatchMode,
  findProjectRoot,
  parseWorkflowStateBlocks,
  resolveActiveTask,
  resolveWorkflowPath,
} from "./workflow.js";
import { dshContextKey } from "./session-env.js";
import { resolveWorkingDirectory } from "./working-directory.js";

let cachedVersion;

/** Read this package's version once. */
export async function pluginVersion() {
  if (cachedVersion !== undefined) return cachedVersion;
  try {
    const text = await readFile(new URL("../package.json", import.meta.url), "utf8");
    cachedVersion = JSON.parse(text).version ?? "unknown";
  } catch {
    cachedVersion = "unknown";
  }
  return cachedVersion;
}

/** Whether a message is a plain diagnostic line command input. */
function acceptNoInput(invocation) {
  const raw = invocation?.rawInput ?? "";
  const attachments = invocation?.attachments ?? [];
  return String(raw).trim() === "" && attachments.length === 0;
}

/**
 * Describe the active task without guessing.
 * @param {string} root
 * @param {string} sessionId
 * @param {object} fs
 * @returns {Promise<string>}
 */
async function describeTask(root, sessionId, fs) {
  const contextKey = dshContextKey(sessionId);
  if (contextKey === "") return "none (no DSH session identity)";
  const task = await resolveActiveTask(root, contextKey, fs);
  if (task === null) return "none (no_task)";
  if (task.status === "task_error") {
    return `${task.path} (task_error: repair task.json before continuing)`;
  }
  return `${task.path} (${task.status})`;
}

/**
 * Build the report text.
 *
 * @param {object} options
 * @param {string} options.root
 * @param {string} options.cwd
 * @param {string} options.sessionId
 * @param {object} options.fs
 * @param {string} options.version
 * @param {ReturnType<typeof detectTrellisConflicts>} options.conflicts
 * @returns {Promise<string>}
 */
export async function collectDoctorReport({
  root,
  cwd,
  sessionId,
  fs = nodeFs,
  version,
  conflicts,
}) {
  const trellisVersion = (await fs.readFile(join(root, ".trellis", ".version")))?.trim();
  const contextKey = dshContextKey(sessionId);
  const active = contextKey === "" ? null : await resolveActiveTask(root, contextKey, fs);
  const workflowPath = await resolveWorkflowPath({
    root,
    taskWorkflow: active?.workflow ?? null,
    fs,
    cache: new Map(),
  });
  const workflowFile = relative(root, workflowPath).split("\\").join("/");
  const workflow = await fs.readFile(workflowPath);
  const blocks = workflow === null ? 0 : parseWorkflowStateBlocks(workflow).size;
  const configText = await fs.readFile(join(root, ".trellis", "config.yaml"));
  const settings = specInjectionSettings(configText);
  const dispatchMode = dshDispatchMode(configText);
  const specs = settings.enabled ? await loadSpecIndex(root, new Map()) : [];
  const label =
    conflicts.status === "checked"
      ? conflicts.conflicts.length === 0
        ? "none"
        : conflicts.conflicts.map((entry) => entry.name).join(", ")
      : `${conflicts.status} (conflict detection did not complete)`;

  return [
    "Trellis doctor",
    `  Project root: ${root}`,
    `  Working directory: ${cwd}`,
    `  Plugin: dsh-trellis ${version}`,
    `  Trellis: ${trellisVersion || "unknown (.trellis/.version missing)"}`,
    `  Workflow: ${workflow === null ? `missing ${workflowFile}` : `${blocks} [workflow-state:*] blocks`}`,
    `  Workflow file: ${workflowFile}`,
    `  Dispatch mode: ${dispatchMode} (dsh.dispatch_mode)`,
    `  Active task: ${await describeTask(root, sessionId, fs)}`,
    settings.enabled
      ? `  Spec injection: enabled (${specs.length} specs declare paths)`
      : "  Spec injection: disabled by .trellis/config.yaml",
    `  Plugin conflicts: ${label}`,
    "  Version monitoring: local versions shown here; upstream commits are checked in Settings → Trellis",
  ].join("\n");
}

/**
 * Register `/trellis-doctor`.
 *
 * @param {import("@deepseek-ai/cordis").Context} ctx
 * @param {object} resolved - normalized plugin config.
 * @param {{fs?: object, conflicts?: typeof detectTrellisConflicts,
 *   version?: () => Promise<string>}} [dependencies]
 * @returns {() => void} disposer.
 */
export function registerDoctorCommand(ctx, resolved, dependencies = {}) {
  const fs = dependencies.fs ?? nodeFs;
  const conflicts = dependencies.conflicts ?? detectTrellisConflicts;
  const version = dependencies.version ?? pluginVersion;

  return ctx.commands.register({
    name: "trellis-doctor",
    description:
      "Diagnose the Trellis project, plugin wiring, spec injection, and plugin conflicts without running Trellis Python.",
    recordInput: false,
    handler: async (invocation) => {
      if (!acceptNoInput(invocation)) {
        return {
          kind: "error",
          text: "This Trellis command does not accept arguments or image attachments.",
        };
      }
      let cwd;
      try {
        cwd = await resolveWorkingDirectory(ctx, invocation?.agent, invocation?.signal);
      } catch (error) {
        return {
          kind: "error",
          text: invocation?.signal?.aborted
            ? "Trellis command cancelled."
            : `Cannot resolve the current DSH working directory: ${error?.message ?? String(error)}`,
        };
      }
      const root = await findProjectRoot(cwd, resolved.projectRootMarkers, fs);
      if (root === null) {
        return {
          kind: "error",
          text: `No project root found from the configured markers (${resolved.projectRootMarkers.join(", ")}).`,
        };
      }
      const sessionId = invocation?.agent?.session?.header?.id ?? "";
      return {
        kind: "success",
        text: await collectDoctorReport({
          root,
          cwd,
          sessionId,
          fs,
          version: await version(),
          conflicts: conflicts(ctx),
        }),
      };
    },
  });
}
