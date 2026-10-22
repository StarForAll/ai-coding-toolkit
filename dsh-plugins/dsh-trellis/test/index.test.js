import { test } from "node:test";
import assert from "node:assert/strict";
import { fileURLToPath } from "node:url";
import { mkdtemp, mkdir, readFile, writeFile, rm } from "node:fs/promises";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { createUserMessage } from "@deepseek-ai/dsh-llm";
import { BREADCRUMB_PROJECTION_KEY as KEY } from "../lib/breadcrumb-projection.js";
import { isBreadcrumbMessage } from "../lib/breadcrumb.js";
import {
  BOOTSTRAP_PROJECTION_KEY as BOOTSTRAP_KEY,
  isBootstrapMessage,
} from "../lib/bootstrap.js";
import { createSessionComposer } from "../lib/session-composer.js";
import { SUBAGENT_IDENTITY_PROJECTION_KEY as IDENTITY_KEY } from "../lib/subagent-identity.js";
import { dshContextKey } from "../lib/session-env.js";
import { sessionRuntime } from "./helpers/session-runtime.js";
import { apply, inject, insertBreadcrumbDecision } from "../lib/index.js";

function harness({ settings = false, projectionRegistry } = {}) {
  const effects = [];
  const listeners = [];
  const registrations = [];
  const active = new Set();
  const settingsState = {
    value: {},
    watcher: undefined,
    registration: undefined,
  };
  const ctx = {
    fiber: { state: 0 },
  };
  const settingsCtx = {
    settings: {
      register(namespace, schema, options) {
        settingsState.registration = { namespace, schema, options };
        settingsState.value = options.base;
        return {
          get: () => settingsState.value,
          watch(callback) {
            settingsState.watcher = callback;
            return () => {
              settingsState.watcher = undefined;
            };
          },
        };
      },
      installSection(owner, namespace, schema, entry, hooks) {
        const scope = this.register(namespace, schema, { base: entry });
        hooks.setSource(() => scope.get());
        hooks.onChange();
        settingsCtx.effect(() => () => {
          if (owner.fiber.state === 5) return;
          hooks.setSource(() => entry);
          hooks.onChange();
        });
        scope.watch(() => {
          if (owner.fiber.state !== 5) hooks.onChange();
        });
      },
    },
    effect(callback, label) {
      effects.push({ owner: "settings", label, dispose: callback() });
    },
  };
  Object.assign(ctx, {
    effect(callback, label) {
      effects.push({ owner: "plugin", label, dispose: callback() });
    },
    on(event, listener) {
      const entry = { event, listener };
      listeners.push(entry);
      active.add(`listener:${event}`);
      return () => {
        active.delete(`listener:${event}`);
        // A remount registers a fresh listener; keeping the disposed entry
        // would make "the newest listener for X" ambiguous.
        const index = listeners.indexOf(entry);
        if (index !== -1) listeners.splice(index, 1);
      };
    },
    inject(services, callback) {
      registrations.push(`inject:${services.join(",")}`);
      if (settings && services.includes("settings")) callback(settingsCtx);
    },
    commands: {
      register(command) {
        registrations.push(`command:${command.name}`);
        active.add(`command:${command.name}`);
        return () => active.delete(`command:${command.name}`);
      },
    },
    subagents: {},
    sessionProjections: {
      register(definition) {
        registrations.push(`projection:${definition.key}`);
        active.add(`projection:${definition.key}`);
        const dispose = projectionRegistry?.register(definition);
        return () => {
          active.delete(`projection:${definition.key}`);
          dispose?.();
        };
      },
      stateOf(session, key) {
        return projectionRegistry ? projectionRegistry.stateOf(session, key) : {};
      },
    },
    shellEnv: {
      register(contributor) {
        registrations.push(`shell-env:${contributor.name}`);
        active.add(`shell-env:${contributor.name}`);
        return () => active.delete(`shell-env:${contributor.name}`);
      },
    },
    tools: {
      register(tool) {
        registrations.push(`tool:${tool.name}`);
        active.add(`tool:${tool.name}`);
        return () => active.delete(`tool:${tool.name}`);
      },
    },
  });
  return {
    ctx,
    effects,
    listeners,
    registrations,
    active,
    settingsState,
    publishSettings(value) {
      settingsState.value = value;
      settingsState.watcher?.();
    },
    detachSettings({ unloading = false } = {}) {
      if (unloading) ctx.fiber.state = 5;
      for (const effect of effects.filter(({ owner }) => owner === "settings")) {
        effect.dispose();
      }
    },
    disposePlugin() {
      ctx.fiber.state = 5;
      for (const effect of effects.filter(({ owner }) => owner === "plugin")) {
        effect.dispose();
      }
    },
  };
}

