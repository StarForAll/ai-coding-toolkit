import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  useSyncExternalStore,
} from "react";
import {
  editDraft,
  isOverridden,
  makeDraft,
  parseDraft,
  planDraft,
  savePlan,
  resetDraft,
} from "./form.js";
import { VersionMonitor } from "./VersionMonitor.jsx";

function Reset({ visible, disabled, label, onClick }) {
  return visible ? (
    <span className="dsh-trellis-field-head">
      <span className="dsh-trellis-badge">{label.overridden}</span>
      <button className="dsh-trellis-reset" type="button" disabled={disabled} onClick={onClick}>
        {label.reset}
      </button>
    </span>
  ) : null;
}

function TextField({ id, label, hint, value, disabled, multiline = false, invalid = false, invalidHint, onChange, onReset, overridden, t }) {
  const Control = multiline ? "textarea" : "input";
  return (
    <div className="dsh-trellis-field">
      <div className="dsh-trellis-field-head">
        <label className="dsh-trellis-label" htmlFor={id}>{label}</label>
        <Reset visible={overridden} disabled={disabled} label={{ overridden: t("overridden"), reset: t("reset") }} onClick={onReset} />
      </div>
      <Control
        id={id}
        className={multiline ? "dsh-trellis-textarea" : "dsh-trellis-input"}
        {...multiline ? {} : { type: "text" }}
        value={value}
        disabled={disabled}
        aria-invalid={invalid || undefined}
        onChange={(event) => onChange(event.target.value)}
      />
      <p className="dsh-trellis-hint" data-invalid={invalid}>{invalid ? (invalidHint ?? t("maxBytesInvalid")) : hint}</p>
    </div>
  );
}

function BooleanField({ id, label, hint, value, disabled, onChange, onReset, overridden, t }) {
  return (
    <div className="dsh-trellis-field">
      <div className="dsh-trellis-field-head">
        <label className="dsh-trellis-switch-row" htmlFor={id}>
          <input id={id} type="checkbox" checked={value} disabled={disabled} onChange={(event) => onChange(event.target.checked)} />
          <span className="dsh-trellis-switch-copy">
            <span className="dsh-trellis-label">{label}</span>
            <span className="dsh-trellis-hint">{hint}</span>
          </span>
        </label>
        <Reset visible={overridden} disabled={disabled} label={{ overridden: t("overridden"), reset: t("reset") }} onClick={onReset} />
      </div>
    </div>
  );
}

export function TrellisSettingsPage({ view, ...props }) {
  return view === "summary" ? props.t("description") : (
    <div className="dsh-trellis-section">
      <h2 className="dsh-trellis-section-title">{props.t("sectionTitle")}</h2>
      <p className="dsh-trellis-section-desc">{props.t("description")}</p>
      <TrellisSettingsCard {...props} presentation="page" />
    </div>
  );
}

