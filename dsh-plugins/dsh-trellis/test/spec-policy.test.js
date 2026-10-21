import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, mkdir, writeFile, rm, stat } from "node:fs/promises";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { planSpecInjection, registerSpecPolicy } from "../lib/spec-policy.js";
import { RETRY_NOTICE } from "../lib/spec-inject.js";
import { specStatePath } from "../lib/spec-state.js";
import { specInjectionSettings } from "../lib/trellis-config.js";

async function project(t, { config, spec } = {}) {
  const root = await mkdtemp(join(tmpdir(), "dsh-trellis-spec-"));
  t.after(() => rm(root, { recursive: true, force: true }));
  await mkdir(join(root, ".trellis", "spec"), { recursive: true });
  await mkdir(join(root, "src"), { recursive: true });
  await writeFile(join(root, "src", "a.ts"), "");
  await writeFile(
    join(root, ".trellis", "config.yaml"),
    config ?? "spec_injection:\n  enabled: true\n",
  );
  await writeFile(
    join(root, ".trellis", "spec", "a.md"),
    spec ?? "---\ndescription: rule a\npaths: [src/*.ts]\n---\nDo the thing.\n",
  );
  return root;
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

const agentFor = (root, id = "session-1") => ({
  session: { header: { id, cwd: root } },
});

function execution(root, { callId = "call-1", name = "edit", file = "src/a.ts" } = {}) {
  return {
    callId,
    name,
    arguments: { file_path: join(root, file) },
    agent: agentFor(root),
  };
}

test("planSpecInjection ignores disabled projects and unrelated tools", async (t) => {
  const root = await project(t, { config: "spec_injection:\n  enabled: false\n" });
  const settings = specInjectionSettings("spec_injection:\n  enabled: false\n");
  const plan = await planSpecInjection({
    root,
    filePath: join(root, "src", "a.ts"),
    toolName: "edit",
    sessionKey: "s",
    store: new Map(),
    indexCache: new Map(),
    settings,
    nowSeconds: 1,
  });
  assert.deepEqual(plan, { kind: "none" });

  const unrelated = await planSpecInjection({
    root,
    filePath: join(root, "src", "a.ts"),
    toolName: "read",
    sessionKey: "s",
    store: new Map(),
    indexCache: new Map(),
    settings: specInjectionSettings("spec_injection:\n  enabled: true\n"),
    nowSeconds: 1,
  });
  assert.deepEqual(unrelated, { kind: "none" });
});

test("planSpecInjection promotes tickets only outside the refresh window", async (t) => {
  const root = await project(t);
  const settings = specInjectionSettings("spec_injection:\n  enabled: true\n");
  const base = {
    root,
    filePath: join(root, "src", "a.ts"),
    toolName: "edit",
    sessionKey: "s",
    indexCache: new Map(),
    settings,
  };

  const first = await planSpecInjection({ ...base, store: new Map(), nowSeconds: 1000 });
  assert.equal(first.kind, "full");
  const store = new Map(first.records.map((record) => [record.spec, record]));

  const silent = await planSpecInjection({ ...base, store, nowSeconds: 1010 });
  assert.deepEqual(silent, { kind: "none" });

  const ticket = await planSpecInjection({ ...base, store, nowSeconds: 1000 + 2700 });
  assert.equal(ticket.kind, "context");
  assert.match(ticket.payload, /<spec-ticket/);
});

test("registerSpecPolicy denies an edit once, then allows the retry", async (t) => {
  const root = await project(t);
  const { ctx, listeners } = harness();
  const dispose = registerSpecPolicy(ctx, { projectRootMarkers: [".trellis"] });
  t.after(dispose);
  const pre = listeners.get("tools/pre-execute");
  assert.equal(typeof pre, "function");

  const denied = await pre(execution(root), async () => ({ kind: "allow" }));
  assert.equal(denied.kind, "deny");
  assert.ok(denied.reason.startsWith(RETRY_NOTICE));
  assert.match(denied.reason, /<spec-context file="src\/a\.ts" spec="\.trellis\/spec\/a\.md"/);
  assert.match(denied.reason, /Do the thing\./);

  const retried = await pre(execution(root, { callId: "call-2" }), async () => ({ kind: "allow" }));
  assert.deepEqual(retried, { kind: "allow" });
});

test("registerSpecPolicy keeps the full spec across a plugin restart", async (t) => {
  const root = await project(t);
  const one = harness();
  const disposeOne = registerSpecPolicy(one.ctx, { projectRootMarkers: [".trellis"] });
  const denied = await one.listeners.get("tools/pre-execute")(
    execution(root),
    async () => ({ kind: "allow" }),
  );
  assert.equal(denied.kind, "deny");
  disposeOne();
  assert.ok(await stat(specStatePath(root, "session-1")));

  const two = harness();
  disposeIn(t, registerSpecPolicy(two.ctx, { projectRootMarkers: [".trellis"] }));
  const again = await two.listeners.get("tools/pre-execute")(
    execution(root, { callId: "call-restart" }),
    async () => ({ kind: "allow" }),
  );
  assert.deepEqual(again, { kind: "allow" });
});

test("registerSpecPolicy never denies a read; it delivers after the call", async (t) => {
  const root = await project(t, {
    config: "spec_injection:\n  enabled: true\n  tools: [Read]\n",
  });
  const { ctx, listeners } = harness();
  disposeIn(t, registerSpecPolicy(ctx, { projectRootMarkers: [".trellis"] }));

  const pre = listeners.get("tools/pre-execute");
  const post = listeners.get("tools/post-execute");
  const exec = execution(root, { callId: "read-1", name: "read" });
  const decision = await pre(exec, async () => ({ kind: "allow" }));
  assert.deepEqual(decision, { kind: "allow" });

  const after = await post(exec, {}, async () => ({ kind: "accept" }));
  assert.equal(after.additionalContexts.length, 1);
  assert.match(after.additionalContexts[0].content[0].text, /<spec-context/);

  // A second read inside the refresh window injects nothing.
  const again = execution(root, { callId: "read-2", name: "read" });
  await pre(again, async () => ({ kind: "allow" }));
  const silent = await post(again, {}, async () => ({ kind: "accept" }));
  assert.equal(silent.additionalContexts, undefined);
});

test("registerSpecPolicy leaves other policies' decisions untouched", async (t) => {
  const root = await project(t);
  const { ctx, listeners } = harness();
  disposeIn(t, registerSpecPolicy(ctx, { projectRootMarkers: [".trellis"] }));
  const pre = listeners.get("tools/pre-execute");
  const deniedByHost = { kind: "deny", reason: "host policy" };
  assert.deepEqual(await pre(execution(root), async () => deniedByHost), deniedByHost);
});

test("compaction also drops the persisted shard, so a restart re-teaches", async (t) => {
  const root = await project(t);
  const { ctx, listeners } = harness();
  const dispose = registerSpecPolicy(ctx, { projectRootMarkers: [".trellis"] });
  t.after(dispose);
  const pre = listeners.get("tools/pre-execute");
  const sessionEvent = listeners.get("session/event");

  await pre(execution(root), async () => ({ kind: "allow" }));
  const path = specStatePath(root, "session-1");
  assert.ok(await stat(path));
  await sessionEvent(
    { id: "session-1", header: { cwd: root } },
    { type: "compaction/end" },
  );
  await assert.rejects(stat(path));
  dispose();

  const restarted = harness();
  disposeIn(t, registerSpecPolicy(restarted.ctx, { projectRootMarkers: [".trellis"] }));
  const afterRestart = await restarted.listeners.get("tools/pre-execute")(
    execution(root, { callId: "call-3" }),
    async () => ({ kind: "allow" }),
  );
  assert.equal(afterRestart.kind, "deny");

  const retry = await restarted.listeners.get("tools/pre-execute")(
    execution(root, { callId: "call-4" }),
    async () => ({ kind: "allow" }),
  );
  assert.deepEqual(retry, { kind: "allow" });
});

test("compaction after a restart clears the shard without a prior tool call", async (t) => {
  const root = await project(t);
  const one = harness();
  const disposeOne = registerSpecPolicy(one.ctx, { projectRootMarkers: [".trellis"] });
  await one.listeners.get("tools/pre-execute")(
    execution(root),
    async () => ({ kind: "allow" }),
  );
  disposeOne();
  const path = specStatePath(root, "session-1");
  assert.ok(await stat(path));

  const two = harness();
  disposeIn(t, registerSpecPolicy(two.ctx, { projectRootMarkers: [".trellis"] }));
  await two.listeners.get("session/event")(
    { id: "session-1", header: { cwd: root } },
    { type: "compaction/end" },
  );
  await assert.rejects(stat(path));
});

function disposeIn(t, dispose) {
  t.after(dispose);
}
