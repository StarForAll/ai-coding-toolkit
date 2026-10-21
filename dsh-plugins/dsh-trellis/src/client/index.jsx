import { ConflictBanner } from "./ConflictBanner.jsx";
import { TrellisSettingsPage } from "./TrellisSettingsCard.jsx";
import { en, zh } from "./locales.js";
import { styles } from "./styles.js";
import {
  defaultStorage,
  isCheckDue,
  runVersionCheck,
} from "./version-check.js";
import { PLUGIN_VERSION } from "./version.js";

export const SETTINGS_NAMESPACE = "dsh-trellis";
export const LOCALE_NAMESPACE = "settings.dsh-trellis";
export const inject = ["slots", "locale"];

/** Settings section id; the shell shows it as "Trellis" in the settings list. */
export const SECTION_ID = "trellis";

export function apply(ctx) {
  ctx.effect(
    () => ctx.locale.register(LOCALE_NAMESPACE, { zh, en }),
    "dsh-trellis.client.locale",
  );
  ctx.effect(() => {
    const selector = 'style[data-plugin-css="dsh-trellis/client"]';
    if (document.querySelector(selector) !== null) return () => {};
    const tag = document.createElement("style");
    tag.dataset.plugin = "dsh-trellis";
    tag.dataset.pluginCss = "dsh-trellis/client";
    tag.textContent = styles;
    document.head.appendChild(tag);
    return () => tag.remove();
  }, "dsh-trellis.client.styles");

  const t = typeof ctx.locale.bind === "function"
    ? ctx.locale.bind(LOCALE_NAMESPACE)
    : (key) => key;

  // Frame-wide so a conflict is visible from any screen. The banner raises the
  // desktop notification itself and remains as the fallback when notifications
  // are not permitted; the Host never logs this to a place users do not read.
  ctx.slots.inject("shell.overlay", () => ctx.slots.register(
    {
      name: "shell.overlay",
      id: "dsh-trellis-conflict",
      order: 20,
      locale: LOCALE_NAMESPACE,
    },
    ConflictBanner,
  ));

  // One settings page, whichever settings service this host exposes. Modern
  // hosts inject `configForms`; older ones bind `settingsScope` directly.
  let registered = false;
  const setup = (slotCtx, scope) => {
    if (registered) return;
    registered = true;
    registerSettingsSection(slotCtx, scope, t);
    startVersionMonitor(slotCtx, scope, t);
  };
  ctx.inject(["configForms"], (formsCtx) => {
    setup(formsCtx, formsCtx.configForms.get(SETTINGS_NAMESPACE));
  });
  ctx.inject(["settingsScope"], (legacyCtx) => {
    setup(legacyCtx, legacyCtx.settingsScope.bind({ namespace: SETTINGS_NAMESPACE }));
  });
}

function registerSettingsSection(ctx, scope, t) {
  ctx.slots.inject("settings.section", () => ctx.slots.register(
    {
      name: "settings.section",
      id: SECTION_ID,
      order: 16,
      label: () => t("sectionTitle"),
      locale: LOCALE_NAMESPACE,
      inject: () => ({ scope }),
    },
    TrellisSettingsPage,
  ));
}

/**
 * Automatic upstream check while the page is open.
 *
 * The browser is the only place a desktop notification can be shown, so the
 * interval lives here rather than in the Host. It re-arms whenever saved
 * settings change; a manual check in the page is independent of it.
 */
function startVersionMonitor(ctx, scope, t) {
  ctx.effect(() => {
    const storage = defaultStorage();
    const configNow = () => scope?.getSnapshot?.()?.value ?? {};
    let timer;
    let disposed = false;
    let running = false;

    const tick = async () => {
      if (disposed || running) return;
      running = true;
      try {
        await runVersionCheck({
          config: configNow(),
          storage,
          notify: true,
          labelOf: (source) => t(source.labelKey),
          localVersion: PLUGIN_VERSION,
        });
      } catch {
        // A failed check is surfaced by the next manual run; never break the page.
      } finally {
        running = false;
      }
    };

    const arm = () => {
      if (timer !== undefined) {
        clearInterval(timer);
        timer = undefined;
      }
      const value = configNow();
      if (value.versionCheck === false) return;
      const minutes = Number(value.versionCheckIntervalMinutes ?? 1440);
      if (!(minutes > 0)) return;
      // A host without a timer global (SSR, a bare harness) keeps the monitor
      // manual-only instead of failing the whole client plugin.
      if (typeof setInterval !== "function") return;
      timer = setInterval(() => { void tick(); }, minutes * 60_000);
      // Node keeps a timer alive; the Web UI does not care either way.
      if (typeof timer?.unref === "function") timer.unref();
    };

    const unsubscribe = typeof scope?.subscribe === "function"
      ? scope.subscribe(() => { arm(); })
      : () => {};
    arm();
    // Only a real browser can act on the result; keeps SSR/tests offline.
    if (typeof Notification !== "undefined" && isCheckDue(configNow(), storage, Date.now())) {
      void tick();
    }

    return () => {
      disposed = true;
      if (timer !== undefined) clearInterval(timer);
      unsubscribe();
    };
  }, "dsh-trellis.client.version-monitor");
}
