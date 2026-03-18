#!/usr/bin/env python3
"""
Unified CLI entry point for trellis-library maintenance workflows.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


SCRIPT_MAP = {
    "validate": "scripts/validation/validate-library-sync.py",
    "assemble": "scripts/assembly/assemble-init-set.py",
}

SYNC_MODE_MAP = {
    "downstream": "scripts/sync/sync-library-assets.py",
    "diff": "scripts/sync/diff-library-assets.py",
    "propose": "scripts/sync/propose-library-sync.py",
    "apply": "scripts/sync/apply-library-sync.py",
}


def print_main_help() -> None:
    print(
        "\n".join(
            [
                "Usage: cli.py <command> [options]",
                "",
                "Unified entry point for trellis-library workflows.",
                "",
                "Commands:",
                "  validate   Run trellis-library validation checks",
                "  assemble   Assemble selected assets into a target project",
                "  sync       Run downstream or upstream sync workflows",
                "",
                "Examples:",
                "  /ops/softwares/python/bin/python3 trellis-library/cli.py validate --strict-warnings",
                "  /ops/softwares/python/bin/python3 trellis-library/cli.py assemble --target /tmp/project --pack pack.go-service-foundation --dry-run",
                "  /ops/softwares/python/bin/python3 trellis-library/cli.py sync --mode downstream --target /tmp/project --dry-run",
                "",
                "Use `cli.py sync --help` to see sync modes.",
            ]
        )
    )


def print_sync_help() -> None:
    print(
        "\n".join(
            [
                "Usage: cli.py sync --mode <downstream|diff|propose|apply> [options]",
                "",
                "Sync modes:",
                "  downstream  Run downstream sync into a target project",
                "  diff        Compare target-project assets against trellis-library",
                "  propose     Generate an upstream contribution proposal",
                "  apply       Apply an approved upstream contribution proposal",
                "",
                "Examples:",
                "  /ops/softwares/python/bin/python3 trellis-library/cli.py sync --mode downstream --target /tmp/project --dry-run",
                "  /ops/softwares/python/bin/python3 trellis-library/cli.py sync --mode diff --target /tmp/project --only-modified",
                "  /ops/softwares/python/bin/python3 trellis-library/cli.py sync --mode propose --target /tmp/project --asset spec.example --scope asset",
                "  /ops/softwares/python/bin/python3 trellis-library/cli.py sync --mode apply --proposal proposal.yaml --patch change.patch",
            ]
        )
    )


def extract_sync_mode(args: list[str]) -> tuple[str | None, list[str]]:
    if not args:
        return None, []

    remaining = list(args)
    if remaining[0] in {"-h", "--help"}:
        return None, remaining

    if "--mode" in remaining:
        index = remaining.index("--mode")
        if index + 1 >= len(remaining):
            raise SystemExit("Missing value for --mode")
        mode = remaining[index + 1]
        del remaining[index : index + 2]
        return mode, remaining

    return None, remaining


def run_script(script_rel_path: str, forwarded_args: list[str]) -> int:
    library_root = Path(__file__).resolve().parent
    script_path = library_root / script_rel_path
    result = subprocess.run([sys.executable, str(script_path), *forwarded_args], check=False)
    return result.returncode


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in {"-h", "--help"}:
        print_main_help()
        return 0

    command = args[0]
    forwarded_args = args[1:]

    if command in SCRIPT_MAP:
        return run_script(SCRIPT_MAP[command], forwarded_args)

    if command == "sync":
        mode, sync_args = extract_sync_mode(forwarded_args)
        if forwarded_args and forwarded_args[0] in {"-h", "--help"}:
            print_sync_help()
            return 0
        if mode is None:
            raise SystemExit("sync requires --mode <downstream|diff|propose|apply>")
        script_rel_path = SYNC_MODE_MAP.get(mode)
        if script_rel_path is None:
            valid_modes = ", ".join(sorted(SYNC_MODE_MAP))
            raise SystemExit(f"Unknown sync mode: {mode}. Expected one of: {valid_modes}")
        return run_script(script_rel_path, sync_args)

    raise SystemExit(f"Unknown command: {command}")


if __name__ == "__main__":
    raise SystemExit(main())
