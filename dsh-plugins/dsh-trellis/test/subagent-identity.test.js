import { test } from "node:test";
import assert from "node:assert/strict";
import {
  SUBAGENT_IDENTITY_PROJECTION_KEY as KEY,
  registerSubagentIdentity,
  subagentIdentityProjection,
} from "../lib/subagent-identity.js";
import { sessionRuntime } from "./helpers/session-runtime.js";

const descriptor = (label) => ({
  version: 1,
  mode: "continuable",
  provider: "local-test",
  label,
});

test("the identity projection folds only the child's own descriptor label", () => {
  const initial = subagentIdentityProjection.init(undefined, 0);
  assert.deepEqual(initial, { inherited: 0 });
  assert.equal(subagentIdentityProjection.apply(initial, { seq: 0, type: "turn/start" }), initial);

  const state = subagentIdentityProjection.apply(initial, {
    seq: 0,
    type: "subagent/descriptor",
    data: descriptor("trellis-agent-implement"),
  });
  assert.deepEqual(state, { inherited: 0, label: "trellis-agent-implement" });
  // Repeating the same label keeps the state reference stable (no re-drive).
  assert.equal(
    subagentIdentityProjection.apply(state, {
      seq: 1,
      type: "subagent/descriptor",
      data: descriptor("trellis-agent-implement"),
    }),
    state,
  );
  // A forked child inherits its parent's log; that descriptor is not this child.
  const forked = subagentIdentityProjection.init(undefined, 3);
  assert.equal(
    subagentIdentityProjection.apply(forked, {
      seq: 1,
      type: "subagent/descriptor",
      data: descriptor("trellis-agent-check"),
    }),
    forked,
  );
  assert.deepEqual(
    subagentIdentityProjection.apply(forked, {
      seq: 3,
      type: "subagent/descriptor",
      data: descriptor("trellis-agent-check"),
    }),
    { inherited: 3, label: "trellis-agent-check" },
  );
  // Malformed labels never enter the state.
  assert.equal(
    subagentIdentityProjection.apply(initial, {
      seq: 0,
      type: "subagent/descriptor",
      data: { label: 42 },
    }),
    initial,
  );
  assert.deepEqual(
    subagentIdentityProjection.stateSchema.parse({ inherited: 0, label: "x" }),
    { inherited: 0, label: "x" },
  );
});

test("the projection reads the label from a real session and replays late registration", async (t) => {
  const ctx = await sessionRuntime(t);
  const session = ctx.sessions.create("child-identity");
  session.append("subagent/descriptor", descriptor("trellis-agent-research"));

  const identity = registerSubagentIdentity(ctx);
  t.after(identity.dispose);
  assert.equal(identity.labelOf(session), "trellis-agent-research");
  assert.equal(ctx.sessionProjections.snapshot(session).values[KEY], undefined);

  const other = ctx.sessions.create("child-generic");
  assert.equal(identity.labelOf(other), null);
  other.append("subagent/descriptor", descriptor("summarise the log"));
  assert.equal(identity.labelOf(other), "summarise the log");
});

test("the label lookup degrades when no projection registry is present", () => {
  const identity = registerSubagentIdentity({});
  assert.equal(identity.labelOf({ id: "child" }), null);
  assert.equal(identity.labelOf(undefined), null);
  identity.dispose();
});

test("the legacy registry shape records the label in a client-visible snapshot", () => {
  const registered = [];
  const states = new WeakMap();
  const ctx = {
    sessionProjections: {
      register(definition) {
        registered.push(definition);
        return () => {};
      },
      snapshot(session) {
        return { values: { [KEY]: states.get(session) } };
      },
    },
  };
  const identity = registerSubagentIdentity(ctx);
  assert.equal(registered.length, 1);
  assert.equal(typeof registered[0].view, "function");
  assert.equal(registered[0].schema, subagentIdentityProjection.stateSchema);

  const session = {};
  states.set(session, { inherited: 0, label: "trellis-agent-check" });
  assert.equal(identity.labelOf(session), "trellis-agent-check");
  states.set(session, { inherited: 0 });
  assert.equal(identity.labelOf(session), null);
  identity.dispose();
});