test("disabled plugin keeps only the optional settings bridge", () => {
  const state = harness();
  apply(state.ctx, { enabled: false });
  assert.deepEqual(
    state.effects.map(({ label }) => label),
    ["dsh-trellis.runtime"],
  );
  assert.deepEqual(state.listeners, []);
  // The upstream-check route registers regardless of the workflow switch: the
  // settings page's monitor is not part of the workflow runtime.
  assert.deepEqual(state.registrations, ["inject:webServer", "inject:settings"]);
  assert.deepEqual([...state.active], []);
});

test("enabled plugin registers commands, wait tool, tool hooks, and a sub-agent push listener", () => {
  const state = harness();
  apply(state.ctx, {});
  assert.deepEqual(
    state.effects.map(({ label }) => label),
    ["dsh-trellis.runtime"],
  );
  // Breadcrumb first, then the spec policy's tool hooks, then the sub-agent
  // push. Each capability owns exactly one listener per event it needs.
  assert.deepEqual(
    state.listeners.map(({ event }) => event),
    [
      "agent/pre-step",
      "tools/pre-execute",
      "tools/post-execute",
      "session/event",
      "agent/pre-step",
      "tools/pre-execute",
      "tools/post-execute",
    ],
  );
  assert.deepEqual(state.registrations.filter((entry) => !entry.startsWith("inject:")).sort(), [
    "command:trellis-doctor",
    "command:trellis-finish",
    "command:trellis-status",
    `projection:${BOOTSTRAP_KEY}`,
    `projection:${KEY}`,
    `projection:${IDENTITY_KEY}`,
    "shell-env:dsh-trellis-session",
    "tool:trellis_wait",
  ]);

  for (const effect of state.effects) effect.dispose();
  assert.deepEqual([...state.active], []);
});

test("settings namespace remounts the plugin from saved values", () => {
  const state = harness({ settings: true });
  apply(state.ctx, { enabled: false, maxBytes: 1024 });

  assert.equal(state.settingsState.registration.namespace, "dsh-trellis");
  assert.deepEqual(state.settingsState.registration.options, {
    base: {
      enabled: false,
      maxBytes: 1024,
    },
  });
  assert.deepEqual([...state.active], []);

  state.publishSettings({ enabled: true, commandsEnabled: false });
  assert.deepEqual([...state.active].sort(), [
    "listener:agent/pre-step",
    "listener:session/event",
    "listener:tools/post-execute",
    "listener:tools/pre-execute",
    `projection:${BOOTSTRAP_KEY}`,
    `projection:${KEY}`,
    `projection:${IDENTITY_KEY}`,
    "shell-env:dsh-trellis-session",
    "tool:trellis_wait",
  ]);

  state.publishSettings({ enabled: true, commandsEnabled: true });
  assert.deepEqual([...state.active].sort(), [
    "command:trellis-doctor",
    "command:trellis-finish",
    "command:trellis-status",
    "listener:agent/pre-step",
    "listener:session/event",
    "listener:tools/post-execute",
    "listener:tools/pre-execute",
    `projection:${BOOTSTRAP_KEY}`,
    `projection:${KEY}`,
    `projection:${IDENTITY_KEY}`,
    "shell-env:dsh-trellis-session",
    "tool:trellis_wait",
  ]);

  state.publishSettings({ enabled: false });
  assert.deepEqual([...state.active], []);
});

