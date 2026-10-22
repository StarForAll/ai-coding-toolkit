/**
 * Sub-agent identity projection: the durable role label DSH already records.
 *
 * The dispatch tool stores its `description` argument as the child's
 * `subagent/descriptor` label. That descriptor is written into the child's own
 * session log before the first turn, which makes it the only child-side signal
 * for "which Trellis role is this" when the dispatch prompt does not name the
 * role. Reading it through the `sessionProjections` registry keeps the plugin
 * off the deprecated synchronous log readers (`eventAt` / `snapshotEvents` /
 * `ownEvents`).
 *
 * The label is display metadata, never task content: the folded state stores a
 * single string and nothing from the descriptor's provider/model fields.
 *
 * @module dsh-trellis/subagent-identity
 */
import { z } from "zod";

export const SUBAGENT_IDENTITY_PROJECTION_KEY = "dsh-trellis.subagent-identity";

export const subagentIdentityProjection = {
  key: SUBAGENT_IDENTITY_PROJECTION_KEY,
  stateVersion: 1,
  stateSchema: z.object({
    inherited: z.number().int().nonnegative(),
    label: z.string().optional(),
  }),
  /**
   * @param {unknown} _header
   * @param {number} [inheritedEventCount]
   * @returns {{inherited: number}}
   */
  init(_header, inheritedEventCount = 0) {
    return { inherited: Number.isSafeInteger(inheritedEventCount) ? inheritedEventCount : 0 };
  },
  /**
   * Fold the child's own descriptor label.
   *
   * A forked child inherits its parent's events; an inherited descriptor
   * describes the parent, not this child, so it is ignored.
   *
   * @param {{inherited: number, label?: string}} state
   * @param {{type: string, seq: number, data?: unknown}} event
   * @returns {{inherited: number, label?: string}}
   */
  apply(state, event) {
    if (event?.type !== "subagent/descriptor") return state;
    if (event.seq < state.inherited) return state;
    const label = event.data?.label;
    if (typeof label !== "string" || label === "" || label === state.label) return state;
    return { ...state, label };
  },
};

/**
 * Register the identity projection and expose the child label lookup.
 *
 * Registration is optional by design: a profile without the projection service
 * (or a unit-test harness) degrades to "prompt-only" role detection instead of
 * failing the sub-agent push.
 *
 * @param {import("@deepseek-ai/cordis").Context} ctx
 * @returns {{dispose: () => void, labelOf: (session: any) => string | null}}
 */
export function registerSubagentIdentity(ctx) {
  const registry = ctx.sessionProjections;
  if (typeof registry?.register !== "function") {
    return { dispose: () => {}, labelOf: () => null };
  }
  const hostOnly = typeof registry.stateOf === "function";
  // rc.6 predates host-only units: it needs the legacy `schema` + `view` shape.
  const definition = hostOnly
    ? subagentIdentityProjection
    : {
        ...subagentIdentityProjection,
        schema: subagentIdentityProjection.stateSchema,
        view: (state) => state,
      };
  const disposeRegistration = registry.register(definition);
  return {
    dispose: disposeRegistration,
    labelOf(session) {
      if (session === undefined || session === null) return null;
      let state;
      try {
        state = hostOnly
          ? registry.stateOf(session, SUBAGENT_IDENTITY_PROJECTION_KEY)
          : registry.snapshot(session)?.values?.[SUBAGENT_IDENTITY_PROJECTION_KEY];
      } catch {
        return null;
      }
      return typeof state?.label === "string" && state.label !== "" ? state.label : null;
    },
  };
}
