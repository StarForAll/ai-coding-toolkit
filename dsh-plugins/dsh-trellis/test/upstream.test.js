import { test } from "node:test";
import assert from "node:assert/strict";
import {
  createVersionCheckHandler,
  decodeXml,
  fetchCommitFeed,
  fetchNpmDistTags,
  fetchReleaseFeed,
  parseCommitFeed,
  parsePackageName,
  parseReleaseFeed,
  parseRepoUrl,
  ROUTE_PATH,
} from "../lib/upstream.js";

const COMMITS_ATOM = `<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <id>tag:github.com,2008:/a/b/commits/main</id>
  <title>Recent Commits to b:main</title>
  <entry>
    <id>tag:github.com,2008:Grit::Commit/32706f7e571ed0b985c2c8930e919e7ca8905347</id>
    <link type="text/html" rel="alternate" href="https://github.com/a/b/commit/32706f7e571ed0b985c2c8930e919e7ca8905347"/>
    <title>
        test: canonicalize &amp; fixture paths
    </title>
    <updated>2026-10-12T16:06:27Z</updated>
  </entry>
  <entry>
    <id>tag:github.com,2008:Grit::Commit/b487c1d90fe45270446937a062c39b966735ce9f</id>
    <link type="text/html" rel="alternate" href="https://github.com/a/b/commit/b487c1d90fe45270446937a062c39b966735ce9f"/>
    <title>older</title>
    <updated>2026-10-12T16:00:46Z</updated>
  </entry>
</feed>`;

const RELEASES_ATOM = `<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>tag:github.com,2008:Repository/1/v0.1.11</id>
    <link type="text/html" rel="alternate" href="https://github.com/a/b/releases/tag/v0.1.11"/>
    <title>v0.1.11</title>
    <updated>2026-10-02T08:40:41Z</updated>
  </entry>
</feed>`;

const jsonResponse = (body, status = 200) => ({
  ok: status >= 200 && status < 300,
  status,
  async json() { return body; },
  async text() { return typeof body === "string" ? body : JSON.stringify(body); },
});

test("the route path is stable", () => {
  assert.equal(ROUTE_PATH, "/dsh-trellis/version-check");
});

test("parseRepoUrl accepts repository URLs and rejects everything else", () => {
  assert.deepEqual(parseRepoUrl("https://github.com/SajoLuo/dsh-trellis"), {
    owner: "SajoLuo",
    repo: "dsh-trellis",
  });
  assert.deepEqual(parseRepoUrl("https://github.com/a/b.git"), { owner: "a", repo: "b" });
  assert.equal(parseRepoUrl("https://github.com/a/b/commits"), null);
  assert.equal(parseRepoUrl("SajoLuo/dsh-trellis"), null);
  assert.equal(parseRepoUrl("https://gitlab.com/a/b"), null);
  assert.equal(parseRepoUrl("https://github.com/orgs/a"), null);
  assert.equal(parseRepoUrl(""), null);
});

test("parsePackageName accepts scoped and plain names", () => {
  assert.equal(parsePackageName("@mindfoldhq/trellis"), "@mindfoldhq/trellis");
  assert.equal(parsePackageName(" @deepseek-ai/dsh "), "@deepseek-ai/dsh");
  assert.equal(parsePackageName("plain"), "plain");
  assert.equal(parsePackageName("https://github.com/a/b"), null);
  assert.equal(parsePackageName("@scope only"), null);
});

test("decodeXml handles the entities GitHub emits", () => {
  assert.equal(decodeXml("a &amp; b &lt;c&gt; &#39;q&#39; &#x27;s&#x27;"), "a & b <c> 'q' 's'");
});