test("settings provider detach falls back to the profile composition entry", () => {
  const state = harness({ settings: true });
  apply(state.ctx, { enabled: false });

  state.publishSettings({ enabled: true, commandsEnabled: false });
  assert.deepEqual([...state.active].sort(), [
    "listener:agent/pre-step",
    "listener:session/event",
    "listener:tools/post-execute",
    "listener:tools/pre-execute",
    `projection:${BOOTSTRAP_KEY}`,
    `projection:${KEY}`,
    `projection:${IDENTITY_KEY}`,
    "shell-env:dsh-trellis-session",
    "tool:trellis_wait",
  ]);

  state.detachSettings();
  assert.deepEqual([...state.active], []);
});

test("plugin teardown does not remount the profile entry while settings detaches", () => {
  const state = harness({ settings: true });
  apply(state.ctx, { enabled: false });

  state.publishSettings({ enabled: true, commandsEnabled: false });
  const mounted = [...state.active].sort();
  state.detachSettings({ unloading: true });
  assert.deepEqual([...state.active].sort(), mounted);

  state.disposePlugin();
  assert.deepEqual([...state.active], []);
});

test("breadcrumb insertion preserves host-owned pre-step decision fields", () => {
  const claimed = { role: "system", content: "workspace instructions" };
  const tail = { role: "user", content: "task" };
  const desired = { role: "user", content: "[workflow-state:in_progress]" };
  const decision = {
    kind: "enter",
    messages: [claimed, tail],
    startsRequestSeries: true,
  };

  assert.deepEqual(insertBreadcrumbDecision(decision, [claimed], desired), {
    kind: "enter",
    messages: [claimed, desired, tail],
    startsRequestSeries: true,
  });
});

const prompt = (text) => createUserMessage({ content: [{ type: "text", text }] });
const fixtureCwd = fileURLToPath(new URL("./fixtures/breadcrumb-project", import.meta.url));
const fixtureConfig = { projectRootMarkers: [".trellis"], commandsEnabled: false };

function inbox(initial = []) {
  return {
    nextStep: [...initial],
    prepend(_lane, message) { this.nextStep.unshift(message); },
    replace(id, message) { this.nextStep[this.nextStep.findIndex((entry) => entry.id === id)] = message; },
    remove(id) { this.nextStep = this.nextStep.filter((entry) => entry.id !== id); },
  };
}

async function preStepRuntime(t, config = {}, cwd = fixtureCwd, sessionMeta = { cwd }) {
  const ctx = await sessionRuntime(t);
  const state = harness({ settings: true, projectionRegistry: ctx.sessionProjections });
  apply(state.ctx, { ...fixtureConfig, ...config });
  t.after(() => state.disposePlugin());
  const agent = {
    session: ctx.sessions.create("pre-step", { meta: sessionMeta }),
    inbox: inbox(),
  };
  const run = async ({ messages = [prompt("Continue")], decision, step = 2, signal } = {}) => {
    const input = decision ?? { kind: "enter", messages, startsRequestSeries: true };
    const listener = state.listeners.filter((entry) => entry.event === "agent/pre-step")[0].listener;
    return listener({ agent, messages, step, signal }, async () => input);
  };
  return { ctx, state, agent, run };
}

test("plugin declares the projection service as a required host capability", () => {
  assert.ok(inject.includes("sessionProjections"));
});

test("pre-step inserts once, clears stale inbox, and dedupes immediately after settings remount", async (t) => {
  const { ctx, state, agent, run } = await preStepRuntime(t);
  const first = await run();
  const message = first.messages.find(isBreadcrumbMessage);
  assert.ok(message);
  assert.equal(first.startsRequestSeries, true);
  agent.session.append("user/message", message, { surfaceOp: "append" });
  const unrelated = prompt("Keep this queued prompt");
  agent.inbox = inbox([message, unrelated]);
  assert.equal((await run()).messages.some(isBreadcrumbMessage), false);
  assert.deepEqual(agent.inbox.nextStep, [unrelated]);
  state.publishSettings({ ...fixtureConfig, enabled: false });
  assert.equal(ctx.sessionProjections.stateOf(agent.session, KEY), undefined);
  state.publishSettings({ ...fixtureConfig, enabled: true });
  assert.equal((await run()).messages.some(isBreadcrumbMessage), false);

  state.publishSettings({ ...fixtureConfig, maxBytes: 24 });
  const smaller = (await run()).messages.find(isBreadcrumbMessage);
  assert.ok(smaller);
  assert.notDeepEqual(smaller.content, message.content);
  assert.equal(smaller.source.digest, message.source.digest);
});

