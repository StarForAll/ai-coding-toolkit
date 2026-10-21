/**
 * Minimal readers for the `.trellis/config.yaml` sections this plugin owns.
 *
 * Trellis writes a deliberately simple YAML subset (`key: value`, block lists,
 * flow lists, comments). We never need a general YAML parser, and pulling one
 * in would add a runtime dependency for two small sections. Unknown keys,
 * nested blocks, block scalars and malformed values are ignored: every reader
 * falls back to the documented default rather than failing the tool call.
 *
 * @module dsh-trellis/trellis-config
 */

/** @typedef {string | string[]} SectionValue */
/** @typedef {Map<string, SectionValue>} Section */

const SECTION_RE = /^([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(?:#.*)?$/;
const KEY_RE = /^\s*([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*)$/;
const ITEM_RE = /^\s*-\s*(.*)$/;

/**
 * Strip an inline YAML comment, respecting single/double quotes.
 * @param {string} value
 * @returns {string}
 */
function stripComment(value) {
  let quote = "";
  for (let index = 0; index < value.length; index += 1) {
    const char = value[index];
    if (quote !== "") {
      if (char === quote) quote = "";
      continue;
    }
    if (char === '"' || char === "'") {
      quote = char;
      continue;
    }
    if (char === "#" && (index === 0 || /\s/.test(value[index - 1]))) {
      return value.slice(0, index);
    }
  }
  return value;
}

/**
 * Remove one layer of matching quotes.
 * @param {string} value
 * @returns {string}
 */
function unquote(value) {
  const trimmed = value.trim();
  if (trimmed.length < 2) return trimmed;
  const first = trimmed[0];
  const last = trimmed[trimmed.length - 1];
  if ((first === '"' && last === '"') || (first === "'" && last === "'")) {
    return trimmed.slice(1, -1);
  }
  return trimmed;
}

/**
 * Parse a flow sequence body (`[a, b]`) into trimmed items.
 * @param {string} value
 * @returns {string[]}
 */
export function parseFlowSequence(value) {
  const inner = value.trim().slice(1, -1);
  if (inner.trim() === "") return [];
  return inner
    .split(",")
    .map((part) => unquote(stripComment(part)))
    .filter((part) => part !== "");
}

/**
 * Read one top-level mapping section from a config document.
 *
 * Returns `null` when the section is absent, so callers can distinguish
 * "missing" (use defaults) from "present but empty" (all keys default).
 *
 * @param {string | null | undefined} content - config.yaml text.
 * @param {string} name - top-level section name.
 * @returns {Section | null}
 */
export function parseSection(content, name) {
  if (typeof content !== "string" || content === "") return null;
  const lines = content.split(/\r?\n/);
  let index = lines.findIndex((line) => {
    const match = SECTION_RE.exec(line);
    return match !== null && match[1] === name;
  });
  if (index === -1) return null;

  /** @type {Section} */
  const section = new Map();
  let listKey = null;
  for (index += 1; index < lines.length; index += 1) {
    const line = lines[index];
    const trimmed = line.trim();
    if (trimmed === "" || trimmed.startsWith("#")) continue;
    // A non-indented line ends the section (the next top-level key).
    if (!/^\s/.test(line)) break;

    const item = ITEM_RE.exec(line);
    if (item !== null) {
      if (listKey === null) continue;
      const value = unquote(stripComment(item[1]));
      if (value === "") continue;
      const current = section.get(listKey);
      section.set(listKey, Array.isArray(current) ? [...current, value] : [value]);
      continue;
    }

    const keyMatch = KEY_RE.exec(line);
    if (keyMatch === null) continue;
    const key = keyMatch[1];
    const raw = stripComment(keyMatch[2]).trim();
    if (raw === "") {
      // An empty value opens either a block list or a nested mapping. Only a
      // following `- item` makes it a list; a nested mapping is ignored.
      listKey = key;
      section.set(key, []);
      continue;
    }
    listKey = null;
    if (raw.startsWith("[") && raw.endsWith("]")) {
      section.set(key, parseFlowSequence(raw));
    } else {
      section.set(key, unquote(raw));
    }
  }
  return section;
}

/**
 * Read one top-level scalar (`key: value` at column 0).
 *
 * Used for `default_workflow`, which is a top-level key rather than a section.
 * Section bodies are indented, so only column-0 lines are considered.
 *
 * @param {string | null | undefined} content - config.yaml text.
 * @param {string} name - top-level key.
 * @returns {string | null}
 */
export function topLevelScalar(content, name) {
  if (typeof content !== "string" || content === "") return null;
  for (const line of content.split(/\r?\n/)) {
    if (line === "" || /^\s/.test(line) || line.startsWith("#")) continue;
    const match = KEY_RE.exec(line);
    if (match === null || match[1] !== name) continue;
    const value = unquote(stripComment(match[2])).trim();
    return value === "" ? null : value;
  }
  return null;
}

/**
 * `prompt_injection.skip_keyword` from `.trellis/config.yaml`.
 *
 * Returns `null` when the section is absent (fall back to the plugin-level
 * default) and the literal value otherwise, including `""` — an explicitly
 * empty keyword disables the escape hatch, matching Trellis's hook.
 *
 * @param {string | null | undefined} content
 * @returns {string | null}
 */
export function promptInjectionSkipKeyword(content) {
  const section = parseSection(content, "prompt_injection");
  if (section === null) return null;
  const raw = section.get("skip_keyword");
  if (typeof raw !== "string") return null;
  return raw.trim();
}

const TRUE_VALUES = new Set(["true", "yes", "1", "on"]);
const FALSE_VALUES = new Set(["false", "no", "0", "off"]);
/**
 * Boolean-ish YAML scalar. Unrecognised values fall back to `fallback`.
 * @param {SectionValue | undefined} raw
 * @param {boolean} fallback
 * @returns {boolean}
 */
export function parseBoolean(raw, fallback) {
  if (typeof raw === "boolean") return raw;
  if (typeof raw !== "string") return fallback;
  const value = raw.trim().toLowerCase();
  if (TRUE_VALUES.has(value)) return true;
  if (FALSE_VALUES.has(value)) return false;
  return fallback;
}

/**
 * Non-negative integer. Negative or non-numeric values fall back.
 * @param {SectionValue | undefined} raw
 * @param {number} fallback
 * @returns {number}
 */
export function parseCount(raw, fallback) {
  if (typeof raw === "number" && Number.isFinite(raw)) {
    return Number.isInteger(raw) && raw >= 0 ? raw : fallback;
  }
  if (typeof raw !== "string") return fallback;
  const value = Number(raw.trim());
  return Number.isInteger(value) && value >= 0 ? value : fallback;
}

/** Spec-injection defaults, mirrored from Trellis's own hook contract. */
export const SPEC_INJECTION_DEFAULTS = Object.freeze({
  enabled: true,
  maxSpecChars: 9400,
  maxTotalChars: 9500,
  refreshWindowSeconds: 2700,
  /**
   * Codex wires this feature through a `PreToolUse` matcher of `Edit|Write`
   * even though Trellis's own default list also names Read/MultiEdit. The DSH
   * parity target is Codex's actual wiring, so Read is opt-in here.
   */
  tools: Object.freeze(["edit", "write"]),
});

/**
 * Normalise a tool name to the DSH-native lower-case form.
 * @param {string} name
 * @returns {string}
 */
export function normalizeToolName(name) {
  const value = String(name ?? "").trim().toLowerCase();
  if (value === "multiedit" || value === "multi_edit") return "edit";
  return value;
}

/**
 * Resolve the `spec_injection:` settings for a project.
 * @param {string | null | undefined} configText - `.trellis/config.yaml`.
 * @returns {{enabled: boolean, maxSpecChars: number, maxTotalChars: number,
 *   refreshWindowSeconds: number, tools: string[]}}
 */
export function specInjectionSettings(configText) {
  const defaults = SPEC_INJECTION_DEFAULTS;
  const section = parseSection(configText, "spec_injection");
  if (section === null) {
    return {
      enabled: defaults.enabled,
      maxSpecChars: defaults.maxSpecChars,
      maxTotalChars: defaults.maxTotalChars,
      refreshWindowSeconds: defaults.refreshWindowSeconds,
      tools: [...defaults.tools],
    };
  }
  const tools = section.get("tools");
  const parsedTools = Array.isArray(tools)
    ? tools.map(normalizeToolName).filter((tool) => tool !== "")
    : defaults.tools;
  return {
    enabled: parseBoolean(section.get("enabled"), defaults.enabled),
    maxSpecChars: parseCount(section.get("max_spec_chars"), defaults.maxSpecChars),
    maxTotalChars: parseCount(section.get("max_total_chars"), defaults.maxTotalChars),
    refreshWindowSeconds: parseCount(
      section.get("refresh_window_seconds"),
      defaults.refreshWindowSeconds,
    ),
    tools: [...parsedTools],
  };
}

/** Sub-agent context limits, mirrored from Trellis's own injection contract. */
export const CONTEXT_INJECTION_DEFAULTS = Object.freeze({
  maxFileBytes: 32768,
  maxArtifactBytes: 65536,
  maxTotalBytes: 131072,
});

/**
 * Resolve the `context_injection:` limits used by the sub-agent push.
 * @param {string | null | undefined} configText - `.trellis/config.yaml`.
 * @returns {{maxFileBytes: number, maxArtifactBytes: number, maxTotalBytes: number}}
 */
export function contextInjectionLimits(configText) {
  const section = parseSection(configText, "context_injection");
  const defaults = CONTEXT_INJECTION_DEFAULTS;
  if (section === null) return { ...defaults };
  return {
    maxFileBytes: parseCount(section.get("max_file_bytes"), defaults.maxFileBytes),
    maxArtifactBytes: parseCount(
      section.get("max_artifact_bytes"),
      defaults.maxArtifactBytes,
    ),
    maxTotalBytes: parseCount(section.get("max_total_bytes"), defaults.maxTotalBytes),
  };
}
