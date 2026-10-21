/**
 * Replayable identity for plugin-owned session messages, driven by DSH's
 * projection registry.
 *
 * One projection is registered per message family (breadcrumb, bootstrap, …).
 * A projection stores only sequence → payload fingerprint, never message bodies
 * or a second event log, so a restored, forked, or compacted session rebuilds
 * the same visibility answer as the live one.
 *
 * @module dsh-trellis/message-projection
 */
import { createHash } from "node:crypto";
import { z } from "zod";

/** Fingerprint of the payload fields that define message identity. */
export function messageFingerprint(message) {
  const json = JSON.stringify(
    { content: message.content, source: message.source },
    (_key, value) =>
      value !== null && typeof value === "object" && !Array.isArray(value)
        ? Object.fromEntries(Object.entries(value).sort(([a], [b]) =>
            a < b ? -1 : a > b ? 1 : 0,
          ))
        : value,
  );
  return createHash("sha256").update(json).digest("hex");
}

/**
 * Build a projection definition for one message family.
 *
 * @param {object} options
 * @param {string} options.key - projection registry key.
 * @param {(message: unknown) => boolean} options.isOwn - message predicate.
 * @returns {object} projection definition accepted by the registry.
 */
export function createMessageProjection({ key, isOwn }) {
  return {
    key,
    stateVersion: 1,
    stateSchema: z.record(
      z.string().regex(/^(0|[1-9]\d*)$/),
      z.string().regex(/^[a-f0-9]{64}$/),
    ),
    init: () => ({}),
    apply(state, event) {
      if (event.type !== "user/message" || !isOwn(event.data)) return state;
      return { ...state, [event.seq]: messageFingerprint(event.data) };
    },
  };
}

/**
 * Register/read one message projection on the owning runtime scope.
 *
 * @param {import("@deepseek-ai/cordis").Context} ctx
 * @param {ReturnType<typeof createMessageProjection>} definition
 * @returns {{dispose: () => void, isVisible(session: any, message: any): boolean}}
 */
export function registerMessageProjection(ctx, definition) {
  const registry = ctx.sessionProjections;
  if (typeof registry?.register !== "function") {
    throw new Error("dsh-trellis requires the DSH sessionProjections service");
  }
  const hostOnly = typeof registry.stateOf === "function";
  // rc.6 predates host-only units. Its projection snapshot contains only our
  // seq -> hash index, not workflow text. This is NOT a Session log snapshot.
  const registered = hostOnly
    ? definition
    : {
        ...definition,
        schema: definition.stateSchema,
        view: (state) => state,
      };
  const dispose = registry.register(registered);
  return {
    dispose,
    isVisible(session, message) {
      const state = hostOnly
        ? registry.stateOf(session, definition.key)
        : registry.snapshot(session).values[definition.key];
      if (state === undefined) {
        throw new Error(`dsh-trellis projection "${definition.key}" is not registered`);
      }
      // Surface order, not maximum event seq: replacements can reorder seqs.
      // Only the LAST visible message of this family may suppress a new one
      // (A -> B -> A). Provenance can cite still-visible nodes, so do not
      // prune by sourceEventSeqs.
      const nodes = session.surface.nodes;
      for (let index = nodes.length - 1; index >= 0; index -= 1) {
        const fingerprint = state[nodes[index]];
        if (fingerprint !== undefined) {
          return fingerprint === messageFingerprint(message);
        }
      }
      return false;
    },
  };
}
