import { test } from "node:test";
import assert from "node:assert/strict";
import { join, resolve } from "node:path";
import {
  parseCurrentTaskPayload,
  parseLegacyCurrentTask,
  pythonCandidates,
  readCurrentTask,
  registerCommands,
  runTrellisScript,
} from "../lib/commands.js";

const root = resolve("C:/trellis-command-test");

function projectFs({ trellis = true } = {}) {
  const paths = new Set([join(root, ".git")]);
  if (trellis) {
    paths.add(join(root, ".trellis", "workflow.md"));
    paths.add(join(root, ".trellis", "scripts", "task.py"));
  }
  return {
    async exists(path) {
      return paths.has(path);
    },
  };
}

function commandHarness() {
  const commands = new Map();
  const disposed = [];
  const ctx = {
    commands: {
      register(command) {
        commands.set(command.name, command);
        return () => disposed.push(command.name);
      },
    },
  };
  return { ctx, commands, disposed };
}

const resolved = {
  pythonCmd: "python-test",
  projectRootMarkers: [".git"],
};

const invocation = {
  agent: { session: { header: { cwd: join(root, "src"), id: "session one" } } },
  rawInput: "",
  attachments: [],
  signal: new AbortController().signal,
};

test("pythonCandidates uses platform-aware defaults and honors an override", () => {
  assert.deepEqual(pythonCandidates({ pythonCmd: "" }, "win32"), [
    { command: "py", prefixArgs: ["-3"] },
    { command: "python", prefixArgs: [] },
  ]);
  assert.deepEqual(pythonCandidates({ pythonCmd: "" }, "linux"), [
    { command: "python3", prefixArgs: [] },
    { command: "python", prefixArgs: [] },
  ]);
  assert.deepEqual(pythonCandidates({ pythonCmd: "custom-python" }, "win32"), [
    { command: "custom-python", prefixArgs: [] },
  ]);
});

test("runTrellisScript falls back after a missing Windows launcher and exports the session id", async () => {
  const previousOuterContext = process.env.TRELLIS_CONTEXT_ID;
  process.env.TRELLIS_CONTEXT_ID = "claude_outer-session";
  const calls = [];
  try {
    const result = await runTrellisScript(
      { pythonCmd: "" },
      root,
      "abc def",
      ["current", "--source"],
      {
        platform: "win32",
        async execFile(command, args, options) {
          calls.push({ command, args, options });
          if (command === "py")
            throw Object.assign(new Error("missing"), { code: "ENOENT" });
          return { stdout: "Current task: demo\n", stderr: "" };
        },
      },
    );

    assert.equal(result.kind, "success");
    assert.deepEqual(
      calls.map(({ command }) => command),
      ["py", "python"],
    );
    assert.deepEqual(calls[0].args.slice(0, 2), [
      "-3",
      join(root, ".trellis", "scripts", "task.py"),
    ]);
    assert.equal(calls[1].options.env.DSH_SESSION_ID, "abc def");
    assert.equal(calls[1].options.env.DSH_SHELL, "1");
    assert.equal(calls[1].options.env.TRELLIS_CONTEXT_ID, "dsh_abc_def");
    assert.equal(
      calls[1].options.env.DSH_TRELLIS_CONTEXT_ID,
      "dsh_abc_def",
    );
  } finally {
    if (previousOuterContext === undefined) {
      delete process.env.TRELLIS_CONTEXT_ID;
    } else {
      process.env.TRELLIS_CONTEXT_ID = previousOuterContext;
    }
  }
});

test("trellis-finish is read-only and command disposal unregisters both commands", async () => {
  const { ctx, commands, disposed } = commandHarness();
  const calls = [];
  const dispose = registerCommands(ctx, resolved, {
    fs: projectFs(),
    platform: "win32",
    async execFile(command, args, options) {
      calls.push({ command, args, options });
      return {
        stdout: JSON.stringify({
          current_task: { dir: ".trellis/tasks/demo", status: "in_progress" },
          source: "session",
          stale: false,
        }),
        stderr: "",
      };
    },
  });

  const result = await commands.get("trellis-finish").handler(invocation);
  assert.equal(result.kind, "success");
  assert.match(result.text, /did not clear or archive anything/);
  assert.equal(commands.get("trellis-status").recordInput, false);
  assert.equal(commands.get("trellis-finish").recordInput, false);
  assert.deepEqual(calls[0].args.slice(-2), ["current", "--json"]);
  assert.equal(calls[0].options.env.DSH_SESSION_ID, "session one");
  assert.equal(calls[0].options.env.DSH_SHELL, "1");
  assert.equal(calls[0].options.signal, invocation.signal);
  assert.ok(!calls[0].args.includes("finish"));

  dispose();
  assert.deepEqual(disposed.sort(), ["trellis-finish", "trellis-status"]);
});

