/**
 * Pure presentation and permission-action half of the conflict banner.
 *
 * The stateful banner (`ConflictBanner.jsx`) owns fetching, dismissal, and the
 * "already notified" set; this module stays JSX-free so the four permission
 * states and the permission-request action are directly testable without a DOM.
 *
 * @module dsh-trellis/client/conflict-view
 */
import { createElement } from "react";
import { conflictSummary } from "./conflicts.js";
import { notifyDesktop, requestNotificationPermission } from "./version-check.js";

/**
 * Which notification affordances a permission state calls for.
 * @param {string} permission - `Notification.permission` or `"unsupported"`.
 * @returns {{canRequest: boolean, blocked: boolean}}
 */
export function conflictPermissionState(permission) {
  return {
    canRequest: permission === "default",
    blocked: permission === "denied",
  };
}

/**
 * Request permission from a user gesture and notify once it is granted.
 *
 * Browsers only show the permission prompt in response to a user gesture, which
 * is why this lives behind the banner button rather than in the page-load
 * effect. A denied/unsupported result changes only the banner state; it never
 * throws into React.
 *
 * @param {object} options
 * @param {Array<{id: string, name: string}>} options.conflicts
 * @param {(key: string) => string} options.t
 * @param {() => Promise<string>} [options.permissionRequest]
 * @param {(title: string, body: string, tag: string) => boolean} [options.notify]
 * @returns {Promise<string>} the resulting permission.
 */
export async function enableConflictNotifications({
  conflicts,
  t,
  permissionRequest = requestNotificationPermission,
  notify = notifyDesktop,
}) {
  const permission = await permissionRequest();
  if (permission !== "granted") return permission;
  notify(
    t("conflict.title"),
    t("conflict.body").replace("{plugins}", conflictSummary(conflicts)),
    "dsh-trellis:conflict",
  );
  return permission;
}

/**
 * Render the banner for one permission state.
 *
 * @param {object} props
 * @param {(key: string) => string} props.t
 * @param {Array<{id: string, name: string}>} props.conflicts
 * @param {string} props.permission
 * @param {() => void} props.onEnable
 * @param {() => void} props.onDismiss
 */
export function ConflictBannerView({
  t,
  conflicts,
  permission,
  onEnable,
  onDismiss,
}) {
  const { canRequest, blocked } = conflictPermissionState(permission);
  return createElement(
    "div",
    { className: "dsh-trellis-conflict", role: "alert" },
    createElement(
      "div",
      { className: "dsh-trellis-conflict-copy", key: "copy" },
      createElement("strong", { key: "title" }, t("conflict.title")),
      createElement(
        "span",
        { key: "body" },
        t("conflict.body").replace("{plugins}", conflictSummary(conflicts)),
      ),
      blocked
        ? createElement(
            "span",
            { key: "hint", className: "dsh-trellis-conflict-hint" },
            t("conflict.notificationsBlocked"),
          )
        : null,
    ),
    canRequest
      ? createElement(
          "button",
          {
            key: "enable",
            type: "button",
            className: "dsh-trellis-button",
            onClick: onEnable,
          },
          t("conflict.enableNotifications"),
        )
      : null,
    createElement(
      "button",
      {
        key: "dismiss",
        type: "button",
        className: "dsh-trellis-button",
        onClick: onDismiss,
      },
      t("conflict.dismiss"),
    ),
  );
}
