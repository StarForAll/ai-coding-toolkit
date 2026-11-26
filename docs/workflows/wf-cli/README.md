# wf command

`docs/workflows/wf-cli/` is the **system-level distribution package** for the `wf` workflow.
It is not part of the target-project release assets (`docs/workflows/wf-release/`): it installs
only the `wf` command into the user's Python tool environment; the command then resolves,
verifies and runs the matching release from the registered Forgejo repository.

## Install the command (no version parameter)

From a checkout, the first-install entry is the local Python script:

```bash
export WF_FORGEJO_BASE="https://forgejo.xzc.com:13785"
python3 scripts/install-wf.py
wf version
```

It runs the local `docs/workflows/wf-cli/install.py` bootstrap, so it does not need to download
the bootstrap script itself. That bootstrap asks the release API for the **newest published
release** of the registered repository, requires the `wf_cli-<version>-py3-none-any.whl` asset of
that release, and installs it with `uv` (or `pipx`). No version or tag is accepted anywhere in this
path: the newest release is selected automatically.

`install-wf.py` resolves `WF_FORGEJO_BASE` / `FORGEJO_TOKEN` from the environment; on a TTY it
prompts for missing values. `--base` can supply the base explicitly, and `--token-env` can point at
another token environment variable; the token is never a CLI argument.

Public repository: leave the token empty. Private repository: provide/paste the token; the
bootstrap uses it for the release API and wheel download.

The base is the **instance root** (`https://forgejo.xzc.com:13785`), not the repository root: the
repository slug comes from the registered source, which is also how the release-asset URL is
composed. On success the install writes that base to the machine record
`~/.wf/system-command.json` (`{schema_version, http_base, repo, written_at}`, mode 0600); it stores
no version or tag, because those change with every upgrade. `wf self-upgrade` reads the same record,
so upgrade downloads from exactly the URL source the install used — see “Upgrade the system
command” below.

### Without a checkout

The same bootstrap is the stable `install.py` asset of every release, and the raw copy on the
default branch is runnable too:

```bash
export WF_FORGEJO_BASE="https://forgejo.xzc.com:13785"
curl -fsSL "${WF_FORGEJO_BASE}/xzc/ai-coding-toolkit/raw/branch/main/docs/workflows/wf-cli/install.py" | python3 -
wf version
```

For a **private** repository that fetch also needs authentication (token stays in the environment;
no token in argv or URL):

```bash
export WF_FORGEJO_BASE="https://forgejo.xzc.com:13785"
export FORGEJO_TOKEN="..."

python3 - <<'PYTHON'
import os, urllib.request
base = os.environ["WF_FORGEJO_BASE"].rstrip("/")
token = os.environ["FORGEJO_TOKEN"]
url = f"{base}/xzc/ai-coding-toolkit/raw/branch/main/docs/workflows/wf-cli/install.py"
request = urllib.request.Request(url, headers={"Authorization": f"token {token}"})
with urllib.request.urlopen(request) as response:
    code = response.read()
exec(compile(code, url, "exec"), {"__name__": "__main__"})
PYTHON

wf version
```

Without `FORGEJO_TOKEN`, a private repository returns 404 for the asset URL (Forgejo hides the
existence of private resources); it does not mean the route is missing.

### Build the release asset

The release asset is built from the release tree's version:

```bash
python3 scripts/build-wf-cli-wheel.py
python3 scripts/attach-wf-cli-asset.py \
  --tag wf-v<version> --wheel tmp/wf-cli-dist/wf_cli-<version>-py3-none-any.whl
```

If the tag exists but the Forgejo release has not been created yet, add `--create-release`; the
script creates the release through the API and then attaches both assets. It never creates the tag.

The attach script uploads both the wheel and `install.py`; `FORGEJO_TOKEN` is read from the
environment. It treats a same-size asset as already attached and refuses a same-name asset with a
different size instead of overwriting it.

The wheel and the release manifest must have the same version; `scripts/build-wf-cli-wheel.py`
checks that and the `verify-wf-release.py` gate checks the CLI package inside the tag. When
`wf-v<version>` already exists, the builder also requires `HEAD == tag commit` and a clean
`docs/workflows/wf-cli` / `docs/workflows/wf-release` worktree. Never attach a wheel built from a
newer working tree to an old tag; bump the version and create a new tag instead. Forgejo Actions is
not available on this instance (there is no `.forgejo/workflows/`), so the release is created by
`scripts/release-wf.py` only — pushing a `wf-v*` tag does not build or attach anything.