export function TrellisSettingsCard({ scope, t, presentation = "card" }) {
  const subscribe = useCallback((listener) => scope.subscribe(listener), [scope]);
  const getSnapshot = useCallback(() => scope.getSnapshot(), [scope]);
  const snapshot = useSyncExternalStore(subscribe, getSnapshot, getSnapshot);
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState(() => makeDraft(snapshot));
  const [revision, setRevision] = useState(snapshot.revision);
  const [saving, setSaving] = useState(false);
  const [failed, setFailed] = useState(false);
  const page = presentation === "page";
  const Container = page ? "section" : "li";

  const plan = useMemo(() => planDraft(snapshot, draft), [snapshot, draft]);
  const dirty = plan.writes.length > 0;
  useEffect(() => {
    if (!dirty && snapshot.status === "ready") {
      setDraft(makeDraft(snapshot));
      setRevision(snapshot.revision);
    }
  }, [dirty, snapshot]);

  if (snapshot.status !== "ready") return null;
  const disabled = !snapshot.writable || saving;
  const parsed = parseDraft(draft);
  const field = (name) => ({
    overridden: isOverridden(snapshot, draft, name),
    onReset: () => {
      setDraft((current) => resetDraft(snapshot, current, name));
      setFailed(false);
    },
  });
  const edit = (name, value) => {
    setDraft((current) => editDraft(current, name, value));
    setFailed(false);
  };
  const discard = () => {
    setDraft(makeDraft(snapshot));
    setRevision(snapshot.revision);
    setFailed(false);
  };
  const save = async () => {
    if (saving || plan.invalid || plan.writes.length === 0) return;
    setSaving(true);
    setFailed(false);
    try {
      const landed = await savePlan(scope, plan.writes, revision);
      if (landed) {
        setDraft(makeDraft(scope.getSnapshot()));
        setRevision(scope.getSnapshot().revision);
      }
      setFailed(!landed);
    } catch {
      // The host may unload or reconnect while saving. Keep the draft and let
      // the user retry against the next snapshot; never leave an unhandled task.
      setFailed(true);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Container className={page ? "dsh-trellis-page" : "dsh-trellis-card"} data-open={page || open}>
      {!page ? <button
        type="button"
        className="dsh-trellis-header"
        aria-expanded={open}
        aria-label={`${t(open ? "collapse" : "expand")}: ${t("title")}`}
        onClick={() => setOpen((value) => !value)}
      >
        <span className="dsh-trellis-head-text">
          <span className="dsh-trellis-name">{t("title")}</span>
          <span className="dsh-trellis-description">{t("description")}</span>
        </span>
        {dirty ? <span className="dsh-trellis-badge">{t("unsaved")}</span> : null}
        <span className="dsh-trellis-chevron" aria-hidden="true">⌄</span>
      </button> : null}
      {page || open ? (
        <div className="dsh-trellis-body">
          {!snapshot.writable ? <p className="dsh-trellis-readonly" role="status">{t("readOnly")}</p> : null}
          <BooleanField id="dsh-trellis-enabled" label={t("enabled")} hint={t("enabledHint")} value={Boolean(draft.enabled.value)} disabled={disabled} onChange={(value) => edit("enabled", value)} t={t} {...field("enabled")} />
          <BooleanField id="dsh-trellis-commands" label={t("commandsEnabled")} hint={t("commandsEnabledHint")} value={Boolean(draft.commandsEnabled.value)} disabled={disabled} onChange={(value) => edit("commandsEnabled", value)} t={t} {...field("commandsEnabled")} />
          <BooleanField id="dsh-trellis-dispatch-guard" label={t("dispatchGuard")} hint={t("dispatchGuardHint")} value={Boolean(draft.dispatchGuard.value)} disabled={disabled} onChange={(value) => edit("dispatchGuard", value)} t={t} {...field("dispatchGuard")} />
          <BooleanField id="dsh-trellis-subagent-context" label={t("subagentContext")} hint={t("subagentContextHint")} value={Boolean(draft.subagentContext.value)} disabled={disabled} onChange={(value) => edit("subagentContext", value)} t={t} {...field("subagentContext")} />
          <BooleanField id="dsh-trellis-spec-injection" label={t("specInjection")} hint={t("specInjectionHint")} value={Boolean(draft.specInjection.value)} disabled={disabled} onChange={(value) => edit("specInjection", value)} t={t} {...field("specInjection")} />
          <TextField id="dsh-trellis-max-bytes" label={t("maxBytes")} hint={t("maxBytesHint")} value={String(draft.maxBytes.value)} disabled={disabled} invalid={parsed.invalid && (!Number.isInteger(parsed.value.maxBytes) || parsed.value.maxBytes < 0)} onChange={(value) => edit("maxBytes", value)} t={t} {...field("maxBytes")} />
          <TextField id="dsh-trellis-markers" label={t("projectRootMarkers")} hint={t("projectRootMarkersHint")} value={Array.isArray(draft.projectRootMarkers.value) ? draft.projectRootMarkers.value.join("\n") : String(draft.projectRootMarkers.value)} disabled={disabled} multiline onChange={(value) => edit("projectRootMarkers", value)} t={t} {...field("projectRootMarkers")} />
          <TextField id="dsh-trellis-skip-keyword" label={t("skipKeyword")} hint={t("skipKeywordHint")} value={String(draft.skipKeyword.value)} disabled={disabled} onChange={(value) => edit("skipKeyword", value)} t={t} {...field("skipKeyword")} />
          <TextField id="dsh-trellis-python" label={t("pythonCmd")} hint={t("pythonCmdHint")} value={String(draft.pythonCmd.value)} disabled={disabled} onChange={(value) => edit("pythonCmd", value)} t={t} {...field("pythonCmd")} />
          <BooleanField id="dsh-trellis-version-check" label={t("versionCheck")} hint={t("versionCheckHint")} value={Boolean(draft.versionCheck.value)} disabled={disabled} onChange={(value) => edit("versionCheck", value)} t={t} {...field("versionCheck")} />
          {draft.versionCheck.value ? (
            <>
              <TextField id="dsh-trellis-version-interval" label={t("versionCheckInterval")} hint={t("versionCheckIntervalHint")} value={String(draft.versionCheckIntervalMinutes.value)} disabled={disabled} invalid={parsed.invalid && (!Number.isInteger(parsed.value.versionCheckIntervalMinutes) || parsed.value.versionCheckIntervalMinutes < 0)} invalidHint={t("versionCheckIntervalInvalid")} onChange={(value) => edit("versionCheckIntervalMinutes", value)} t={t} {...field("versionCheckIntervalMinutes")} />
              <BooleanField id="dsh-trellis-version-notify" label={t("versionCheckNotify")} hint={t("versionCheckNotifyHint")} value={Boolean(draft.versionCheckNotify.value)} disabled={disabled} onChange={(value) => edit("versionCheckNotify", value)} t={t} {...field("versionCheckNotify")} />
              <BooleanField id="dsh-trellis-version-local-probe" label={t("versionCheckLocalProbe")} hint={t("versionCheckLocalProbeHint")} value={Boolean(draft.versionCheckLocalProbe.value)} disabled={disabled} onChange={(value) => edit("versionCheckLocalProbe", value)} t={t} {...field("versionCheckLocalProbe")} />
              <TextField id="dsh-trellis-plugin-repo" label={t("versionCheckPluginRepo")} hint={t("versionCheckPluginRepoHint")} value={String(draft.versionCheckPluginRepo.value)} disabled={disabled} onChange={(value) => edit("versionCheckPluginRepo", value)} t={t} {...field("versionCheckPluginRepo")} />
              <TextField id="dsh-trellis-trellis-package" label={t("versionCheckTrellisPackage")} hint={t("versionCheckPackageHint")} value={String(draft.versionCheckTrellisPackage.value)} disabled={disabled} onChange={(value) => edit("versionCheckTrellisPackage", value)} t={t} {...field("versionCheckTrellisPackage")} />
              <TextField id="dsh-trellis-dsh-package" label={t("versionCheckDshPackage")} hint={t("versionCheckPackageHint")} value={String(draft.versionCheckDshPackage.value)} disabled={disabled} onChange={(value) => edit("versionCheckDshPackage", value)} t={t} {...field("versionCheckDshPackage")} />
              {page ? <VersionMonitor config={parsed.value} t={t} disabled={disabled} /> : null}
            </>
          ) : null}
          <div className="dsh-trellis-footer">
            {failed ? <p className="dsh-trellis-error" role="status">{t("saveFailed")}</p> : null}
            <button className="dsh-trellis-button" type="button" disabled={!dirty || saving} onClick={discard}>{t("discard")}</button>
            <button className="dsh-trellis-button" data-primary="true" type="button" disabled={!snapshot.writable || plan.invalid || plan.writes.length === 0 || saving} onClick={() => void save()}>{t(saving ? "saving" : "save")}</button>
          </div>
        </div>
      ) : null}
    </Container>
  );
}
