import { test } from "node:test";
import assert from "node:assert/strict";
import { join, resolve, sep } from "node:path";
import { createSessionComposer } from "../lib/session-composer.js";
import { resolveConfig } from "../lib/config.js";

const projectRoot = resolve("composer-fixture");
const proj = (rel) => join(projectRoot, rel);

/** Minimal in-memory fs shim ({exists, stat, readFile}) for the composer. */
function memoryFs(initial = {}) {
  const files = new Map(Object.entries(initial));
  const mtimes = new Map();
  let tick = 1;
  return {
    async exists(path) {
      if (files.has(path)) return true;
      const prefix = `${path}${sep}`;
      return [...files.keys()].some((p) => p.startsWith(prefix));
    },
    async stat(path) {
      const prefix = `${path}${sep}`;
      const dir = !files.has(path) && [...files.keys()].some((p) => p.startsWith(prefix));
      if (!files.has(path) && !dir) return null;
      if (!mtimes.has(path)) mtimes.set(path, tick++);
      return { mtimeMs: mtimes.get(path), isDirectory: dir };
    },
    async readFile(path) {
      return files.has(path) ? files.get(path) : null;
    },
  };
}

const WORKFLOW = `[workflow-state:no_task]
No active task. Ask for task-creation consent.
[/workflow-state:no_task]
`;

const prompt = (text) => [{ content: [{ type: "text", text }] }];

function composerFor(fs, pluginConfig = {}) {
  return createSessionComposer(resolveConfig(pluginConfig), { get: () => undefined }, {
    fs,
  });
}

const agent = { session: { header: { id: "session-1", cwd: projectRoot } } };

function fsWithConfig(configText) {
  return memoryFs({
    [proj(".trellis/workflow.md")]: WORKFLOW,
    ...(configText === null ? {} : { [proj(".trellis/config.yaml")]: configText }),
  });
}

test("composer: project prompt_injection.skip_keyword skips the breadcrumb", async () => {
  const composer = composerFor(
    fsWithConfig("prompt_injection:\n  skip_keyword: skip-me\n"),
  );
  assert.equal((await composer.compose(agent, prompt("please skip-me now"))).length, 0);
  // The plugin-level default must not be consulted when the project sets one.
  assert.equal((await composer.compose(agent, prompt("no-trellis"))).length, 2);
});

test("composer: plugin skipKeyword remains the fallback without project config", async () => {
  const composer = composerFor(fsWithConfig(null));
  assert.equal((await composer.compose(agent, prompt("no-trellis"))).length, 0);
  assert.equal((await composer.compose(agent, prompt("hello"))).length, 2);
});

test("composer: an explicitly empty project keyword disables the escape hatch", async () => {
  const composer = composerFor(
    fsWithConfig('prompt_injection:\n  skip_keyword: ""\n'),
  );
  assert.equal((await composer.compose(agent, prompt("no-trellis"))).length, 2);
});

test("composer: child agent with no task is silent", async () => {
  const composer = composerFor(fsWithConfig(null));
  const child = {
    session: {
      header: { id: "session-2", cwd: projectRoot, origin: "subagent" },
    },
  };
  assert.equal((await composer.compose(child, prompt("hello"))).length, 0);
});
