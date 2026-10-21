/**
 * Decision logic and payload assembly for path-scoped spec injection.
 *
 * Pure functions only: no filesystem access, no session state. The tool-policy
 * layer (spec-policy.js) owns IO, identity and the per-session record map, so
 * every rule below is unit-testable without a runtime.
 *
 * Budgets are counted in characters, mirroring Trellis's hook contract: the
 * platform ceiling it respects is expressed in characters, and counting bytes
 * would make CJK specs pay three times for the same text.
 *
 * @module dsh-trellis/spec-inject
 */

/** Upper bound on the index-line reserve while FULL blocks are still packed. */
export const INDEX_RESERVE_MAX_CHARS = 900;

/** State record schema version; other versions re-teach instead of staying silent. */
export const STATE_VERSION = 2;

/** Model-facing instruction attached to a deny-once retry. */
export const RETRY_NOTICE =
  "Trellis injected governing specs. Review them, then retry this tool call.";

/**
 * True when the last emission is still inside the refresh window.
 *
 * A window of `0` means "never refresh unchanged content just because time
 * passed" (an infinite window). Missing or negative timestamps are treated as
 * outside the window — re-teaching is the safe side of the asymmetry.
 *
 * @param {number} nowSeconds
 * @param {number} lastTs
 * @param {number} winSeconds
 * @returns {boolean}
 */
export function withinWindow(nowSeconds, lastTs, winSeconds) {
  if (!Number.isFinite(nowSeconds) || !Number.isFinite(lastTs)) return false;
  if (winSeconds === 0) return true;
  const delta = nowSeconds - lastTs;
  return delta >= 0 && delta < winSeconds;
}

/**
 * Return `"full"`, `"ticket"` or `"silent"` for one spec.
 *
 * Order is contractual: stateless first, then first sight, content change,
 * context reset, the refresh window, and finally completeness. A ticket claims
 * "you were shown this spec", which is false when the recorded FULL was
 * truncated — an incomplete record is re-taught in full instead.
 *
 * @param {object} options
 * @param {boolean} options.stateless - no stable identity; always a ticket.
 * @param {{sha256?: string, ts?: number, reset?: string, complete?: boolean} | null} options.last
 * @param {string} options.sha256 - current spec content hash.
 * @param {number} options.nowSeconds
 * @param {number} options.winSeconds
 * @param {string} [options.resetId]
 * @returns {"full" | "ticket" | "silent"}
 */
export function decide({ stateless, last, sha256, nowSeconds, winSeconds, resetId }) {
  if (stateless) return "ticket";
  if (last === null || last === undefined) return "full";
  if (last.sha256 !== sha256) return "full";
  if ((last.reset ?? null) !== (resetId ?? null)) return "full";
  if (withinWindow(nowSeconds, last.ts, winSeconds)) return "silent";
  if (last.complete === false) return "full";
  return "ticket";
}

/**
 * Slice text to at most `cap` code points. `cap <= 0` means no limit.
 * @param {string} text
 * @param {number} cap
 * @returns {string}
 */
export function truncateChars(text, cap) {
  if (cap <= 0 || text.length <= cap) return text;
  return text.slice(0, cap);
}

/**
 * In-body notice appended when a spec body had to be truncated.
 * @param {string} relPath
 * @param {number} cap
 * @returns {string}
 */
export function truncationNotice(relPath, cap) {
  return `\n[Trellis: truncated at ${cap} characters — read ${relPath} for the full content]`;
}

/**
 * Render one full spec block.
 * @param {{editedRel: string, specRel: string, sha12: string, body: string}} block
 * @returns {string}
 */
export function renderFull({ editedRel, specRel, sha12, body }) {
  return `<spec-context file="${editedRel}" spec="${specRel}" sha256="${sha12}">\n${body}\n</spec-context>`;
}

/**
 * Render one ticket block.
 * @param {{editedRel: string, specRel: string, sha12: string, stateless: boolean}} ticket
 * @returns {string}
 */
export function renderTicket({ editedRel, specRel, sha12, stateless }) {
  const body = stateless
    ? `This spec governs the file you just touched. If you have not read it in\nthis session, read ${specRel} before continuing.`
    : `You were shown this spec earlier in this session and its content is unchanged.\nIt still governs edits to matching files. If you no longer remember it, read\n${specRel} before continuing.`;
  return `<spec-ticket file="${editedRel}" spec="${specRel}" sha256="${sha12}">\n${body}\n</spec-ticket>`;
}

/**
 * Render one index line for a spec whose body did not fit the budget.
 * @param {{specRel: string, description?: string | null}} match
 * @returns {string}
 */
export function indexLine(match) {
  return `- ${match.specRel} — ${match.description ?? "no description"}`;
}

/**
 * Render the degraded index block.
 * @param {string[]} lines
 * @returns {string}
 */
