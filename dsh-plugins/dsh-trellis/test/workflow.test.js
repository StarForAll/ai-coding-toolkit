import { test } from "node:test";
import assert from "node:assert/strict";
import { join, resolve, sep } from "node:path";
import {
  parseWorkflowStateBlocks,
  resolveTrellisState,
  sanitizeContextKey,
  mapStatus,
  normalizeDshCommandRefs,
  FALLBACK_BREADCRUMB,
} from "../lib/workflow.js";
import { truncateUtf8 } from "../lib/breadcrumb.js";

/** In-memory filesystem shim for workflow.js, keyed by absolute path. */
function memoryFs(initial = {}) {
  const files = new Map();
  for (const [key, value] of Object.entries(initial)) files.set(key, value);
  const mtimes = new Map();
  let tick = 1;
  const info = (path) => {
    if (!files.has(path)) return null;
    if (!mtimes.has(path)) mtimes.set(path, tick++);
    return { mtimeMs: mtimes.get(path) };
  };
  return {
    files,
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
    async listDir(path) {
      const prefix = `${path}${sep}`;
      const names = new Set();
      for (const key of files.keys()) {
        if (key.startsWith(prefix)) {
          names.add(key.slice(prefix.length).split(sep)[0]);
        }
      }
      return [...names];
    },
  };
}

const projectRoot = resolve("fixture-project");
const proj = (rel) => join(projectRoot, rel);

const WORKFLOW_MD = `# Workflow
[workflow-state:no_task]
No active task. Ask for task-creation consent.
[/workflow-state:no_task]
[workflow-state:task_error]
Repair the active task record. Do not create or activate another task.
[/workflow-state:task_error]
[workflow-state:planning]
Load trellis-brainstorm; stay in planning.
[/workflow-state:planning]
[workflow-state:in_progress]
Flow: implement -> check -> update-spec -> commit.
[/workflow-state:in_progress]
`;

test("parseWorkflowStateBlocks extracts every status body", () => {
  const blocks = parseWorkflowStateBlocks(WORKFLOW_MD);
  assert.equal(blocks.size, 4);
  assert.equal(
    blocks.get("no_task"),
    "No active task. Ask for task-creation consent.",
  );
  assert.equal(
    blocks.get("planning"),
    "Load trellis-brainstorm; stay in planning.",
  );
  assert.match(blocks.get("in_progress"), /implement -> check/);
});

test("parseWorkflowStateBlocks ignores unrelated bracketed text", () => {
  const blocks = parseWorkflowStateBlocks(
    "[Claude Code, Cursor]\nstuff\n[/Claude Code]\n[workflow-state:no_task]\nbody\n[/workflow-state:no_task]",
  );
  assert.deepEqual([...blocks.keys()], ["no_task"]);
});

test("sanitizeContextKey matches Trellis task.py sanitization", () => {
  assert.equal(
    sanitizeContextKey("019e456c-ea72-7b60-a8a6"),
    "019e456c-ea72-7b60-a8a6",
  );
  assert.equal(sanitizeContextKey("a b!c"), "a_b_c");
  assert.equal(sanitizeContextKey("..__x.."), "x");
});

test("mapStatus passes task statuses through and only degrades an absent one", () => {
  assert.equal(mapStatus("planning"), "planning");
  assert.equal(mapStatus("in_progress"), "in_progress");
  assert.equal(mapStatus("task_error"), "task_error");
  assert.equal(mapStatus("stale"), "stale");
  assert.equal(mapStatus("completed"), "completed");
  assert.equal(mapStatus("blocked"), "blocked");
  assert.equal(mapStatus(null), "no_task");
  assert.equal(mapStatus(""), "no_task");
});

test("resolveTrellisState: no trellis project → null", async () => {
  const fs = memoryFs();
  const state = await resolveTrellisState({
    cwd: proj("sub"),
    markers: [".git"],
    contextKey: "dsh_x",
    fs,
    cache: new Map(),
  });
  assert.equal(state, null);
});

test("resolveTrellisState: no active task → no_task breadcrumb", async () => {
  const fs = memoryFs({
    [proj(".git")]: "",
    [proj(join(".trellis", "workflow.md"))]: WORKFLOW_MD,
  });
  const state = await resolveTrellisState({
    cwd: proj("sub"),
    markers: [".git"],
    contextKey: "dsh_x",
    fs,
    cache: new Map(),
  });
  assert.ok(state);
  assert.equal(state.status, "no_task");
  assert.equal(state.taskPath, null);
  assert.equal(state.body, "No active task. Ask for task-creation consent.");
});

