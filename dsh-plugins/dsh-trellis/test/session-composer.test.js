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
  const dirs = new Set();
  const mtimes = new Map();
  let tick = 1;
  return {
    async exists(path) {
      if (files.has(path) || dirs.has(path)) return true;
      const prefix = `${path}${sep}`;
      return [...files.keys(), ...dirs].some((p) => p.startsWith(prefix));
    },
    async stat(path) {
      const prefix = `${path}${sep}`;
      const dir = dirs.has(path) ||
        (!files.has(path) && [...files.keys(), ...dirs].some((p) => p.startsWith(prefix)));
      if (!files.has(path) && !dir) return null;
      if (!mtimes.has(path)) mtimes.set(path, tick++);
      return { mtimeMs: mtimes.get(path), isDirectory: dir };
    },
    async readFile(path) {
      return files.has(path) ? files.get(path) : null;
    },
    async writeFile(path, content) {
      files.set(path, content);
      mtimes.set(path, tick++);
    },
    async rename(from, to) {
      files.set(to, files.get(from));
      files.delete(from);
      mtimes.set(to, tick++);
    },
    async mkdir(path) {
      dirs.add(path);
      mtimes.set(path, tick++);
    },
    async rmdir(path) {
      dirs.delete(path);
    },
    async unlink(path) {
      files.delete(path);
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

test("composer: the skip keyword covers every step of its turn", async () => {
  const composer = composerFor(fsWithConfig(null));
  // Step 1 carries the prompt, so it decides the turn.
  assert.deepEqual(
    await composer.compose(agent, prompt("no-trellis this turn"), undefined, { turn: 1 }),
    [],
  );
  // A later step only claims the tool result; the decision must still stand.
  assert.deepEqual(
    await composer.compose(agent, prompt("tool output"), undefined, { turn: 1 }),
    [],
  );
  // The next turn is a fresh decision.
  assert.equal(
    (await composer.compose(agent, prompt("now do the work"), undefined, { turn: 2 })).length,
    2,
  );
});

test("composer: a keyword seen mid-turn skips the rest of that turn only", async () => {
  const composer = composerFor(fsWithConfig(null));
  assert.equal(
    (await composer.compose(agent, prompt("start"), undefined, { turn: 1 })).length,
    2,
  );
  assert.deepEqual(
    await composer.compose(agent, prompt("no-trellis"), undefined, { turn: 1 }),
    [],
  );
  assert.deepEqual(
    await composer.compose(agent, prompt("more tool output"), undefined, { turn: 1 }),
    [],
  );
  assert.equal(
    (await composer.compose(agent, prompt("next turn"), undefined, { turn: 2 })).length,
    2,
  );
});

test("composer: without a turn position the skip stays step-scoped", async () => {
  // Hosts that do not report a turn keep the previous behaviour instead of
  // silently remembering a decision they cannot scope.
  const composer = composerFor(fsWithConfig(null));
  assert.deepEqual(await composer.compose(agent, prompt("no-trellis")), []);
  assert.equal((await composer.compose(agent, prompt("tool output"))).length, 2);
});

function messageText(message) {
  return message.content.map((part) => part.text ?? "").join("");
}

test("composer: bootstraps dsh.dispatch_mode before the first breadcrumb", async () => {
  const fs = fsWithConfig("session_auto_commit: false\n");
  const composer = composerFor(fs);
  const composed = await composer.compose(agent, prompt("hello"));
  const crumb = composed.find((message) => messageText(message).includes("Trellis workflow state"));
  assert.ok(crumb, "breadcrumb expected");
  assert.match(messageText(crumb), /<dsh-mode>/);
  assert.match(
    await fs.readFile(proj(".trellis/config.yaml")),
    /\ndsh:\n  dispatch_mode: inline\n$/,
  );
});

test("composer: an explicit dispatch_mode is not overwritten", async () => {
  const source = "dsh:\n  dispatch_mode: auto\n";
  const fs = fsWithConfig(source);
  const composed = await composerFor(fs).compose(agent, prompt("hello"));
  const crumb = composed.find((message) => messageText(message).includes("Trellis workflow state"));
  assert.ok(crumb, "breadcrumb expected");
  assert.doesNotMatch(messageText(crumb), /<dsh-mode>/);
  assert.equal(await fs.readFile(proj(".trellis/config.yaml")), source);
});

test("composer: a zero breadcrumb budget still bootstraps the project config", async () => {
  const fs = fsWithConfig("a: 1\n");
  const composed = await composerFor(fs, { maxBytes: 0 }).compose(agent, prompt("hello"));
  assert.deepEqual(composed, []);
  assert.match(await fs.readFile(proj(".trellis/config.yaml")), /\ndsh:\n  dispatch_mode: inline\n$/);
});

test("composer: a Trellis project with a broken workflow still gets fallback + bootstrap", async () => {
  const fs = memoryFs({
    [proj(".trellis/workflow.md")]: "# no state blocks\n",
    [proj(".trellis/config.yaml")]: "dsh:\n  dispatch_mode: auto\n",
  });
  const composed = await composerFor(fs).compose(agent, prompt("hello"));
  assert.equal(composed.length, 2);
  const text = composed.map(messageText).join("\n");
  assert.match(text, /Trellis workflow state: no_task/);
  assert.match(text, /no matching \[workflow-state\] block found/);
  assert.match(text, /<trellis-bootstrap>/);
});

test("composer: a non-Trellis directory stays silent", async () => {
  const fs = memoryFs({});
  assert.deepEqual(await composerFor(fs).compose(agent, prompt("hello")), []);
});
