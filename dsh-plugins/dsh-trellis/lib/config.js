/**
 * dsh-trellis plugin configuration (Schemastery).
 *
 * @module dsh-trellis/config
 */
import z from "@deepseek-ai/schemastery";
import * as settingsModule from "@deepseek-ai/dsh-settings";

const fields = {
  /** Runtime master switch; the settings namespace remains available for re-enabling. */
  enabled: z
    .boolean()
    .default(true)
    .description(
      "Enable Trellis breadcrumbs, commands, session facts, and the wait tool for this profile.",
    ),
  /** UTF-8 byte budget for the injected breadcrumb text. 0 disables injection. */
  maxBytes: z
    .number()
    .step(1)
    .min(0)
    .default(4096)
    .description(
      "Maximum UTF-8 bytes in a workflow-state breadcrumb; 0 disables breadcrumbs.",
    ),
  /**
   * Directory markers that identify a project root while walking upward from
   * the session cwd. `.trellis` comes first so a Trellis project is found even
   * when it is not a Git checkout (Codex locates the root by `.trellis/` too);
   * `.git` remains accepted for repositories that keep `.trellis` elsewhere.
   */
  projectRootMarkers: z
    .array(z.string())
    .default([".trellis", ".git"])
    .description(
      "Directory entries used while walking upward to find the project root; .trellis keeps non-Git Trellis projects working.",
    ),
  /** Standalone word (case-insensitive) in the user prompt that skips breadcrumb injection for that turn. Empty disables. */
  skipKeyword: z
    .string()
    .default("no-trellis")
    .description(
      "Standalone prompt keyword that skips breadcrumb injection for the whole turn (every step it triggers); empty disables the escape hatch.",
    ),
  /** Python executable used by /trellis commands. Empty selects a platform-aware fallback chain. */
  pythonCmd: z
    .string()
    .default("")
    .description(
      "Python 3 executable for Trellis scripts; empty selects a platform-aware launcher chain.",
    ),
  /** Register the deterministic /trellis-status and read-only /trellis-finish commands. */
  commandsEnabled: z
    .boolean()
    .default(true)
    .description(
      "Register /trellis-status and the read-only /trellis-finish helper.",
    ),
  /**
   * Path-scoped spec injection. `.trellis/config.yaml` (`spec_injection.enabled`)
   * remains the per-project authority; this is the profile-level switch.
   */
  specInjection: z
    .boolean()
    .default(true)
    .description(
      "Inject matching .trellis/spec documents when a tool touches a file (deny-once on edit/write, context on later touches).",
    ),
  /** Push curated task context before a Trellis role sub-agent's first step. */
  subagentContext: z
    .boolean()
    .default(true)
    .description(
      "Push prd/design/implement plus the role manifest before a trellis-agent-* child's first model request.",
    ),
  /**
   * Refuse a trellis-agent-implement/check dispatch that has no readable task.
   * Stricter than Codex, which silently injects nothing and lets the child run.
   */
  dispatchGuard: z
    .boolean()
    .default(true)
    .description(
      "Fail closed when a trellis-agent-implement/check dispatch has no readable task; research is allowed and reminded to confirm its output location.",
    ),
  /** Version monitoring master switch (client-side; no host network access). */
  versionCheck: z
    .boolean()
    .default(true)
    .description(
      "Watch this plugin, Trellis, and DSH upstream repositories for new commits from the settings page.",
    ),
  /** Auto-check interval in minutes; 0 = manual checks only. */
  versionCheckIntervalMinutes: z
    .number()
    .step(1)
    .min(0)
    .default(1440)
    .description(
      "Minutes between automatic upstream commit checks; 0 keeps monitoring manual-only.",
    ),
  /** Notify on a new upstream commit (browser desktop notification). */
  versionCheckNotify: z
    .boolean()
    .default(true)
    .description(
      "Show a browser notification when an upstream repository gains a new commit.",
    ),
  /** Probe the local dsh/trellis CLIs so npm rows compare installed versions. */
  versionCheckLocalProbe: z
    .boolean()
    .default(true)
    .description(
      "Run `dsh --version` and `trellis -v` on this machine so the npm sources compare installed versions with the published channel; a failed probe is reported as unknown, never guessed.",
    ),
  /** Upstream fork whose improvements this plugin absorbs (commit watch). */
  versionCheckPluginRepo: z
    .string()
    .default("https://github.com/SajoLuo/dsh-trellis")
    .description(
      "GitHub fork repository this plugin absorbs improvements from; owner/repo or a full URL. Monitored by commit.",
    ),
  /** Official Trellis npm package whose published versions are watched. */
  versionCheckTrellisPackage: z
    .string()
    .default("@mindfoldhq/trellis")
    .description(
      "npm package of Trellis; its published dist-tags are compared like `npm view` does.",
    ),
  /** Official DSH npm package whose published versions are watched. */
  versionCheckDshPackage: z
    .string()
    .default("@deepseek-ai/dsh")
    .description(
      "npm package of DeepSeek Harness; its published dist-tags are compared like `npm view` does.",
    ),
};

