/**
 * Shared Trellis-project resolution for the plugin's runtime layers.
 *
 * Every capability needs the same three answers: the working directory this
 * call runs in, the directory that owns `.trellis`, and that project's
 * `.trellis/config.yaml`. Keeping one implementation means the spec policy, the
 * dispatch guard, and any future capability cannot disagree about the root.
 *
 * @module dsh-trellis/project
 */
import { join } from "node:path";
import { nodeFs } from "./node-fs.js";
import { findProjectRoot, readCached } from "./workflow.js";
import { resolveWorkingDirectory } from "./working-directory.js";

/** The directory owning `.trellis` is the only marker every capability needs. */
export const TRELLIS_MARKERS = Object.freeze([".trellis"]);

/**
 * Resolve the current Trellis project for one agent invocation.
 *
 * @param {object} options
 * @param {import("@deepseek-ai/cordis").Context} options.ctx
 * @param {any} options.agent
 * @param {AbortSignal | undefined} options.signal
 * @param {object} [options.fs] - filesystem shim.
 * @param {Map<string, {mtimeMs: number, content: string | null}>} [options.cache]
 * @returns {Promise<{root: string, configText: string | null, cwd: string} | null>}
 */
export async function resolveTrellisProject({
  ctx,
  agent,
  signal,
  fs = nodeFs,
  cache,
}) {
  const cwd = await resolveWorkingDirectory(ctx, agent, signal);
  const root = await findProjectRoot(cwd, TRELLIS_MARKERS, fs);
  if (root === null) return null;
  const configPath = join(root, ".trellis", "config.yaml");
  const configText = cache
    ? await readCached(configPath, fs, cache)
    : await fs.readFile(configPath);
  return { root, configText, cwd };
}
