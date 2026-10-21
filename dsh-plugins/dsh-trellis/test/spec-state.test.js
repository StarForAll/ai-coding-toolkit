import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, mkdir, readFile, rm, stat, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { tmpdir } from "node:os";
import {
  clearSpecState,
  loadSpecState,
  normalizeSpecRecord,
  saveSpecState,
  specStatePath,
  SPEC_RECORD_VERSION,
  SPEC_STATE_VERSION,
} from "../lib/spec-state.js";

async function root(t) {
  const dir = await mkdtemp(join(tmpdir(), "dsh-trellis-spec-state-"));
  t.after(() => rm(dir, { recursive: true, force: true }));
  return dir;
}

function record(overrides = {}) {
  return {
    v: SPEC_RECORD_VERSION,
    spec: ".trellis/spec/a.md",
    sha256: "a".repeat(64),
    mode: "full",
    ts: 1000,
    ...overrides,
  };
}

test("save/load round-trips one session shard", async (t) => {
  const dir = await root(t);
  const store = new Map([[".trellis/spec/a.md", record()]]);
  assert.equal(await saveSpecState(dir, "session-1", store), true);

  assert.ok(await stat(specStatePath(dir, "session-1")));
  const loaded = await loadSpecState(dir, "session-1");
  assert.deepEqual(loaded.get(".trellis/spec/a.md"), record());
});

test("corrupt or version-mismatched shards fall back to no history", async (t) => {
  const dir = await root(t);
  const path = specStatePath(dir, "session-1");
  await mkdir(join(path, ".."), { recursive: true });
  await writeFile(path, "{not json", "utf8");
  assert.equal((await loadSpecState(dir, "session-1")).size, 0);

  await writeFile(path, JSON.stringify({
    version: 999,
    records: [record()],
  }), "utf8");
  assert.equal((await loadSpecState(dir, "session-1")).size, 0);
});

test("malformed records are skipped without discarding valid ones", async (t) => {
  const dir = await root(t);
  const path = specStatePath(dir, "session-1");
  await mkdir(join(path, ".."), { recursive: true });
  await writeFile(path, JSON.stringify({
    version: SPEC_STATE_VERSION,
    records: [
      record(),
      record({ spec: "", mode: "ticket" }),
      record({ spec: ".trellis/spec/b.md", mode: "silent" }),
      record({ spec: ".trellis/spec/c.md", sha256: "not-a-hash" }),
    ],
  }), "utf8");
  const loaded = await loadSpecState(dir, "session-1");
  assert.deepEqual([...loaded.keys()], [".trellis/spec/a.md"]);
});

test("normalizeSpecRecord keeps only the documented fields", () => {
  assert.deepEqual(
    normalizeSpecRecord({
      ...record({ reset: "r1", complete: false }),
      extra: "drop",
    }),
    record({ reset: "r1", complete: false }),
  );
  assert.equal(normalizeSpecRecord(record({ mode: "silent" })), null);
});

test("clear removes the shard; an empty store also clears it", async (t) => {
  const dir = await root(t);
  await saveSpecState(dir, "session-1", new Map([[".trellis/spec/a.md", record()]]));
  await clearSpecState(dir, "session-1");
  await assert.rejects(stat(specStatePath(dir, "session-1")));

  await saveSpecState(dir, "session-1", new Map([[".trellis/spec/a.md", record()]]));
  assert.equal(await saveSpecState(dir, "session-1", new Map()), true);
  await assert.rejects(stat(specStatePath(dir, "session-1")));
});

test("session keys are sanitized and the shard stays inside the state dir", async (t) => {
  const dir = await root(t);
  const path = specStatePath(dir, "../../escape");
  assert.equal(path.startsWith(join(dir, ".trellis", ".runtime", "spec-inject")), true);
  assert.match(path, /escape\.json$/);
});

test("a persisted shard is plain JSON, not a serialized Map", async (t) => {
  const dir = await root(t);
  await saveSpecState(dir, "session-1", new Map([[".trellis/spec/a.md", record()]]));
  const text = await readFile(specStatePath(dir, "session-1"), "utf8");
  const parsed = JSON.parse(text);
  assert.equal(parsed.version, SPEC_STATE_VERSION);
  assert.equal(Array.isArray(parsed.records), true);
});
