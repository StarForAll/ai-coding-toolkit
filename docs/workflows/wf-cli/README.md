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

The attach script uploads both the wheel and `install.py`; `FORGEJO_TOKEN` is read from the
environment. It treats a same-size asset as already attached and refuses a same-name asset with a
different size instead of overwriting it.

The wheel and the release manifest must have the same version; `scripts/build-wf-cli-wheel.py`
checks that and the `verify-wf-release.py` gate checks the CLI package inside the tag. Pushing a
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

## Upgrade the system command (distinct from project upgrade)

```bash
wf self-upgrade          # newest system release; no version argument
wf self-upgrade --json
```

`wf self-upgrade` upgrades the **system-level command itself**. It is separate from `wf upgrade`,
which upgrades the wf assets inside the current project. It downloads the same release wheel when
present and falls back to building the command from the selected release tag if the asset is
missing. Use `--manager uv|pipx|pip` only when automatic detection fails.

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