import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, mkdir, rm } from "node:fs/promises";
import { join } from "node:path";
import { tmpdir } from "node:os";
import {
  compareSpecificity,
  globToRegex,
  normalizeRepoRelative,
  specificityRank,
  validateGlob,
} from "../lib/spec-glob.js";

test("validateGlob rejects only unsafe or meaningless globs", () => {
  for (const glob of [
    "packages/cli/**",
    "src/util?.py",
    "packages/@scope/[slug]/(marketing)/*.ts",
    "文档/**",
  ]) {
    assert.equal(validateGlob(glob), null, glob);
  }
  assert.match(validateGlob(""), /empty/);
  assert.match(validateGlob("/abs/path"), /absolute/);
  assert.match(validateGlob("../outside"), /'\.\.'/);
  assert.match(validateGlob("a/../b"), /'\.\.'/);
  assert.match(validateGlob("a\\b"), /backslash/);
  assert.match(validateGlob("a\u0001b"), /control/);
});

test("globToRegex follows the documented segment grammar", () => {
  const match = (glob, path) => globToRegex(glob).test(path);

  assert.equal(match("packages/cli/src/commands/update.ts", "packages/cli/src/commands/update.ts"), true);
  assert.equal(match("packages/cli/src/commands/update.ts", "packages/cli/src/commands/other.ts"), false);

  assert.equal(match("packages/cli/src/commands/*.ts", "packages/cli/src/commands/update.ts"), true);
  assert.equal(match("packages/cli/src/commands/*.ts", "packages/cli/src/commands/channel/spawn.ts"), false);

  assert.equal(match("packages/cli/src/templates/**", "packages/cli/src/templates/trellis/index.ts"), true);
  assert.equal(match("packages/cli/src/templates/**", "packages/cli/src/templates"), false);

  assert.equal(match("packages/**/index.ts", "packages/index.ts"), true);
  assert.equal(match("packages/**/index.ts", "packages/cli/src/index.ts"), true);
  assert.equal(match("packages/**/index.ts", "packages/cli/src/index.tsx"), false);

  assert.equal(match("src/util?.py", "src/utils.py"), true);
  assert.equal(match("src/util?.py", "src/util.py"), false);
  assert.equal(match("src/util?.py", "src/utilXY.py"), false);

  assert.equal(match("packages/cli/", "packages/cli/anything/deep.ts"), true);
  assert.equal(match("packages/cli/", "packages/cli"), false);
});

test("normalizeRepoRelative accepts absolute and repo-relative inputs", async (t) => {
  const root = await mkdtemp(join(tmpdir(), "dsh-trellis-glob-"));
  t.after(() => rm(root, { recursive: true, force: true }));
  await mkdir(join(root, "src"), { recursive: true });

  assert.equal(normalizeRepoRelative(root, join(root, "src", "a.ts")), "src/a.ts");
  assert.equal(normalizeRepoRelative(root, "./src/b.ts"), "src/b.ts");
  assert.equal(normalizeRepoRelative(root, "src\\c.ts"), "src/c.ts");
  assert.equal(normalizeRepoRelative(root, join(root, "..", "outside.ts")), null);
  assert.equal(normalizeRepoRelative(root, ""), null);
  assert.equal(normalizeRepoRelative(root, "."), null);
});

test("specificity ranks exact globs ahead of broad tree globs", () => {
  const exact = specificityRank("packages/cli/src/commands/update.ts");
  const narrow = specificityRank("packages/cli/src/commands/*.ts");
  const broad = specificityRank("packages/**");
  assert.ok(compareSpecificity(exact, narrow) < 0);
  assert.ok(compareSpecificity(narrow, broad) < 0);
});
