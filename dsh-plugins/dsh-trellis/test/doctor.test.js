import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, mkdir, writeFile, rm } from "node:fs/promises";
import { join } from "node:path";
import { tmpdir } from "node:os";
import {
  collectDoctorReport,
  registerDoctorCommand,
} from "../lib/doctor.js";
import { nodeFs } from "../lib/node-fs.js";
import { dshContextKey } from "../lib/session-env.js";

async function project(t, { brokenTask = false } = {}) {
  const root = await mkdtemp(join(tmpdir(), "dsh-trellis-doctor-"));
  t.after(() => rm(root, { recursive: true, force: true }));
  await mkdir(join(root, ".trellis", "spec"), { recursive: true });
  await mkdir(join(root, ".trellis", "tasks", "demo"), { recursive: true });
  await mkdir(join(root, ".trellis", ".runtime", "sessions"), { recursive: true });
  await writeFile(join(root, ".trellis", ".version"), "0.7.0-beta.4\n");
  await writeFile(join(root, ".trellis", "workflow.md"), [
    "[workflow-state:no_task]\nIdle.\n[/workflow-state:no_task]",
    "[workflow-state:in_progress]\nWork.\n[/workflow-state:in_progress]",
  ].join("\n"));
  await writeFile(join(root, ".trellis", "config.yaml"), "spec_injection:\n  enabled: true\n");
  await writeFile(join(root, ".trellis", "spec", "a.md"), "---\npaths: [src/*.ts]\n---\nRules.\n");
  await writeFile(
    join(root, ".trellis", "tasks", "demo", "task.json"),
    brokenTask ? "{broken" : JSON.stringify({ status: "in_progress" }),
  );
  await writeFile(
    join(root, ".trellis", ".runtime", "sessions", `${dshContextKey("s1")}.json`),
    JSON.stringify({ current_task: ".trellis/tasks/demo" }),
  );
  return root;
}

const report = (root, overrides = {}) => collectDoctorReport({
  root,
  cwd: root,
  sessionId: "s1",
  fs: nodeFs,
  version: "9.9.9",
  conflicts: { status: "checked", conflicts: [] },
  ...overrides,
});

test("doctor reports project, versions, workflow blocks, task, specs, conflicts", async (t) => {
  const root = await project(t);
  const text = await report(root);
  assert.match(text, /Project root: /);
  assert.match(text, /Plugin: dsh-trellis 9\.9\.9/);
  assert.match(text, /Trellis: 0\.7\.0-beta\.4/);
  assert.match(text, /Workflow: 2 \[workflow-state:\*\] blocks/);
  assert.match(text, /Active task: \.trellis\/tasks\/demo \(in_progress\)/);
  assert.match(text, /Spec injection: enabled \(1 specs declare paths\)/);
  assert.match(text, /Plugin conflicts: none/);
  assert.match(text, /upstream commits are checked in Settings → Trellis/);
});

test("doctor surfaces a broken task as task_error and reports missing pieces", async (t) => {
  const root = await project(t, { brokenTask: true });
  await rm(join(root, ".trellis", ".version"));
  await rm(join(root, ".trellis", "spec"), { recursive: true, force: true });
  const text = await report(root);
  assert.match(text, /task_error: repair task\.json/);
  assert.match(text, /unknown \(\.trellis\/\.version missing\)/);
  assert.match(text, /Spec injection: enabled \(0 specs declare paths\)/);
});

test("doctor reports disabled spec injection and conflict detection state", async (t) => {
  const root = await project(t);
  await writeFile(join(root, ".trellis", "config.yaml"), "spec_injection:\n  enabled: false\n");
  const text = await report(root, {
    conflicts: { status: "unverified", conflicts: [{ id: "plus", name: "dsh-trellis-plus" }] },
  });
  assert.match(text, /Spec injection: disabled by \.trellis\/config\.yaml/);
  assert.match(text, /Plugin conflicts: unverified \(conflict detection did not complete\)/);
});

test("the doctor command refuses input and reports success without it", async (t) => {
  const root = await project(t);
  const commands = new Map();
  const ctx = { commands: { register(command) { commands.set(command.name, command); return () => {}; } } };
  t.after(registerDoctorCommand(ctx, { projectRootMarkers: [".trellis"] }, {
    version: async () => "9.9.9",
    conflicts: () => ({ status: "checked", conflicts: [] }),
  }));
  const command = commands.get("trellis-doctor");
  assert.equal(command.recordInput, false);

  const agent = { session: { header: { id: "s1", cwd: root } } };
  assert.equal((await command.handler({ agent, rawInput: "fix it" })).kind, "error");
  const result = await command.handler({ agent, rawInput: "" });
  assert.equal(result.kind, "success");
  assert.match(result.text, /Trellis doctor/);
  assert.match(result.text, /Plugin: dsh-trellis 9\.9\.9/);
});