test("zero-input commands reject rc.8 command envelope payloads before touching the project", async () => {
  const { ctx, commands } = commandHarness();
  let executed = false;
  registerCommands(ctx, resolved, {
    fs: projectFs(),
    async execFile() {
      executed = true;
      return { stdout: "", stderr: "" };
    },
  });

  const withText = await commands.get("trellis-status").handler({
    ...invocation,
    rawInput: " unexpected",
  });
  const withImage = await commands.get("trellis-finish").handler({
    ...invocation,
    attachments: [{ type: "image", mimeType: "image/png", data: "abc" }],
  });

  assert.equal(withText.kind, "error");
  assert.match(withText.text, /does not accept arguments/);
  assert.equal(withImage.kind, "error");
  assert.match(withImage.text, /image attachments/);
  assert.equal(executed, false);
});

test("an aborted native command signal cancels execution without Python fallback", async () => {
  const controller = new AbortController();
  controller.abort();
  const calls = [];
  const result = await runTrellisScript(
    { pythonCmd: "" },
    root,
    "session",
    ["current"],
    {
      platform: "win32",
      signal: controller.signal,
      async execFile(command) {
        calls.push(command);
        throw Object.assign(new Error("aborted"), { name: "AbortError" });
      },
    },
  );

  assert.deepEqual(result, {
    kind: "error",
    text: "Trellis command cancelled.",
    code: null,
    stdout: "",
    stderr: "",
  });
  assert.deepEqual(calls, ["py"]);
});

test("commands reject a git repository that is not initialized for Trellis", async () => {
  const { ctx, commands } = commandHarness();
  let executed = false;
  registerCommands(ctx, resolved, {
    fs: projectFs({ trellis: false }),
    async execFile() {
      executed = true;
      return { stdout: "", stderr: "" };
    },
  });

  const result = await commands.get("trellis-status").handler(invocation);
  assert.equal(result.kind, "error");
  assert.match(result.text, /No Trellis project found/);
  assert.equal(executed, false);
});

const noTaskPayload = JSON.stringify({
  current_task: null,
  source: "none",
  stale: false,
});

test("runTrellisScript keeps stdout and the exit code when the script exits non-zero", async () => {
  const result = await runTrellisScript(
    { pythonCmd: "python-test" },
    root,
    "session",
    ["current", "--json"],
    {
      async execFile() {
        throw Object.assign(new Error("Command failed"), {
          code: 1,
          stdout: `${noTaskPayload}\n`,
          stderr: "",
        });
      },
    },
  );

  assert.equal(result.kind, "error");
  assert.equal(result.code, 1);
  assert.equal(result.stdout.trim(), noTaskPayload);
  assert.doesNotMatch(result.text, /Current task/);
});

