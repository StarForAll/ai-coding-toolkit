import { test } from "node:test";
import assert from "node:assert/strict";
import {
  CONFLICTS_ROUTE_PATH,
  createConflictsHandler,
  detectTrellisConflicts,
} from "../lib/conflicts.js";

function ctxWith(entries, { fiber, locate } = {}) {
  return {
    fiber,
    get(name) {
      if (name !== "loader") return undefined;
      return { entries: () => entries[Symbol.iterator](), locate };
    },
  };
}

const entry = (id, name, options = {}) => ({
  id,
  options: { id, name, ...options },
  fiber: options.fiber,
  disabled: options.disabled ?? false,
});

test("another enabled Trellis plugin is a conflict; self is excluded by fiber", () => {
  const fiber = {};
  const result = detectTrellisConflicts(ctxWith([
    entry("dsh-trellis", "dsh-trellis", { fiber }),
    entry("plus", "dsh-trellis-plus"),
  ], { fiber }));
  assert.deepEqual(result, {
    status: "checked",
    conflicts: [{ id: "plus", name: "dsh-trellis-plus" }],
  });
});

test("a disabled or trellis-free entry is not a conflict", () => {
  const fiber = {};
  const result = detectTrellisConflicts(ctxWith([
    entry("dsh-trellis", "dsh-trellis", { fiber }),
    entry("old", "dsh-trellis-old", { disabled: true }),
    entry("other", "dsh-example"),
  ], { fiber }));
  assert.deepEqual(result, { status: "checked", conflicts: [] });
});

test("any plugin whose name or loader id mentions trellis is reported", () => {
  const fiber = {};
  const idOnly = {
    id: "trellis-alt",
    options: { id: "trellis-alt", name: "generic-wrapper" },
    disabled: false,
  };
  const result = detectTrellisConflicts(ctxWith([
    entry("dsh-trellis", "dsh-trellis", { fiber }),
    entry("helper", "trellis-helper"),
    entry("scoped", "@scope/my-trellis"),
    entry("mixed", "SomeTrellisWrapper"),
    idOnly,
    entry("plain", "dsh-example"),
  ], { fiber }));
  assert.deepEqual(result, {
    status: "checked",
    conflicts: [
      { id: "helper", name: "trellis-helper" },
      { id: "scoped", name: "@scope/my-trellis" },
      { id: "mixed", name: "SomeTrellisWrapper" },
      { id: "trellis-alt", name: "generic-wrapper" },
    ],
  });
});

test("loader.locate identifies self when fiber identity is unavailable", () => {
  const fiber = {};
  const result = detectTrellisConflicts(ctxWith([
    entry("self-id", "dsh-trellis"),
    entry("plus", "dsh-trellis-plus"),
  ], { fiber, locate: (candidate) => (candidate === fiber ? "self-id" : undefined) }));
  assert.deepEqual(result, { status: "checked", conflicts: [{ id: "plus", name: "dsh-trellis-plus" }] });
});

test("an unavailable loader or an unidentifiable self is reported honestly", () => {
  assert.deepEqual(detectTrellisConflicts({}), {
    status: "unavailable",
    conflicts: [],
  });
  assert.deepEqual(detectTrellisConflicts(ctxWith([], { fiber: {} })), {
    status: "unavailable",
    conflicts: [],
  });
  assert.deepEqual(
    detectTrellisConflicts(ctxWith([
      entry("dsh-trellis", "dsh-trellis"),
      entry("plus", "dsh-trellis-plus"),
    ], { fiber: {} })),
    { status: "unverified", conflicts: [] },
  );
});

function harness({ method = "GET", headers = { "sec-fetch-site": "same-origin" } } = {}) {
  const response = { status: 0, headers: undefined, body: "" };
  const res = {
    writeHead(status, responseHeaders) { response.status = status; response.headers = responseHeaders; },
    end(body) { response.body = body; },
  };
  const req = { method, url: CONFLICTS_ROUTE_PATH, headers };
  return { req, res, response };
}

test("the route reports the conflict result as data", async () => {
  const { req, res, response } = harness();
  await createConflictsHandler(() => ({
    status: "checked",
    conflicts: [{ id: "plus", name: "dsh-trellis-plus" }],
  }))(req, res);
  assert.equal(response.status, 200);
  assert.equal(response.headers["cache-control"], "no-store");
  assert.deepEqual(JSON.parse(response.body), {
    ok: true,
    status: "checked",
    conflicts: [{ id: "plus", name: "dsh-trellis-plus" }],
  });
});

test("the route is read-only and refuses cross-site calls", async () => {
  const post = harness({ method: "POST" });
  await createConflictsHandler(() => ({ status: "checked", conflicts: [] }))(post.req, post.res);
  assert.equal(post.response.status, 405);

  const crossSite = harness({ headers: { "sec-fetch-site": "cross-site" } });
  await createConflictsHandler(() => ({ status: "checked", conflicts: [] }))(crossSite.req, crossSite.res);
  assert.equal(crossSite.response.status, 403);
});

test("a detection failure becomes a JSON error, not a crash", async () => {
  const { req, res, response } = harness();
  await createConflictsHandler(() => { throw new Error("loader exploded"); })(req, res);
  assert.equal(response.status, 500);
  assert.match(JSON.parse(response.body).error, /loader exploded/);
});
