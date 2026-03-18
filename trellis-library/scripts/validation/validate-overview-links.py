#!/usr/bin/env python3
"""
Overview link checker for trellis-library framework specs.

Scans all framework overview.md files and their referenced sub-files for broken
relative links. This is a targeted check for entry-point documents that are
most likely to accumulate link regressions.

Usage:
    python3 validate-overview-links.py [root] [--json]
    python3 validate-overview-links.py trellis-library/specs --json

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
    link_pattern = re.compile(r'\[([^\]]+)\]\(([^\)]+)\)')
    links = []
    for i, line in enumerate(content.splitlines(), start=1):
        for match in link_pattern.finditer(line):
            href = match.group(2)
            links.append((i, href))
    return links


def check_link(href: str, base_dir: pathlib.Path, file_path: pathlib.Path) -> BrokenLink | None:
    """Return BrokenLink if href is broken, None if valid."""
    if href.startswith(('http://', 'https://', 'mailto:', 'tel:')):
        return None
    if href.startswith('#'):
        return None
    try:
        href_clean = href.split('#')[0]
        if not href_clean:
            return None
        target = (file_path.parent / href_clean).resolve()
        root = base_dir.resolve()
        try:
            target.relative_to(root)
        except ValueError:
            return BrokenLink(str(file_path), -1, href, str(target), "Path escapes root")
        if not target.exists():
            return BrokenLink(str(file_path), -1, href, str(target), "File not found")
        return None
    except Exception as e:
        return BrokenLink(str(file_path), -1, href, "", str(e))


def validate_overview(overview_path: pathlib.Path, root: pathlib.Path) -> list[BrokenLink]:
    """Validate all links in a single overview.md and its referenced sub-files."""
    broken: list[BrokenLink] = []
    visited: set[pathlib.Path] = set()

    def check_file(path: pathlib.Path, depth: int = 0):
        if depth > 3 or path in visited:
            return
        visited.add(path)
        try:
            content = path.read_text(encoding='utf-8')
        except Exception:
            return
        for line_num, href in extract_links(content):
            # Only follow relative links that look like .md files
            if href.startswith('.') and not href.startswith('..'):
                sub_path = (path.parent / href).resolve()
                check_file(sub_path, depth + 1)
            elif not href.startswith('..'):
                result = check_link(href, root, path)
                if result:
                    bl = BrokenLink(result[0], line_num, result[2], result[3], result[4])
                    broken.append(bl)
            else:
                result = check_link(href, root, path)
                if result:
                    bl = BrokenLink(result[0], line_num, result[2], result[3], result[4])
                    broken.append(bl)

    check_file(overview_path)
    return broken


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Validate links in framework overview.md files and their sub-files"
    )
    parser.add_argument(
        'root',
        nargs='?',
        default='trellis-library/specs',
        help="Root specs directory (default: trellis-library/specs)"
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

    # Find all framework overview.md files
    # Use specs/ as root so cross-directory links (../../../scenarios/) resolve correctly
    specs_dir = root / 'technologies' / 'frameworks'
    overview_files = list(specs_dir.glob('*/overview.md'))

    all_broken: list[dict] = []
    total_files = 0

    for overview in sorted(overview_files):
        framework_name = overview.parent.name
        broken = validate_overview(overview, root)
        total_files += 1
        for b in broken:
            all_broken.append({
                "framework": framework_name,
                "file": b.file,
                "line": b.line,
                "link": b.link,
                "resolved": b.resolved,
                "reason": b.reason,
            })

    if not all_broken:
        if args.json:
            import json
            print(json.dumps({
                "status": "ok",
                "overviews_checked": total_files,
                "broken": []
            }))
        else:
            names = [f.parent.name for f in overview_files]
            print(f"✅ All links valid ({total_files} overview(s): {', '.join(names)})")
        sys.exit(0)

    if args.json:
        import json
        print(json.dumps({
            "status": "broken",
            "overviews_checked": total_files,
            "broken": all_broken
        }, indent=2))
    else:
        print(f"❌ {len(all_broken)} broken link(s) in {total_files} overview(s):\n")
        for b in all_broken:
            rel = pathlib.Path(b['file']).relative_to(root)
            print(f"  [{b['framework']}] {rel}:{b['line']}")
            print(f"    Link: {b['link']}")
            print(f"    Reason: {b['reason']}")
            print()
    sys.exit(1)


if __name__ == '__main__':
    main()
