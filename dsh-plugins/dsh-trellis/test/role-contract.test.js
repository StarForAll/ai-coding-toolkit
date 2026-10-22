import { test } from "node:test";
import assert from "node:assert/strict";
import { roleFromLabel, stripPullOnlyContext } from "../lib/role-contract.js";

test("roleFromLabel accepts only a whole role label", () => {
  assert.equal(roleFromLabel("trellis-agent-implement"), "implement");
  assert.equal(roleFromLabel("trellis-check"), "check");
  assert.equal(roleFromLabel("  trellis-agent-research  "), "research");
  assert.equal(roleFromLabel("`Trellis-Agent-Check`"), "check");
  assert.equal(roleFromLabel("trellis-agent-implement."), "implement");
  assert.equal(roleFromLabel("“trellis-research”"), "research");
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
    "trellis-agent-check: docs",
    "load trellis-agent-research",
    "trellis-agent-implement 插件的实现",
  ]) {
    assert.equal(roleFromLabel(label), null, label);
  }
});

test("stripPullOnlyContext leaves a body without the pull section intact", () => {
  const body = "# Role\n\nDo the work.\n";
  assert.equal(stripPullOnlyContext(body, "implement"), body);
  assert.equal(stripPullOnlyContext("", "check"), "");
});
