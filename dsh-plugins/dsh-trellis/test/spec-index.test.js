import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, mkdir, writeFile, rm } from "node:fs/promises";
import { join } from "node:path";
import { tmpdir } from "node:os";
import {
  HEAD_MAX_BYTES,
  matchSpecsForFile,
  parseSpecFrontmatter,
  readSpecBody,
} from "../lib/spec-index.js";

test("parseSpecFrontmatter recognises block and flow path lists", () => {
  assert.deepEqual(
    parseSpecFrontmatter([
      "---",
      "name: cli-workflow",
      "description: workflow command conventions",
      "paths:",
      "  - packages/cli/src/commands/*.ts",
      "  - .trellis/scripts/**",
      "---",
      "Body",
    ].join("\n")),
    {
      paths: ["packages/cli/src/commands/*.ts", ".trellis/scripts/**"],
      name: "cli-workflow",
      description: "workflow command conventions",
    },
  );

  assert.deepEqual(
    parseSpecFrontmatter("---\npaths: [a.md, 'b c.md']\n---\nBody").paths,
    ["a.md", "b c.md"],
  );
});

test("parseSpecFrontmatter tolerates prose, comments and block scalars", () => {
  // A horizontal rule opening a prose file is not frontmatter.
  assert.equal(parseSpecFrontmatter("---\nJust prose.\n---\n"), null);
  assert.equal(parseSpecFrontmatter("# Title\n\n---\n"), null);

  assert.deepEqual(
    parseSpecFrontmatter([
      "---",
      "# leading comment",
      "name: x",
      "description: >",
      "  a folded paragraph",
      "  keeps going",
      "paths:",
      "  - src/*.ts  # trailing comment",
      "---",
    ].join("\n")),
    { paths: ["src/*.ts"], name: "x", description: null },
  );

  // A BOM before the opening marker is tolerated.
  assert.deepEqual(
    parseSpecFrontmatter("\uFEFF---\npaths: [x]\n---\n").paths,
    ["x"],
  );
});

test("parseSpecFrontmatter rejects routing metadata it cannot trust", () => {
  assert.throws(
    () => parseSpecFrontmatter("---\npaths: src/*.ts\n---\n"),
    /must be a list/,
  );
  assert.throws(
    () => parseSpecFrontmatter(`---\npaths:\n  - ${"a".repeat(HEAD_MAX_BYTES)}\n`),
    /never closed/,
  );
});

test("readSpecBody returns the body and a stable content hash", async (t) => {
  const root = await mkdtemp(join(tmpdir(), "dsh-trellis-body-"));
  t.after(() => rm(root, { recursive: true, force: true }));
  const file = join(root, "a.md");
  await writeFile(file, "hello");
  const first = await readSpecBody(file);
  const second = await readSpecBody(file);
  assert.equal(first.body, "hello");
  assert.equal(first.sha256, second.sha256);
  assert.match(first.sha256, /^[a-f0-9]{64}$/);
  assert.equal(await readSpecBody(join(root, "missing.md")), null);
});

test("matchSpecsForFile orders matches and ignores non-matching specs", async (t) => {
  const root = await mkdtemp(join(tmpdir(), "dsh-trellis-index-"));
  t.after(() => rm(root, { recursive: true, force: true }));
  const specs = join(root, ".trellis", "spec");
  await mkdir(join(specs, "cli"), { recursive: true });
  await mkdir(join(root, "packages", "cli", "src"), { recursive: true });
  await writeFile(join(root, "packages", "cli", "src", "command.ts"), "");
  await writeFile(join(specs, "cli", "exact.md"), [
    "---",
    "description: exact command rules",
    "paths:",
    '  - "packages/cli/src/command.ts"',
    "---",
    "Exact rules.",
  ].join("\n"));
  await writeFile(join(specs, "cli", "broad.md"), [
    "---",
    "description: whole package",
    "paths: [packages/**]",
    "---",
    "Broad rules.",
  ].join("\n"));
  await writeFile(join(specs, "cli", "unrelated.md"), [
    "---",
    "paths: [packages/web/**]",
    "---",
    "Web rules.",
  ].join("\n"));
  await writeFile(join(specs, "cli", "prose.md"), "# Prose\n\nNo routing hint.\n");

  const matches = await matchSpecsForFile(
    root,
    join(root, "packages", "cli", "src", "command.ts"),
    new Map(),
  );
  assert.deepEqual(
    matches.map((match) => match.specRel),
    [".trellis/spec/cli/exact.md", ".trellis/spec/cli/broad.md"],
  );
  assert.equal(matches[0].description, "exact command rules");
  assert.equal(matches[0].relPath, "packages/cli/src/command.ts");
});

test("matchSpecsForFile returns nothing for a project without specs", async (t) => {
  const root = await mkdtemp(join(tmpdir(), "dsh-trellis-nospec-"));
  t.after(() => rm(root, { recursive: true, force: true }));
  assert.deepEqual(await matchSpecsForFile(root, join(root, "a.ts"), new Map()), []);
});