test("resolveTrellisState: exact session pointer → in_progress breadcrumb", async () => {
  const fs = memoryFs({
    [proj(".git")]: "",
    [proj(join(".trellis", "workflow.md"))]: WORKFLOW_MD,
    [proj(join(".trellis", "tasks", "04-17-foo", "task.json"))]: JSON.stringify(
      { status: "in_progress" },
    ),
    [proj(join(".trellis", ".runtime", "sessions", "dsh_x.json"))]:
      JSON.stringify({
        current_task: ".trellis/tasks/04-17-foo",
      }),
  });
  const state = await resolveTrellisState({
    cwd: proj(""),
    markers: [".git"],
    contextKey: "dsh_x",
    fs,
    cache: new Map(),
  });
  assert.equal(state.status, "in_progress");
  assert.equal(state.taskPath, ".trellis/tasks/04-17-foo");
});

test("resolveTrellisState: session-scoped pointer wins over another session", async () => {
  const fs = memoryFs({
    [proj(".git")]: "",
    [proj(join(".trellis", "workflow.md"))]: WORKFLOW_MD,
    [proj(join(".trellis", "tasks", "04-17-a", "task.json"))]: JSON.stringify({
      status: "in_progress",
    }),
    [proj(join(".trellis", "tasks", "04-17-b", "task.json"))]: JSON.stringify({
      status: "planning",
    }),
    [proj(join(".trellis", ".runtime", "sessions", "dsh_me.json"))]:
      JSON.stringify({
        platform: "dsh",
        current_task: ".trellis/tasks/04-17-b",
        last_seen_at: "2026-08-14T00:00:00Z",
      }),
    [proj(join(".trellis", ".runtime", "sessions", "dsh_other.json"))]:
      JSON.stringify({
        current_task: ".trellis/tasks/04-17-a",
      }),
  });
  const state = await resolveTrellisState({
    cwd: proj(""),
    markers: [".git"],
    contextKey: "dsh_me",
    fs,
    cache: new Map(),
  });
  assert.equal(state.status, "planning");
  assert.equal(state.taskPath, ".trellis/tasks/04-17-b");
});

test("resolveTrellisState: sole foreign-session pointer is not read or borrowed", async () => {
  const fs = memoryFs({
    [proj(".git")]: "",
    [proj(join(".trellis", "workflow.md"))]: WORKFLOW_MD,
    [proj(join(".trellis", "tasks", "04-17-a", "task.json"))]: JSON.stringify({
      status: "in_progress",
    }),
    [proj(join(".trellis", ".runtime", "sessions", "codex_zzz.json"))]:
      JSON.stringify({
        platform: "codex",
        current_task: ".trellis/tasks/04-17-a",
        last_seen_at: "2026-08-14T00:00:00Z",
      }),
  });
  const before = [...fs.files];
  const originalRead = fs.readFile;
  const reads = [];
  fs.readFile = async (path) => {
    reads.push(path);
    return originalRead(path);
  };
  const state = await resolveTrellisState({
    cwd: proj(""),
    markers: [".git"],
    contextKey: "dsh_me",
    fs,
    cache: new Map(),
  });
  assert.equal(state.status, "no_task");
  assert.equal(state.taskPath, null);
  assert.ok(!reads.some((path) => path.endsWith("codex_zzz.json")));
  assert.deepEqual([...fs.files], before);
});

test("resolveTrellisState: multiple foreign session pointers refuse to guess", async () => {
  const fs = memoryFs({
    [proj(".git")]: "",
    [proj(join(".trellis", "workflow.md"))]: WORKFLOW_MD,
    [proj(join(".trellis", "tasks", "04-17-a", "task.json"))]: JSON.stringify({
      status: "in_progress",
    }),
    [proj(join(".trellis", "tasks", "04-17-b", "task.json"))]: JSON.stringify({
      status: "planning",
    }),
    [proj(join(".trellis", ".runtime", "sessions", "dsh_a.json"))]:
      JSON.stringify({
        current_task: ".trellis/tasks/04-17-a",
      }),
    [proj(join(".trellis", ".runtime", "sessions", "dsh_b.json"))]:
      JSON.stringify({
        current_task: ".trellis/tasks/04-17-b",
      }),
  });
  const state = await resolveTrellisState({
    cwd: proj(""),
    markers: [".git"],
    contextKey: "dsh_unknown",
    fs,
    cache: new Map(),
  });
  assert.equal(state.status, "no_task");
  assert.equal(state.taskPath, null);
});

test("resolveTrellisState: zero workflow-state blocks degrades visibly", async () => {
  const fs = memoryFs({
    [proj(".git")]: "",
    [proj(join(".trellis", "workflow.md"))]: "# no blocks",
  });
  const state = await resolveTrellisState({
    cwd: proj(""),
    markers: [".git"],
    contextKey: "dsh_x",
    fs,
    cache: new Map(),
  });
  assert.equal(state.status, "no_task");
  assert.equal(state.taskPath, null);
  assert.equal(state.body, FALLBACK_BREADCRUMB);
  assert.match(state.digest, /^[a-f0-9]{40}$/);
});