test("pre-step reinjects after compaction and dedupes a newly resumed session", async (t) => {
  const { ctx, agent, run } = await preStepRuntime(t);
  const first = (await run()).messages.find(isBreadcrumbMessage);
  const committed = agent.session.append("user/message", first, { surfaceOp: "append" });
  agent.session = ctx.sessions.create("resumed-pre-step", {
    seed: [committed], meta: { cwd: fixtureCwd },
  });
  assert.equal((await run()).messages.some(isBreadcrumbMessage), false);
  agent.session.append("user/message", prompt("Compacted"), {
    surfaceOp: { op: "replace", startSeq: 0, endSeq: 0 }, sourceEventSeqs: [0],
  });
  assert.ok((await run()).messages.find(isBreadcrumbMessage));
});

test("a no-task step injects the breadcrumb and exactly one bootstrap nudge", async (t) => {
  const { agent, run } = await preStepRuntime(t);
  const first = await run();
  assert.equal(first.messages.filter(isBreadcrumbMessage).length, 1);
  assert.equal(first.messages.filter(isBootstrapMessage).length, 1);

  // Commit both to the surface: the steady state is silent.
  for (const message of first.messages.filter(
    (candidate) => isBreadcrumbMessage(candidate) || isBootstrapMessage(candidate),
  )) {
    agent.session.append("user/message", message, { surfaceOp: "append" });
  }
  const second = await run();
  assert.equal(
    second.messages.some(
      (message) => isBreadcrumbMessage(message) || isBootstrapMessage(message),
    ),
    false,
  );
});

test("default project markers find a Trellis project that is not a Git checkout", async (t) => {
  const project = await temporaryProject(t);
  const { state, run } = await preStepRuntime(t, {}, project.root);
  // Drop the fixture's explicit markers so the plugin defaults apply: Codex
  // locates the Trellis root by `.trellis/`, not by `.git`.
  state.publishSettings({ enabled: true });
  const message = (await run()).messages.find(isBreadcrumbMessage);
  assert.ok(message);
  assert.equal(message.source.status, "no_task");
});

test("a delegated sub-agent with no task of its own receives neither family", async (t) => {
  const { agent, run } = await preStepRuntime(t, {}, fixtureCwd, {
    cwd: fixtureCwd,
    parentSession: "parent-session",
    origin: "subagent",
  });
  const result = await run();
  assert.equal(result.messages.some(isBreadcrumbMessage), false);
  assert.equal(result.messages.some(isBootstrapMessage), false);
  assert.deepEqual(agent.inbox.nextStep, []);
});

test("a child marked only by delegation depth is still treated as a sub-agent", async (t) => {
  const { run } = await preStepRuntime(t, {}, fixtureCwd, {
    cwd: fixtureCwd,
    parentSession: "parent-session",
    delegationDepth: 1,
  });
  const result = await run();
  assert.equal(result.messages.some(isBreadcrumbMessage), false);
  assert.equal(result.messages.some(isBootstrapMessage), false);
});

test("a generic sub-agent stays silent, matching Codex's non-Trellis SubagentStart path", async (t) => {
  const project = await temporaryProject(t);
  const { state, agent } = await preStepRuntime(t, {}, project.root, {
    cwd: project.root,
    parentSession: "parent-session",
    origin: "subagent",
  });
  await writeFile(
    join(project.sessions, "dsh_parent-session.json"),
    JSON.stringify({ current_task: project.task }),
  );

  const dispatch = prompt("Summarize the files in this directory.");
  let decision = { kind: "enter", messages: [dispatch] };
  for (const entry of state.listeners.filter((item) => item.event === "agent/pre-step")) {
    decision = await entry.listener(
      { agent, messages: [dispatch], step: 1, signal: undefined },
      async () => decision,
    );
  }

  // Codex's inject-subagent-context.py exits 0 for non-Trellis subagent types;
  // the child-side skills remain the pull path. Do not invent workflow state.
  assert.deepEqual(decision.messages, [dispatch]);
});

