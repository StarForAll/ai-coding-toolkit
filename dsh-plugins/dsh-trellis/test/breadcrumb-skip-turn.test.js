import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, mkdir, readFile, rm, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { fileURLToPath } from "node:url";
import { LlmAdapter, createUserMessage } from "@deepseek-ai/dsh-llm";
import { defineTool } from "@deepseek-ai/dsh-tools";
import { agentRuntime } from "./helpers/agent-runtime.js";
import * as plugin from "../lib/index.js";
import { isBreadcrumbMessage } from "../lib/breadcrumb.js";
import { isBootstrapMessage } from "../lib/bootstrap.js";

const cwd = fileURLToPath(new URL("./fixtures/breadcrumb-project", import.meta.url));
const user = (text) =>
  createUserMessage({ content: [{ type: "text", text }], source: { kind: "user" } });

/** One tool call, then plain text: a real multi-step turn. */
class ToolThenTextAdapter extends LlmAdapter {
  requests = [];
  calls = 0;
  async *stream(options) {
    options.signal?.throwIfAborted();
    this.requests.push(options);
    if (this.calls++ === 0) {
      yield { type: "block-start", index: 0, blockType: "tool-call" };
      yield { type: "block-end", index: 0, block: {
        type: "tool-call",
        id: "probe",
        name: "probe_echo",
        arguments: "{}",
      } };
      yield { type: "finish", reason: { kind: "tool-calls" } };
      return;
    }
    yield { type: "block-start", index: 0, blockType: "text" };
    yield { type: "block-end", index: 0, block: { type: "text", text: "done" } };
    yield { type: "finish", reason: { kind: "stop" } };
  }
}

const pluginMessages = (messages) =>
  messages.filter(
    (message) => isBreadcrumbMessage(message) || isBootstrapMessage(message),
  );

const textOf = (request) =>
  (request.messages ?? [])
    .flatMap((message) => message.content ?? [])
    .map((part) => (typeof part?.text === "string" ? part.text : ""))
    .join("\n");

async function skippingRuntime(t, root = cwd) {
  const ctx = await agentRuntime(t);
  ctx.provide("commands", { register: () => () => {} });
  ctx.provide("shellEnv", { register: () => () => {} });
  ctx.provide("subagents", { async listChildren() { return []; } });
  await ctx.plugin(plugin, { projectRootMarkers: [".trellis"], commandsEnabled: false });
  ctx.tools.register(
    defineTool({
      name: "probe_echo",
      description: "Test tool: acknowledges one call.",
      parameters: {},
      output: {
        schema: {
          type: "object",
          additionalProperties: false,
          properties: { ok: { type: "boolean", required: true } },
        },
        render: () => [{ type: "text", text: "ok" }],
      },
      async execute() {
        return { ok: true };
      },
    }),
  );
  const adapter = new ToolThenTextAdapter();
  ctx.llm.registerAdapter(["scripted"], adapter);
  const agent = await ctx.agentLoop.create(
    "skip-turn",
    { provider: "scripted", model: "local" },
    { cwd: root },
  );
  return { ctx, adapter, agent };
}

async function temporaryTrellisProject(t, config) {
  const root = await mkdtemp(join(tmpdir(), "dsh-trellis-skip-"));
  t.after(() => rm(root, { recursive: true, force: true }));
  await mkdir(join(root, ".trellis"), { recursive: true });
  await writeFile(
    join(root, ".trellis", "workflow.md"),
    "[workflow-state:no_task]\nNo active task.\n[/workflow-state:no_task]\n",
  );
  await writeFile(join(root, ".trellis", "config.yaml"), config);
  return root;
}

