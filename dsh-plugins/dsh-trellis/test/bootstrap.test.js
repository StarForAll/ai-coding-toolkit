import { test } from "node:test";
import assert from "node:assert/strict";
import {
  BOOTSTRAP_MAX_BYTES,
  BOOTSTRAP_NOTICE,
  bootstrapMessage,
  isBootstrapMessage,
  registerBootstrapProjection,
  SOURCE_FORM,
  SOURCE_KIND,
} from "../lib/bootstrap.js";
import { breadcrumbMessage } from "../lib/breadcrumb.js";
import { sessionRuntime } from "./helpers/session-runtime.js";

const prompt = (text) => ({ content: [{ type: "text", text }] });

test("bootstrap is its own message family", () => {
  const message = bootstrapMessage();
  assert.equal(isBootstrapMessage(message), true);
  assert.deepEqual(message.source, { kind: SOURCE_KIND, form: SOURCE_FORM });
  assert.notEqual(SOURCE_FORM, "breadcrumb");
  assert.ok(message.content[0].text.includes("<trellis-bootstrap>"));
  assert.ok(message.content[0].text.includes("trellis-start"));
});

test("bootstrap never matches the breadcrumb predicate and vice versa", () => {
  const bootstrap = bootstrapMessage();
  const breadcrumb = breadcrumbMessage(
    { status: "no_task", taskPath: null, body: "Idle.", digest: "d" },
    4096,
  );
  assert.equal(isBootstrapMessage(breadcrumb), false);
  // The breadcrumb no longer embeds the nudge; it is delivered separately.
  assert.equal(breadcrumb.content[0].text.includes("<trellis-bootstrap>"), false);
});

test("bootstrap honours its own byte ceiling", () => {
  const message = bootstrapMessage(48);
  assert.ok(Buffer.byteLength(message.content[0].text) <= 48);
  assert.ok(BOOTSTRAP_MAX_BYTES >= Buffer.byteLength(BOOTSTRAP_NOTICE));
});

test("bootstrap visibility is independent of breadcrumb visibility", async (t) => {
  const ctx = await sessionRuntime(t);
  const projection = registerBootstrapProjection(ctx);
  const session = ctx.sessions.create("bootstrap");
  const bootstrap = bootstrapMessage();
  const breadcrumb = breadcrumbMessage(
    { status: "no_task", taskPath: null, body: "Idle.", digest: "d" },
    4096,
  );

  assert.equal(projection.isVisible(session, bootstrap), false);
  session.append("user/message", breadcrumb, { surfaceOp: "append" });
  // A visible breadcrumb does not make the bootstrap visible.
  assert.equal(projection.isVisible(session, bootstrap), false);

  session.append("user/message", bootstrap, { surfaceOp: "append" });
  assert.equal(projection.isVisible(session, bootstrap), true);

  // Compaction removes it from the surface; the nudge must be re-delivered.
  session.append("user/message", prompt("Compacted"), {
    surfaceOp: { op: "replace", startSeq: 0, endSeq: 1 },
    sourceEventSeqs: [0, 1],
  });
  assert.equal(projection.isVisible(session, bootstrap), false);
});
