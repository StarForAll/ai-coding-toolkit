import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, mkdir, writeFile, rm } from "node:fs/promises";
import { join } from "node:path";
import { tmpdir } from "node:os";
import {
  buildSubagentContext,
  parentTaskPath,
  parseDispatchPrompt,
  readManifest,
  readRoleInstructions,
  registerSubagentContext,
  buildResearchContext,
  stripYamlFrontmatter,
  subagentContextMessage,
  truncateUtf8,
} from "../lib/subagent-context.js";
import { dshContextKey } from "../lib/session-env.js";

const prompt = (text) => ({ content: [{ type: "text", text }] });

async function fixture(t) {
  const root = await mkdtemp(join(tmpdir(), "dsh-trellis-subagent-"));
  t.after(() => rm(root, { recursive: true, force: true }));
  const task = ".trellis/tasks/demo";
  await mkdir(join(root, task), { recursive: true });
  await mkdir(join(root, ".trellis", "spec"), { recursive: true });
  await mkdir(join(root, ".dsh", "skills", "trellis-agent-implement"), {
    recursive: true,
  });
  await writeFile(
    join(root, ".dsh", "skills", "trellis-agent-implement", "SKILL.md"),
    "---\nname: trellis-agent-implement\ndescription: test role\n---\n# Role\n\nDo the role.\n",
  );
  await writeFile(join(root, ".trellis", "spec", "a.md"), "Spec rules.\n");
  await writeFile(join(root, task, "task.json"), JSON.stringify({ status: "in_progress" }));
  await writeFile(join(root, task, "prd.md"), "The requirement.\n");
  await writeFile(join(root, task, "design.md"), "The design.\n");
  await writeFile(join(root, task, "implement.jsonl"), [
    JSON.stringify({ file: ".trellis/spec/a.md", reason: "coding rules" }),
    JSON.stringify({ _example: "placeholder" }),
  ].join("\n"));
  await writeFile(join(root, task, "check.jsonl"), JSON.stringify({
    file: ".trellis/spec/a.md",
    reason: "review rules",
  }));
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

const childAgent = (root, { id = "child-1", parentSession = "parent-1" } = {}) => ({
  session: { id, header: { id, cwd: root, parentSession } },
});

test("parseDispatchPrompt recovers the role and the Active task prelude", () => {
  assert.deepEqual(
    parseDispatchPrompt([
      prompt("Active task: .trellis/tasks/10-19-demo\nLoad `.dsh/skills/trellis-agent-check/SKILL.md` once."),
    ]),
    { role: "check", taskPath: ".trellis/tasks/10-19-demo", finish: false },
  );
  assert.equal(
    parseDispatchPrompt([prompt("trellis-implement: implement the plan")]).role,
    "implement",
  );
  assert.equal(
    parseDispatchPrompt([prompt("Active task: .trellis/tasks/x\n[finish] final check")]).finish,
    true,
  );
  assert.deepEqual(parseDispatchPrompt([prompt("Summarise this file")]), {
    role: null,
    taskPath: null,
    finish: false,
  });
});

test("stripYamlFrontmatter keeps only the role body", () => {
  assert.equal(
    stripYamlFrontmatter("---\nname: role\ndescription: test\n---\n# Role\n\nDo it.\n"),
    "# Role\n\nDo it.\n",
  );
  assert.equal(stripYamlFrontmatter("# Role\n"), "# Role\n");
  assert.equal(stripYamlFrontmatter("---\nnot closed\n"), "---\nnot closed\n");
});

test("readRoleInstructions reads the installed DSH role skill", async (t) => {
  const { root } = await fixture(t);
  const body = await readRoleInstructions({ root, role: "implement" });
  assert.match(body, /^# Role/m);
  assert.match(body, /Do the role\./);
  assert.doesNotMatch(body, /^name:/m);

  assert.equal(await readRoleInstructions({ root, role: "unknown" }), null);
  assert.equal(await readRoleInstructions({ root, role: "check" }), null);
});

test("subagentContextMessage keeps a role pointer when the skill is absent", () => {
  const message = subagentContextMessage({
    role: "check",
    taskPath: ".trellis/tasks/demo",
    context: "Curated.",
  });
  assert.match(
    message.content[0].text,
    /Load `\.dsh\/skills\/trellis-agent-check\/SKILL\.md` once before acting\./,
  );
  assert.match(message.content[0].text, /## Role Instructions/);
  // The push overrides the role skill's "load context yourself" step instead
  // of leaving the child with two contradictory instructions.
  assert.match(message.content[0].text, /do not run[\s\S]{0,20}`task\.py current`/);
  assert.doesNotMatch(
    message.content[0].text,
    /"Required: Load Trellis Context First" section is fully/,
  );
  // No skill body was inlined, so the message must not claim one is below.
  assert.doesNotMatch(message.content[0].text, /role skill is included immediately below/);
  assert.match(message.content[0].text, /Curated\./);
  // The prepared-context statement appears exactly once in one push.
  assert.equal(
    message.content[0].text.split("prepared by dsh-trellis").length - 1,
    1,
  );
});

test("subagentContextMessage tells the child not to reload an inlined skill", () => {
  const message = subagentContextMessage({
    role: "implement",
    taskPath: ".trellis/tasks/demo",
    context: "Curated.",
    roleInstructions: "## Task Context\n\nSee below.\n\n# Implement\n\nDo the work.",
  });
  const text = message.content[0].text;
  assert.match(text, /role skill is included immediately below/);
  assert.match(text, /Do not load `\.dsh\/skills\/trellis-agent-implement\/SKILL\.md` again/);
  assert.match(text, /ignore any "load the task context yourself" step/);
  assert.match(text, /# Implement/);
  // One preamble, one context pointer: the old duplication must not return.
  assert.equal(text.split("prepared by dsh-trellis").length - 1, 1);
  assert.equal((text.match(/^## Task Context$/gm) ?? []).length, 1);
  // The skill pointer fallback is not appended when the body is inlined.
  assert.doesNotMatch(text, /Load `\.dsh\/skills\/trellis-agent-implement\/SKILL\.md` once/);
});

test("parseDispatchPrompt falls back to the child descriptor label", () => {
  const roleless = [prompt("Active task: .trellis/tasks/demo\nResearch the spec tree.")];
  assert.deepEqual(parseDispatchPrompt(roleless, "trellis-agent-research"), {
    role: "research",
    taskPath: ".trellis/tasks/demo",
    finish: false,
  });
  // The prompt still wins when both carry a role.
  assert.equal(
    parseDispatchPrompt([prompt("trellis-agent-check")], "trellis-agent-implement").role,
    "check",
  );
  // A label that is not a Trellis role keeps the push silent.
  assert.equal(parseDispatchPrompt(roleless, "fix the flaky test").role, null);
  assert.equal(parseDispatchPrompt(roleless, null).role, null);
  // A label that only mentions a role (a research topic) is not a role.
  assert.equal(
    parseDispatchPrompt(roleless, "about trellis-agent-check plugin docs").role,
    null,
  );
  assert.equal(
    parseDispatchPrompt(roleless, "研究 trellis-agent-implement 插件的 README").role,
    null,
  );
  // Exact labels still work, including wrapping backticks and case.
  assert.equal(parseDispatchPrompt(roleless, "`Trellis-Agent-Check`").role, "check");
});

test("parentTaskPath drops a stale parent pointer", async (t) => {
  const { root } = await fixture(t);
  const sessions = join(root, ".trellis", ".runtime", "sessions");
  await mkdir(sessions, { recursive: true });
  const pointer = join(sessions, `${dshContextKey("parent-1")}.json`);
  await writeFile(pointer, JSON.stringify({ current_task: ".trellis/tasks/gone" }));
  // The directory is gone, so there is no context to push for it.
  assert.equal(await parentTaskPath(root, "parent-1"), null);
  await writeFile(pointer, JSON.stringify({ current_task: ".trellis/tasks/demo" }));
  assert.equal(await parentTaskPath(root, "parent-1"), ".trellis/tasks/demo");
  assert.equal(await parentTaskPath(root, ""), null);
});

test("readManifest skips placeholder rows and keeps real entries", async (t) => {
  const { root, task } = await fixture(t);
  assert.deepEqual(await readManifest(root, `${task}/implement.jsonl`), [
    { file: ".trellis/spec/a.md", type: "file", reason: "coding rules" },
  ]);
  assert.deepEqual(await readManifest(root, `${task}/missing.jsonl`), []);
});

test("buildSubagentContext inlines the manifest and task artifacts", async (t) => {
  const { root, task } = await fixture(t);
  const context = await buildSubagentContext({
    root,
    taskPath: task,
    role: "implement",
    limits: { maxFileBytes: 32768, maxArtifactBytes: 65536, maxTotalBytes: 131072 },
  });
  assert.match(context, /=== \.trellis\/spec\/a\.md ===/);
  assert.match(context, /Spec rules\./);
  assert.match(context, /=== \.trellis\/tasks\/demo\/prd\.md \(Requirements\) ===/);
  assert.match(context, /The requirement\./);
  assert.match(context, /The design\./);
});

test("buildSubagentContext reports an empty manifest instead of silence", async (t) => {
  const { root, task } = await fixture(t);
  await rm(join(root, task, "implement.jsonl"));
  const context = await buildSubagentContext({
    root,
    taskPath: task,
    role: "implement",
    limits: { maxFileBytes: 32768, maxArtifactBytes: 65536, maxTotalBytes: 131072 },
  });
  assert.match(context, /implement\.jsonl has no curated entries/);
});

test("buildSubagentContext refuses a task path outside the repository", async (t) => {
  const { root } = await fixture(t);
  assert.equal(
    await buildSubagentContext({
      root,
      taskPath: "../outside",
      role: "implement",
      limits: { maxFileBytes: 1024, maxArtifactBytes: 1024, maxTotalBytes: 4096 },
    }),
    null,
  );
});

test("truncateUtf8 never splits a code point", () => {
  const text = "aé中";
  assert.equal(truncateUtf8(text, 100), text);
  assert.equal(truncateUtf8(text, 2), "a");
  assert.equal(truncateUtf8(text, 3), "aé");
});

test("registerSubagentContext pushes once, before the child's first request", async (t) => {
  const { root, task } = await fixture(t);
  const { ctx, listeners } = harness();
  const dispose = registerSubagentContext(ctx, { projectRootMarkers: [".trellis"] });
  t.after(dispose);
  const pre = listeners.get("agent/pre-step");

  const agent = childAgent(root);
  const decision = {
    kind: "enter",
    messages: [
      prompt(`Active task: ${task}\nLoad \`.dsh/skills/trellis-agent-implement/SKILL.md\` once.`),
    ],
  };
  const first = await pre(
    { agent, messages: decision.messages, step: 1, signal: undefined },
    async () => decision,
  );
  const injected = first.messages.at(-1);
  assert.equal(injected.source.form, "subagent-context");
  assert.equal(injected.source.role, "implement");
  assert.match(injected.content[0].text, /Active task: \.trellis\/tasks\/demo/);
  assert.match(injected.content[0].text, /## Role Instructions/);
  assert.match(injected.content[0].text, /Do the role\./);
  assert.match(injected.content[0].text, /Spec rules\./);

  const second = await pre(
    { agent, messages: decision.messages, step: 1, signal: undefined },
    async () => decision,
  );
  assert.deepEqual(second, decision);
});

test("registerSubagentContext stays silent outside a Trellis role's first step", async (t) => {
  const { root, task } = await fixture(t);
  const { ctx, listeners } = harness();
  const dispose = registerSubagentContext(ctx, { projectRootMarkers: [".trellis"] });
  t.after(dispose);
  const pre = listeners.get("agent/pre-step");
  const messages = [prompt(`Active task: ${task}\ntrellis-agent-check`)];
  const decision = { kind: "enter", messages };

  const topLevel = { session: { id: "top", header: { id: "top", cwd: root } } };
  assert.deepEqual(
    await pre({ agent: topLevel, messages, step: 1 }, async () => decision),
    decision,
  );

  const child = childAgent(root);
  assert.deepEqual(
    await pre({ agent: child, messages, step: 2 }, async () => decision),
    decision,
  );

  const roleless = [prompt(`Active task: ${task}\nJust summarise this.`)];
  const rolelessDecision = { kind: "enter", messages: roleless };
  assert.deepEqual(
    await pre({ agent: child, messages: roleless, step: 1 }, async () => rolelessDecision),
    rolelessDecision,
  );
});

test("readRoleInstructions strips pull-only context instructions from the pushed copy", async (t) => {
  const { root } = await fixture(t);
  await writeFile(
    join(root, ".dsh", "skills", "trellis-agent-implement", "SKILL.md"),
    [
      "---",
      "name: trellis-agent-implement",
      "description: test",
      "---",
      "# Implement Agent",
      "",
      "## Required: Load Trellis Context First",
      "",
      "This platform does NOT auto-inject task context via hook. Before doing anything else, you MUST load context yourself.",
      "",
      "### Step 1: Find the active task path",
      "",
      "Run `python3 ./.trellis/scripts/task.py current --source` or ask the user.",
      "",
      "## Recursion Guard",
      "",
      "Do not spawn another role.",
      "",
      "dsh does not auto-inject SessionStart task context. Always pull context as required below.",
      "",
      "## Context",
      "",
      "Read the specs.",
      "",
    ].join("\n"),
  );
  const body = await readRoleInstructions({ root, role: "implement" });
  assert.match(body, /## Task Context/);
  assert.match(body, /## Recursion Guard/);
  assert.match(body, /## Context/);
  assert.doesNotMatch(body, /MUST load context yourself/);
  assert.doesNotMatch(body, /does NOT auto-inject/);
  assert.doesNotMatch(body, /Run `python3 .*task\.py current/);
  assert.doesNotMatch(body, /ask the user which task|ask the user where/);
});

test("readRoleInstructions rewrites the research task-resolution step", async (t) => {
  const { root } = await fixture(t);
  await mkdir(join(root, ".dsh", "skills", "trellis-agent-research"), { recursive: true });
  await writeFile(
    join(root, ".dsh", "skills", "trellis-agent-research", "SKILL.md"),
    [
      "---",
      "name: trellis-agent-research",
      "description: test",
      "---",
      "# Research Agent",
      "",
      "## Workflow",
      "",
      "### Step 1: Resolve Current Task",
      "",
      "Run `python3 ./.trellis/scripts/task.py current --source`. If no task, ask the user where to write output.",
      "",
      "### Step 2: Understand Search Request",
      "",
      "Classify the request.",
      "",
    ].join("\n"),
  );
  const body = await readRoleInstructions({ root, role: "research" });
  assert.match(body, /### Step 1: Prepare Output Directory/);
  assert.match(body, /\{TASK_DIR\}\/research\//);
  assert.match(body, /### Step 2: Understand Search Request/);
  assert.doesNotMatch(body, /task\.py current/);
  assert.doesNotMatch(body, /ask the user where/);
});

test("buildSubagentContext gives research the spec tree instead of task artifacts", async (t) => {
  const { root, task } = await fixture(t);
  const context = await buildResearchContext({
    root,
    taskPath: task,
    limits: { maxFileBytes: 32768, maxArtifactBytes: 65536, maxTotalBytes: 131072 },
  });
  assert.match(context, /## Project Spec Directory Structure/);
  assert.match(context, /## Search Tips/);
  assert.match(context, /get_context\.py --mode packages/);
  assert.doesNotMatch(context, /The requirement\./);
  assert.doesNotMatch(context, /no curated entries/);
});
