import { test } from "node:test";
import assert from "node:assert/strict";
import {
  conflictSignature,
  conflictSummary,
  CONFLICTS_ROUTE_PATH,
  fetchConflicts,
} from "../src/client/conflicts.js";

const jsonResponse = (body, status = 200) => ({
  ok: status >= 200 && status < 300,
  status,
  async json() { return body; },
});

test("fetchConflicts reads the host's checked result", async () => {
  const seen = [];
  const result = await fetchConflicts(async (url) => {
    seen.push(url);
    return jsonResponse({ ok: true, status: "checked", conflicts: [{ id: "plus", name: "dsh-trellis-plus" }] });
  });
  assert.deepEqual(seen, [CONFLICTS_ROUTE_PATH]);
  assert.deepEqual(result, {
    status: "checked",
    conflicts: [{ id: "plus", name: "dsh-trellis-plus" }],
  });
});

test("a missing route or host error degrades to unavailable, never to no-conflict", async () => {
  assert.deepEqual(await fetchConflicts(async () => jsonResponse({}, 404)), {
    status: "unavailable",
    conflicts: [],
  });
  assert.deepEqual(await fetchConflicts(async () => ({ ok: false, status: 500, async json() { throw new Error("x"); } })), {
    status: "unavailable",
    conflicts: [],
  });
  assert.deepEqual(await fetchConflicts(async () => { throw new Error("offline"); }), {
    status: "unavailable",
    conflicts: [],
  });
  assert.deepEqual(await fetchConflicts(async () => jsonResponse({ ok: false, error: "nope" })), {
    status: "unavailable",
    conflicts: [],
  });
});

test("conflict identity and summary are stable and readable", () => {
  const conflicts = [
    { id: "plus", name: "dsh-trellis-plus" },
    { id: "old", name: "dsh-trellis-old" },
  ];
  assert.equal(conflictSignature(conflicts), "old:dsh-trellis-old|plus:dsh-trellis-plus");
  assert.equal(
    conflictSummary(conflicts),
    "dsh-trellis-plus（plus）、dsh-trellis-old（old）",
  );
  assert.equal(conflictSummary(conflicts, ", "), "dsh-trellis-plus（plus）, dsh-trellis-old（old）");
  assert.equal(conflictSignature(conflicts), conflictSignature([...conflicts].reverse()));
});