test("resolveTrellisState: a missing workflow file also degrades visibly", async () => {
  const fs = memoryFs({
    [proj(".git")]: "",
    [proj(join(".trellis", "config.yaml"))]: "",
  });
  const state = await resolveTrellisState({
    cwd: proj(""),
    markers: [".git"],
    contextKey: "dsh_x",
    fs,
    cache: new Map(),
  });
  assert.equal(state.status, "no_task");
  assert.equal(state.body, FALLBACK_BREADCRUMB);
});

test("normalizeDshCommandRefs maps Codex command references to DSH", () => {
  assert.equal(
    normalizeDshCommandRefs("run `/trellis:finish-work` or `/trellis:status`"),
    "run `/trellis-finish-work` or `/trellis-status`",
  );
  assert.equal(
    normalizeDshCommandRefs("unknown `/trellis:unknown` stays"),
    "unknown `/trellis:unknown` stays",
  );
});

test("resolveTrellisState: in_progress with no matching block uses fallback text", async () => {
  const fs = memoryFs({
    [proj(".git")]: "",
    [proj(join(".trellis", "workflow.md"))]:
      "[workflow-state:no_task]\nbody\n[/workflow-state:no_task]",
    [proj(join(".trellis", "tasks", "t", "task.json"))]: JSON.stringify({
      status: "in_progress",
    }),
    [proj(join(".trellis", ".runtime", "sessions", "dsh_x.json"))]:
      JSON.stringify({
        current_task: ".trellis/tasks/t",
      }),
  });
  const state = await resolveTrellisState({
    cwd: proj(""),
    markers: [".git"],
    contextKey: "dsh_x",
    fs,
    cache: new Map(),
  });
  assert.equal(state.status, "in_progress");
  assert.equal(state.body, FALLBACK_BREADCRUMB);
});

test("truncateUtf8 respects byte budget without splitting code points", () => {
  const text = "中文字符串" + "a".repeat(100);
  const cut = truncateUtf8(text, 13);
  assert.ok(Buffer.byteLength(cut, "utf8") <= 13);
  assert.ok(!cut.endsWith("\ufffd"));
  assert.equal(truncateUtf8("short", 100), "short");
});

for (const [name, record] of [
  ["malformed JSON", "{broken"],
  ["null", "null"],
  ["array", "[]"],
  ["scalar", '"planning"'],
  ["missing status", "{}"],
  ["empty status", '{"status":""}'],
  ["blank status", '{"status":"  "}'],
  ["non-string status", '{"status":false}'],
  ["missing file", null],
  ["unreadable file", new Error("EACCES")],
]) {
  test(`resolveTrellisState: ${name} preserves the bound task as task_error`, async () => {
    const taskPath = ".trellis/tasks/broken";
    const taskJson = proj(join(taskPath, "task.json"));
    const fs = memoryFs({
      [proj(".git")]: "",
      [proj(".trellis/workflow.md")]: WORKFLOW_MD,
      [proj(".trellis/.runtime/sessions/dsh_me.json")]: JSON.stringify({ current_task: taskPath }),
      // The task directory exists (a sibling artifact is present); only
      // task.json itself is missing/unreadable. A genuinely missing directory
      // is the separate `stale` state covered below.
      [proj(join(taskPath, "prd.md"))]: "# PRD",
      ...(typeof record === "string" ? { [taskJson]: record } : {}),
    });
    if (record instanceof Error) {
      const originalRead = fs.readFile;
      fs.readFile = async (path) => {
        if (path === taskJson) throw record;
        return originalRead(path);
      };
    }
    const before = [...fs.files];
    const state = await resolveTrellisState({ cwd: projectRoot, markers: [".git"], contextKey: "dsh_me", fs, cache: new Map() });
    assert.equal(state.status, "task_error");
    assert.equal(state.taskPath, taskPath);
    assert.match(state.body, /Do not create or activate another task/);
    assert.deepEqual([...fs.files], before);
  });
}

for (const errorBlock of [
  "",
  "\n[workflow-state:task_error]\n  \n[/workflow-state:task_error]",
]) {
  test(`resolveTrellisState: ${errorBlock ? "empty" : "missing"} task-error block uses a safe fallback`, async () => {
    const fs = memoryFs({
      [proj(".git")]: "",
      [proj(".trellis/workflow.md")]:
        "[workflow-state:no_task]\nCreate a task.\n[/workflow-state:no_task]" + errorBlock,
      [proj(".trellis/.runtime/sessions/dsh_me.json")]: '{"current_task":".trellis/tasks/broken"}',
      [proj(".trellis/tasks/broken/task.json")]: "{broken",
    });
    const state = await resolveTrellisState({
      cwd: projectRoot, markers: [".git"], contextKey: "dsh_me", fs, cache: new Map(),
    });
    assert.equal(state.status, "task_error");
    assert.equal(state.taskPath, ".trellis/tasks/broken");
    assert.match(state.body, /Do not create or activate another task/);
    assert.match(state.body, /task\.json/);
  });
}