## Forgejo token

Local release tooling needs a token with write access; `scripts/attach-wf-cli-asset.py`,
`scripts/prune-wf-releases.py` and `scripts/install-wf.py` all read it from an environment variable:

1. In Forgejo open **Settings → Applications → Generate New Token**.
2. Give it a name such as `wf-release` and scopes `read:repository` plus `write:repository`.
3. Copy the value once into a password manager or environment variable; it cannot be shown again.
4. Locally: `export FORGEJO_TOKEN="..."` (the scripts read the environment, never an argument).

Never put the token into a URL, command line, committed file, or workflow log.

## When Forgejo HTTP/API is unavailable

The release-based installer and `attach-wf-cli-asset.py` need the Forgejo **HTTP/API** endpoint.
`ssh://git@forgejo.xzc.com` may work while `https://forgejo.xzc.com` is refused; check both:

```bash
curl -I --max-time 5 "https://forgejo.xzc.com"
git ls-remote "ssh://git@forgejo.xzc.com/xzc/ai-coding-toolkit.git" HEAD
```

If web/API is on a different host, port or reverse proxy, set its base explicitly:

```bash
export WF_FORGEJO_BASE="https://your-forgejo-web-base"
export WF_GIT_URL="ssh://git@forgejo.xzc.com/xzc/ai-coding-toolkit.git"  # optional
```

Then rerun `install.py` or `attach-wf-cli-asset.py` (both also accept `--base`). To find the
instance's real address, check Forgejo's `[server] ROOT_URL` (for example
`grep ROOT_URL /etc/forgejo/app.ini` on the host) or the browser URL you use to open the web UI.

If only SSH is reachable and the HTTP API is unavailable from this machine:

```bash
bash scripts/install-wf-ssh.sh
```

It clones the registered repository over SSH, resolves the newest `wf-v*` tag by creation date,
and installs that tag with uv/pipx; it takes no version argument. Release upload and release-asset
installation still need the HTTP endpoint (web UI or a machine that can reach it). SSH alone
cannot create or attach Forgejo release assets, so a tag push builds nothing: releases are created
by `scripts/release-wf.py` on a machine that can reach the API.


## Upgrade the system command (distinct from project upgrade)

```bash
wf self-upgrade          # newest system release; no version argument
wf self-upgrade --json
```

`wf self-upgrade` upgrades the **system-level command itself**. It is separate from `wf upgrade`,
which upgrades the wf assets inside the current project. It downloads the release wheel of the
newest release, and only falls back to building the command from that release tag when the asset
cannot be used. Use `--manager uv|pipx|pip` only when automatic detection fails.

The asset base is resolved as `WF_FORGEJO_BASE` → the machine install record written by the install
→ the registered default (`https://forgejo.xzc.com:13785`). It is never derived from the git source
URL: git and the Web/API listen on different ports, so a derived base loses the port and cannot
connect.

When the asset is not used (HTTP 404 or a connection failure), the upgrade still installs from the
release tag but reports the **degradation** in its output: the rejected asset URL, the base it used
and the reason, plus a fix exit. A plain upgrade message therefore always means the wheel asset was
actually installed; the install record is written only in that case, because only then is the base
proven to serve assets.

`wf self-upgrade` reads `FORGEJO_TOKEN` from the environment only — unlike the install entry, it
never prompts. For a private repository, export the token before upgrading; otherwise the asset URL
answers 404 (Forgejo hides private resources) and the command is built from the release tag.

To remove the system command itself (not a project install):

```bash
wf self-uninstall          # preview only
wf self-uninstall --apply  # remove the installed wf-cli tool
```

The preview prints the exact `uv tool uninstall wf-cli` / `pipx uninstall wf-cli` command. Project
removal remains `wf uninstall` inside the project and is a different operation.

## One-shot release

A pre-push-only flow cannot create the release: at pre-push time the tag does not exist on the
Forgejo remote yet, and git has no post-push hook. Use the one-shot release script for the
complete sequence:

```bash
export WF_FORGEJO_BASE="https://forgejo.xzc.com:13785"
export FORGEJO_TOKEN="..."
python3 scripts/release-wf.py
```

