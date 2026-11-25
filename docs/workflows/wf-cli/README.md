# wf command

`docs/workflows/wf-cli/` is the **system-level distribution package** for the `wf` workflow.
It is not part of the target-project release assets (`docs/workflows/wf-release/`): it installs
only the `wf` command into the user's Python tool environment; the command then resolves,
verifies and runs the matching release from the registered Forgejo repository.

## Install the command (no version parameter)

```bash
curl -fsSL "https://forgejo.xzc.com/xzc/ai-coding-toolkit/releases/download/latest/install.py" | python3 -
wf version
```

The install command itself is the stable `install.py` asset of the **latest Forgejo release**
(`releases/download/latest/install.py`); it asks the release API for that release, requires the
`wf_cli-<version>-py3-none-any.whl` asset, and installs it with `uv` (or `pipx`). It never
accepts a version or tag: the newest release is selected automatically. For a private repository,
set `FORGEJO_TOKEN` in the environment; the token is read from the environment and sent only in the
HTTP header, never passed as an argument. For a private repository the raw-script fetch itself
may also need your HTTP credentials; that credential is not part of the install command.

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
newer working tree to an old tag; bump the version and create a new tag instead. Pushing a
`wf-v*` tag also runs `.forgejo/workflows/wf-release.yml`, which verifies the tag and attaches the
wheel plus `install.py` to the Forgejo release automatically. The workflow uses `runs-on: docker`;
replace that label if your Forgejo runner uses another label.

## Forgejo token

The tag-push workflow uses Forgejo's automatic per-workflow token; for a non-PR workflow it has
write permission to the repository, so no secret is required. If you use a token locally or in a
workflow that needs an explicit secret:

1. In Forgejo open **Settings → Applications → Generate New Token**.
2. Give it a name such as `wf-release` and scopes `read:repository` plus `write:repository`.
3. Copy the value once into a password manager or environment variable; it cannot be shown again.
4. Locally: `export FORGEJO_TOKEN="..."` (the scripts read the environment, never an argument).
5. In CI: repository **Settings → Actions → Secrets → New secret** `FORGEJO_TOKEN`, then pass it as
   the `token` input only if you are not using the automatic token.

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

If only SSH is reachable and Actions/HTTP are unavailable from this machine:

```bash
bash scripts/install-wf-ssh.sh
```

It clones the registered repository over SSH, resolves the newest `wf-v*` tag by creation date,
and installs that tag with uv/pipx; it takes no version argument. Release upload and release-asset
installation still need the HTTP endpoint (web UI or a machine that can reach it). SSH alone
cannot create or attach Forgejo release assets, and Forgejo Actions must be enabled for a tag push
to build a release automatically.


## Upgrade the system command (distinct from project upgrade)

```bash
wf self-upgrade          # newest system release; no version argument
wf self-upgrade --json
```

`wf self-upgrade` upgrades the **system-level command itself**. It is separate from `wf upgrade`,
which upgrades the wf assets inside the current project. It downloads the same release wheel when
present and falls back to building the command from the selected release tag if the asset is
missing. Use `--manager uv|pipx|pip` only when automatic detection fails.

To remove the system command itself (not a project install):

```bash
wf self-uninstall          # preview only
wf self-uninstall --apply  # remove the installed wf-cli tool
```

The preview prints the exact `uv tool uninstall wf-cli` / `pipx uninstall wf-cli` command. Project
removal remains `wf uninstall` inside the project and is a different operation.

## Git hook / push wrapper

A pre-push hook can verify the tag and build the wheel locally, but it **cannot** attach release
assets: at pre-push time the tag does not exist on the Forgejo remote yet, and git has no
post-push hook. Use the wrapper for the complete sequence:

```bash
export WF_FORGEJO_BASE="https://forgejo.xzc.com:13785"
export FORGEJO_TOKEN="..."
scripts/push-wf-tag.sh wf-v0.0.8 backup
```

- `.git/hooks/pre-push` / `scripts/git-hooks/pre-push` verifies the release and builds
  `tmp/wf-cli-dist/` before the push;
- the wrapper pushes the tag, then creates the release and attaches the wheel plus `install.py`;
- if attachment fails, the wrapper reports the exact retry command. The tag is already pushed, so
  do not recreate it.

A direct `git push backup wf-v0.0.8` runs the build/verify hook but leaves the release attachment
for the post-push command printed by the hook.

## Use it in a project

```bash
# in a project that has no .wf/ yet
wf install          # preview of the system command's version
wf install --confirm

# later
wf upgrade          # preview of the newest project release
wf upgrade --apply  # apply after the terminal preview token

wf uninstall        # forwards to the installed independent uninstall entry
wf repair           # forwards to the installed independent repair entry
```

Running `wf` inside a project also forwards ordinary runtime commands to `.wf/bin/wf.py`, so
`task-new`, `task-check`, `spec`, `review-*`, etc. no longer need a project-local path. Use
`wf --project <absolute-path> <command>` outside the project root.

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
- `--release-ref`, `--source`, `--release` and `--target` are retired for users: the release
  identity comes from the system command and the registered source, never from a local checkout.
- `install.py` remains the release-internal entry; it self-locates its release root and derives
  the tag from `wf-release.json`. The system command invokes it with an internal `--target`.