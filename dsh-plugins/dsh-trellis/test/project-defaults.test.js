import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, mkdir, readFile, writeFile, readdir, rm, utimes, stat } from "node:fs/promises";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { nodeFs } from "../lib/node-fs.js";
import {
  createDshDefaultsEnsurer,
  mergeDshDispatchMode,
  LOCK_STALE_MS,
} from "../lib/project-defaults.js";

test("mergeDshDispatchMode leaves a missing config alone", () => {
  assert.deepEqual(mergeDshDispatchMode(null), {
    content: "",
    changed: false,
    reason: "no-config",
  });
});

test("mergeDshDispatchMode appends the documented block to a bare config", () => {
  const result = mergeDshDispatchMode("session_auto_commit: false\n");
  assert.equal(result.changed, true);
  assert.equal(result.reason, "appended");
  assert.match(result.content, /^session_auto_commit: false\n\n# dsh-trellis: /);
  assert.match(result.content, /\ndsh:\n  dispatch_mode: inline\n$/);
  // The migration must be idempotent.
  assert.equal(mergeDshDispatchMode(result.content).changed, false);
});

test("mergeDshDispatchMode preserves comments and inserts into an existing dsh section", () => {
  const source = [
    "# project config",
    "session_auto_commit: false",
    "",
    "dsh:",
    "  inline_allow_dispatch: true  # explicit delegation",
    "",
    "codex:",
    "  dispatch_mode: inline",
    "",
  ].join("\n");
  const result = mergeDshDispatchMode(source);
  assert.equal(result.changed, true);
  assert.equal(result.reason, "inserted");
  assert.equal(
    result.content,
    [
      "# project config",
      "session_auto_commit: false",
      "",
      "dsh:",
      "  inline_allow_dispatch: true  # explicit delegation",
      "  dispatch_mode: inline",
      "",
      "codex:",
      "  dispatch_mode: inline",
      "",
    ].join("\n"),
  );
});

test("mergeDshDispatchMode inserts before a column-zero comment that documents the next key", () => {
  const source = "dsh:\n  other: 1\n# codex settings\ncodex:\n  dispatch_mode: auto\n";
  const result = mergeDshDispatchMode(source);
  assert.equal(result.changed, true);
  assert.equal(
    result.content,
    "dsh:\n  other: 1\n  dispatch_mode: inline\n# codex settings\ncodex:\n  dispatch_mode: auto\n",
  );
});

test("mergeDshDispatchMode inserts into an empty dsh section at EOF", () => {
  const result = mergeDshDispatchMode("other: 1\ndsh:\n");
  assert.equal(result.changed, true);
  assert.equal(result.content, "other: 1\ndsh:\n  dispatch_mode: inline\n");
});

test("mergeDshDispatchMode never overwrites an explicit dispatch_mode", () => {
  for (const value of ["auto", "inline", '"auto"', "InLiNe  # comment"]) {
    const source = `dsh:\n  dispatch_mode: ${value}\n`;
    const result = mergeDshDispatchMode(source);
    assert.equal(result.changed, false, value);
    assert.equal(result.reason, "present", value);
    assert.equal(result.content, source, value);
  }
});

test("mergeDshDispatchMode refuses to rewrite a non-block dsh value", () => {
  const source = "dsh: {dispatch_mode: auto}\n";
  const result = mergeDshDispatchMode(source);
  assert.equal(result.changed, false);
  assert.equal(result.reason, "dsh-not-block");
  assert.equal(result.content, source);
});

test("mergeDshDispatchMode keeps CRLF line endings", () => {
  const result = mergeDshDispatchMode("a: 1\r\n");
  assert.equal(result.changed, true);
  assert.ok(result.content.includes("\r\n\r\n# dsh-trellis: "));
  assert.ok(result.content.endsWith("\r\n"));
});

test("mergeDshDispatchMode adds an active key even when only a comment exists", () => {
  const result = mergeDshDispatchMode("dsh:\n  # dispatch_mode: auto\n");
  assert.equal(result.changed, true);
  assert.match(result.content, /# dispatch_mode: auto\n  dispatch_mode: inline\n$/);
});

test("mergeDshDispatchMode handles an empty file", () => {
  const result = mergeDshDispatchMode("");
  assert.equal(result.changed, true);
  assert.match(result.content, /^# dsh-trellis: /);
  assert.match(result.content, /\ndsh:\n  dispatch_mode: inline\n$/);
});

async function project(t, configText) {
  const root = await mkdtemp(join(tmpdir(), "dsh-trellis-defaults-"));
  t.after(() => rm(root, { recursive: true, force: true }));
  await mkdir(join(root, ".trellis"), { recursive: true });
  if (configText !== null) {
    await writeFile(join(root, ".trellis", "config.yaml"), configText);
  }
  return root;
}

test("ensureDshDefaults writes once and preserves the rest of the file", async (t) => {
  const root = await project(t, "# keep me\nsession_auto_commit: false\n");
  const ensure = createDshDefaultsEnsurer({ fs: nodeFs });
  const first = await ensure({
    root,
    configText: "# keep me\nsession_auto_commit: false\n",
  });
  assert.equal(first.changed, true);
  const text = await readFile(join(root, ".trellis", "config.yaml"), "utf8");
  assert.match(text, /^# keep me\nsession_auto_commit: false\n\n# dsh-trellis: /);
  assert.match(text, /\n  dispatch_mode: inline\n$/);

  const second = await ensure({ root, configText: text });
  assert.equal(second.changed, false);
  assert.equal(second.reason, "present");
  assert.deepEqual(
    (await readdir(join(root, ".trellis", ".runtime"))).filter((name) => name.includes(".tmp")),
    [],
  );
});

test("ensureDshDefaults respects an explicit mode", async (t) => {
  const source = "dsh:\n  dispatch_mode: auto\n";
  const root = await project(t, source);
  const before = (await stat(join(root, ".trellis", "config.yaml"))).mtimeMs;
  const result = await createDshDefaultsEnsurer({ fs: nodeFs })({ root, configText: source });
  assert.equal(result.changed, false);
  assert.equal(await readFile(join(root, ".trellis", "config.yaml"), "utf8"), source);
  assert.equal((await stat(join(root, ".trellis", "config.yaml"))).mtimeMs, before);
});

test("ensureDshDefaults never creates a missing config", async (t) => {
  const root = await project(t, null);
  const result = await createDshDefaultsEnsurer({ fs: nodeFs })({ root, configText: null });
  assert.equal(result.changed, false);
  assert.equal(result.reason, "no-config");
  assert.deepEqual(await readdir(join(root, ".trellis")), []);
});

test("ensureDshDefaults skips a read-only shim instead of failing", async () => {
  const shim = { async readFile() { return ""; } };
  const result = await createDshDefaultsEnsurer({ fs: shim })({
    root: "/tmp/irrelevant",
    configText: "a: 1\n",
  });
  assert.equal(result.changed, false);
  assert.equal(result.reason, "fs-readonly");
});

test("ensureDshDefaults honours a live lock and recovers a stale one", async (t) => {
  const root = await project(t, "a: 1\n");
  const runtime = join(root, ".trellis", ".runtime");
  await mkdir(runtime, { recursive: true });
  const lock = join(runtime, ".dsh-trellis-config.lock");
  await mkdir(lock);
  const ensure = createDshDefaultsEnsurer({ fs: nodeFs });

  const blocked = await ensure({ root, configText: "a: 1\n" });
  assert.equal(blocked.changed, false);
  assert.equal(blocked.reason, "locked");
  assert.equal(await readFile(join(root, ".trellis", "config.yaml"), "utf8"), "a: 1\n");

  const old = new Date(Date.now() - LOCK_STALE_MS - 1000);
  await utimes(lock, old, old);
  const recovered = await ensure({ root, configText: "a: 1\n" });
  assert.equal(recovered.changed, true);
  assert.match(
    await readFile(join(root, ".trellis", "config.yaml"), "utf8"),
    /dispatch_mode: inline/,
  );
});

test("ensureDshDefaults re-reads under the lock instead of trusting a stale snapshot", async (t) => {
  const source = "dsh:\n  dispatch_mode: inline\n";
  const root = await project(t, source);
  // The snapshot says "no dsh section", but the file already has one: a second
  // session may have written it between the read and the lock.
  const result = await createDshDefaultsEnsurer({ fs: nodeFs })({
    root,
    configText: "a: 1\n",
  });
  assert.equal(result.changed, false);
  assert.equal(result.reason, "present");
  assert.equal(await readFile(join(root, ".trellis", "config.yaml"), "utf8"), source);
});

test("ensureDshDefaults applies the merge to the fresh file, preserving concurrent edits", async (t) => {
  const root = await project(t, "a: 2\n");
  const result = await createDshDefaultsEnsurer({ fs: nodeFs })({
    root,
    configText: "a: 1\n", // stale: the file now says a: 2
  });
  assert.equal(result.changed, true);
  const text = await readFile(join(root, ".trellis", "config.yaml"), "utf8");
  assert.match(text, /^a: 2\n/);
  assert.doesNotMatch(text, /a: 1/);
  assert.match(text, /\ndsh:\n  dispatch_mode: inline\n$/);
});

test("ensureDshDefaults caches a write failure instead of retrying every step", async () => {
  let writes = 0;
  const warnings = [];
  const shim = {
    async readFile() { return "a: 1\n"; },
    async writeFile() { writes += 1; throw new Error("read-only filesystem"); },
    async rename() {},
    async mkdir() {},
    async rmdir() {},
    async stat() { return null; },
    async unlink() {},
  };
  const ensure = createDshDefaultsEnsurer({
    fs: shim,
    logger: { warn: (...args) => warnings.push(args) },
  });
  const first = await ensure({ root: "/tmp/readonly", configText: "a: 1\n" });
  const second = await ensure({ root: "/tmp/readonly", configText: "a: 1\n" });
  assert.equal(first.reason, "write-failed");
  assert.equal(second.reason, "write-failed");
  assert.equal(writes, 1);
  assert.equal(warnings.length, 1);
});