test("resolveTrellisState: empty identity cannot resolve a generic session pointer", async () => {
  const fs = memoryFs({
    [proj(".git")]: "",
    [proj(".trellis/workflow.md")]: WORKFLOW_MD,
    [proj(".trellis/.runtime/sessions/.json")]: '{"current_task":".trellis/tasks/foreign"}',
    [proj(".trellis/tasks/foreign/task.json")]: '{"status":"planning"}',
  });
  const state = await resolveTrellisState({ cwd: projectRoot, markers: [".git"], contextKey: "", fs, cache: new Map() });
  assert.equal(state.status, "no_task");
  assert.equal(state.taskPath, null);
});

for (const record of [
  "{broken", "null", "[]", "{}", '{"current_task":""}', '{"current_task":"  "}',
]) {
  test(`resolveTrellisState: invalid own pointer ${record} does not borrow a foreign session`, async () => {
    const fs = memoryFs({
      [proj(".git")]: "",
      [proj(".trellis/workflow.md")]: WORKFLOW_MD,
      [proj(".trellis/.runtime/sessions/dsh_me.json")]: record,
      [proj(".trellis/.runtime/sessions/dsh_other.json")]: '{"current_task":".trellis/tasks/foreign"}',
      [proj(".trellis/tasks/foreign/task.json")]: '{"status":"planning"}',
    });
    const before = [...fs.files];
    const state = await resolveTrellisState({ cwd: projectRoot, markers: [".git"], contextKey: "dsh_me", fs, cache: new Map() });
    assert.equal(state.status, "no_task");
    assert.equal(state.taskPath, null);
    assert.deepEqual([...fs.files], before);
  });
}

test("resolveTrellisState: exact binding does not require listing session files", async () => {
  const fs = memoryFs({
    [proj(".git")]: "",
    [proj(".trellis/workflow.md")]: WORKFLOW_MD,
    [proj(".trellis/.runtime/sessions/dsh_me.json")]: '{"current_task":".trellis/tasks/own"}',
    [proj(".trellis/tasks/own/task.json")]: '{"status":"planning"}',
  });
  delete fs.listDir;
  const state = await resolveTrellisState({ cwd: projectRoot, markers: [".git"], contextKey: "dsh_me", fs, cache: new Map() });
  assert.equal(state.status, "planning");
  assert.equal(state.taskPath, ".trellis/tasks/own");
});

// ---------------------------------------------------------------------------
// Breadcrumb-contract regressions: tags mentioned inline (comments, docs) must
// never open a block, and statuses must not be rewritten into no_task.
// ---------------------------------------------------------------------------

test("parseWorkflowStateBlocks ignores tags mentioned inside an HTML comment", () => {
  const contents = `<!--
  TAG ↔ PHASE scoping:
    [workflow-state:no_task]      → no active task; before Phase 1
    [workflow-state:stale]        → active-task pointer exists but is missing
    [workflow-state:planning]     → all of Phase 1
-->
[workflow-state:no_task]
No active task. Ask for task-creation consent.
[/workflow-state:no_task]
[workflow-state:stale]
Repair the stale pointer.
[/workflow-state:stale]
[workflow-state:planning]
Stay in planning.
[/workflow-state:planning]
`;
  const blocks = parseWorkflowStateBlocks(contents);
  assert.equal(blocks.size, 3);
  assert.equal(
    blocks.get("no_task"),
    "No active task. Ask for task-creation consent.",
  );
  assert.equal(blocks.get("stale"), "Repair the stale pointer.");
  assert.equal(blocks.get("planning"), "Stay in planning.");
});

test("parseWorkflowStateBlocks requires the opening tag to end its line", () => {
  assert.equal(
    parseWorkflowStateBlocks(
      "[workflow-state:no_task]inline body[/workflow-state:no_task]",
    ).size,
    0,
  );
  assert.equal(
    parseWorkflowStateBlocks(
      "[workflow-state:no_task]  \nbody\n[/workflow-state:no_task]",
    ).get("no_task"),
    "body",
  );
});

test("parseWorkflowStateBlocks drops empty and whitespace-only bodies", () => {
  // Trellis's load_breadcrumbs keeps a tag only when its body is non-empty;
  // an empty block must degrade to the generic line, not to an empty prompt.
  const blocks = parseWorkflowStateBlocks(
    [
      "[workflow-state:no_task]",
      "body",
      "[/workflow-state:no_task]",
      "[workflow-state:completed]",
      "   ",
      "[/workflow-state:completed]",
      "[workflow-state:stale]",
      "",
      "[/workflow-state:stale]",
    ].join("\n"),
  );
  assert.deepEqual([...blocks.keys()], ["no_task"]);
});

