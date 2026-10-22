import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, mkdir, writeFile, rm } from "node:fs/promises";
import { join } from "node:path";
import { tmpdir } from "node:os";
import {
  denyReason,
  hasReadableTask,
  inlineDenyReason,
  parseDispatchRequest,
  registerDispatchGuard,
} from "../lib/dispatch-guard.js";
import { dshContextKey } from "../lib/session-env.js";

const prompt = (text) => ({ content: [{ type: "text", text }] });

async function project(t) {
  const root = await mkdtemp(join(tmpdir(), "dsh-trellis-guard-"));
  t.after(() => rm(root, { recursive: true, force: true }));
  const task = ".trellis/tasks/demo";
  await mkdir(join(root, task), { recursive: true });
  await mkdir(join(root, ".trellis", ".runtime", "sessions"), { recursive: true });
  await writeFile(join(root, task, "task.json"), JSON.stringify({ status: "in_progress" }));
  await writeFile(join(root, ".trellis", "workflow.md"), "[workflow-state:no_task]\nIdle.\n[/workflow-state:no_task]\n");
  return { root, task };
}

function harness() {
  const listeners = new Map();
  const ctx = {
    on(event, listener) {
      listeners.set(event, listener);
      return () => listeners.delete(event);
    },
    logger: { warn() {} },
  };
  return { ctx, listeners };
}

const exec = (root, { callId = "call-1", name = "subagent", text = "" } = {}) => ({
  callId,
  name,
  arguments: { prompt: text },
  agent: { session: { header: { id: "parent-1", cwd: root } } },
});

test("parseDispatchRequest reads the role and the Active task prelude", () => {
  assert.deepEqual(
    parseDispatchRequest("Load `.dsh/skills/trellis-agent-check/SKILL.md`.\nActive task: .trellis/tasks/x"),
    { role: "check", taskPath: ".trellis/tasks/x" },
  );
  assert.deepEqual(parseDispatchRequest("trellis-agent-research: find it"), {
    role: "research",
    taskPath: null,
  });
  assert.deepEqual(parseDispatchRequest("plain task"), { role: null, taskPath: null });
});

test("hasReadableTask accepts the parent pointer, the prelude, and nothing else", async (t) => {
  const { root, task } = await project(t);
  const pointer = join(root, ".trellis", ".runtime", "sessions", `${dshContextKey("parent-1")}.json`);
  await writeFile(pointer, JSON.stringify({ current_task: task }));

  assert.equal(await hasReadableTask({ root, taskPath: null, sessionId: "parent-1" }), true);
  assert.equal(await hasReadableTask({ root, taskPath: task, sessionId: "other" }), true);
  assert.equal(await hasReadableTask({ root, taskPath: null, sessionId: "other" }), false);
  assert.equal(
    await hasReadableTask({ root, taskPath: ".trellis/tasks/missing", sessionId: "parent-1" }),
    false,
  );
});

test("a stale parent pointer is not a readable task", async (t) => {
  const { root, task } = await project(t);
  const pointer = join(
    root, ".trellis", ".runtime", "sessions", `${dshContextKey("parent-1")}.json`,
  );
  // The pointed-at directory does not exist: Trellis calls this `stale`, and a
  // child dispatched from it would have no task to read.
  await writeFile(pointer, JSON.stringify({ current_task: ".trellis/tasks/gone" }));
  assert.equal(
    await hasReadableTask({ root, taskPath: null, sessionId: "parent-1" }),
    false,
  );
  // A prelude naming the same vanished directory is refused for the same reason.
  assert.equal(
    await hasReadableTask({
      root, taskPath: ".trellis/tasks/gone", sessionId: "parent-1",
    }),
    false,
  );
  // The same pointer shape is accepted once it names a live task.
  await writeFile(pointer, JSON.stringify({ current_task: task }));
  assert.equal(
    await hasReadableTask({ root, taskPath: null, sessionId: "parent-1" }),
    true,
  );
});

test("an implement dispatch without evidence is denied with an actionable reason", async (t) => {
  const { root } = await project(t);
  const { ctx, listeners } = harness();
  const dispose = registerDispatchGuard(ctx, { projectRootMarkers: [".trellis"] });
  t.after(dispose);

  const decision = await listeners.get("tools/pre-execute")(
    exec(root, { text: "Active: no task here. Load trellis-agent-implement." }),
    async () => ({ kind: "allow" }),
  );
  assert.equal(decision.kind, "deny");
  assert.match(decision.reason, /no readable active task for trellis-agent-implement/);
  assert.equal(decision.reason, denyReason("implement"));
});