test("a no-active-task exit 1 with the documented payload is a successful status", async () => {
  const { ctx, commands } = commandHarness();
  registerCommands(ctx, resolved, {
    fs: projectFs(),
    async execFile(_command, args) {
      if (args.includes("current")) {
        throw Object.assign(new Error("Command failed"), {
          code: 1,
          stdout: `${noTaskPayload}\n`,
          stderr: "",
        });
      }
      return { stdout: "## main\n M file.txt\n", stderr: "" };
    },
  });

  const result = await commands.get("trellis-status").handler(invocation);
  assert.equal(result.kind, "success");
  assert.match(result.text, /^Current task: \(none\)\nSource: none/);
  assert.match(result.text, /Git status:\n## main/);
  assert.doesNotMatch(result.text, /Trellis script failed/);
});

test("trellis-finish reports no active task without the archive checklist", async () => {
  const { ctx, commands } = commandHarness();
  const calls = [];
  registerCommands(ctx, resolved, {
    fs: projectFs(),
    async execFile(command, args) {
      calls.push({ command, args });
      throw Object.assign(new Error("Command failed"), {
        code: 1,
        stdout: `${noTaskPayload}\n`,
        stderr: "",
      });
    },
  });

  const result = await commands.get("trellis-finish").handler(invocation);
  assert.equal(result.kind, "success");
  assert.match(result.text, /No active task/);
  assert.doesNotMatch(result.text, /did not clear or archive anything/);
  assert.deepEqual(calls[0].args.slice(-2), ["current", "--json"]);
});

test("a bare exit 1 without the payload stays a script failure", async () => {
  const { ctx, commands } = commandHarness();
  registerCommands(ctx, resolved, {
    fs: projectFs(),
    async execFile() {
      throw Object.assign(new Error("Command failed"), {
        code: 1,
        stdout: "",
        stderr: "Traceback (most recent call last): ...",
      });
    },
  });

  const result = await commands.get("trellis-status").handler(invocation);
  assert.equal(result.kind, "error");
  assert.match(result.text, /Trellis script failed/);
  assert.match(result.text, /Traceback/);
});

test("readCurrentTask formats the machine-readable task payload", async () => {
  const result = await readCurrentTask({ pythonCmd: "python-test" }, root, "session", {
    async execFile() {
      return {
        stdout: JSON.stringify({
          current_task: {
            dir: ".trellis/tasks/demo",
            status: "in_progress",
            title: "Demo task",
          },
          source: "session:dsh_session",
          stale: false,
        }),
        stderr: "",
      };
    },
  });

  assert.equal(result.kind, "success");
  assert.equal(result.noTask, false);
  assert.equal(result.task.dir, ".trellis/tasks/demo");
  assert.match(result.text, /Status: in_progress/);
  assert.match(result.text, /Title: Demo task/);
  assert.match(result.text, /Source: session:dsh_session/);
});

test("parseCurrentTaskPayload rejects non-contract shapes", () => {
  assert.deepEqual(parseCurrentTaskPayload(noTaskPayload), {
    current_task: null,
    source: "none",
    stale: false,
  });
  assert.equal(parseCurrentTaskPayload(""), null);
  assert.equal(parseCurrentTaskPayload("Current task: none"), null);
  assert.equal(parseCurrentTaskPayload("[]"), null);
  assert.equal(parseCurrentTaskPayload('{"source":"none"}'), null);
  assert.equal(parseCurrentTaskPayload('{"current_task":{}}'), null);
  assert.equal(parseCurrentTaskPayload('{"current_task":{"dir":""}}'), null);
});

test("parseLegacyCurrentTask accepts only the documented --source output", () => {
  assert.deepEqual(parseLegacyCurrentTask("Current task: (none)\nSource: none\n"), {
    kind: "success",
    noTask: true,
    task: null,
    text: "Current task: (none)\nSource: none",
  });
  assert.deepEqual(
    parseLegacyCurrentTask("Current task: .trellis/tasks/demo\nSource: session:dsh_x\nState: stale\n"),
    {
      kind: "success",
      noTask: false,
      task: { dir: ".trellis/tasks/demo" },
      text: "Current task: .trellis/tasks/demo\nSource: session:dsh_x\nState: stale",
    },
  );
  assert.equal(parseLegacyCurrentTask(""), null);
  assert.equal(parseLegacyCurrentTask("Traceback (most recent call last):"), null);
  assert.equal(parseLegacyCurrentTask("Current task:   \nSource: none\n"), null);
});

test("a Trellis without current --json falls back to --source for no task", async () => {
  const calls = [];
  const result = await readCurrentTask({ pythonCmd: "python-test" }, root, "session", {
    async execFile(_command, args) {
      calls.push(args);
      if (args.includes("--json")) {
        throw Object.assign(new Error("Command failed"), {
          code: 2,
          stdout: "",
          stderr: "task.py: error: unrecognized arguments: --json",
        });
      }
      throw Object.assign(new Error("Command failed"), {
        code: 1,
        stdout: "Current task: (none)\nSource: none\n",
        stderr: "",
      });
    },
  });

  assert.equal(result.kind, "success");
  assert.equal(result.noTask, true);
  assert.match(result.text, /^Current task: \(none\)/);
  assert.deepEqual(calls.map((args) => args.slice(-2)), [
    ["current", "--json"],
    ["current", "--source"],
  ]);
});

test("the legacy fallback also returns an active task", async () => {
  const result = await readCurrentTask({ pythonCmd: "python-test" }, root, "session", {
    async execFile(_command, args) {
      if (args.includes("--json")) {
        throw Object.assign(new Error("Command failed"), {
          code: 2,
          stdout: "",
          stderr: "task.py: error: unrecognized arguments: --json",
        });
      }
      return {
        stdout: "Current task: .trellis/tasks/demo\nSource: session:dsh_x\n",
        stderr: "",
      };
    },
  });

  assert.equal(result.kind, "success");
  assert.equal(result.noTask, false);
  assert.equal(result.task.dir, ".trellis/tasks/demo");
});

test("the legacy fallback does not swallow a real failure", async () => {
  const result = await readCurrentTask({ pythonCmd: "python-test" }, root, "session", {
    async execFile(_command, args) {
      if (args.includes("--json")) {
        throw Object.assign(new Error("Command failed"), {
          code: 2,
          stdout: "",
          stderr: "task.py: error: unrecognized arguments: --json",
        });
      }
      throw Object.assign(new Error("Command failed"), {
        code: 1,
        stdout: "",
        stderr: "Traceback (most recent call last): ...",
      });
    },
  });

  assert.equal(result.kind, "error");
  assert.match(result.text, /Traceback/);
});

test("an unrelated exit 2 does not trigger the legacy fallback", async () => {
  let calls = 0;
  const result = await readCurrentTask({ pythonCmd: "python-test" }, root, "session", {
    async execFile() {
      calls += 1;
      throw Object.assign(new Error("Command failed"), {
        code: 2,
        stdout: "",
        stderr: "task.py: error: the following arguments are required: task",
      });
    },
  });

  assert.equal(result.kind, "error");
  assert.equal(calls, 1);
});
