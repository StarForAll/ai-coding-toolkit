import { test } from "node:test";
import assert from "node:assert/strict";
import {
  checkRouteUrl,
  compareVersions,
  isCheckDue,
  LAST_CHECK_KEY,
  memoryStorage,
  requestUpstream,
  ROUTE_PATH,
  runVersionCheck,
  SEEN_PREFIX,
  tagSignature,
  tagSummary,
} from "../src/client/version-check.js";

const jsonResponse = (body, status = 200) => ({
  ok: status >= 200 && status < 300,
  status,
  async json() { return body; },
});

const commitPayload = (sha = "0123456789abcdef", message = "Fix the thing") => ({
  ok: true,
  commit: {
    sha,
    shortSha: sha.slice(0, 7),
    date: "2026-10-12T16:06:27Z",
    message,
    url: `https://github.com/a/b/commit/${sha}`,
  },
  release: null,
});

test("checkRouteUrl targets the host route with the right parameter", () => {
  const plugin = { id: "plugin", kind: "commits" };
  const npm = { id: "trellis", kind: "npm" };
  assert.equal(ROUTE_PATH, "/dsh-trellis/version-check");
  assert.equal(
    checkRouteUrl(plugin, "https://github.com/a/b"),
    "/dsh-trellis/version-check?source=plugin&url=https%3A%2F%2Fgithub.com%2Fa%2Fb",
  );
  assert.equal(
    checkRouteUrl(npm, "@a/trellis"),
    "/dsh-trellis/version-check?source=npm&name=%40a%2Ftrellis",
  );
});

test("requestUpstream returns the payload and surfaces host errors", async () => {
  const seen = [];
  const payload = await requestUpstream({
    source: { id: "plugin", kind: "commits" },
    value: "https://github.com/a/b",
    fetchImpl: async (url) => {
      seen.push(url);
      return jsonResponse(commitPayload());
    },
  });
  assert.match(seen[0], /^\/dsh-trellis\/version-check\?source=plugin/);
  assert.equal(payload.commit.sha, "0123456789abcdef");

  await assert.rejects(
    requestUpstream({
      source: { id: "npm", kind: "npm" },
      value: "@a/b",
      fetchImpl: async () => jsonResponse({ ok: false, error: "npm registry returned 404 for @a/b" }, 502),
    }),
    /npm registry returned 404/,
  );
  await assert.rejects(
    requestUpstream({
      source: { id: "npm", kind: "npm" },
      value: "@a/b",
      fetchImpl: async () => ({ ok: false, status: 500, async json() { throw new Error("not json"); } }),
    }),
    /route returned 500/,
  );
});

test("first run records baselines; a changed commit and a changed dist-tag both notify", async () => {
  const storage = memoryStorage();
  const notified = [];
  const config = {
    versionCheck: true,
    versionCheckNotify: true,
    versionCheckPluginRepo: "https://github.com/a/plugin",
    versionCheckTrellisPackage: "@a/trellis",
    versionCheckDshPackage: "@a/dsh",
  };
  let sha = "1111111";
  let trellisLatest = "0.6.17";
  const fetchImpl = async (url) => {
    if (url.includes("source=npm")) {
      return url.includes("%40a%2Ftrellis")
        ? jsonResponse({ ok: true, tags: { latest: trellisLatest, beta: "0.7.0-beta.4" } })
        : jsonResponse({ ok: true, tags: { latest: "0.2.1-rc.2" } });
    }
    return jsonResponse(commitPayload(sha, "msg"));
  };

  const first = await runVersionCheck({
    config,
    fetchImpl,
    storage,
    notify: true,
    labelOf: (source) => source.id,
    notifyImpl: (...args) => notified.push(args),
    now: 1000,
    localVersion: "0.2.2",
  });
  assert.deepEqual(first.results.map((row) => [row.id, row.ok, row.isNew, row.firstSeen]), [
    ["plugin", true, false, true],
    ["trellis", true, false, true],
    ["dsh", true, false, true],
  ]);
  assert.equal(first.results[1].npm.tags.beta, "0.7.0-beta.4");
  assert.deepEqual(notified, []);
  assert.equal(storage.getItem(`${SEEN_PREFIX}plugin`), "1111111");
  assert.equal(storage.getItem(LAST_CHECK_KEY), "1000");

  sha = "3333333";
  trellisLatest = "0.6.18";
  const second = await runVersionCheck({
    config,
    fetchImpl,
    storage,
    notify: true,
    labelOf: (source) => source.id,
    notifyImpl: (...args) => notified.push(args),
    now: 2000,
  });
  assert.deepEqual(second.results.map((row) => [row.id, row.isNew]), [
    ["plugin", true],
    ["trellis", true],
    ["dsh", false],
  ]);
  assert.equal(notified.length, 2);
  assert.match(notified[0][0], /plugin/);
  assert.match(notified[1][1], /latest 0\.6\.18/);
});