test("a readable pointer or prelude allows the dispatch", async (t) => {
  const { root, task } = await project(t);
  const { ctx, listeners } = harness();
  t.after(registerDispatchGuard(ctx, { projectRootMarkers: [".trellis"] }));
  const pre = listeners.get("tools/pre-execute");

  const pointer = join(root, ".trellis", ".runtime", "sessions", `${dshContextKey("parent-1")}.json`);
  await writeFile(pointer, JSON.stringify({ current_task: task }));
  assert.deepEqual(
    await pre(exec(root, { text: "trellis-agent-implement" }), async () => ({ kind: "allow" })),
    { kind: "allow" },
  );

  const other = { ...exec(root, { callId: "c2", text: `Active task: ${task}\ntrellis-agent-check` }) };
  other.agent = { session: { header: { id: "unbound", cwd: root } } };
  assert.deepEqual(
    await pre(other, async () => ({ kind: "allow" })),
    { kind: "allow" },
  );
});

test("research is allowed without a task and told to confirm its output location", async (t) => {
  const { root } = await project(t);
  const { ctx, listeners } = harness();
  t.after(registerDispatchGuard(ctx, { projectRootMarkers: [".trellis"] }));
  const pre = listeners.get("tools/pre-execute");
  const post = listeners.get("tools/post-execute");
  const run = exec(root, { callId: "r1", text: "trellis-agent-research: compare approaches" });

  assert.deepEqual(await pre(run, async () => ({ kind: "allow" })), { kind: "allow" });
  const after = await post(run, {}, async () => ({ kind: "accept" }));
  assert.equal(after.additionalContexts.length, 1);
  assert.match(after.additionalContexts[0].content[0].text, /Confirm where its findings/);

  // The notice is delivered once, not on every later tool call.
  const again = await post(run, {}, async () => ({ kind: "accept" }));
  assert.equal(again.additionalContexts, undefined);
});

test("the guard ignores non-dispatch tools, non-Trellis prompts, and host denials", async (t) => {
  const { root } = await project(t);
  const { ctx, listeners } = harness();
  t.after(registerDispatchGuard(ctx, { projectRootMarkers: [".trellis"] }));
  const pre = listeners.get("tools/pre-execute");

  assert.deepEqual(
    await pre(exec(root, { name: "edit", text: "trellis-agent-implement" }), async () => ({ kind: "allow" })),
    { kind: "allow" },
  );
  assert.deepEqual(
    await pre(exec(root, { text: "summarise this file" }), async () => ({ kind: "allow" })),
    { kind: "allow" },
  );
  const denied = { kind: "deny", reason: "host policy" };
  assert.deepEqual(await pre(exec(root, { text: "trellis-agent-implement" }), async () => denied), denied);
});

test("inline mode refuses implement/check dispatch even with a readable task", async (t) => {
  const { root, task } = await project(t);
  await writeFile(join(root, ".trellis", "config.yaml"), "dsh:\n  dispatch_mode: inline\n");
  const { ctx, listeners } = harness();
  t.after(registerDispatchGuard(ctx, { projectRootMarkers: [".trellis"] }));
  const pre = listeners.get("tools/pre-execute");

  const implement = await pre(
    exec(root, { text: `Active task: ${task}\ntrellis-agent-implement` }),
    async () => ({ kind: "allow" }),
  );
  assert.equal(implement.kind, "deny");
  assert.equal(implement.reason, inlineDenyReason("implement"));

  const check = await pre(
    exec(root, { callId: "c2", text: `Active task: ${task}\ntrellis-agent-check` }),
    async () => ({ kind: "allow" }),
  );
  assert.equal(check.kind, "deny");
  assert.equal(check.reason, inlineDenyReason("check"));
});

test("inline mode still allows research", async (t) => {
  const { root } = await project(t);
  await writeFile(join(root, ".trellis", "config.yaml"), "dsh:\n  dispatch_mode: inline\n");
  const { ctx, listeners } = harness();
  t.after(registerDispatchGuard(ctx, { projectRootMarkers: [".trellis"] }));
  const pre = listeners.get("tools/pre-execute");
  assert.deepEqual(
    await pre(exec(root, { text: "trellis-agent-research: compare approaches" }), async () => ({ kind: "allow" })),
    { kind: "allow" },
  );
});

test("dsh.inline_allow_dispatch is the explicit escape hatch", async (t) => {
  const { root, task } = await project(t);
  await writeFile(
    join(root, ".trellis", "config.yaml"),
    "dsh:\n  dispatch_mode: inline\n  inline_allow_dispatch: true\n",
  );
  const { ctx, listeners } = harness();
  t.after(registerDispatchGuard(ctx, { projectRootMarkers: [".trellis"] }));
  const pre = listeners.get("tools/pre-execute");
  assert.deepEqual(
    await pre(exec(root, { text: `Active task: ${task}\ntrellis-agent-implement` }), async () => ({ kind: "allow" })),
    { kind: "allow" },
  );
});