// Legacy Settings validates plain values; profile-backed Settings exposes only
// volatile fields. Select the schema from the host capability, not a version.
export const Config = z.object(Object.fromEntries(
  Object.entries(fields).map(([key, field]) => [key,
    typeof settingsModule.SettingsForms === "function" ? field.volatile() : field,
  ]),
));

export function hasLiveConfig(config) {
  return Object.values(config).some((value) =>
    value !== null && typeof value === "object" &&
    Symbol.for("cosmokit.volatile.write") in value,
  );
}

/**
 * Normalized runtime configuration.
 * @param {Partial<Record<string, unknown>>} config
 * @returns {{
 *   enabled: boolean,
 *   maxBytes: number,
 *   projectRootMarkers: string[],
 *   skipKeyword: string,
 *   pythonCmd: string,
 *   commandsEnabled: boolean,
 *   specInjection: boolean,
 *   subagentContext: boolean,
 *   dispatchGuard: boolean,
 *   versionCheck: boolean,
 *   versionCheckIntervalMinutes: number,
 *   versionCheckNotify: boolean,
 *   versionCheckPluginRepo: string,
 *   versionCheckTrellisPackage: string,
 *   versionCheckDshPackage: string,
 * }}
 */
export function resolveConfig(config) {
  config = Object.fromEntries(Object.entries(config).map(([key, value]) => [key,
    value !== null && typeof value === "object" &&
    Symbol.for("cosmokit.volatile.write") in value ? value.get() : value,
  ]));
  return {
    enabled: config.enabled !== false,
    maxBytes: config.maxBytes ?? 4096,
    projectRootMarkers: config.projectRootMarkers ?? [".trellis", ".git"],
    skipKeyword: config.skipKeyword ?? "no-trellis",
    pythonCmd:
      typeof config.pythonCmd === "string" ? config.pythonCmd.trim() : "",
    commandsEnabled: config.commandsEnabled !== false,
    specInjection: config.specInjection !== false,
    subagentContext: config.subagentContext !== false,
    dispatchGuard: config.dispatchGuard !== false,
    versionCheck: config.versionCheck !== false,
    versionCheckIntervalMinutes:
      typeof config.versionCheckIntervalMinutes === "number" &&
      config.versionCheckIntervalMinutes >= 0
        ? config.versionCheckIntervalMinutes
        : 1440,
    versionCheckNotify: config.versionCheckNotify !== false,
    versionCheckPluginRepo:
      typeof config.versionCheckPluginRepo === "string" &&
      config.versionCheckPluginRepo.trim() !== ""
        ? config.versionCheckPluginRepo.trim()
        : "https://github.com/SajoLuo/dsh-trellis",
    versionCheckTrellisPackage:
      typeof config.versionCheckTrellisPackage === "string" &&
      config.versionCheckTrellisPackage.trim() !== ""
        ? config.versionCheckTrellisPackage.trim()
        : "@mindfoldhq/trellis",
    versionCheckDshPackage:
      typeof config.versionCheckDshPackage === "string" &&
      config.versionCheckDshPackage.trim() !== ""
        ? config.versionCheckDshPackage.trim()
        : "@deepseek-ai/dsh",
  };
}