test("resolveTrellisState: an empty inline block does not shadow the base block", async () => {
  const fs = memoryFs({
    [proj(".git")]: "",
    [proj(".trellis/workflow.md")]:
      WORKFLOW_MD +
      "[workflow-state:in_progress-inline]\n  \n[/workflow-state:in_progress-inline]",
    [proj(".trellis/config.yaml")]: "codex:\n  dispatch_mode: inline\n",
    [proj(".trellis/.runtime/sessions/dsh_me.json")]:
      '{"current_task":".trellis/tasks/t"}',
    [proj(".trellis/tasks/t/task.json")]: '{"status":"in_progress"}',
  });
  const state = await resolveTrellisState({
    cwd: projectRoot, markers: [".git"], contextKey: "dsh_me", fs, cache: new Map(),
  });
  assert.equal(state.status, "in_progress");
  assert.match(state.body, /implement -> check/);
});

test("resolveTrellisState: completed status uses the completed block", async () => {
  const fs = memoryFs({
    [proj(".git")]: "",
    [proj(".trellis/workflow.md")]:
      WORKFLOW_MD +
      "[workflow-state:completed]\nCode committed. Finish the session.\n[/workflow-state:completed]",
    [proj(".trellis/.runtime/sessions/dsh_me.json")]: '{"current_task":".trellis/tasks/t"}',
    [proj(".trellis/tasks/t/task.json")]: '{"status":"completed"}',
  });
  const state = await resolveTrellisState({
    cwd: projectRoot, markers: [".git"], contextKey: "dsh_me", fs, cache: new Map(),
  });
  assert.equal(state.status, "completed");
  assert.equal(state.body, "Code committed. Finish the session.");
});

test("resolveTrellisState: unknown custom status falls back instead of no_task", async () => {
  const fs = memoryFs({
    [proj(".git")]: "",
    [proj(".trellis/workflow.md")]: WORKFLOW_MD,
    [proj(".trellis/.runtime/sessions/dsh_me.json")]: '{"current_task":".trellis/tasks/t"}',
    [proj(".trellis/tasks/t/task.json")]: '{"status":"blocked"}',
  });
  const state = await resolveTrellisState({
    cwd: projectRoot, markers: [".git"], contextKey: "dsh_me", fs, cache: new Map(),
  });
  assert.equal(state.status, "blocked");
  assert.equal(state.body, FALLBACK_BREADCRUMB);
});

test("resolveTrellisState: pointer to a missing directory is stale, with its own block", async () => {
  const fs = memoryFs({
    [proj(".git")]: "",
    [proj(".trellis/workflow.md")]:
      WORKFLOW_MD +
      "[workflow-state:stale]\nRepair the stale pointer.\n[/workflow-state:stale]",
    [proj(".trellis/.runtime/sessions/dsh_me.json")]:
      '{"current_task":".trellis/tasks/gone"}',
  });
  const state = await resolveTrellisState({
    cwd: projectRoot, markers: [".git"], contextKey: "dsh_me", fs, cache: new Map(),
  });
  assert.equal(state.status, "stale");
  assert.equal(state.taskPath, ".trellis/tasks/gone");
  assert.equal(state.body, "Repair the stale pointer.");
});

test("resolveTrellisState: stale without a stale block degrades to the fallback line", async () => {
  const fs = memoryFs({
    [proj(".git")]: "",
    [proj(".trellis/workflow.md")]: WORKFLOW_MD,
    [proj(".trellis/.runtime/sessions/dsh_me.json")]:
      '{"current_task":".trellis/tasks/gone"}',
  });
  const state = await resolveTrellisState({
    cwd: projectRoot, markers: [".git"], contextKey: "dsh_me", fs, cache: new Map(),
  });
  assert.equal(state.status, "stale");
  assert.equal(state.body, FALLBACK_BREADCRUMB);
});

function variantProject(extra = {}) {
  return memoryFs({
    [proj(".git")]: "",
    [proj(".trellis/workflow.md")]: WORKFLOW_MD,
    [proj(".trellis/.runtime/sessions/dsh_me.json")]: '{"current_task":".trellis/tasks/t"}',
    ...extra,
  });
}

test("resolveTrellisState: task workflow pin outranks personal/team defaults", async () => {
  const fs = variantProject({
    [proj(".trellis/workflows/alt.md")]:
      "[workflow-state:planning]\nALT TASK PIN\n[/workflow-state:planning]",
    [proj(".trellis/workflows/personal.md")]:
      "[workflow-state:planning]\nPERSONAL\n[/workflow-state:planning]",
    [proj(".trellis/.developer")]: "name=x\nworkflow=personal\n",
    [proj(".trellis/config.yaml")]: "default_workflow: personal\n",
    [proj(".trellis/tasks/t/task.json")]: '{"status":"planning","workflow":"alt"}',
  });
  const state = await resolveTrellisState({
    cwd: projectRoot, markers: [".git"], contextKey: "dsh_me", fs, cache: new Map(),
  });
  assert.equal(state.status, "planning");
  assert.equal(state.body, "ALT TASK PIN");
});