test("parseCommitFeed returns the first entry", () => {
  assert.deepEqual(parseCommitFeed(COMMITS_ATOM), {
    sha: "32706f7e571ed0b985c2c8930e919e7ca8905347",
    shortSha: "32706f7",
    date: "2026-10-12T16:06:27Z",
    message: "test: canonicalize & fixture paths",
    url: "https://github.com/a/b/commit/32706f7e571ed0b985c2c8930e919e7ca8905347",
  });
  assert.equal(parseCommitFeed("<feed></feed>"), null);
});

test("parseReleaseFeed returns the first tag", () => {
  assert.deepEqual(parseReleaseFeed(RELEASES_ATOM), {
    tag: "v0.1.11",
    date: "2026-10-02T08:40:41Z",
    url: "https://github.com/a/b/releases/tag/v0.1.11",
  });
  assert.equal(parseReleaseFeed("<feed></feed>"), null);
});

test("fetchCommitFeed reads commits.atom, never the REST API", async () => {
  const urls = [];
  const commit = await fetchCommitFeed({
    repo: { owner: "a", repo: "b" },
    fetchImpl: async (url) => {
      urls.push(url);
      return { ok: true, status: 200, async text() { return COMMITS_ATOM; } };
    },
  });
  assert.deepEqual(urls, ["https://github.com/a/b/commits.atom"]);
  assert.equal(commit.shortSha, "32706f7");
});

test("fetchNpmDistTags reads the dist-tags endpoint", async () => {
  const urls = [];
  const tags = await fetchNpmDistTags({
    name: "@mindfoldhq/trellis",
    fetchImpl: async (url) => {
      urls.push(url);
      return jsonResponse({ latest: "0.6.17", beta: "0.7.0-beta.4" });
    },
  });
  assert.deepEqual(urls, ["https://registry.npmjs.org/-/package/@mindfoldhq%2Ftrellis/dist-tags"]);
  assert.deepEqual(tags, { latest: "0.6.17", beta: "0.7.0-beta.4" });
});

function harness({ method = "GET", query = "", headers = { "sec-fetch-site": "same-origin" } } = {}) {
  const response = { status: 0, headers: undefined, body: "" };
  const res = {
    writeHead(status, headers) { response.status = status; response.headers = headers; },
    end(body) { response.body = body; },
  };
  const req = { method, url: `${ROUTE_PATH}${query}`, headers };
  return { req, res, response };
}

test("the handler serves a commit and its release from Atom feeds", async () => {
  const fetchImpl = async (url) => url.endsWith("commits.atom")
    ? { ok: true, status: 200, async text() { return COMMITS_ATOM; } }
    : { ok: true, status: 200, async text() { return RELEASES_ATOM; } };
  const { req, res, response } = harness({ query: "?source=plugin&url=https%3A%2F%2Fgithub.com%2Fa%2Fb" });
  await createVersionCheckHandler({ fetchImpl })(req, res);
  const payload = JSON.parse(response.body);
  assert.equal(response.status, 200);
  assert.equal(response.headers["cache-control"], "no-store");
  assert.equal(payload.ok, true);
  assert.equal(payload.commit.shortSha, "32706f7");
  assert.equal(payload.release.tag, "v0.1.11");
});

test("the handler serves npm dist-tags", async () => {
  const fetchImpl = async () => jsonResponse({ latest: "0.6.17" });
  const { req, res, response } = harness({ query: "?source=npm&name=%40a%2Ftrellis" });
  await createVersionCheckHandler({ fetchImpl })(req, res);
  assert.equal(response.status, 200);
  assert.deepEqual(JSON.parse(response.body).tags, { latest: "0.6.17" });
});

test("the handler rejects invalid input, cross-site calls and bad methods", async () => {
  const cases = [
    { query: "?source=plugin&url=https%3A%2F%2Fgitlab.com%2Fa%2Fb", status: 400 },
    { query: "?source=npm&name=not%20a%20package", status: 400 },
    { query: "?source=unknown", status: 400 },
    { query: "?source=npm&name=a", headers: { "sec-fetch-site": "cross-site" }, status: 403 },
    { query: "?source=npm&name=a", method: "POST", status: 405 },
  ];
  for (const entry of cases) {
    const { req, res, response } = harness(entry);
    await createVersionCheckHandler({ fetchImpl: async () => jsonResponse({}) })(req, res);
    assert.equal(response.status, entry.status, JSON.stringify(entry));
    assert.equal(JSON.parse(response.body).ok, false);
  }
});

