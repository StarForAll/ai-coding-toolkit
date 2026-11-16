#!/usr/bin/env python3
"""Author-side single owner for test path resolution, scope markers and managed layout.

Why this module exists: the runner creates results, fixtures, caches, locks, pycache,
candidate/test-release trees and their sidecars.  Every one of those writes must be
decided by *one* rule before the first byte is written, otherwise a later entry point
(shell stage, independent CLI, worker) can silently escape an owned test scope.

Contracts:

- **Canonical resolution**: the raw path is made absolute against the real cwd, then a
  single component walk resolves `.`/`..`, every *existing* ancestor symlink and any
  not-yet-existing tail.  The result never depends on whether the final target exists.
  A broken symlink component or an unresolvable ancestor is refused with a reason.
- **Containment**: scope membership is decided on path components (`path == scope` or
  `scope` is a parent of `path`), never on string prefixes.  Similar prefixes, file
  parents and paths that resolve through symlinks out of the scope are refused.
- **Scope marker**: the marker/owner/root/uid tuple is validated here; `fixture_scope`
  delegates to this module so there is no second marker implementation.
- **Managed layout**: with a scope active every unset managed path derives from the
  scope, and an explicitly supplied out-of-scope path is refused *before* mkdir/open/
  lock/pyc-prune.  Without a scope the legacy defaults are unchanged.
- **No reverse import**: this module must stay importable from author-side scripts
  outside the runner; it never imports the runner (`fixture_scope`, `plan`, ...).

CLI (used by the shell entry points and by independent low-level CLIs):

    wf_test_paths.py layout --kind run|repro [--pid N] [--mode MODE]
    wf_test_paths.py check-scope <path> [<path> ...]
    wf_test_paths.py create-scope [--parent DIR]
    wf_test_paths.py show-scope

`layout` prints shell assignments for the resolved values (`LAYOUT_RESULTS_DIR`, ...);
it performs no write, so list/dry-run plans stay provably zero-write.
"""
from __future__ import annotations

import argparse
import json
import os
import shlex
import sys
import tempfile
from pathlib import Path
from typing import Iterable

SCOPE_OWNER = 'wf-runner-test-scope-v1'
SCOPE_MARKER = '.wf-scope.json'
PRODUCTION_RESULTS_LOCK = '/tmp/wf-test-results-%d.lock' % os.getuid()
DEFAULT_RESULTS_CACHE = Path.home() / '.cache' / 'wf-test-run'
DEFAULT_TEST_RELEASE_CACHE = Path.home() / '.cache' / 'wf-test-release'
DEFAULT_CANDIDATE_CACHE = Path.home() / '.cache' / 'wf-candidate-repo'
ENV_SCOPE = 'WF_TEST_SCOPE_ROOT'


class PathError(Exception):
    """可预期的路径/作用域拒绝（调用方据此非零退出，不 fallback）。"""


def canonical(path) -> Path:
    """Resolve a path deterministically without following a non-existent tail.

    Symlinks are resolved for components that currently exist; `..` is applied to the
    *resolved* prefix, so `scope/../outside` is judged by where it really lands.  A
    dangling symlink component is refused instead of being treated as a literal name.
    """
    if path is None:
        raise PathError('path is required')
    raw = os.fspath(path)
    if not raw:
        raise PathError('path is empty')
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = Path.cwd() / candidate
    current = Path(candidate.anchor or os.sep)
    for component in candidate.parts[1:]:
        if component in ('', '.'):
            continue
        if component == '..':
            current = current.parent
            continue
        nxt = current / component
        if os.path.islink(nxt):
            if not os.path.exists(nxt):
                raise PathError(f'path component is a broken symlink: {nxt}')
            current = Path(os.path.realpath(nxt))
        else:
            current = nxt
    return Path(os.path.normpath(str(current)))


def contains(scope, path) -> bool:
    scope_path = canonical(scope)
    target = canonical(path)
    return target == scope_path or scope_path in target.parents


