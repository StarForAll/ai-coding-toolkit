import { test } from "node:test";
import assert from "node:assert/strict";
import {
  assemblePayload,
  decide,
  fitFullBlock,
  renderFull,
  renderTicket,
  truncationNotice,
  withinWindow,
} from "../lib/spec-inject.js";

const candidate = (overrides = {}) => ({
  editedRel: "src/a.ts",
  specRel: ".trellis/spec/a.md",
  description: "rule a",
  sha256: "a".repeat(64),
  sha12: "a".repeat(12),
  body: "Rule body.",
  mode: "full",
  ...overrides,
});

test("withinWindow treats 0 as an infinite window and bad clocks as expired", () => {
  assert.equal(withinWindow(1000, 900, 200), true);
  assert.equal(withinWindow(1000, 900, 50), false);
  assert.equal(withinWindow(1000, 900, 0), true);
  assert.equal(withinWindow(1000, Number.NaN, 200), false);
  assert.equal(withinWindow(1000, 1100, 200), false);
});

test("decide follows the documented order", () => {
  const record = { sha256: "h", ts: 1000, reset: "r", complete: true };
  const base = { stateless: false, sha256: "h", nowSeconds: 1100, winSeconds: 50, resetId: "r" };

  assert.equal(decide({ ...base, stateless: true, last: null }), "ticket");
  assert.equal(decide({ ...base, last: null }), "full");
  assert.equal(decide({ ...base, last: { ...record, sha256: "other" } }), "full");
  assert.equal(decide({ ...base, last: record, resetId: "other" }), "full");
  assert.equal(decide({ ...base, nowSeconds: 1020, last: record }), "silent");
  assert.equal(decide({ ...base, nowSeconds: 5000, last: record }), "ticket");
  assert.equal(
    decide({ ...base, nowSeconds: 5000, last: { ...record, complete: false } }),
    "full",
  );
});

test("fitFullBlock truncates with an in-body notice", () => {
  const body = "x".repeat(400);
  const fitted = fitFullBlock(
    { ...candidate(), body },
    (block) => block.length <= 250,
    0,
  );
  assert.ok(fitted);
  assert.equal(fitted.complete, false);
  assert.ok(fitted.block.length <= 250);
  const cap = Number(fitted.block.match(/truncated at (\d+) characters/)[1]);
  assert.ok(fitted.block.includes(truncationNotice(candidate().specRel, cap)));
  assert.ok(fitted.block.startsWith('<spec-context file="src/a.ts"'));
  // The largest fitting cap is chosen, not an arbitrary prefix.
  assert.ok(fitted.block.length > 200);
});

test("fitFullBlock keeps a body that already fits whole", () => {
  const fitted = fitFullBlock({ ...candidate(), body: "short" }, () => true, 0);
  assert.equal(fitted.complete, true);
  assert.equal(fitted.block, renderFull({
    editedRel: "src/a.ts",
    specRel: candidate().specRel,
    sha12: candidate().sha12,
    body: "short",
  }));
});

test("assemblePayload packs a single full spec whole", () => {
  const { payload, records } = assemblePayload({
    editedRel: "src/a.ts",
    candidates: [candidate()],
    maxSpecChars: 9400,
    maxTotalChars: 9500,
    stateless: false,
    nowSeconds: 42,
    resetId: "r1",
  });
  assert.match(payload, /<spec-context file="src\/a.ts" spec="\.trellis\/spec\/a\.md"/);
  assert.match(payload, /Rule body\./);
  assert.deepEqual(records, [{
    v: 2,
    spec: ".trellis/spec/a.md",
    sha256: "a".repeat(64),
    mode: "full",
    ts: 42,
    reset: "r1",
  }]);
});

test("assemblePayload never exceeds the per-event ceiling", () => {
  for (const maxTotalChars of [200, 400, 800]) {
    const { payload } = assemblePayload({
      editedRel: "src/a.ts",
      candidates: [
        candidate({ specRel: ".trellis/spec/a.md", body: "A".repeat(500) }),
        candidate({ specRel: ".trellis/spec/b.md", body: "B".repeat(500) }),
        candidate({ specRel: ".trellis/spec/c.md", body: "C".repeat(500) }),
      ],
      maxSpecChars: 9400,
      maxTotalChars,
      stateless: false,
      nowSeconds: 42,
    });
    assert.ok(payload.length <= maxTotalChars, `${payload.length} > ${maxTotalChars}`);
  }
});

test("assemblePayload degrades over-budget specs to an index block", () => {
  const { payload, records } = assemblePayload({
    editedRel: "src/a.ts",
    candidates: [
      candidate({ specRel: ".trellis/spec/a.md", body: "A".repeat(400) }),
      candidate({ specRel: ".trellis/spec/b.md", body: "B".repeat(400) }),
    ],
    maxSpecChars: 9400,
    maxTotalChars: 600,
    stateless: false,
    nowSeconds: 42,
  });
  assert.ok(payload.includes("<spec-context"));
  assert.ok(payload.includes("<spec-index>"));
  assert.ok(payload.includes("- .trellis/spec/b.md — rule a"));
  // Only the emission that actually reached the model records state.
  assert.equal(records.length, 1);
  assert.equal(records[0].spec, ".trellis/spec/a.md");
});

test("tickets do not record a full and silent matches emit nothing", () => {
  const ticket = assemblePayload({
    editedRel: "src/a.ts",
    candidates: [candidate({ mode: "ticket" })],
    maxSpecChars: 9400,
    maxTotalChars: 9500,
    stateless: true,
    nowSeconds: 42,
  });
  assert.match(ticket.payload, /<spec-ticket/);
  assert.equal(ticket.records[0].mode, "ticket");
  // An absent `complete` flag means "a whole body was shown", matching Trellis.
  assert.equal("complete" in ticket.records[0], false);

  const silent = assemblePayload({
    editedRel: "src/a.ts",
    candidates: [candidate({ mode: "silent" })],
    maxSpecChars: 9400,
    maxTotalChars: 9500,
    stateless: false,
    nowSeconds: 42,
  });
  assert.equal(silent.payload, "");
  assert.deepEqual(silent.records, []);
});

test("an unreadable spec body degrades to an index line instead of throwing", () => {
  const { payload, records } = assemblePayload({
    editedRel: "src/a.ts",
    candidates: [candidate({ body: null })],
    maxSpecChars: 9400,
    maxTotalChars: 9500,
    stateless: false,
    nowSeconds: 42,
  });
  assert.match(payload, /<spec-index>/);
  assert.deepEqual(records, []);
});

test("renderTicket distinguishes stateless from recorded wording", () => {
  assert.match(
    renderTicket({ editedRel: "a", specRel: "s", sha12: "x", stateless: true }),
    /If you have not read it/,
  );
  assert.match(
    renderTicket({ editedRel: "a", specRel: "s", sha12: "x", stateless: false }),
    /You were shown this spec earlier/,
  );
});
