export const DEFAULTS = Object.freeze({
  enabled: true,
  maxBytes: 4096,
  projectRootMarkers: Object.freeze([".trellis", ".git"]),
  skipKeyword: "no-trellis",
  pythonCmd: "",
  commandsEnabled: true,
  specInjection: true,
  subagentContext: true,
  dispatchGuard: true,
  versionCheck: true,
  versionCheckIntervalMinutes: 1440,
  versionCheckNotify: true,
  versionCheckPluginRepo: "https://github.com/SajoLuo/dsh-trellis",
  versionCheckTrellisPackage: "@mindfoldhq/trellis",
  versionCheckDshPackage: "@deepseek-ai/dsh",
});

export const FIELD_NAMES = Object.freeze(Object.keys(DEFAULTS));

function record(value) {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? value
    : {};
}

export function sameValue(left, right) {
  return JSON.stringify(left) === JSON.stringify(right);
}

export function fallbackValue(snapshot, field) {
  const base = record(snapshot.base);
  return Object.hasOwn(base, field) ? base[field] : DEFAULTS[field];
}

export function makeDraft(snapshot) {
  const value = record(snapshot.value);
  return Object.fromEntries(
    FIELD_NAMES.map((field) => [
      field,
      { mode: "clean", value: value[field] ?? DEFAULTS[field] },
    ]),
  );
}

export function editDraft(draft, field, value) {
  return { ...draft, [field]: { mode: "set", value } };
}

export function resetDraft(snapshot, draft, field) {
  return {
    ...draft,
    [field]: { mode: "unset", value: fallbackValue(snapshot, field) },
  };
}

export function parseMarkers(text) {
  return [...new Set(text.split(/\r?\n/).map((entry) => entry.trim()).filter(Boolean))];
}

export function parseDraft(draft) {
  const maxBytes = Number(String(draft.maxBytes.value).trim());
  const interval = Number(String(draft.versionCheckIntervalMinutes.value).trim());
  const booleans = [
    "enabled",
    "commandsEnabled",
    "specInjection",
    "subagentContext",
    "dispatchGuard",
    "versionCheck",
    "versionCheckNotify",
  ];
  return {
    invalid:
      !Number.isInteger(maxBytes) ||
      maxBytes < 0 ||
      !Number.isInteger(interval) ||
      interval < 0 ||
      booleans.some((field) => typeof draft[field].value !== "boolean"),
    value: {
      enabled: draft.enabled.value,
      maxBytes,
      projectRootMarkers: parseMarkers(Array.isArray(draft.projectRootMarkers.value)
        ? draft.projectRootMarkers.value.join("\n") : String(draft.projectRootMarkers.value)),
      skipKeyword: String(draft.skipKeyword.value),
      pythonCmd: String(draft.pythonCmd.value),
      commandsEnabled: draft.commandsEnabled.value,
      specInjection: draft.specInjection.value,
      subagentContext: draft.subagentContext.value,
      dispatchGuard: draft.dispatchGuard.value,
      versionCheck: draft.versionCheck.value,
      versionCheckIntervalMinutes: interval,
      versionCheckNotify: draft.versionCheckNotify.value,
      versionCheckPluginRepo: String(draft.versionCheckPluginRepo.value),
      versionCheckTrellisPackage: String(draft.versionCheckTrellisPackage.value),
      versionCheckDshPackage: String(draft.versionCheckDshPackage.value),
    },
  };
}

export function planDraft(snapshot, draft) {
  const user = record(snapshot.user);
  const current = record(snapshot.value);
  const parsed = parseDraft(draft);
  const writes = [];
  for (const field of FIELD_NAMES) {
    const staged = draft[field];
    if (staged.mode === "clean") continue;
    if (staged.mode === "unset") {
      if (Object.hasOwn(user, field)) writes.push({ field, kind: "unset" });
      continue;
    }
    const value = parsed.value[field];
    if (!sameValue(current[field], value)) {
      writes.push({ field, kind: "set", value });
    }
  }
  return { invalid: parsed.invalid, writes };
}

export function isOverridden(snapshot, draft, field) {
  if (draft[field].mode === "set") return true;
  if (draft[field].mode === "unset") return false;
  return Object.hasOwn(record(snapshot.user), field);
}

export function planLanded(snapshot, writes) {
  const user = record(snapshot.user);
  return writes.every((write) =>
    write.kind === "unset"
      ? !Object.hasOwn(user, write.field)
      : Object.hasOwn(user, write.field) && sameValue(user[write.field], write.value),
  );
}

/** New hosts commit a staged form atomically against its edit-start revision. */
export async function savePlan(scope, writes, revision) {
  if (typeof scope.mutate === "function") {
    const accepted = await scope.mutate(writes.map(({ kind, field, value }) =>
      kind === "unset" ? { op: "unset", path: [field] }
        : { op: "set", path: [field], value },
    ), revision);
    if (accepted === false) return false;
  } else {
    for (const write of writes) {
      const accepted = write.kind === "unset"
        ? await scope.unset(write.field) : await scope.set(write.field, write.value);
      if (accepted === false) return false;
    }
  }
  return planLanded(scope.getSnapshot(), writes);
}
