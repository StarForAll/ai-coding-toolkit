import { test } from "node:test";
import assert from "node:assert/strict";
import {
  contextInjectionLimits,
  dshInlineDispatchAllowed,
  normalizeToolName,
  parseBoolean,
  parseCount,
  parseFlowSequence,
  parseSection,
  specInjectionSettings,
  SPEC_INJECTION_DEFAULTS,
} from "../lib/trellis-config.js";

const CONFIG = `
# Trellis Configuration
session_auto_commit: false

spec_injection:
  enabled: false
  max_spec_chars: 1200  # inline comment
  tools:
    - Edit
    - Write

context_injection:
  max_total_bytes: 4096

codex:
  dispatch_mode: inline
`;

test("parseSection returns only the requested top-level section", () => {
  const section = parseSection(CONFIG, "spec_injection");
  assert.equal(section.get("enabled"), "false");
  assert.equal(section.get("max_spec_chars"), "1200");
  assert.deepEqual(section.get("tools"), ["Edit", "Write"]);
  assert.equal(section.has("dispatch_mode"), false);
  assert.equal(parseSection(CONFIG, "missing"), null);
  assert.equal(parseSection("", "spec_injection"), null);
});

test("parseSection handles flow lists, quoting and absence of a value", () => {
  const section = parseSection(
    "spec_injection:\n  tools: [\"Edit\", Write]\n  empty:\n  name: 'a b'\nnext: 1\n",
    "spec_injection",
  );
  assert.deepEqual(section.get("tools"), ["Edit", "Write"]);
  assert.deepEqual(section.get("empty"), []);
  assert.equal(section.get("name"), "a b");
  assert.equal(section.has("next"), false);
});

test("scalar coercion falls back instead of throwing", () => {
  assert.equal(parseBoolean("yes", false), true);
  assert.equal(parseBoolean("off", true), false);
  assert.equal(parseBoolean("maybe", true), true);
  assert.equal(parseCount("42", 7), 42);
  assert.equal(parseCount("4.2", 7), 7);
  assert.equal(parseCount("-1", 7), 7);
  assert.equal(parseCount(undefined, 7), 7);
  assert.deepEqual(parseFlowSequence("[a, , b]"), ["a", "b"]);
});

test("specInjectionSettings honours the project switch and defaults", () => {
  const configured = specInjectionSettings(CONFIG);
  assert.equal(configured.enabled, false);
  assert.equal(configured.maxSpecChars, 1200);
  assert.equal(configured.maxTotalChars, SPEC_INJECTION_DEFAULTS.maxTotalChars);
  assert.equal(
    configured.refreshWindowSeconds,
    SPEC_INJECTION_DEFAULTS.refreshWindowSeconds,
  );
  assert.deepEqual(configured.tools, ["edit", "write"]);

  const absent = specInjectionSettings("# no section\n");
  assert.equal(absent.enabled, true);
  assert.deepEqual(absent.tools, ["edit", "write"]);
});

test("specInjectionSettings accepts a read trigger and an empty tool list", () => {
  assert.deepEqual(
    specInjectionSettings("spec_injection:\n  tools: [Read, Edit, MultiEdit]\n").tools,
    ["read", "edit", "edit"],
  );
  assert.deepEqual(specInjectionSettings("spec_injection:\n  tools: []\n").tools, []);
});

test("contextInjectionLimits falls back per key", () => {
  assert.deepEqual(contextInjectionLimits(CONFIG), {
    maxFileBytes: 32768,
    maxArtifactBytes: 65536,
    maxTotalBytes: 4096,
  });
  assert.deepEqual(contextInjectionLimits(null), {
    maxFileBytes: 32768,
    maxArtifactBytes: 65536,
    maxTotalBytes: 131072,
  });
});

test("normalizeToolName lower-cases and folds MultiEdit", () => {
  assert.equal(normalizeToolName("Edit"), "edit");
  assert.equal(normalizeToolName(" MultiEdit "), "edit");
  assert.equal(normalizeToolName("WRITE"), "write");
});

test("dshInlineDispatchAllowed defaults to false and reads the escape hatch", () => {
  assert.equal(dshInlineDispatchAllowed(""), false);
  assert.equal(dshInlineDispatchAllowed("dsh:\n  dispatch_mode: inline\n"), false);
  assert.equal(
    dshInlineDispatchAllowed("dsh:\n  dispatch_mode: inline\n  inline_allow_dispatch: true\n"),
    true,
  );
  assert.equal(
    dshInlineDispatchAllowed("dsh:\n  inline_allow_dispatch: \"yes\"\n"),
    true,
  );
  assert.equal(
    dshInlineDispatchAllowed("dsh:\n  inline_allow_dispatch: maybe\n"),
    false,
  );
});