test("resolveTrellisState: personal workflow outranks the team default", async () => {
  const fs = variantProject({
    [proj(".trellis/workflows/personal.md")]:
      "[workflow-state:planning]\nPERSONAL\n[/workflow-state:planning]",
    [proj(".trellis/workflows/team.md")]:
      "[workflow-state:planning]\nTEAM\n[/workflow-state:planning]",
    [proj(".trellis/.developer")]: "workflow=personal\n",
    [proj(".trellis/config.yaml")]: "default_workflow: team\n",
    [proj(".trellis/tasks/t/task.json")]: '{"status":"planning"}',
  });
  const state = await resolveTrellisState({
    cwd: projectRoot, markers: [".git"], contextKey: "dsh_me", fs, cache: new Map(),
  });
  assert.equal(state.body, "PERSONAL");
});

test("resolveTrellisState: team default applies, and a missing pin falls through", async () => {
  const fs = variantProject({
    [proj(".trellis/workflows/team.md")]:
      "[workflow-state:planning]\nTEAM\n[/workflow-state:planning]",
    [proj(".trellis/config.yaml")]: 'default_workflow: "team"  # team default\n',
    [proj(".trellis/tasks/t/task.json")]: '{"status":"planning","workflow":"missing"}',
  });
  const state = await resolveTrellisState({
    cwd: projectRoot, markers: [".git"], contextKey: "dsh_me", fs, cache: new Map(),
  });
  assert.equal(state.body, "TEAM");
});

test("resolveTrellisState: invalid variant ids are ignored", async () => {
  const fs = variantProject({
    [proj(".trellis/.developer")]: "workflow=../../etc\n",
    [proj(".trellis/tasks/t/task.json")]: '{"status":"planning","workflow":"../x"}',
  });
  const state = await resolveTrellisState({
    cwd: projectRoot, markers: [".git"], contextKey: "dsh_me", fs, cache: new Map(),
  });
  assert.equal(state.status, "planning");
  assert.equal(state.body, "Load trellis-brainstorm; stay in planning.");
});

test("resolveTrellisState: DSH ignores the Codex-only dispatch_mode=inline variant", async () => {
  const inlineWorkflow = WORKFLOW_MD.replace(
    "[workflow-state:planning]\nLoad trellis-brainstorm; stay in planning.\n[/workflow-state:planning]",
    "[workflow-state:planning]\nSUBAGENT PLANNING\n[/workflow-state:planning]\n" +
      "[workflow-state:planning-inline]\nINLINE PLANNING\n[/workflow-state:planning-inline]",
  );
  const fs = memoryFs({
    [proj(".git")]: "",
    [proj(".trellis/workflow.md")]: inlineWorkflow,
    [proj(".trellis/config.yaml")]: "codex:\n  dispatch_mode: inline\n",
    [proj(".trellis/.runtime/sessions/dsh_me.json")]: '{"current_task":".trellis/tasks/t"}',
    [proj(".trellis/tasks/t/task.json")]: '{"status":"planning"}',
  });
  const state = await resolveTrellisState({
    cwd: projectRoot, markers: [".git"], contextKey: "dsh_me", fs, cache: new Map(),
  });
  // Trellis's carrier selects *-inline only for platform="codex"
  // (resolve_breadcrumb_key). DSH keeps the base block, which carries the
  // DSH-specific dispatch protocol.
  assert.equal(state.status, "planning");
  assert.equal(state.body, "SUBAGENT PLANNING");
});

test("resolveTrellisState: dispatch_mode=auto keeps the ordinary block", async () => {
  const inlineWorkflow = WORKFLOW_MD +
    "[workflow-state:planning-inline]\nINLINE PLANNING\n[/workflow-state:planning-inline]";
  const fs = memoryFs({
    [proj(".git")]: "",
    [proj(".trellis/workflow.md")]: inlineWorkflow,
    [proj(".trellis/config.yaml")]: "codex:\n  dispatch_mode: auto\n",
    [proj(".trellis/.runtime/sessions/dsh_me.json")]: '{"current_task":".trellis/tasks/t"}',
    [proj(".trellis/tasks/t/task.json")]: '{"status":"planning"}',
  });
  const state = await resolveTrellisState({
    cwd: projectRoot, markers: [".git"], contextKey: "dsh_me", fs, cache: new Map(),
  });
  assert.equal(state.status, "planning");
});