test("blank values are skipped and a failing source does not stop the others", async () => {
  const storage = memoryStorage();
  const result = await runVersionCheck({
    config: {
      versionCheckPluginRepo: "",
      versionCheckTrellisPackage: "bad value",
      versionCheckDshPackage: "@a/dsh",
    },
    fetchImpl: async (url) => url.includes("name=bad")
      ? jsonResponse({ ok: false, error: "unrecognized npm package name" }, 400)
      : jsonResponse({ ok: true, tags: { latest: "0.2.1-rc.2" } }),
    storage,
    now: 5,
  });
  assert.equal(result.results[0].skipped, true);
  assert.equal(result.results[1].ok, false);
  assert.match(result.results[1].error, /unrecognized npm package/);
  assert.equal(result.results[2].ok, true);
});

test("a newer plugin release is flagged against the local version", async () => {
  const storage = memoryStorage();
  const result = await runVersionCheck({
    config: { versionCheckPluginRepo: "https://github.com/a/plugin" },
    localVersion: "0.2.2",
    storage,
    now: 1,
    fetchImpl: async () => jsonResponse({
      ok: true,
      commit: commitPayload("1234567").commit,
      release: { tag: "v0.3.0", url: "https://github.com/a/plugin/releases/tag/v0.3.0", date: "2026-10-01" },
    }),
  });
  assert.equal(result.results[0].updateAvailable, true);
  assert.equal(result.results[0].latestRelease.tag, "v0.3.0");
});

test("tag helpers and compareVersions", () => {
  const tags = { latest: "0.6.17", beta: "0.7.0-beta.4" };
  assert.equal(tagSignature(tags), "beta=0.7.0-beta.4;latest=0.6.17");
  assert.equal(tagSummary(tags), "beta 0.7.0-beta.4 · latest 0.6.17");
  assert.equal(compareVersions("v0.3.0", "0.2.2"), 1);
  assert.equal(compareVersions("0.2.2", "0.2.2"), 0);
  assert.equal(compareVersions("0.10.0", "0.9.9"), 1);
  assert.equal(compareVersions("", "0.0.1"), -1);
});

test("isCheckDue respects the switch, the interval and the recorded time", () => {
  const storage = memoryStorage({ [LAST_CHECK_KEY]: String(10_000) });
  assert.equal(isCheckDue({ versionCheck: true, versionCheckIntervalMinutes: 1 }, storage, 10_000 + 59_000), false);
  assert.equal(isCheckDue({ versionCheck: true, versionCheckIntervalMinutes: 1 }, storage, 10_000 + 61_000), true);
  assert.equal(isCheckDue({ versionCheck: false, versionCheckIntervalMinutes: 1 }, storage, 10_000 + 61_000), false);
  assert.equal(isCheckDue({ versionCheck: true, versionCheckIntervalMinutes: 0 }, storage, 10_000 + 61_000), false);
});

test("a partial commit feed is shown as a retryable result, not a raw abort", async () => {
  const storage = memoryStorage();
  const result = await runVersionCheck({
    config: { versionCheckPluginRepo: "https://github.com/a/plugin" },
    storage,
    now: 7,
    fetchImpl: async () => jsonResponse({
      ok: true,
      commit: null,
      release: {
        tag: "v0.3.0",
        url: "https://github.com/a/plugin/releases/tag/v0.3.0",
        date: "2026-10-01",
      },
      errors: [{ feed: "commits", message: "GitHub request timed out after 10000 ms" }],
    }),
  });
  const row = result.results[0];
  assert.equal(row.ok, true);
  assert.equal(row.partial, true);
  assert.equal(row.latestRelease.tag, "v0.3.0");
  assert.match(row.error, /timed out after 10000 ms/);
  assert.doesNotMatch(row.error, /This operation was aborted/);
  assert.equal(storage.getItem(`${SEEN_PREFIX}plugin`), null);
});
