import { useEffect, useState } from "react";
import {
  conflictSignature,
  conflictSummary,
  fetchConflicts,
} from "./conflicts.js";
import {
  ConflictBannerView,
  enableConflictNotifications,
} from "./conflict-view.js";
import { notifyDesktop } from "./version-check.js";

/** Desktop notifications already raised for this page, one per conflict set. */
const notified = new Set();

function notificationPermission() {
  return typeof Notification === "undefined"
    ? "unsupported"
    : Notification.permission;
}

/**
 * Frame-wide banner for a competing Trellis plugin.
 *
 * A desktop notification is the primary signal the user asked for, but it only
 * exists while the browser permission is granted. The banner therefore offers
 * the permission request itself (a click is the user gesture browsers require)
 * instead of waiting for the user to find the notification setting, and stays
 * visible as the fallback when notifications are blocked or unsupported.
 *
 * @param {{t: (key: string) => string}} props
 */
export function ConflictBanner({ t }) {
  const [conflicts, setConflicts] = useState([]);
  const [dismissed, setDismissed] = useState(false);
  const [permission, setPermission] = useState(notificationPermission);

  useEffect(() => {
    let cancelled = false;
    void fetchConflicts().then((result) => {
      if (cancelled) return;
      if (result.status !== "checked" || result.conflicts.length === 0) return;
      setConflicts(result.conflicts);
      const signature = conflictSignature(result.conflicts);
      if (notified.has(signature)) return;
      notified.add(signature);
      notifyDesktop(
        t("conflict.title"),
        t("conflict.body").replace(
          "{plugins}",
          conflictSummary(result.conflicts),
        ),
        "dsh-trellis:conflict",
      );
    });
    return () => {
      cancelled = true;
    };
  }, [t]);

  const enableNotifications = async () => {
    setPermission(await enableConflictNotifications({ conflicts, t }));
  };

  if (dismissed || conflicts.length === 0) return null;
  return (
    <ConflictBannerView
      t={t}
      conflicts={conflicts}
      permission={permission}
      onEnable={enableNotifications}
      onDismiss={() => setDismissed(true)}
    />
  );
}