test("a delegated sub-agent bound to its own task gets a breadcrumb but never bootstrap", async (t) => {
  const project = await temporaryProject(t);
  const { agent, run } = await preStepRuntime(t, {}, project.root, {
    cwd: project.root,
    parentSession: "parent-session",
    origin: "subagent",
  });
  await writeFile(
    join(project.sessions, `${dshContextKey(agent.session.header.id)}.json`),
    JSON.stringify({ current_task: project.task }),
  );

  const result = await run();
  const crumb = result.messages.find(isBreadcrumbMessage);
  assert.ok(crumb);
  assert.equal(crumb.source.status, "planning");
  assert.equal(result.messages.some(isBootstrapMessage), false);
});

test("a delegated sub-agent first step carries only the pushed task context", async (t) => {
  const project = await temporaryProject(t);
  const { state, agent } = await preStepRuntime(t, {}, project.root, {
    cwd: project.root,
    parentSession: "parent-session",
    origin: "subagent",
  });
  await writeFile(
    join(project.sessions, "dsh_parent-session.json"),
    JSON.stringify({ current_task: project.task }),
  );

  const dispatch = prompt(
    "Active task: .trellis/tasks/demo\nLoad `trellis-agent-implement` and implement the task.",
  );
  let decision = { kind: "enter", messages: [dispatch] };
  for (const entry of state.listeners.filter((item) => item.event === "agent/pre-step")) {
    decision = await entry.listener(
      { agent, messages: [dispatch], step: 1, signal: undefined },
      async () => decision,
    );
  }

  assert.equal(decision.messages.some(isBreadcrumbMessage), false);
  assert.equal(decision.messages.some(isBootstrapMessage), false);
  const pushed = decision.messages.find((message) =>
    message.source?.form === "subagent-context",
  );
  assert.ok(pushed);
  assert.match(pushed.content[0].text, /Trellis Native Implement Subagent/);
  assert.match(pushed.content[0].text, /Active task: \.trellis\/tasks\/demo/);
});

test("a parent-linked session without subagent origin keeps root behavior", async (t) => {
  const { run } = await preStepRuntime(t, {}, fixtureCwd, {
    cwd: fixtureCwd,
    parentSession: "source-session",
  });
  const result = await run();
  assert.equal(result.messages.filter(isBreadcrumbMessage).length, 1);
  assert.equal(result.messages.filter(isBootstrapMessage).length, 1);
});

test("bootstrap is not redelivered by workflow state churn but returns after compaction", async (t) => {
  const project = await temporaryProject(t);
  const { agent, run } = await preStepRuntime(t, {}, project.root);
  const own = join(project.sessions, `${dshContextKey(agent.session.header.id)}.json`);

  const initial = await run();
  const crumb = initial.messages.find(isBreadcrumbMessage);
  const nudge = initial.messages.find(isBootstrapMessage);
  assert.ok(crumb);
  assert.ok(nudge);
  agent.session.append("user/message", crumb, { surfaceOp: "append" });
  const nudgeSeq = agent.session.append("user/message", nudge, { surfaceOp: "append" }).seq;

  // no_task -> planning: only the breadcrumb changes.
  await writeFile(own, JSON.stringify({ current_task: project.task }));
  const planning = await run();
  const planningCrumb = planning.messages.find(isBreadcrumbMessage);
  assert.equal(planningCrumb.source.status, "planning");
  assert.equal(planning.messages.some(isBootstrapMessage), false);
  agent.session.append("user/message", planningCrumb, { surfaceOp: "append" });

  // planning -> no_task: the breadcrumb returns, the nudge must not.
  await rm(own);
  const back = await run();
  const backCrumb = back.messages.find(isBreadcrumbMessage);
  assert.equal(backCrumb.source.status, "no_task");
  assert.equal(back.messages.some(isBootstrapMessage), false);
  agent.session.append("user/message", backCrumb, { surfaceOp: "append" });

  // A compaction that removes only the nudge re-delivers only the nudge.
  agent.session.append("user/message", prompt("Compacted"), {
    surfaceOp: { op: "replace", startSeq: nudgeSeq, endSeq: nudgeSeq },
    sourceEventSeqs: [nudgeSeq],
  });
  const restored = await run();
  assert.equal(restored.messages.some(isBreadcrumbMessage), false);
  assert.equal(restored.messages.filter(isBootstrapMessage).length, 1);
});

