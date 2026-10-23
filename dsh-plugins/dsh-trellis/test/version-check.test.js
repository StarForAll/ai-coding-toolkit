import { test } from "node:test";
import assert from "node:assert/strict";
import {
  ACK_PREFIX,
  checkRouteUrl,
  compareReleaseTags,
  compareVersions,
  isCheckDue,
  isNewerReleaseTag,
  localRouteUrl,
  LAST_CHECK_KEY,
  memoryStorage,
  readAck,
  requestUpstream,
  ROUTE_PATH,
  requestLocalVersions,
  runVersionCheck,
  SEEN_PREFIX,
  tagSignature,
  tagSummary,
  trellisTagChannel,
  writeAck,
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
    localVersions: {},
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
    localVersions: {},
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
    localVersions: {},
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

test("an acknowledged snapshot suppresses both hints until upstream moves", async () => {
  const storage = memoryStorage();
  let sha = "aaaaaaa";
  let tag = "v0.1.13";
  const fetchImpl = async () => jsonResponse({
    ok: true,
    commit: commitPayload(sha).commit,
    release: { tag, url: `https://github.com/a/b/releases/tag/${tag}`, date: "2026-10-20" },
  });
  const run = () => runVersionCheck({
    config: { versionCheckPluginRepo: "https://github.com/a/b" },
    localVersion: "0.1.7",
    storage,
    now: 1,
    fetchImpl,
  });

  await run();
  sha = "bbbbbbb";
  const changed = (await run()).results[0];
  assert.equal(changed.isNew, true);
  assert.equal(changed.updateAvailable, true);
  assert.equal(changed.acknowledged, false);

  writeAck(storage, "plugin", { sha: changed.latest.sha, tag: changed.latestRelease.tag });
  const acked = (await run()).results[0];
  assert.equal(acked.acknowledged, true);
  assert.equal(acked.isNew, false);
  assert.equal(acked.updateAvailable, false);
  assert.deepEqual(acked.ack, { sha: "bbbbbbb", tag: "v0.1.13", signature: null });

  // Same release, new commit: the commit hint returns, the version badge does not.
  sha = "ccccccc";
  const moved = (await run()).results[0];
  assert.equal(moved.isNew, true);
  assert.equal(moved.updateAvailable, false);

  // A later release reopens the badge.
  tag = "v0.2.0";
  const released = (await run()).results[0];
  assert.equal(released.updateAvailable, true);
});

test("an acknowledged prerelease still flags the stable release of the same core", async () => {
  const storage = memoryStorage({
    [SEEN_PREFIX + "plugin"]: "ccccccc",
    [ACK_PREFIX + "plugin"]: JSON.stringify({ sha: "ccccccc", tag: "v0.2.0-rc.1" }),
  });
  const result = await runVersionCheck({
    config: { versionCheckPluginRepo: "https://github.com/a/b" },
    localVersion: "0.1.7",
    storage,
    now: 1,
    fetchImpl: async () => jsonResponse({
      ok: true,
      commit: commitPayload("ccccccc").commit,
      release: { tag: "v0.2.0", url: "https://github.com/a/b/releases/tag/v0.2.0" },
    }),
  });
  const row = result.results[0];
  assert.equal(row.acknowledged, true);
  assert.equal(row.isNew, false);
  assert.equal(row.updateAvailable, true);
});

test("ack records tolerate corrupt, empty and partial values", async () => {
  const storage = memoryStorage({ [ACK_PREFIX + "plugin"]: "{not json" });
  assert.equal(readAck(storage, "plugin"), undefined);
  storage.setItem(ACK_PREFIX + "plugin", JSON.stringify({}));
  assert.equal(readAck(storage, "plugin"), undefined);
  storage.setItem(ACK_PREFIX + "plugin", JSON.stringify(["sha"]));
  assert.equal(readAck(storage, "plugin"), undefined);
  storage.setItem(ACK_PREFIX + "plugin", JSON.stringify({ sha: "abc", tag: null }));
  assert.deepEqual(readAck(storage, "plugin"), { sha: "abc", tag: null, signature: null });

  // A broken record must not break the check itself.
  storage.setItem(ACK_PREFIX + "plugin", "{not json");
  const result = await runVersionCheck({
    config: { versionCheckPluginRepo: "https://github.com/a/b" },
    localVersion: "0.1.7",
    storage,
    now: 1,
    fetchImpl: async () => jsonResponse({
      ok: true,
      commit: commitPayload("ddddddd").commit,
      release: { tag: "v0.4.0", url: "https://github.com/a/b/releases/tag/v0.4.0" },
    }),
  });
  assert.equal(result.results[0].ok, true);
  assert.equal(result.results[0].acknowledged, false);
  assert.equal(result.results[0].updateAvailable, true);
  assert.equal(result.results[0].ack, undefined);
});

test("compareReleaseTags keeps prerelease precedence that compareVersions drops", () => {
  assert.equal(compareReleaseTags("v0.1.13", "0.1.13"), 0);
  assert.equal(compareReleaseTags("0.1.14", "v0.1.13"), 1);
  assert.equal(compareReleaseTags("0.2.0", "0.2.0-rc.1"), 1);
  assert.equal(compareReleaseTags("0.2.0-rc.1", "0.2.0"), -1);
  assert.equal(compareReleaseTags("0.2.1-rc.2", "0.2.1-rc.1"), 1);
  assert.equal(compareReleaseTags("0.2.1-alpha.2", "0.2.1-rc.1"), -1);
  assert.equal(isNewerReleaseTag("v0.1.13", "0.1.13"), false);
  assert.equal(isNewerReleaseTag("0.1.14", "0.1.13"), true);
  // compareVersions keeps its documented conservative behaviour.
  assert.equal(compareVersions("0.2.0", "0.2.0-rc.1"), 0);
});

test("an ack older than the local version never resurrects superseded releases", async () => {
  const storage = memoryStorage({
    [SEEN_PREFIX + "plugin"]: "eeeeeee",
    [ACK_PREFIX + "plugin"]: JSON.stringify({ sha: "eeeeeee", tag: "v0.1.5" }),
  });
  const run = (tag) => runVersionCheck({
    config: { versionCheckPluginRepo: "https://github.com/a/b" },
    localVersion: "0.1.8",
    storage,
    now: 1,
    fetchImpl: async () => jsonResponse({
      ok: true,
      commit: commitPayload("eeeeeee").commit,
      release: { tag, url: `https://github.com/a/b/releases/tag/${tag}` },
    }),
  });
  assert.equal((await run("v0.1.6")).results[0].updateAvailable, false);
  assert.equal((await run("v0.1.8")).results[0].updateAvailable, false);
  assert.equal((await run("v0.1.9")).results[0].updateAvailable, true);
});

test("requestLocalVersions asks the local source and keeps only known ids", async () => {
  const payload = await requestLocalVersions({
    fetchImpl: async (url) => {
      assert.equal(url, localRouteUrl());
      assert.match(url, /source=local$/);
      return jsonResponse({
        ok: true,
        local: { dsh: "0.2.1-rc.2", other: "1.0.0", trellis: "" },
        errors: [{ id: "trellis", message: "trellis was not found on PATH" }],
      });
    },
  });
  assert.deepEqual(payload.versions, { dsh: "0.2.1-rc.2" });
  assert.equal(payload.errors.length, 1);
});

test("trellisTagChannel follows the channel of the local version", () => {
  assert.equal(trellisTagChannel("0.7.0-beta.4"), "beta");
  assert.equal(trellisTagChannel("v0.6.0-rc.0"), "rc");
  assert.equal(trellisTagChannel("0.6.17"), "latest");
  assert.equal(trellisTagChannel("0.7.0-alpha.1"), "latest");
  assert.equal(trellisTagChannel(null), "latest");
});

test("npm rows compare the installed CLI with the published channel", async () => {
  const config = {
    versionCheckTrellisPackage: "@a/trellis",
    versionCheckDshPackage: "@a/dsh",
  };
  const fetchImpl = async (url) => url.includes("%40a%2Ftrellis")
    ? jsonResponse({ ok: true, tags: { latest: "0.6.17", beta: "0.7.0-beta.5", rc: "0.6.0-rc.0" } })
    : jsonResponse({ ok: true, tags: { latest: "0.2.1-rc.3", next: "0.2.1-rc.4" } });
  const run = (localVersions) => runVersionCheck({
    config, fetchImpl, storage: memoryStorage(), now: 1, localVersions,
  }).then((result) => Object.fromEntries(result.results.map((row) => [row.id, row])));

  const behind = await run({ dsh: "0.2.1-rc.2", trellis: "0.7.0-beta.4" });
  // DSH always compares against `latest`, even though `next` is also newer.
  assert.equal(behind.dsh.channel, "latest");
  assert.equal(behind.dsh.targetVersion, "0.2.1-rc.3");
  assert.equal(behind.dsh.updateAvailable, true);
  // Trellis beta compares against `beta`, not the older stable `latest`.
  assert.equal(behind.trellis.channel, "beta");
  assert.equal(behind.trellis.targetVersion, "0.7.0-beta.5");
  assert.equal(behind.trellis.updateAvailable, true);

  const current = await run({ dsh: "0.2.1-rc.3", trellis: "0.7.0-beta.5" });
  assert.equal(current.dsh.updateAvailable, false);
  assert.equal(current.trellis.updateAvailable, false);

  const stable = await run({ dsh: "0.2.1-rc.3", trellis: "0.6.17" });
  assert.equal(stable.trellis.channel, "latest");
  assert.equal(stable.trellis.targetVersion, "0.6.17");
  assert.equal(stable.trellis.updateAvailable, false);

  const ahead = await run({ dsh: "0.6.0", trellis: "0.6.17" });
  assert.equal(ahead.dsh.updateAvailable, false);
});

test("a failed local probe degrades to unknown instead of a guess", async () => {
  const result = await runVersionCheck({
    config: { versionCheckTrellisPackage: "@a/trellis", versionCheckDshPackage: "@a/dsh" },
    fetchImpl: async () => jsonResponse({ ok: true, tags: { latest: "0.6.17" } }),
    storage: memoryStorage(),
    now: 1,
    localProbe: async () => ({
      versions: {},
      errors: [{ id: "trellis", message: "trellis was not found on PATH" }],
    }),
  });
  assert.equal(result.local.errors.length, 1);
  const trellisRow = result.results.find((row) => row.id === "trellis");
  assert.equal(trellisRow.localVersion, null);
  assert.equal(trellisRow.updateAvailable, false);
  assert.equal(trellisRow.ok, true);
});

test("the probe is skipped when disabled or when no package source is configured", async () => {
  let calls = 0;
  const localProbe = async () => { calls += 1; return { versions: {}, errors: [] }; };
  const fetchImpl = async () => jsonResponse({ ok: true, tags: { latest: "0.6.17" } });
  await runVersionCheck({
    config: {
      versionCheckLocalProbe: false,
      versionCheckTrellisPackage: "@a/trellis",
      versionCheckDshPackage: "@a/dsh",
    },
    fetchImpl,
    storage: memoryStorage(),
    now: 1,
    localProbe,
  });
  await runVersionCheck({
    config: { versionCheckTrellisPackage: "", versionCheckDshPackage: "" },
    fetchImpl,
    storage: memoryStorage(),
    now: 1,
    localProbe,
  });
  assert.equal(calls, 0);
});

test("npm rows can be acknowledged and reopen on the next published version", async () => {
  const storage = memoryStorage();
  let dshLatest = "0.2.1-rc.3";
  const fetchImpl = async () => jsonResponse({ ok: true, tags: { latest: dshLatest } });
  const run = () => runVersionCheck({
    config: { versionCheckDshPackage: "@a/dsh" },
    fetchImpl,
    storage,
    now: 1,
    localVersions: { dsh: "0.2.1-rc.2" },
  }).then((result) => result.results.find((row) => row.id === "dsh"));

  const first = await run();
  assert.equal(first.updateAvailable, true);
  assert.equal(first.firstSeen, true);

  writeAck(storage, "dsh", { sha: null, tag: first.targetVersion, signature: first.signature });
  const acked = await run();
  assert.equal(acked.acknowledged, true);
  assert.equal(acked.updateAvailable, false);
  assert.equal(acked.isNew, false);

  dshLatest = "0.2.1-rc.4";
  const moved = await run();
  assert.equal(moved.updateAvailable, true);
  assert.equal(moved.isNew, true);
});
