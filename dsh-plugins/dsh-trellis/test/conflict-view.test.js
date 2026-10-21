import { test } from "node:test";
import assert from "node:assert/strict";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { en, zh } from "../src/client/locales.js";
import {
  ConflictBannerView,
  conflictPermissionState,
  enableConflictNotifications,
} from "../src/client/conflict-view.js";

const t = (key) => zh[key] ?? key;
const conflicts = [{ id: "plus", name: "dsh-trellis-plus" }];

function renderBanner(permission) {
  return renderToStaticMarkup(createElement(ConflictBannerView, {
    t,
    conflicts,
    permission,
    onEnable() {},
    onDismiss() {},
  }));
}

test("the conflict banner offers permission only while the browser still allows it", () => {
  const promptable = renderBanner("default");
  assert.match(promptable, /启用桌面通知/);
  assert.match(promptable, /知道了/);
  assert.doesNotMatch(promptable, /桌面通知已被浏览器拒绝/);

  const blocked = renderBanner("denied");
  assert.match(blocked, /桌面通知已被浏览器拒绝/);
  assert.match(blocked, /知道了/);
  assert.doesNotMatch(blocked, /启用桌面通知/);

  for (const permission of ["granted", "unsupported"]) {
    const settled = renderBanner(permission);
    assert.match(settled, /知道了/);
    assert.doesNotMatch(settled, /启用桌面通知/);
    assert.doesNotMatch(settled, /桌面通知已被浏览器拒绝/);
  }
});

test("the banner names the competing plugins in its fallback text", () => {
  const html = renderBanner("default");
  assert.match(html, /dsh-trellis-plus（plus）/);
});

test("conflictPermissionState maps every Notification permission", () => {
  assert.deepEqual(conflictPermissionState("default"), {
    canRequest: true,
    blocked: false,
  });
  assert.deepEqual(conflictPermissionState("denied"), {
    canRequest: false,
    blocked: true,
  });
  for (const permission of ["granted", "unsupported"]) {
    assert.deepEqual(conflictPermissionState(permission), {
      canRequest: false,
      blocked: false,
    });
  }
});

test("enabling notifications notifies only after permission is granted", async () => {
  const notifications = [];
  const granted = await enableConflictNotifications({
    conflicts,
    t,
    permissionRequest: async () => "granted",
    notify: (title, body, tag) => {
      notifications.push({ title, body, tag });
      return true;
    },
  });
  assert.equal(granted, "granted");
  assert.deepEqual(notifications, [{
    title: "检测到另一个 Trellis 插件",
    body: "请只保留一个：dsh-trellis-plus（plus）。两者会重复注入工作流消息并争用同一组工具和命令。",
    tag: "dsh-trellis:conflict",
  }]);

  for (const permission of ["denied", "unsupported"]) {
    let requested = 0;
    let notified = 0;
    const result = await enableConflictNotifications({
      conflicts,
      t,
      permissionRequest: async () => {
        requested += 1;
        return permission;
      },
      notify: () => {
        notified += 1;
        return true;
      },
    });
    assert.equal(result, permission);
    assert.equal(requested, 1);
    assert.equal(notified, 0);
  }
});

test("both locales carry the new permission copy", () => {
  for (const locale of [zh, en]) {
    assert.equal(typeof locale["conflict.enableNotifications"], "string");
    assert.equal(typeof locale["conflict.notificationsBlocked"], "string");
    assert.notEqual(locale["conflict.enableNotifications"], "");
    assert.notEqual(locale["conflict.notificationsBlocked"], "");
  }
});