test("an upstream failure becomes a partial result, not a raw crash", async () => {
  const fetchImpl = async () => { throw new Error("offline"); };
  const { req, res, response } = harness({ query: "?source=plugin&url=https%3A%2F%2Fgithub.com%2Fa%2Fb" });
  await createVersionCheckHandler({ fetchImpl })(req, res);
  assert.equal(response.status, 200);
  const payload = JSON.parse(response.body);
  assert.equal(payload.ok, true);
  assert.equal(payload.commit, null);
  assert.equal(payload.release, null);
  assert.match(payload.errors.map((entry) => entry.message).join(" "), /offline/);
});

test("a hanging GitHub feed returns a friendly partial result", async () => {
  const fetchImpl = (_url, { signal }) => new Promise((_resolve, reject) => {
    signal.addEventListener("abort", () => {
      reject(Object.assign(new Error("This operation was aborted"), { name: "AbortError" }));
    }, { once: true });
  });
  const { req, res, response } = harness({ query: "?source=plugin&url=https%3A%2F%2Fgithub.com%2Fa%2Fb" });
  await createVersionCheckHandler({ fetchImpl, timeoutMs: 10 })(req, res);
  assert.equal(response.status, 200);
  const payload = JSON.parse(response.body);
  assert.equal(payload.ok, true);
  assert.equal(payload.commit, null);
  assert.equal(payload.release, null);
  assert.match(payload.errors.map((entry) => entry.message).join(" "), /timed out after 10 ms/);
  assert.doesNotMatch(response.body, /This operation was aborted/);
});

test("fetchCommitFeed falls back to the REST API when Atom is unavailable", async () => {
  const urls = [];
  const commit = await fetchCommitFeed({
    repo: { owner: "a", repo: "b" },
    fetchImpl: async (url) => {
      urls.push(url);
      if (url.endsWith("commits.atom")) throw new Error("feed offline");
      return jsonResponse([{
        sha: "abcdef1234567",
        html_url: "https://github.com/a/b/commit/abcdef1234567",
        commit: {
          message: "fix: fallback\n\nbody",
          author: { date: "2026-10-21T00:00:00Z" },
        },
      }]);
    },
  });
  assert.deepEqual(urls, [
    "https://github.com/a/b/commits.atom",
    "https://api.github.com/repos/a/b/commits?per_page=1",
  ]);
  assert.equal(commit.sha, "abcdef1234567");
  assert.equal(commit.message, "fix: fallback");
  assert.equal(commit.date, "2026-10-21T00:00:00Z");
});

test("fetchReleaseFeed falls back to the REST API and treats 404 as no release", async () => {
  const release = await fetchReleaseFeed({
    repo: { owner: "a", repo: "b" },
    fetchImpl: async (url) => {
      if (url.endsWith("releases.atom")) throw new Error("feed offline");
      return jsonResponse([{
        tag_name: "v0.1.1",
        published_at: "2026-10-21T00:00:00Z",
        html_url: "https://github.com/a/b/releases/tag/v0.1.1",
      }]);
    },
  });
  assert.deepEqual(release, {
    tag: "v0.1.1",
    date: "2026-10-21T00:00:00Z",
    url: "https://github.com/a/b/releases/tag/v0.1.1",
  });
  const none = await fetchReleaseFeed({
    repo: { owner: "a", repo: "b" },
    fetchImpl: async (url) => {
      if (url.endsWith("releases.atom")) throw new Error("feed offline");
      return jsonResponse({ message: "Not Found" }, 404);
    },
  });
  assert.equal(none, null);
});