test("auto mode keeps dispatching allowed for a readable task", async (t) => {
  const { root, task } = await project(t);
  await writeFile(join(root, ".trellis", "config.yaml"), "dsh:\n  dispatch_mode: auto\n");
  const { ctx, listeners } = harness();
  t.after(registerDispatchGuard(ctx, { projectRootMarkers: [".trellis"] }));
  const pre = listeners.get("tools/pre-execute");
  assert.deepEqual(
    await pre(exec(root, { text: `Active task: ${task}\ntrellis-agent-implement` }), async () => ({ kind: "allow" })),
    { kind: "allow" },
  );
});

test("parseDispatchRequest falls back to the dispatch description", () => {
  assert.deepEqual(
    parseDispatchRequest("Implement the plan.", "trellis-agent-implement"),
    { role: "implement", taskPath: null },
  );
  // The prompt wins over the description when both name a role.
  assert.deepEqual(
    parseDispatchRequest("trellis-agent-research: compare", "trellis-agent-check"),
    { role: "research", taskPath: null },
  );
  // A description that is not a Trellis role stays generic.
  assert.deepEqual(
    parseDispatchRequest("plain task", "update docs"),
    { role: null, taskPath: null },
  );
  // Talking about a role is not selecting it: the whole label must be the role.
  for (const description of [
    "研究 trellis-agent-implement 插件的 README",
    "about trellis-agent-check plugin docs",
    "trellis-agent-implement task",
  ]) {
    assert.deepEqual(
      parseDispatchRequest("plain task", description),
      { role: null, taskPath: null },
      description,
    );
  }
  // Wrapping punctuation and case do not change an exact role label.
  assert.equal(parseDispatchRequest("plain task", "`Trellis-Agent-Check`").role, "check");
  assert.equal(parseDispatchRequest("plain task", "trellis-research.").role, "research");
});

test("a topical description is allowed just like a generic dispatch", async (t) => {
  const { root } = await project(t);
  const { ctx, listeners } = harness();
  t.after(registerDispatchGuard(ctx, { projectRootMarkers: [".trellis"] }));
  const pre = listeners.get("tools/pre-execute");
  const call = {
    callId: "topic-1",
    name: "subagent",
    arguments: {
      prompt: "Do it.",
      description: "研究 trellis-agent-implement 插件的 README",
    },
    agent: { session: { header: { id: "parent-1", cwd: root } } },
  };
  // No task and no role: this is a generic dispatch, so nothing is refused.
  assert.deepEqual(await pre(call, async () => ({ kind: "allow" })), { kind: "allow" });

  await writeFile(join(root, ".trellis", "config.yaml"), "dsh:\n  dispatch_mode: inline\n");
  assert.deepEqual(await pre(call, async () => ({ kind: "allow" })), { kind: "allow" });
});

test("the inline guard sees a role that only the description names", async (t) => {
  const { root, task } = await project(t);
  await writeFile(join(root, ".trellis", "config.yaml"), "dsh:\n  dispatch_mode: inline\n");
  const { ctx, listeners } = harness();
  t.after(registerDispatchGuard(ctx, { projectRootMarkers: [".trellis"] }));
  const pre = listeners.get("tools/pre-execute");

  const call = {
    callId: "d1",
    name: "subagent",
    arguments: { prompt: `Active task: ${task}\nDo the work.`, description: "trellis-agent-implement" },
    agent: { session: { header: { id: "parent-1", cwd: root } } },
  };
  const decision = await pre(call, async () => ({ kind: "allow" }));
  assert.equal(decision.kind, "deny");
  assert.equal(decision.reason, inlineDenyReason("implement"));
});

test("a description-only check dispatch without a task is still refused", async (t) => {
  const { root } = await project(t);
  await writeFile(join(root, ".trellis", "config.yaml"), "dsh:\n  dispatch_mode: auto\n");
  const { ctx, listeners } = harness();
  t.after(registerDispatchGuard(ctx, { projectRootMarkers: [".trellis"] }));
  const pre = listeners.get("tools/pre-execute");
  const call = {
    callId: "d2",
    name: "subagent_fork",
    arguments: { prompt: "Verify the change.", description: "trellis-agent-check" },
    agent: { session: { header: { id: "unbound", cwd: root } } },
  };
  const decision = await pre(call, async () => ({ kind: "allow" }));
  assert.equal(decision.kind, "deny");
  assert.equal(decision.reason, denyReason("check"));
});

test("the inline denial leaves the config change to the user", () => {
  const reason = inlineDenyReason("implement");
  assert.match(reason, /user's decision, not\s+yours/);
  assert.match(reason, /Do not edit `\.trellis\/config\.yaml`/);
  assert.match(reason, /not a security boundary/);
});