def read_scope(root) -> Path:
    """Validate the owned test scope marker; any mismatch is a hard refusal."""
    given = Path(root)
    if given.is_symlink() or not given.is_dir():
        raise PathError(f'scope root is not a real directory: {given}')
    resolved = canonical(given)
    if str(resolved) != str(given):
        raise PathError(f'scope path contains a symlink: {given}')
    marker = resolved / SCOPE_MARKER
    if marker.is_symlink():
        raise PathError(f'scope marker must not be a symlink: {marker}')
    try:
        record = json.loads(marker.read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        raise PathError(f'scope marker is missing or unreadable: {resolved}') from exc
    expected = {'schema_version': 1, 'owner': SCOPE_OWNER, 'root': str(resolved), 'uid': os.getuid()}
    if record != expected:
        raise PathError(f'scope marker does not describe this root/uid: {resolved}')
    return resolved


def current_scope():
    value = os.environ.get(ENV_SCOPE)
    if not value:
        return None
    return read_scope(value)


def write_scope_marker(root: Path) -> None:
    payload = {'schema_version': 1, 'owner': SCOPE_OWNER, 'root': str(root), 'uid': os.getuid()}
    target = root / SCOPE_MARKER
    temporary = None
    try:
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=root,
                                         prefix='.' + SCOPE_MARKER, delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(payload, stream, sort_keys=True)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(target)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def create_test_scope(parent=None) -> Path:
    """Create an owned temporary scope: canonical absolute path, no symlink, fixed marker."""
    root = Path(tempfile.mkdtemp(prefix='wf-test-scope-', dir=parent))
    if str(root) != str(canonical(root)):
        raise PathError(f'scope path resolved through a symlink: {root}')
    write_scope_marker(root)
    (root / 'locks').mkdir()
    return root


def require_in_scope(*targets, scope=None) -> None:
    """Refuse every managed target that does not resolve inside the active scope.

    A target that merely *looks* like a child (`scope-x` vs `scope`, or `..`/symlink
    components) is refused with the reason instead of being string-matched.
    """
    active = scope if scope is not None else current_scope()
    if active is None:
        return
    scope_path = canonical(active)
    for target in targets:
        if not target:
            continue
        resolved = canonical(target)
        if resolved == scope_path or scope_path in resolved.parents:
            continue
        raise PathError(f'runner-managed path escapes the test scope: {target} -> {resolved}'
                        f' (scope {scope_path})')


def default_layout(scope, kind='run', pid=None, mode=None) -> dict:
    """Managed path defaults for an active scope (pure derivation, no writes)."""
    scope_path = canonical(scope)
    pid = os.getpid() if pid is None else int(pid)
    if kind == 'run':
        results = scope_path / f'run-{pid}'
        fixture = scope_path / 'fixtures' / f'run-{pid}'
    elif kind == 'repro':
        results = scope_path / f'repro-{mode or "both"}-{pid}'
        fixture = scope_path / 'fixtures' / f'repro-{mode or "both"}-{pid}'
    else:
        raise PathError(f'unknown layout kind: {kind!r}')
    results_cache = scope_path / 'cache'
    return {
        'results_dir': results,
        'fixture': fixture,
        'legacy_fixture': Path(str(fixture) + '.legacy'),
        'results_cache': results_cache,
        'state': scope_path / 'state',
        'locks': scope_path / 'locks',
        'template': results_cache / 'template',
        'test_release': scope_path / 'test-release',
        'candidate': scope_path / 'candidate',
        'pycache': results / 'pycache',
        'pycache_bootstrap': scope_path / 'pycache-bootstrap',
        'repro_state': scope_path / 'state' / 'repro-state.json',
        'plan_log': results / 'plan-calls',
    }


def production_layout(kind='run', pid=None, mode=None) -> dict:
    """Legacy defaults used when no scope is active (unchanged behaviour)."""
    pid = os.getpid() if pid is None else int(pid)
    if kind == 'run':
        results = DEFAULT_RESULTS_CACHE / f'run-{pid}'
        fixture = Path(f'/tmp/wf-fixtures/run-{pid}')
    elif kind == 'repro':
        results = DEFAULT_RESULTS_CACHE / f'repro-{mode or "both"}-{pid}'
        fixture = Path(f'/tmp/wf-fixtures/repro-{mode or "both"}-{pid}')
    else:
        raise PathError(f'unknown layout kind: {kind!r}')
    results_cache = DEFAULT_RESULTS_CACHE
    return {
        'results_dir': results,
        'fixture': fixture,
        'legacy_fixture': Path(str(fixture) + '.legacy'),
        'results_cache': results_cache,
        'state': DEFAULT_RESULTS_CACHE / 'state',
        'locks': Path('/tmp'),
        'template': results_cache / 'template',
        'test_release': DEFAULT_TEST_RELEASE_CACHE,
        'candidate': DEFAULT_CANDIDATE_CACHE,
        'pycache': results / 'pycache',
        'pycache_bootstrap': Path(tempfile.gettempdir()) / 'wf-pycache-bootstrap',
        'repro_state': DEFAULT_RESULTS_CACHE / 'repro-state.json',
        'plan_log': results / 'plan-calls',
    }


def resolve_layout(kind='run', pid=None, mode=None, env=None) -> dict:
    """Final managed layout: explicit env values win, everything else derives.

    Every resolved value is scope-checked *before* any caller writes (mkdir, open,
    lock, pyc).  Explicit out-of-scope values are refused here, not later.
    """
    env = os.environ if env is None else env
    scope = None
    value = env.get(ENV_SCOPE)
    if value:
        scope = read_scope(value)
        layout = default_layout(scope, kind, pid, mode)
    else:
        layout = production_layout(kind, pid, mode)
    overrides = {
        'results_dir': env.get('WF_RESULTS_DIR'),
        'fixture': env.get('WF_FIX'),
        'results_cache': env.get('WF_RESULTS_CACHE'),
        'state': env.get('WF_TEST_RUN_CACHE'),
        'test_release': env.get('WF_TEST_RELEASE_CACHE'),
        'candidate': env.get('WF_CANDIDATE_CACHE'),
        'pycache': env.get('WF_PYCACHE'),
    }
    for key, explicit in overrides.items():
        if not explicit:
            continue
        path = Path(explicit)
        layout[key] = canonical(path)
    if scope is not None:
        require_in_scope(*[layout[key] for key in overrides if layout[key]],
                         layout['results_dir'], layout['fixture'],
                         layout['legacy_fixture'], scope=scope)
        # 派生值也必须落在 scope 内（默认值不得自己越界）。
        require_in_scope(*[layout[key] for key in layout if key not in ('repro_state',)],
                         scope=scope)
    return layout


def shell_assignments(layout: dict) -> str:
    names = {
        'results_dir': 'LAYOUT_RESULTS_DIR',
        'fixture': 'LAYOUT_FIX',
        'legacy_fixture': 'LAYOUT_LEGACY_FIX',
        'results_cache': 'LAYOUT_RESULTS_CACHE',
        'state': 'LAYOUT_STATE',
        'locks': 'LAYOUT_LOCKS',
        'template': 'LAYOUT_TEMPLATE_CACHE',
        'test_release': 'LAYOUT_TEST_RELEASE_CACHE',
        'candidate': 'LAYOUT_CANDIDATE_CACHE',
        'pycache': 'LAYOUT_PYCACHE',
        'pycache_bootstrap': 'LAYOUT_PYCACHE_BOOTSTRAP',
        'repro_state': 'LAYOUT_REPRO_STATE',
        'plan_log': 'LAYOUT_PLAN_LOG',
    }
    lines = [f'{name}=' + shlex.quote(str(layout[key])) for key, name in names.items()]
    lines.append('LAYOUT_OK=1')
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='operation', required=True)
    layout = sub.add_parser('layout')
    layout.add_argument('--kind', choices=('run', 'repro'), default='run')
    layout.add_argument('--pid', type=int, default=None)
    layout.add_argument('--mode', default=None)
    layout.add_argument('--format', default='sh', choices=('sh', 'json'))
    scope = sub.add_parser('check-scope')
    scope.add_argument('paths', nargs='+')
    create = sub.add_parser('create-scope')
    create.add_argument('--parent', default=None)
    sub.add_parser('show-scope')
    args = parser.parse_args(argv)
    try:
        if args.operation == 'layout':
            resolved = resolve_layout(args.kind, args.pid, args.mode)
            if args.format == 'json':
                print(json.dumps({key: str(value) for key, value in resolved.items()},
                                 ensure_ascii=False, indent=2, sort_keys=True))
            else:
                print(shell_assignments(resolved))
            return 0
        if args.operation == 'check-scope':
            require_in_scope(*args.paths)
            return 0
        if args.operation == 'create-scope':
            print(create_test_scope(args.parent))
            return 0
        scope_root = current_scope()
        print(scope_root if scope_root else '-')
        return 0
    except (PathError, OSError, ValueError) as exc:
        print(f'PATH-REFUSED: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
