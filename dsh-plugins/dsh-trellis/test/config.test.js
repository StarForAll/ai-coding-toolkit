import { test } from "node:test";
import assert from "node:assert/strict";
import { Config, resolveConfig } from "../lib/config.js";

test("resolveConfig leaves pythonCmd empty for platform-aware auto detection", () => {
  assert.equal(resolveConfig({}).pythonCmd, "");
  assert.equal(
    resolveConfig({ pythonCmd: "  py-custom  " }).pythonCmd,
    "py-custom",
  );
});

test("resolveConfig preserves explicit feature switches", () => {
  const config = resolveConfig({ enabled: false, commandsEnabled: false });
  assert.equal(config.enabled, false);
  assert.equal(config.commandsEnabled, false);
});

test("Config publishes descriptions for DSH plugin configuration surfaces", () => {
  const json = Config.toJSON();
  const root = json.refs[String(json.uid)];
  for (const key of Object.keys(root.dict)) {
    const field = json.refs[String(root.dict[key])];
    assert.equal(typeof field.meta.description, "string", key);
    assert.notEqual(field.meta.description, "", key);
  }
});

test("project root discovery prefers .trellis so non-Git Trellis projects still work", () => {
  assert.deepEqual(resolveConfig({}).projectRootMarkers, [".trellis", ".git"]);
  assert.deepEqual(
    resolveConfig({ projectRootMarkers: [".git"] }).projectRootMarkers,
    [".git"],
  );
});

test("dispatch guard defaults on and can be switched off explicitly", () => {
  assert.equal(resolveConfig({}).dispatchGuard, true);
  assert.equal(resolveConfig({ dispatchGuard: false }).dispatchGuard, false);
});