test("resolveTrellisState: legacy tasks/<slug> pointers resolve like Trellis", async () => {
  const fs = memoryFs({
    [proj(".git")]: "",
    [proj(".trellis/workflow.md")]: WORKFLOW_MD,
    [proj(".trellis/.runtime/sessions/dsh_me.json")]: '{"current_task":"tasks/t"}',
    [proj(".trellis/tasks/t/task.json")]: '{"status":"planning"}',
  });
  const state = await resolveTrellisState({
    cwd: projectRoot, markers: [".git"], contextKey: "dsh_me", fs, cache: new Map(),
  });
  assert.equal(state.status, "planning");
  assert.equal(state.taskPath, ".trellis/tasks/t");
});

test("resolveTrellisState: absolute pointers inside the repo resolve", async () => {
  const absolute = proj(".trellis/tasks/t");
  const fs = memoryFs({
    [proj(".git")]: "",
    [proj(".trellis/workflow.md")]: WORKFLOW_MD,
    [proj(".trellis/.runtime/sessions/dsh_me.json")]:
      JSON.stringify({ current_task: absolute }),
    [proj(".trellis/tasks/t/task.json")]: '{"status":"planning"}',
  });
  const state = await resolveTrellisState({
    cwd: projectRoot, markers: [".git"], contextKey: "dsh_me", fs, cache: new Map(),
  });
  assert.equal(state.status, "planning");
  assert.equal(state.taskPath, ".trellis/tasks/t");
});

test("resolveTrellisState: a pointer to a file (not a directory) is stale", async () => {
  const fs = memoryFs({
    [proj(".git")]: "",
    [proj(".trellis/workflow.md")]: WORKFLOW_MD,
    [proj(".trellis/.runtime/sessions/dsh_me.json")]:
      '{"current_task":".trellis/tasks/ofile"}',
    [proj(".trellis/tasks/ofile")]: "not a directory",
  });
  const state = await resolveTrellisState({
    cwd: projectRoot, markers: [".git"], contextKey: "dsh_me", fs, cache: new Map(),
  });
  assert.equal(state.status, "stale");
});

test("resolveTrellisState: a pointer escaping the project root is stale", async () => {
  const fs = memoryFs({
    [proj(".git")]: "",
    [proj(".trellis/workflow.md")]: WORKFLOW_MD,
    [proj(".trellis/.runtime/sessions/dsh_me.json")]:
      '{"current_task":"../../outside"}',
  });
  const state = await resolveTrellisState({
    cwd: projectRoot, markers: [".git"], contextKey: "dsh_me", fs, cache: new Map(),
  });
  assert.equal(state.status, "stale");
});

test("resolveTrellisState: dsh.dispatch_mode=inline selects the inline block plus DSH banner", async () => {
  const inlineWorkflow = WORKFLOW_MD +
    "[workflow-state:planning-inline]\nINLINE PLANNING\n[/workflow-state:planning-inline]";
  const fs = memoryFs({
    [proj(".git")]: "",
    [proj(".trellis/workflow.md")]: inlineWorkflow,
    [proj(".trellis/config.yaml")]: "dsh:\n  dispatch_mode: inline\n",
    [proj(".trellis/.runtime/sessions/dsh_me.json")]: '{"current_task":".trellis/tasks/t"}',
    [proj(".trellis/tasks/t/task.json")]: '{"status":"planning"}',
  });
  const state = await resolveTrellisState({
    cwd: projectRoot, markers: [".git"], contextKey: "dsh_me", fs, cache: new Map(),
  });
  assert.equal(state.status, "planning-inline");
  assert.match(state.body, /^INLINE PLANNING/);
  assert.match(state.body, /<dsh-mode>/);
  assert.match(state.body, /Do not dispatch trellis-agent-implement/);
  assert.match(state.body, /the trellis-check skill/);
});

test("resolveTrellisState: dsh.dispatch_mode=auto keeps the base block", async () => {
  const inlineWorkflow = WORKFLOW_MD +
    "[workflow-state:planning-inline]\nINLINE PLANNING\n[/workflow-state:planning-inline]";
  const fs = memoryFs({
    [proj(".git")]: "",
    [proj(".trellis/workflow.md")]: inlineWorkflow,
    [proj(".trellis/config.yaml")]: "dsh:\n  dispatch_mode: auto\n",
    [proj(".trellis/.runtime/sessions/dsh_me.json")]: '{"current_task":".trellis/tasks/t"}',
    [proj(".trellis/tasks/t/task.json")]: '{"status":"planning"}',
  });
  const state = await resolveTrellisState({
    cwd: projectRoot, markers: [".git"], contextKey: "dsh_me", fs, cache: new Map(),
  });
  assert.equal(state.status, "planning");
  assert.equal(state.body, "Load trellis-brainstorm; stay in planning.");
});