test("reject and empty first-step decisions keep one pending message per family", async (t) => {
  const { agent, run } = await preStepRuntime(t);
  const decision = { kind: "reject", reason: "host-owned reason" };
  assert.equal(await run({ decision }), decision);
  const pending = agent.inbox.nextStep.filter(isBreadcrumbMessage);
  const nudges = agent.inbox.nextStep.filter(isBootstrapMessage);
  assert.equal(pending.length, 1);
  assert.equal(nudges.length, 1);
  const queued = [...agent.inbox.nextStep];
  await run({ decision });
  // Same queued objects are reused, not replaced with fresh payload copies.
  assert.deepEqual(agent.inbox.nextStep, queued);
  const empty = { kind: "enter", messages: [], startsRequestSeries: true };
  assert.equal(await run({ decision: empty, step: 1 }), empty);
  assert.deepEqual(agent.inbox.nextStep, queued);
  const result = await run();
  assert.equal(result.messages.filter(isBreadcrumbMessage).length, 1);
  assert.equal(result.messages.filter(isBootstrapMessage).length, 1);
  assert.deepEqual(agent.inbox.nextStep, []);
});

test("disabling removes only queued Trellis breadcrumbs and re-enabling reinjects once", async (t) => {
  const { state, agent, run } = await preStepRuntime(t);
  const unrelated = prompt("Keep the user's queued input");
  agent.inbox.nextStep.push(unrelated);
  await run({ decision: { kind: "reject" } });
  assert.equal(agent.inbox.nextStep.filter(isBreadcrumbMessage).length, 1);
  state.publishSettings({ ...fixtureConfig, enabled: false });
  assert.deepEqual(agent.inbox.nextStep, [unrelated]);
  state.publishSettings(fixtureConfig);
  assert.equal((await run()).messages.filter(isBreadcrumbMessage).length, 1);
});

test("an unloaded pre-step listener cannot inject after its downstream continuation resolves", async (t) => {
  const { state, agent } = await preStepRuntime(t);
  const listener = state.listeners.filter((entry) => entry.event === "agent/pre-step")[0].listener;
  let release;
  const decision = { kind: "enter", messages: [prompt("Continue")] };
  const pending = listener({ agent, messages: decision.messages, step: 2 }, () => new Promise((resolve) => { release = resolve; }));
  state.disposePlugin();
  release(decision);
  assert.equal(await pending, decision);
  assert.deepEqual(agent.inbox.nextStep, []);
});

test("skip, disabled byte budget, missing project, and cancellation do not inject", async (t) => {
  const { state, agent, run, ctx } = await preStepRuntime(t);
  await run({ decision: { kind: "reject" } });
  assert.equal(agent.inbox.nextStep.filter(isBreadcrumbMessage).length, 1);
  assert.equal(agent.inbox.nextStep.filter(isBootstrapMessage).length, 1);
  assert.equal((await run({ messages: [prompt("no-trellis")] })).messages.some(isBreadcrumbMessage), false);
  assert.equal(agent.inbox.nextStep.length, 0);
  state.publishSettings({ ...fixtureConfig, maxBytes: 0 });
  assert.equal((await run()).messages.some(isBreadcrumbMessage), false);
  state.publishSettings({ ...fixtureConfig, projectRootMarkers: [".nonexistent-trellis-test-marker"] });
  assert.equal((await run()).messages.some(isBreadcrumbMessage), false);
  state.publishSettings(fixtureConfig);
  const controller = new AbortController();
  controller.abort();
  await assert.rejects(run({ signal: controller.signal }), { name: "AbortError" });
  assert.deepEqual(ctx.sessionProjections.stateOf(agent.session, KEY), {});
  assert.deepEqual(agent.inbox.nextStep, []);
});

