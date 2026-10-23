/**
 * Host-side local CLI version probe.
 *
 * The settings page compares the official npm packages with what is installed
 * on this machine, so the Host runs the two fixed CLIs and returns their
 * versions. Only constant command names and arguments are executed; nothing
 * from the request reaches the process call.
 *
 * @module dsh-trellis/local-version
 */

import { execFile } from "node:child_process";
import { promisify } from "node:util";

const execFileAsync = promisify(execFile);

/** Fixed probes; the ids mirror the npm source ids on the client. */
export const LOCAL_PROBES = Object.freeze([
  Object.freeze({ id: "dsh", command: "dsh", args: Object.freeze(["--version"]) }),
  Object.freeze({ id: "trellis", command: "trellis", args: Object.freeze(["-v"]) }),
]);

/**
 * Extract a version from CLI output.
 *
 * Accepts `0.2.1-rc.2`, `v0.7.0-beta.4`, or a prefixed form such as
 * `trellis 0.7.0`; anything else is "unknown" rather than a guess.
 *
 * @param {unknown} text
 * @returns {string | null}
 */
export function parseVersionOutput(text) {
  const firstLine = String(text ?? "").split(/\r?\n/)[0] ?? "";
  const match = /(?:^|\s)v?(\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?)/.exec(firstLine.trim());
  return match === null ? null : match[1];
}

/**
 * Probe the local `dsh` and `trellis` CLIs.
 *
 * A missing binary, a timeout, or unparsable output is reported per probe and
 * never rejects: one unavailable CLI must not hide the other result.
 *
 * @param {object} [options]
 * @param {(command: string, args: string[], options: object) => Promise<{stdout: string}>} [options.execFileImpl]
 * @param {number} [options.timeoutMs]
 * @param {ReadonlyArray<{id: string, command: string, args: readonly string[]}>} [options.probes]
 * @param {NodeJS.Platform} [options.platform]
 * @returns {Promise<{versions: Record<string, string>, errors: Array<{id: string, message: string}>}>}
 */
export async function probeLocalVersions({
  execFileImpl,
  timeoutMs = 5_000,
  probes = LOCAL_PROBES,
  platform = process.platform,
} = {}) {
  const run = execFileImpl ?? execFileAsync;
  const versions = {};
  const errors = [];
  await Promise.all(probes.map(async (probe) => {
    try {
      const result = await run(probe.command, [...probe.args], {
        timeout: timeoutMs,
        windowsHide: true,
        // Windows resolves `dsh`/`trellis` shims (.cmd) through the shell. The
        // command and arguments are constants, so nothing is interpolated.
        shell: platform === "win32",
        maxBuffer: 64 * 1024,
      });
      const version = parseVersionOutput(result?.stdout);
      if (version === null) {
        errors.push({ id: probe.id, message: `${probe.command} returned no parsable version` });
        return;
      }
      versions[probe.id] = version;
    } catch (error) {
      const code = error?.code;
      const message = code === "ENOENT"
        ? `${probe.command} was not found on PATH`
        : code === "ETIMEDOUT" || error?.killed
          ? `${probe.command} timed out after ${timeoutMs} ms`
          : `${probe.command} failed: ${error?.message ?? String(error)}`;
      errors.push({ id: probe.id, message });
    }
  }));
  return { versions, errors };
}