The worktree must be clean before it runs; the script refuses to sweep unrelated changes. The
Python script reads the current version from the release manifest, chooses the next version,
updates the README/release tree, builds and commits the release, creates the local tag, verifies
the tag, builds the wheel, pushes the project branch to **all configured git remotes**, then pushes
the tag to the Forgejo remote and creates the release with the wheel plus `install.py`. Tags never
go to the non-Forgejo remotes. After a successful release it deletes the Forgejo releases (and then
the tags) beyond the newest three, so the release list stays as small as the tag list; run
`python3 scripts/prune-wf-releases.py --keep 3 --protect wf-v<version>` to clean history standalone.

Version selection:

- default: `x.x.y -> x.x.(y+1)`;
- `--minor`: `x.x.y -> x.(x+1).0`;
- `--major`: `x.x.y -> (x+1).0.0`.

If the current manifest version has no local tag yet, the default branch releases that prepared
version as-is instead of skipping it; `--minor`/`--major` always bump explicitly. It does not need
a manual `git tag`; the wf-specific pre-push hook was removed and the remaining pre-push hook only
checks plugin bundles.

Retention: after a successful release, Forgejo keeps only the newest three `wf-v*` **releases**;
the historical releases are deleted first — with their `wf_cli-*.whl` and `install.py` assets — and
then the older remote tags are deleted (mandatory). A tag and its release are two separate Forgejo
objects, so pruning only tags leaves the `/releases` pages behind. Local old tags are kept by
default; add `--prune-local-tags` to delete them too. The comparison is creation time
(`creatordate` / release `created_at`), matching release selection, not semantic version order.
`--prune-tags` is an add-on to the normal release flow, not a standalone cleanup command; remote
pruning already runs after every successful release, and the flag only makes that intent explicit.
It never replaces version bump/build/tag/push/attach.

`FORGEJO_TOKEN` / `WF_FORGEJO_BASE` are read from the environment. If either is missing, the
script prompts on a TTY; in a non-interactive process it fails instead of hanging. The token uses
`getpass` and is never printed or passed as an argument.

If attachment fails, the script reports the exact retry command. The tag is already pushed, so do
not recreate it.

## Use it in a project

```bash
# in a project that has no .wf/ yet
wf install          # preview of the system command's version
wf install --confirm

# later
wf upgrade          # preview of the newest project release
wf upgrade --apply  # apply after the terminal preview token

wf uninstall        # forwards to the installed independent uninstall entry
wf repair           # repairs a leftover write record (writer.json → idle)
```

`--project` is optional for every command: run inside the project and the current directory is
used (`install` uses it directly, the other commands walk up to the nearest `.wf/`); pass
`--project <absolute-path>` only when you are outside the target project. The installed
independent `repair.py` / `uninstall.py` entries accept the same contract — `--project`, then
`WF_PROJECT_ROOT`, then the current directory — so they stay runnable from the project root when
the runtime or its configuration is broken.

Running `wf` inside a project also forwards ordinary runtime commands to `.wf/bin/wf.py`, so
`task-new`, `task-check`, `spec`, `review-*`, etc. no longer need a project-local path.

## Release contract

- System command installation selects the newest Forgejo release automatically; it does not pin a
  version/tag in the install command.
- The Forgejo release for `wf-vX.Y.Z` must carry `wf_cli-X.Y.Z-py3-none-any.whl` and the
  stable `install.py`; without them the release-based install blocks instead of installing an
  unreleased branch.
- `wf install` in a project without wf uses the version of the installed `wf` command.
- `wf upgrade` resolves the **newest release tag on the default branch** and upgrades the project
  to it; there is no version/ref parameter.
- `wf self-upgrade` resolves the newest system command release and replaces the installed command;
  it is not the project upgrade command.
- The system command's asset base is a single fact shared by install and self-upgrade
  (`WF_FORGEJO_BASE` → `~/.wf/system-command.json` → registered default); an asset that cannot be
  used is reported as a git-tag degradation with its URL and reason, never as a normal upgrade.
- Forgejo keeps only the newest three `wf-v*` releases and their tags. A release is a separate
  object from its tag, so `scripts/release-wf.py` deletes the historical releases (with their
  assets) before deleting the old tags; `scripts/prune-wf-releases.py` does the same cleanup alone.
- `wf repair` repairs leftover write state only: it resets `.wf/writer.json` to idle (generation
  + 1, maintenance receipts kept) and `--dispose <plan>` writes one receipt's disposition. It
  never rewrites business records or skill assets.
- `--release-ref`, `--source`, `--release` and `--target` are retired for users: the release
  identity comes from the system command and the registered source, never from a local checkout.
- `install.py` remains the release-internal entry; it self-locates its release root and derives
  the tag from `wf-release.json`. The system command invokes it with an internal `--target`.