async function temporaryProject(t) {
  const root = await mkdtemp(join(tmpdir(), "dsh-trellis-isolation-"));
  t.after(() => rm(root, { recursive: true, force: true }));
  const sessions = join(root, ".trellis", ".runtime", "sessions");
  const task = ".trellis/tasks/demo";
  const taskJson = join(root, task, "task.json");
  await mkdir(sessions, { recursive: true });
  await mkdir(join(root, task), { recursive: true });
  await writeFile(taskJson, JSON.stringify({ status: "planning" }));
  // Deliberately use an old workflow without task_error to cover upgrade order.
  await writeFile(join(root, ".trellis", "workflow.md"), [
    "[workflow-state:no_task]\nNo active task.\n[/workflow-state:no_task]",
    "[workflow-state:planning]\nPlan the task.\n[/workflow-state:planning]",
  ].join("\n"));
  return { root, sessions, task, taskJson };
}

test("pre-step isolates real session files and recovers task_error across settings reload and unbind", async (t) => {
  const project = await temporaryProject(t);
  const { agent, state, run } = await preStepRuntime(t, {}, project.root);
  const foreign = join(project.sessions, "dsh_other.json");
  const binding = JSON.stringify({ current_task: project.task });
  await writeFile(foreign, binding);
  const own = join(project.sessions, `${dshContextKey(agent.session.header.id)}.json`);
  const commitBreadcrumb = async () => {
    const message = (await run()).messages.find(isBreadcrumbMessage);
    assert.ok(message);
    agent.session.append("user/message", message, { surfaceOp: "append" });
    return message;
  };

  const unbound = await commitBreadcrumb();
  assert.equal(unbound.source.status, "no_task");
  assert.equal(unbound.source.task, null);
  await writeFile(own, binding);
  const planning = await commitBreadcrumb();
  assert.equal(planning.source.status, "planning");
  assert.equal(planning.source.task, project.task);

  await writeFile(project.taskJson, "{broken");
  const error = await commitBreadcrumb();
  assert.equal(error.source.status, "task_error");
  assert.equal(error.source.task, project.task);
  assert.match(error.content[0].text, /Do not create or activate another task/);
  assert.match(error.content[0].text, /Active task: \.trellis\/tasks\/demo/);
  assert.equal((await run()).messages.some(isBreadcrumbMessage), false);
  state.publishSettings({ ...fixtureConfig, enabled: false });
  state.publishSettings({ ...fixtureConfig, enabled: true });
  assert.equal((await run()).messages.some(isBreadcrumbMessage), false);
  assert.equal(await readFile(project.taskJson, "utf8"), "{broken");

  await writeFile(project.taskJson, JSON.stringify({ status: "planning" }));
  const repaired = await commitBreadcrumb();
  assert.equal(repaired.source.status, "planning");
  assert.notEqual(repaired.source.digest, error.source.digest);
  assert.equal(repaired.source.digest, planning.source.digest);
  await rm(own);
  assert.equal((await commitBreadcrumb()).source.status, "no_task");
  assert.equal(await readFile(foreign, "utf8"), binding);
});

test("composer without a native session id never borrows the generic dsh pointer", async (t) => {
  const project = await temporaryProject(t);
  const binding = JSON.stringify({ current_task: project.task });
  await writeFile(join(project.sessions, "dsh.json"), binding);
  const composer = createSessionComposer({
    maxBytes: 4096, skipKeyword: "no-trellis", projectRootMarkers: [".trellis"],
  }, {});
  const messages = await composer.compose({ session: { header: { cwd: project.root } } }, [], new AbortController().signal);
  assert.equal(messages[0].source.status, "no_task");
  assert.equal(messages[0].source.task, null);
  assert.equal(await readFile(join(project.sessions, "dsh.json"), "utf8"), binding);
});
