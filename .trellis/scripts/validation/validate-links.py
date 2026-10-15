#!/usr/bin/env python3
"""
Link validator for trellis-library markdown files.

Scans all .md files under a given root directory, extracts relative links,
resolves them against each file's directory, and reports broken links.

Usage:
    python3 validate-links.py [root_dir] [--json]
    python3 validate-links.py trellis-library/specs --json

Exit codes:
    0 = all links valid
    1 = one or more broken links found
"""

import pathlib
import re
import sys
from typing import NamedTuple


class BrokenLink(NamedTuple):
    file: str
    line: int
    link: str
    resolved: str
    reason: str


def extract_links(content: str) -> list[tuple[int, str]]:
    """Extract (line_number, link_target) pairs from markdown content."""
    # Match markdown links: [text](url)
    link_pattern = re.compile(r'\[([^\]]+)\]\(([^\)]+)\)')
    links = []
    for i, line in enumerate(content.splitlines(), start=1):
        for match in link_pattern.finditer(line):
            href = match.group(2)
            links.append((i, href))
    return links


def is_broken(href: str, base_dir: pathlib.Path, file_path: pathlib.Path) -> BrokenLink | None:
    """
    Check if a relative href is broken.
    Returns a BrokenLink if broken, None if valid.
    """
    # Only check relative links (not URLs, not anchors)
    if href.startswith(('http://', 'https://', 'mailto:', 'tel:')):
        return None
    if href.startswith('#'):
        return None

    # Anchor-only links like "#section"
    if href.startswith('#'):
        return None

    # Resolve relative to the markdown file's directory
    try:
        # Remove any anchor from href
        href_clean = href.split('#')[0]
        if not href_clean:
            return None

        target = (file_path.parent / href_clean).resolve()

        # Don't follow outside of root
        root = (base_dir / '..').resolve()
        try:
            target.relative_to(root)
        except ValueError:
            return BrokenLink(
                file=str(file_path),
                line=-1,
                link=href,
                resolved=str(target),
                reason="Path escapes root directory"
            )
            return None

        if not target.exists():
            return BrokenLink(
                file=str(file_path),
                line=-1,
                link=href,
                resolved=str(target),
                reason="File not found"
            )
        return None
    except Exception as e:
        return BrokenLink(
            file=str(file_path),
            line=-1,
            link=href,
            resolved="",
            reason=str(e)
        )


def validate_dir(root: pathlib.Path, json_output: bool = False) -> int:
    """Validate all markdown files in root directory."""
    md_files = list(root.rglob('*.md'))
    broken: list[BrokenLink] = []

    for md_file in sorted(md_files):
        try:
            content = md_file.read_text(encoding='utf-8')
        except Exception as e:
            broken.append(BrokenLink(str(md_file), 0, "", "", f"Cannot read: {e}"))
            continue

        links = extract_links(content)
        for line_num, href in links:
            result = is_broken(href, root, md_file)
            if result:
                # Inject line number from links list
                bl = BrokenLink(result.file, line_num, result.link, result.resolved, result.reason)
                broken.append(bl)

    if not broken:
        if json_output:
            import json
            print(json.dumps({"status": "ok", "files_checked": len(md_files), "broken": []}))
        else:
            print(f"✅ All links valid ({len(md_files)} files checked)")
        return 0

    if json_output:
        import json
        print(json.dumps({
            "status": "broken",
            "files_checked": len(md_files),
            "broken": [
                {
                    "file": b.file,
                    "line": b.line,
                    "link": b.link,
                    "resolved": b.resolved,
                    "reason": b.reason,
                }
                for b in broken
            ]
        }, indent=2))
    else:
        print(f"❌ {len(broken)} broken link(s) found in {len(md_files)} files:\n")
        for b in broken:
            print(f"  {b.file}:{b.line}")
            print(f"    Link: {b.link}")
            print(f"    Resolved: {b.resolved}")
            print(f"    Reason: {b.reason}")
            print()

    return 1


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Validate relative links in markdown files")
    default_root = 'trellis-library/specs'
    parser.add_argument(
        'root',
        nargs='?',
        default=default_root,
        help=f"Root directory to scan (default: {default_root})"
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help="Output results as JSON"
    )
    args = parser.parse_args()

    root = pathlib.Path(args.root).resolve()
    if not root.exists():
        print(f"Error: Directory not found: {root}", file=sys.stderr)
        sys.exit(1)

    exit_code = validate_dir(root, json_output=args.json)
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
