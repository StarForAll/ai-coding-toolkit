import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, mkdir, writeFile, rm } from "node:fs/promises";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { LlmAdapter } from "@deepseek-ai/dsh-llm";
import { agentRuntime } from "./helpers/agent-runtime.js";
import { registerSubagentContext } from "../lib/subagent-context.js";

/** Record every model request and answer with one short report. */
class RecordingAdapter extends LlmAdapter {
  requests = [];
  async resolveModel(provider, model) {
    return { provider, id: model, name: model };
  }
  async *stream(options) {
    this.requests.push(options);
    yield { type: "block-start", index: 0, blockType: "text" };
    yield { type: "text-delta", index: 0, text: "child report" };
    yield { type: "block-end", index: 0, block: { type: "text", text: "child report" } };
    yield { type: "finish", reason: { kind: "stop" } };
  }
}

const user = (text) => ({ role: "user", content: [{ type: "text", text }] });

const requestText = (options) =>
  (options.messages ?? [])
    .flatMap((message) => message.content ?? [])
    .map((part) => (typeof part?.text === "string" ? part.text : ""))
    .join("\n");

async function trellisProject(t) {
  const root = await mkdtemp(join(tmpdir(), "dsh-trellis-push-"));
  t.after(() => rm(root, { recursive: true, force: true }));
  const task = ".trellis/tasks/demo";
  await mkdir(join(root, task), { recursive: true });
  await mkdir(join(root, ".trellis", "spec"), { recursive: true });
  await mkdir(join(root, ".dsh", "skills", "trellis-agent-implement"), { recursive: true });
  await writeFile(join(root, ".trellis", "workflow.md"),
    "[workflow-state:in_progress]\nImplement.\n[/workflow-state:in_progress]\n");
  await writeFile(join(root, ".trellis", "config.yaml"), "dsh:\n  dispatch_mode: auto\n");
  await writeFile(join(root, ".trellis", "spec", "rules.md"), "Spec rules.\n");
  await writeFile(join(root, task, "task.json"), JSON.stringify({ status: "in_progress" }));
  await writeFile(join(root, task, "prd.md"), "The requirement.\n");
  await writeFile(join(root, task, "implement.jsonl"), JSON.stringify({
    file: ".trellis/spec/rules.md", reason: "coding rules",
  }));
  await writeFile(join(root, ".dsh", "skills", "trellis-agent-implement", "SKILL.md"),
    "---\nname: trellis-agent-implement\ndescription: test role\n---\n# Implement Agent\n\nDo the role.\n");
  return { root, task };
}

test("a real child whose role only the dispatch label names still receives the push", {
  timeout: 15_000,
}, async (t) => {
  const { root, task } = await trellisProject(t);
  const ctx = await agentRuntime(t);
  const adapter = new RecordingAdapter();
  ctx.llm.registerAdapter(["scripted"], adapter);
  const dispose = registerSubagentContext(ctx, { projectRootMarkers: [".trellis"] });
  t.after(dispose);

  const parent = await ctx.agentLoop.create(
    "push-parent", { provider: "scripted", model: "local" }, { cwd: root },
  );
  // The child header carries parentSession and the role label lands in the
  // durable descriptor event, exactly as subagent runtime records it for
  // `description: "trellis-agent-implement"`.
  const child = await ctx.agentLoop.create(
    "push-child",
    { provider: "scripted", model: "local" },
    { cwd: root, parentSession: parent.session.header.id, origin: "subagent", delegationDepth: 1 },
  );
  child.session.append("subagent/descriptor", {
    version: 1, mode: "continuable", provider: "local-test", label: "trellis-agent-implement",
  });

  // No role name in the prompt: only the descriptor label can select the role.
  child.followup(user(`Active task: ${task}\nImplement the task.`));
  await child.whenIdle();

  const text = requestText(adapter.requests.at(-1));
  assert.match(text, /# Trellis Native Implement Subagent/);
  assert.match(text, /Do not load `\.dsh\/skills\/trellis-agent-implement\/SKILL\.md` again/);
  assert.match(text, /Do the role\./);
  assert.match(text, /Spec rules\./);
  assert.match(text, /The requirement\./);
  assert.equal(text.split("prepared by dsh-trellis").length - 1, 1);
});

test("a topical dispatch label stays generic in a real child", {
  timeout: 15_000,
}, async (t) => {
  const { root, task } = await trellisProject(t);
  const ctx = await agentRuntime(t);
  const adapter = new RecordingAdapter();
  ctx.llm.registerAdapter(["scripted"], adapter);
  const dispose = registerSubagentContext(ctx, { projectRootMarkers: [".trellis"] });
  t.after(dispose);

  const parent = await ctx.agentLoop.create(
    "topic-parent", { provider: "scripted", model: "local" }, { cwd: root },
  );
  const child = await ctx.agentLoop.create(
    "topic-child",
    { provider: "scripted", model: "local" },
    { cwd: root, parentSession: parent.session.header.id, origin: "subagent", delegationDepth: 1 },
  );
  // The label talks about the role; it does not select it.
  child.session.append("subagent/descriptor", {
    version: 1, mode: "continuable", provider: "local-test",
    label: "研究 trellis-agent-implement 插件的 README",
  });

  child.followup(user(`Active task: ${task}\nSummarise the change.`));
  await child.whenIdle();

  const text = requestText(adapter.requests.at(-1));
  assert.doesNotMatch(text, /Trellis Native Implement Subagent/);
  assert.match(text, /Summarise the change\./);
});