test("resolveTrellisState: invalid dsh.dispatch_mode falls back to auto", async () => {
  const inlineWorkflow = WORKFLOW_MD +
    "[workflow-state:planning-inline]\nINLINE PLANNING\n[/workflow-state:planning-inline]";
  const fs = memoryFs({
    [proj(".git")]: "",
    [proj(".trellis/workflow.md")]: inlineWorkflow,
    [proj(".trellis/config.yaml")]: "dsh:\n  dispatch_mode: sideways\n",
    [proj(".trellis/.runtime/sessions/dsh_me.json")]: '{"current_task":".trellis/tasks/t"}',
    [proj(".trellis/tasks/t/task.json")]: '{"status":"planning"}',
  });
  const state = await resolveTrellisState({
    cwd: projectRoot, markers: [".git"], contextKey: "dsh_me", fs, cache: new Map(),
  });
  assert.equal(state.status, "planning");
});

test("resolveTrellisState: dsh inline without a matching block keeps the base block but still announces the mode", async () => {
  const fs = memoryFs({
    [proj(".git")]: "",
    [proj(".trellis/workflow.md")]: WORKFLOW_MD,
    [proj(".trellis/config.yaml")]: "dsh:\n  dispatch_mode: inline\n",
    [proj(".trellis/.runtime/sessions/dsh_me.json")]: '{"current_task":".trellis/tasks/t"}',
    [proj(".trellis/tasks/t/task.json")]: '{"status":"planning"}',
  });
  const state = await resolveTrellisState({
    cwd: projectRoot, markers: [".git"], contextKey: "dsh_me", fs, cache: new Map(),
  });
  assert.equal(state.status, "planning");
  assert.match(state.body, /^Load trellis-brainstorm; stay in planning\./);
  assert.match(state.body, /<dsh-mode>/);
});

test("resolveTrellisState: dsh inline announces the mode for statuses without an inline variant", async () => {
  const fs = memoryFs({
    [proj(".git")]: "",
    [proj(".trellis/workflow.md")]: WORKFLOW_MD,
    [proj(".trellis/config.yaml")]: "dsh:\n  dispatch_mode: inline\n",
    [proj(".trellis/.runtime/sessions/dsh_me.json")]: '{"current_task":".trellis/tasks/t"}',
    [proj(".trellis/tasks/t/task.json")]: '{"status":"completed"}',
  });
  const state = await resolveTrellisState({
    cwd: projectRoot, markers: [".git"], contextKey: "dsh_me", fs, cache: new Map(),
  });
  assert.equal(state.status, "completed");
  assert.match(state.body, /<dsh-mode>/);
});

test("resolveTrellisState: flow-style dsh.dispatch_mode selects the inline block", async () => {
  const fs = memoryFs({
    [proj(".git")]: "",
    [proj(join(".trellis", "config.yaml"))]: "dsh: {dispatch_mode: inline}\n",
    [proj(join(".trellis", "workflow.md"))]: `[workflow-state:in_progress]
BASE
[/workflow-state:in_progress]
[workflow-state:in_progress-inline]
INLINE
[/workflow-state:in_progress-inline]
`,
    [proj(join(".trellis", "tasks", "t", "task.json"))]: JSON.stringify({
      status: "in_progress",
    }),
    [proj(join(".trellis", ".runtime", "sessions", "dsh_x.json"))]:
      JSON.stringify({ current_task: ".trellis/tasks/t" }),
  });
  const state = await resolveTrellisState({
    cwd: proj(""),
    markers: [".git"],
    contextKey: "dsh_x",
    fs,
    cache: new Map(),
  });
  assert.equal(state.status, "in_progress-inline");
  assert.match(state.body, /^INLINE/m);
  assert.match(state.body, /<dsh-mode>/);
  assert.match(state.body, /--allow-empty-context/);
});

test("resolveTrellisState: command refs in a state body are DSH-native", async () => {
  const fs = memoryFs({
    [proj(".git")]: "",
    [proj(join(".trellis", "config.yaml"))]: "dsh:\n  dispatch_mode: auto\n",
    [proj(join(".trellis", "workflow.md"))]: `[workflow-state:in_progress]
Flow: commit then \`/trellis:finish-work\`.
[/workflow-state:in_progress]
`,
    [proj(join(".trellis", "tasks", "t", "task.json"))]: JSON.stringify({
      status: "in_progress",
    }),
    [proj(join(".trellis", ".runtime", "sessions", "dsh_x.json"))]:
      JSON.stringify({ current_task: ".trellis/tasks/t" }),
  });
  const state = await resolveTrellisState({
    cwd: proj(""),
    markers: [".git"],
    contextKey: "dsh_x",
    fs,
    cache: new Map(),
  });
  assert.match(state.body, /\/trellis-finish-work/);
  assert.doesNotMatch(state.body, /\/trellis:finish-work/);
});

test("resolveTrellisState: a plain Git repository without .trellis stays silent", async () => {
  const fs = memoryFs({ [proj(".git")]: "" });
  const state = await resolveTrellisState({
    cwd: proj(""),
    markers: [".git", ".trellis"],
    contextKey: "dsh_x",
    fs,
    cache: new Map(),
  });
  assert.equal(state, null);
});
