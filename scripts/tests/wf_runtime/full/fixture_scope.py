#!/usr/bin/env python3
"""Own fixture directories before rebuilding; serialize legacy shared paths."""
from __future__ import annotations

import argparse
import fcntl
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

REPO = Path(__file__).resolve().parents[4]
OWNER = 'wf-test-fixture-v1'


class FixtureError(Exception):
    """Refused a fixture operation before touching its contents."""


def validate(root, forbidden=()):
    root = Path(root).absolute()
    if root != root.resolve():
        raise FixtureError(f'fixture path contains a symlink: {root}')
    temp = Path(tempfile.gettempdir()).resolve()
    if root == temp / 'wf-fixtures':
        raise FixtureError(f'fixture root must not replace the shared fixture hub: {root}')
    caches = (Path.home() / '.cache' / 'wf-test-run',
              Path.home() / '.cache' / 'wf-fixtures')
    if not (temp in root.parents or any(cache in root.parents for cache in caches)):
        raise FixtureError(f'fixture must be a child of temporary storage: {root}')
    for other in (REPO, Path.home(), *map(Path, forbidden)):
        other = other.resolve()
        if root == other or root in other.parents or (other != Path.home() and other in root.parents):
            raise FixtureError(f'fixture overlaps protected path: {root} / {other}')
    return root


def marker(root):
    return root.parent / ('.' + root.name + '.wf-owner.json')


def results_marker(root):
    return root / '.wf-results-owner.json'


def write_marker(path, payload):
    if path.is_symlink():
        raise FixtureError(f'ownership marker must not be a symlink: {path}')
    temporary = None
    try:
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent,
                                         prefix='.' + path.name, delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(payload, stream, sort_keys=True)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def claim_results(root):
    root = validate(root)
    root.parent.mkdir(parents=True, exist_ok=True)
    owner = results_marker(root)
    if root.is_symlink() or (root.exists() and not root.is_dir()):
        raise FixtureError(f'results path must be a real directory: {root}')
    if root.exists():
        try:
            record = json.loads(owner.read_text())
        except (OSError, ValueError):
            record = {}
        if any(root.iterdir()) and record != {'owner': OWNER, 'root': str(root)}:
            raise FixtureError(f'unowned nonempty results directory: {root}; choose a new temporary directory')
    else:
        root.mkdir()
    write_marker(owner, {'owner': OWNER, 'root': str(root)})
    return root


def prepare_results(root):
    root = claim_results(root)
    for path in root.iterdir():
        if path.name == 'logs':
            if path.is_symlink() or not path.is_dir():
                raise FixtureError(f'results log path must be a real directory: {path}')
            shutil.rmtree(path)
        elif path.is_dir() and marker(path).is_file():
            remove(path)
        elif path.is_file() and path.name.startswith('.') and path.name.endswith('.wf-owner.json'):
            owned_root = root / path.name[1:-len('.wf-owner.json')]
            if not owned_root.exists():
                path.unlink()
        elif (path.is_file() or path.is_symlink()) and path.name not in ('.wf-results-owner.json', '.runner.log', '.runner.json') and (
                path.name == 'plan.json' or path.suffix in ('.json', '.out', '.log', '.timing')
                or path.name in ('selection.tsv', 'lines', 'plan.err')):
            path.unlink()
    (root / 'logs').mkdir(exist_ok=True)
    return root


def reset(root, forbidden=()):
    root = validate(root, forbidden)
    owner = marker(root)
    if owner.is_symlink():
        raise FixtureError(f'ownership marker must not be a symlink: {owner}')
    if root.exists():
        if not root.is_dir():
            raise FixtureError(f'fixture is not a directory: {root}')
        try:
            record = json.loads(owner.read_text())
        except (OSError, ValueError):
            record = {}
        if any(root.iterdir()) and record != {'owner': OWNER, 'root': str(root)}:
            raise FixtureError(f'unowned nonempty fixture: {root}; choose a new temporary directory')
        shutil.rmtree(root)
    root.mkdir(parents=True)
    write_marker(owner, {'owner': OWNER, 'root': str(root)})
    return root


