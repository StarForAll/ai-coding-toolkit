import { test } from "node:test";
import assert from "node:assert/strict";
import { roleFromLabel, roleFromPrompt, stripPullOnlyContext } from "../lib/role-contract.js";

test("roleFromLabel accepts only a whole role label", () => {
  assert.equal(roleFromLabel("trellis-agent-implement"), "implement");
  assert.equal(roleFromLabel("trellis-check"), "check");
  assert.equal(roleFromLabel("  trellis-agent-research  "), "research");
  assert.equal(roleFromLabel("`Trellis-Agent-Check`"), "check");
  assert.equal(roleFromLabel("trellis-agent-implement."), "implement");
  assert.equal(roleFromLabel("“trellis-research”"), "research");
  // A role name followed by an annotation still selects the role.
  assert.equal(roleFromLabel("trellis-agent-implement (audit round 3)"), "implement");
  assert.equal(roleFromLabel("trellis-agent-check（第 3 轮）"), "check");
  assert.equal(roleFromLabel("trellis-agent-research: compare options"), "research");
  assert.equal(roleFromLabel("trellis-agent-implement — round 3"), "implement");
  assert.equal(roleFromLabel("trellis-agent-check - docs review"), "check");
  // Non-strings and empty labels never select a role.
  assert.equal(roleFromLabel(undefined), null);
  assert.equal(roleFromLabel(null), null);
  assert.equal(roleFromLabel(42), null);
  assert.equal(roleFromLabel("   "), null);
});

test("roleFromLabel keeps topical mentions generic", () => {
  for (const label of [
    "研究 trellis-agent-implement 插件的 README",
    "about trellis-agent-check plugin docs",
    "trellis-agent-implement task",
    "trellis-agent-check plugin docs",
    "load trellis-agent-research",
    "trellis-agent-implement 插件的实现",
    "trellis-agent-researcher",
  ]) {
    assert.equal(roleFromLabel(label), null, label);
  }
});

test("roleFromPrompt requires a declaration, not a path or prose mention", () => {
  assert.equal(roleFromPrompt("trellis-agent-implement"), "implement");
  assert.equal(roleFromPrompt("trellis-implement: implement the plan"), "implement");
  assert.equal(roleFromPrompt("trellis-check (round 3)"), "check");
  assert.equal(roleFromPrompt("Active task: .trellis/tasks/x\nRole: trellis-agent-check"), "check");
  assert.equal(roleFromPrompt("Agent：trellis-research"), "research");
  assert.equal(
    roleFromPrompt("You are the `trellis-implement` sub-agent.\nActive task: .trellis/tasks/x"),
    "implement",
  );
  assert.equal(
    roleFromPrompt("You are already the trellis-check role.\nActive task: .trellis/tasks/x"),
    "check",
  );
  assert.equal(
    roleFromPrompt("You are the dispatched `trellis-implement` role.\nActive task: .trellis/tasks/x"),
    "implement",
  );
  for (const text of [
    "Read .dsh/skills/trellis-agent-implement/SKILL.md and report its length.",
    "Load `.dsh/skills/trellis-agent-check/SKILL.md` once.",
    "Run the trellis-check skill after editing.",
    "About trellis-agent-research plugin docs.",
    "trellis-agent-implement plugin docs",
    "",
    null,
  ]) {
    assert.equal(roleFromPrompt(text), null, String(text));
  }
});

test("stripPullOnlyContext leaves a body without the pull section intact", () => {
  const body = "# Role\n\nDo the work.\n";
  assert.equal(stripPullOnlyContext(body, "implement"), body);
  assert.equal(stripPullOnlyContext("", "check"), "");
});
