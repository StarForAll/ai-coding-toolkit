import { test } from "node:test";
import assert from "node:assert/strict";
import { parseVersionOutput, probeLocalVersions } from "../lib/local-version.js";

test("parseVersionOutput accepts release, prerelease and prefixed output", () => {
  assert.equal(parseVersionOutput("0.2.1-rc.2\n"), "0.2.1-rc.2");
  assert.equal(parseVersionOutput("v0.7.0-beta.4"), "0.7.0-beta.4");
  assert.equal(parseVersionOutput("trellis 0.7.0"), "0.7.0");
  assert.equal(parseVersionOutput("0.6.0-rc.0\r\n"), "0.6.0-rc.0");
  assert.equal(parseVersionOutput(""), null);
  assert.equal(parseVersionOutput("no version here"), null);
  assert.equal(parseVersionOutput(undefined), null);
});

test("probeLocalVersions runs the fixed commands and collects versions", async () => {
  const calls = [];
  const result = await probeLocalVersions({
    execFileImpl: async (command, args, options) => {
      calls.push({ command, args, options });
      return { stdout: command === "dsh" ? "0.2.1-rc.2\n" : "0.7.0-beta.4\n" };
    },
    platform: "linux",
    timeoutMs: 1234,
  });
  assert.deepEqual(result.versions, { dsh: "0.2.1-rc.2", trellis: "0.7.0-beta.4" });
  assert.deepEqual(result.errors, []);
  assert.deepEqual(calls.map((call) => [call.command, call.args]), [
    ["dsh", ["--version"]],
    ["trellis", ["-v"]],
  ]);
  assert.equal(calls[0].options.timeout, 1234);
  assert.equal(calls[0].options.shell, false);
  assert.equal(calls[0].options.windowsHide, true);
});

test("a Windows probe goes through the shell for .cmd shims", async () => {
  const shells = [];
  await probeLocalVersions({
    execFileImpl: async (command, args, options) => {
      shells.push(options.shell);
      return { stdout: "1.2.3" };
    },
    platform: "win32",
  });
  assert.deepEqual(shells, [true, true]);
});

test("probe failures are per probe and never hide the other result", async () => {
  const result = await probeLocalVersions({
    execFileImpl: async (command) => {
      if (command === "dsh") {
        const error = new Error("spawn dsh ENOENT");
        error.code = "ENOENT";
        throw error;
      }
      return { stdout: "0.7.0-beta.4" };
    },
    platform: "linux",
  });
  assert.deepEqual(result.versions, { trellis: "0.7.0-beta.4" });
  assert.equal(result.errors.length, 1);
  assert.equal(result.errors[0].id, "dsh");
  assert.match(result.errors[0].message, /not found on PATH/);
});

test("a timeout and unparsable output are reported without throwing", async () => {
  const result = await probeLocalVersions({
    execFileImpl: async (command) => {
      if (command === "dsh") {
        const error = new Error("Command failed");
        error.killed = true;
        throw error;
      }
      return { stdout: "unknown\n" };
    },
    platform: "linux",
    timeoutMs: 10,
  });
  assert.deepEqual(result.versions, {});
  assert.deepEqual(result.errors.map((entry) => entry.id), ["dsh", "trellis"]);
  assert.match(result.errors[0].message, /timed out after 10 ms/);
  assert.match(result.errors[1].message, /no parsable version/);
});