def remove(root, forbidden=()):
    root = validate(root, forbidden)
    owner = marker(root)
    if owner.is_symlink():
        raise FixtureError(f'ownership marker must not be a symlink: {owner}')
    if not root.exists():
        try:
            record = json.loads(owner.read_text())
        except (OSError, ValueError):
            return False
        if record == {'owner': OWNER, 'root': str(root)}:
            owner.unlink()
        return False
    try:
        record = json.loads(owner.read_text())
    except (OSError, ValueError) as exc:
        raise FixtureError(f'refusing to remove an unowned fixture: {root}') from exc
    if record != {'owner': OWNER, 'root': str(root)}:
        raise FixtureError(f'refusing to remove an unowned fixture: {root}')
    shutil.rmtree(root)
    owner.unlink(missing_ok=True)
    return True


def clone(source, target):
    source = Path(source).resolve()
    target = reset(target, forbidden=[source])
    shutil.copytree(source, target, dirs_exist_ok=True, symlinks=True)
    return target


def verify_lease():
    """Prove an ancestor still holds the inherited kernel flock, across mount namespaces."""
    try:
        pid = int(os.environ['WF_FIXTURE_LEASE_PID'])
        fd = int(os.environ['WF_FIXTURE_LEASE_FD'])
        current = os.getpid()
        while current not in (pid, 0, 1):
            status = Path(f'/proc/{current}/status').read_text()
            current = int(next(line.split()[1] for line in status.splitlines() if line.startswith('PPid:')))
        if current != pid:
            raise ValueError('lease owner is not an ancestor')
        target = Path(os.readlink(f'/proc/{pid}/fd/{fd}'))
        if target.parent != Path('/tmp') or not target.name.startswith('wf-test-fixtures-') or target.suffix != '.lock':
            raise ValueError('unexpected lease descriptor')
        info = Path(f'/proc/{pid}/fdinfo/{fd}').read_text()
        locks = [line for line in info.splitlines() if line.startswith('lock:')]
        if not any('FLOCK' in line and 'WRITE' in line and f' {pid} ' in line for line in locks):
            raise ValueError('fixture flock is not held by the declared ancestor')
        return True
    except (KeyError, ValueError, OSError, StopIteration) as exc:
        raise FixtureError(f'invalid inherited fixture lease: {exc}') from exc


def lock_run(command):
    """A child inherits the lease descriptor, so nested harnesses cannot deadlock."""
    inherited = os.environ.get('WF_FIXTURE_LEASE_FD')
    if inherited:
        verify_lease()
    else:
        lock_path = Path('/tmp') / f'wf-test-fixtures-{os.getuid()}.lock'
        fd = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            os.close(fd)
            raise FixtureError('another wf harness owns the shared fixture lease') from exc
        os.environ['WF_FIXTURE_LEASE_FD'] = str(fd)
        os.environ['WF_FIXTURE_LEASE_PID'] = str(os.getpid())
        os.set_inheritable(fd, True)
    os.execvp(command[0], command)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='operation', required=True)
    for name in ('reset', 'remove', 'validate'):
        p = sub.add_parser(name)
        p.add_argument('root')
        p.add_argument('--forbid', action='append', default=[])
    p = sub.add_parser('clone')
    p.add_argument('source')
    p.add_argument('target')
    p = sub.add_parser('claim-results')
    p.add_argument('root')
    p = sub.add_parser('prepare-results')
    p.add_argument('root')
    p = sub.add_parser('lease')
    p.add_argument('command', nargs=argparse.REMAINDER)
    sub.add_parser('check-lease')
    args = parser.parse_args(argv)
    try:
        if args.operation == 'lease':
            command = args.command[1:] if args.command[:1] == ['--'] else args.command
            if not command:
                raise FixtureError('lease command is required')
            lock_run(command)
        elif args.operation == 'check-lease':
            verify_lease()
        elif not os.environ.get('WF_FIXTURE_LEASE_FD'):
            lock_run([sys.executable, __file__, *sys.argv[1:]])
        else:
            verify_lease()
            if args.operation == 'clone':
                clone(args.source, args.target)
            elif args.operation == 'claim-results':
                claim_results(args.root)
            elif args.operation == 'prepare-results':
                prepare_results(args.root)
            else:
                {'reset': reset, 'remove': remove, 'validate': validate}[args.operation](args.root, args.forbid)
        return 0
    except (FixtureError, OSError) as exc:
        print(f'FIXTURE-REFUSED: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