test("the skip keyword covers every step of its turn in a real agent loop", {
  timeout: 20_000,
}, async (t) => {
  const { adapter, agent } = await skippingRuntime(t);
  agent.followup(user("no-trellis: just read the file, no workflow state please"));
  await agent.whenIdle();

  // The turn really was multi-step: step 1 issued a tool call, step 2 answered.
  const steps = agent.session
    .snapshotEvents()
    .filter((event) => event.type === "step/start");
  assert.deepEqual(steps.map((event) => [event.data.turn, event.data.step]), [[1, 1], [1, 2]]);
  assert.equal(adapter.requests.length, 2);
  const [first, second] = adapter.requests;
  assert.ok(
    first.messages.some((message) =>
      message.content?.some((part) => /no-trellis/.test(part.text ?? "")),
    ),
    "step 1 sees the prompt that carries the keyword",
  );
  assert.ok(
    second.messages.some((message) => message.role === "tool"),
    "step 2 sees the tool result, not the prompt",
  );

  for (const [index, request] of [first, second].entries()) {
    assert.deepEqual(
      pluginMessages(request.messages).map((message) => message.source?.form),
      [],
      `step ${index + 1} of the skipped turn must stay free of Trellis messages`,
    );
  }
  assert.deepEqual(
    agent.session
      .snapshotEvents()
      .filter((event) => event.type === "user/message")
      .map((event) => event.data)
      .filter((message) => isBreadcrumbMessage(message) || isBootstrapMessage(message)),
    [],
    "the skipped turn logs no Trellis message",
  );

  // The skip is turn-scoped, not sticky: the next prompt gets the breadcrumb.
  const before = adapter.requests.length;
  agent.followup(user("Now do the work"));
  await agent.whenIdle();
  const next = adapter.requests.at(-1);
  assert.equal(adapter.requests.length, before + 1);
  assert.deepEqual(
    pluginMessages(next.messages).map((message) => message.source?.form),
    ["breadcrumb", "bootstrap"],
  );

  // A resumed turn still dedupes: a second step must not inject a second copy.
  adapter.calls = 0;
  const afterResume = adapter.requests.length;
  agent.followup(user("Do one more tool call"));
  await agent.whenIdle();
  assert.equal(adapter.requests.length, afterResume + 2);
  const secondStep = adapter.requests.at(-1);
  assert.deepEqual(
    pluginMessages(secondStep.messages).map((message) => message.source?.form),
    ["breadcrumb", "bootstrap"],
    "an injected breadcrumb is not repeated on the turn's later steps",
  );
});

test("a project skip keyword is turn-scoped and still lets the project bootstrap run", {
  timeout: 20_000,
}, async (t) => {
  const root = await temporaryTrellisProject(
    t,
    "prompt_injection:\n  skip_keyword: skip-me\nsession_auto_commit: false\n",
  );
  const { adapter, agent } = await skippingRuntime(t, root);
  agent.followup(user("skip-me: just read the file"));
  await agent.whenIdle();

  const steps = agent.session
    .snapshotEvents()
    .filter((event) => event.type === "step/start");
  assert.deepEqual(steps.map((event) => [event.data.turn, event.data.step]), [[1, 1], [1, 2]]);
  assert.equal(adapter.requests.length, 2);
  for (const [index, request] of adapter.requests.entries()) {
    assert.deepEqual(
      pluginMessages(request.messages).map((message) => message.source?.form),
      [],
      `step ${index + 1} of the skipped turn must stay free of Trellis messages`,
    );
  }
  // Skipping the breadcrumb must not skip the project defaults migration.
  assert.match(
    await readFile(join(root, ".trellis", "config.yaml"), "utf8"),
    /\ndsh:\n {2}dispatch_mode: inline\n$/,
  );

  // The project keyword is authoritative: the plugin fallback does not match.
  agent.followup(user("no-trellis is not this project's keyword"));
  await agent.whenIdle();
  const next = adapter.requests.at(-1);
  assert.deepEqual(
    pluginMessages(next.messages).map((message) => message.source?.form),
    ["breadcrumb", "bootstrap"],
  );
  assert.match(textOf(next), /Trellis workflow state: no_task/);
});