import { useCallback, useState } from "react";
import {
  notifyDesktop,
  requestNotificationPermission,
  runVersionCheck,
  tagSummary,
} from "./version-check.js";
import { PLUGIN_VERSION } from "./version.js";

/**
 * Upstream version monitor rendered inside the Trellis settings page.
 *
 * Manual checks run with the page's current draft values, so a repository URL
 * can be verified before saving it. The automatic check (owned by the client
 * plugin, not this component) uses saved values.
 *
 * @param {object} props
 * @param {Record<string, unknown>} props.config - parsed draft values.
 * @param {(key: string) => string} props.t
 * @param {boolean} props.disabled
 */
export function VersionMonitor({ config, t, disabled }) {
  const [state, setState] = useState({ phase: "idle", result: null, error: null });
  const [permission, setPermission] = useState(() =>
    typeof Notification === "undefined" ? "unsupported" : Notification.permission,
  );

  const check = useCallback(async () => {
    setState((current) => current.phase === "running"
      ? current
      : { phase: "running", result: current.result, error: null });
    try {
      if (config.versionCheckNotify !== false) {
        setPermission(await requestNotificationPermission());
      }
      const result = await runVersionCheck({
        config,
        notify: false,
        labelOf: (source) => t(source.labelKey),
        localVersion: PLUGIN_VERSION,
      });
      setState({ phase: "done", result, error: null });
      if (config.versionCheckNotify !== false) {
        // A manual run always reports: the user asked for this check, so one
        // summary notification is expected even when nothing changed.
        const changed = result.results.filter((row) => row.isNew || row.updateAvailable).length;
        notifyDesktop(
          t("monitor.doneTitle"),
          t("monitor.doneBody")
            .replace("{count}", String(result.results.length))
            .replace("{changed}", String(changed)),
          "dsh-trellis:manual-check",
        );
      }
    } catch (error) {
      setState({ phase: "failed", result: null, error: error?.message ?? String(error) });
    }
  }, [config, t]);

  const running = state.phase === "running";
  const result = state.result;
  return (
    <section className="dsh-trellis-monitor" aria-label={t("monitor.title")}>
      <div className="dsh-trellis-field-head">
        <span className="dsh-trellis-label">{t("monitor.title")}</span>
        <span className="dsh-trellis-badge">{t("monitor.localVersion")} {PLUGIN_VERSION}</span>
      </div>
      <p className="dsh-trellis-hint">{t("monitor.description")}</p>
      <p className="dsh-trellis-hint">{t("monitor.localNote")}</p>
      {permission === "granted" ? null : (
        <p className="dsh-trellis-hint" data-invalid={permission === "denied" || undefined}>
          {permission === "denied"
            ? t("monitor.permissionDenied")
            : t("monitor.permissionHint")}
        </p>
      )}
      <div className="dsh-trellis-monitor-actions">
        <button
          className="dsh-trellis-button"
          type="button"
          disabled={disabled || running}
          onClick={() => { void check(); }}
        >
          {running ? t("monitor.checking") : t("monitor.checkNow")}
        </button>
        {result === null ? null : (
          <span className="dsh-trellis-hint">
            {t("monitor.lastChecked")}: {new Date(result.checkedAt).toLocaleString()}
          </span>
        )}
      </div>
      {state.error === null ? null : <p className="dsh-trellis-error">{state.error}</p>}
      {result === null ? null : (
        <ul className="dsh-trellis-monitor-list">
          {result.results.map((row) => (
            <li className="dsh-trellis-monitor-row" key={row.id}>
              <span className="dsh-trellis-monitor-source">{t(row.labelKey)}</span>
              {row.ok && row.npm !== undefined ? (
                <>
                  <span className="dsh-trellis-monitor-status" data-new={row.isNew || undefined}>
                    {row.isNew
                      ? t("monitor.versionChanged")
                      : row.firstSeen
                        ? t("monitor.firstSeen")
                        : t("monitor.upToDate")}
                  </span>
                  <a className="dsh-trellis-monitor-link" href={row.url} target="_blank" rel="noreferrer">
                    {tagSummary(row.npm.tags)}
                  </a>
                  <span className="dsh-trellis-monitor-meta">{row.npm.name}</span>
                </>
              ) : row.ok && row.latest !== undefined ? (
                <>
                  <span
                    className="dsh-trellis-monitor-status"
                    data-new={row.isNew || undefined}
                  >
                    {row.isNew
                      ? t("monitor.newCommit")
                      : row.firstSeen
                        ? t("monitor.firstSeen")
                        : t("monitor.upToDate")}
                  </span>
                  {row.updateAvailable && row.latestRelease ? (
                    <span className="dsh-trellis-monitor-status" data-new="true">
                      {t("monitor.updateAvailable")} {row.latestRelease.tag}
                    </span>
                  ) : null}
                  <a
                    className="dsh-trellis-monitor-link"
                    href={row.latest.url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    {row.latest.shortSha}
                  </a>
                  <span className="dsh-trellis-monitor-meta">
                    {[row.latest.date, row.latest.message].filter(Boolean).join(" · ")}
                  </span>
                </>
              ) : row.skipped ? (
                <span className="dsh-trellis-monitor-status">{t("monitor.disabledSource")}</span>
              ) : (
                <span className="dsh-trellis-monitor-status" data-error="true">{row.error}</span>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