export function renderIndex(lines) {
  return `<spec-index>\n${lines.join("\n")}\n</spec-index>`;
}

/**
 * Find the largest truncated FULL block that fits.
 *
 * The rendered length is monotone non-decreasing in the body cap, so a binary
 * search over the cap finds the largest one that fits in ~log2(len) renders.
 *
 * @param {object} candidate
 * @param {(block: string) => boolean} fits
 * @param {number} maxSpecChars
 * @returns {{block: string, complete: boolean} | null}
 */
export function fitFullBlock(candidate, fits, maxSpecChars) {
  const { body, specRel, sha12 } = candidate;
  const ceiling = maxSpecChars <= 0 ? body.length : Math.min(maxSpecChars, body.length);
  const renderAt = (cap) => {
    const truncated = cap < body.length;
    const text = truncated
      ? truncateChars(body, cap) + truncationNotice(specRel, cap)
      : body;
    return {
      block: renderFull({ editedRel: candidate.editedRel, specRel, sha12, body: text }),
      complete: !truncated,
    };
  };
  if (body.length === 0) {
    const rendered = renderAt(0);
    return fits(rendered.block) ? rendered : null;
  }
  let low = 1;
  let high = Math.max(1, ceiling);
  let best = null;
  while (low <= high) {
    const mid = Math.floor((low + high) / 2);
    const rendered = renderAt(mid);
    if (fits(rendered.block)) {
      best = rendered;
      low = mid + 1;
    } else {
      high = mid - 1;
    }
  }
  return best;
}

/**
 * Assemble the per-event payload from already-decided candidates.
 *
 * `candidates[i].mode` is `"full" | "ticket" | "silent"`. The returned
 * `records` cover only the emissions that actually made it into the payload —
 * silent hits and budget-dropped candidates record nothing, so they stay
 * eligible for a later event.
 *
 * @param {object} options
 * @param {string} options.editedRel - repo-relative path handed to the tool.
 * @param {Array<{specRel: string, description?: string | null, sha256: string,
 *   sha12: string, body: string, mode: "full" | "ticket" | "silent"}>} options.candidates
 * @param {number} options.maxSpecChars
 * @param {number} options.maxTotalChars
 * @param {boolean} options.stateless
 * @param {number} options.nowSeconds
 * @param {string} [options.resetId]
 * @returns {{payload: string, records: Array<Record<string, unknown>>}}
 */
export function assemblePayload({
  editedRel,
  candidates,
  maxSpecChars,
  maxTotalChars,
  stateless,
  nowSeconds,
  resetId,
}) {
  const blocks = [];
  const records = [];
  const indexLines = [];
  const pending = candidates.filter((candidate) => candidate.mode !== "silent");

  // Reserve room for the degraded index block before packing bodies: a full
  // block must never eat the budget of the specs behind it. The reserve is
  // capped so a wide fan-out cannot starve the body that could still be
  // taught, and it only exists when more than one emission is pending.
  const indexReserve =
    pending.length > 1
      ? Math.min(INDEX_RESERVE_MAX_CHARS, renderIndex(pending.map(indexLine)).length)
      : 0;

  const measured = (list) => list.join("\n\n").length;
  const fits = (block) => {
    if (maxTotalChars <= 0) return true;
    return measured([...blocks, block]) + indexReserve <= maxTotalChars;
  };

  const record = (candidate, mode, complete = true) => {
    const value = {
      v: STATE_VERSION,
      spec: candidate.specRel,
      sha256: candidate.sha256,
      mode,
      ts: nowSeconds,
    };
    if (resetId !== undefined) value.reset = resetId;
    if (!complete) value.complete = false;
    return value;
  };

  for (const candidate of pending) {
    if (candidate.mode === "full") {
      if (candidate.body === null || candidate.body === undefined) {
        indexLines.push(indexLine(candidate));
        continue;
      }
      const fitted = fitFullBlock(
        { ...candidate, editedRel },
        fits,
        maxSpecChars,
      );
      if (fitted === null) {
        indexLines.push(indexLine(candidate));
        continue;
      }
      blocks.push(fitted.block);
      records.push(record(candidate, "full", fitted.complete));
      continue;
    }

    const block = renderTicket({
      editedRel,
      specRel: candidate.specRel,
      sha12: candidate.sha12,
      stateless,
    });
    if (!fits(block)) {
      indexLines.push(indexLine(candidate));
      continue;
    }
    blocks.push(block);
    records.push(record(candidate, "ticket"));
  }

  if (indexLines.length > 0) {
    const block = renderIndex(indexLines);
    // The reserve above already accounted for this block while bodies were
    // packed; re-check against the real (possibly shorter) line set.
    if (maxTotalChars <= 0 || measured([...blocks, block]) <= maxTotalChars) {
      blocks.push(block);
    }
  }

  return { payload: blocks.join("\n\n"), records };
}
