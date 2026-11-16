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
sys.path.insert(0, str(REPO / 'scripts'))
import wf_test_paths  # noqa: E402  （作者侧路径/scope 唯一所有者；本模块只委托）

OWNER = 'wf-test-fixture-v1'
SCOPE_OWNER = wf_test_paths.SCOPE_OWNER
SCOPE_MARKER = wf_test_paths.SCOPE_MARKER
PRODUCTION_RESULTS_LOCK = wf_test_paths.PRODUCTION_RESULTS_LOCK


class FixtureError(wf_test_paths.PathError):
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
        elif (path.is_file() or path.is_symlink()) and path.name not in ('.wf-results-owner.json', '.runner.log') and (
                path.name == 'plan.json' or path.suffix in ('.json', '.out', '.log', '.timing')
                or path.name in ('selection.tsv', 'lines', 'stages', 'plan-calls', 'plan.err')):
            # stages/plan-calls 与 lines 同属"每 run 证据"：复用显式结果目录时必须从本轮重新计数，
            # 否则一次 run 的"4 阶段/2 次计划"会跨轮累积（实测 4→8、2→4）。
            # `.runner.json` 是外层 C 的每 run 控制结果；保留旧值会让下一轮在 C 写回前
            # 失败时把上一轮 cleanup=unknown 误聚合成本轮证据。
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
    except (OSError, ValueError):
        record = None
    if record != {'owner': OWNER, 'root': str(root)}:
        # 空的无主目录可以回收（删除空目录不丢数据，且调用方指定的就是 runner 管理路径）；
        # 非空无主目录仍然拒绝——那是别人的数据。
        try:
            empty = root.is_dir() and not any(root.iterdir())
        except OSError as exc:
            raise FixtureError(f'refusing to remove an unowned fixture: {root}: {exc}') from exc
        if not empty:
            raise FixtureError(f'refusing to remove an unowned fixture: {root}')
        root.rmdir()
        owner.unlink(missing_ok=True)
        return True
    shutil.rmtree(root)
    owner.unlink(missing_ok=True)
    return True


def move(source, target, forbidden=()):
    """Rename an owned fixture and keep its ownership marker consistent.

    Used by the template cache publisher: a directory rename without moving the
    marker would leave the new path unowned (and the old marker stale), which
    would either refuse later cleanup or let an unowned tree be adopted.
    """
    source = validate(source, forbidden)
    target = validate(target, forbidden)
    owner = marker(source)
    if owner.is_symlink():
        raise FixtureError(f'ownership marker must not be a symlink: {owner}')
    if not source.exists():
        raise FixtureError(f'fixture does not exist: {source}')
    try:
        record = json.loads(owner.read_text())
    except (OSError, ValueError) as exc:
        raise FixtureError(f'refusing to move an unowned fixture: {source}') from exc
    # 只要求 marker 是本工具的格式；`root` 允许指向旧路径——缓存根被整体移动/拷贝后，
    # marker 随目录走但记录仍指向旧根，这正是要处理的“搬动后的缓存条目”。`remove` 保持
    # 严格 root 比对（删除数据），`move` 只是改名并重写 marker（不丢数据）。
    if record.get('owner') != OWNER:
        raise FixtureError(f'refusing to move an unowned fixture: {source}')
    if target.exists():
        raise FixtureError(f'move target already exists: {target}')
    os.rename(source, target)
    owner.unlink(missing_ok=True)
    write_marker(marker(target), {'owner': OWNER, 'root': str(target)})
    return target


def clone(source, target):
    source = Path(source).resolve()
    target = reset(target, forbidden=[source])
    shutil.copytree(source, target, dirs_exist_ok=True, symlinks=True)
    return target


DEFAULT_CACHE = Path.home() / '.cache' / 'wf-test-run'
_KEEP_NAMES = {'lines', 'plan.err', 'selection.tsv'}
_KEEP_DIRS = {'logs', 'repro', 'template'}


def _validate_cache_root(root):
    root = Path(root)
    if root != root.resolve():
        raise FixtureError(f'prune root 包含符号链接：{root}')
    resolved = root.resolve()
    temp = Path(tempfile.gettempdir()).resolve()
    if resolved != DEFAULT_CACHE.resolve() and temp not in resolved.parents:
        raise FixtureError(
            f'prune root 必须是标准缓存根（{DEFAULT_CACHE}）或临时目录之下：{root}')
    return root


def _valid_results_owner(directory):
    marker = results_marker(directory)
    try:
        return json.loads(marker.read_text()) == {'owner': OWNER, 'root': str(directory)}
    except (OSError, ValueError):
        return False


def _bootstrap_eligible(directory):
    """无主历史目录的保守判定：顶层内容全部为运行器已知产物（复用 prepare-results
    的文件白名单 + 已知子目录名 logs/repro/template）。子树内容不再逐项审查——
    它们全部是运行器自产副本，整树删除是有意行为（实现注释，见任务 design D5.3）。"""
    try:
        for name in os.listdir(directory):
            if name.endswith(('.json', '.out', '.log', '.timing')) or name in _KEEP_NAMES:
                continue
            if name in _KEEP_DIRS and os.path.isdir(Path(directory) / name):
                continue
            return False, name
    except OSError:
        return False, os.listdir(directory)
    return True, None


def prune_results(root, scope, keep=20, exclude=(), bootstrap=False):
    """回收结果缓存：只删带有效所有权 marker 的目录（marker 校验兜底，宁可留着）。

    - root：标准缓存根（DEFAULT_CACHE）；scope：'run'|'repro' 前缀隔离，run_all 与
      独立 repro 入口互不越界回收对方产物；
    - bootstrap：额外允许删除"无主但顶层内容全部为运行器已知产物"的历史目录
      （一次性存量收敛；无自动调用点，仅手工执行）；
    - liveness 安全前提：全局 flock 只允许一个根运行器持有 lease（lock_run），
      其他运行器无法创建有效 marker，故不存在"删到活目录"的窗口——该前提若被
      破坏，prune 只会漏删不会误删；
    - 单条删除失败跳过并计数，不中断；输出 PRUNED=<n> KEPT=<m>。
    """
    root = _validate_cache_root(root)
    if scope not in ('run', 'repro'):
        raise FixtureError(f'--scope 只接受 run|repro（收到 {scope!r}）')
    if not root.exists():
        # 缓存根尚未建立（冷启动）：没有可回收条目，不是错误，也不创建目录。
        print('PRUNED=0 KEPT=0', file=sys.stderr)
        return 0
    prefix = {'run': 'run-', 'repro': 'repro-'}[scope]
    exclude = {Path(item).absolute() for item in exclude}
    candidates = []
    for entry in root.iterdir():
        if entry.name == 'repro-state.json' or not entry.is_dir() or entry.is_symlink():
            continue
        if not entry.name.startswith(prefix):
            continue
        if entry in exclude:
            continue
        candidates.append(entry)
    owned = [entry for entry in candidates if _valid_results_owner(entry)]
    owned.sort(key=lambda entry: (results_marker(entry).stat().st_mtime), reverse=True)
    pruned = 0
    kept = 0
    for index, entry in enumerate(owned):
        if index < keep:
            kept += 1
            continue
        try:
            shutil.rmtree(entry)
            pruned += 1
        except OSError as exc:
            # marker 校验兜底的 fail-safe：删不掉就留着并报告，不中断后续回收。
            print(f'PRUNE-SKIPPED {entry.name}: {exc}', file=sys.stderr)
            kept += 1
    if bootstrap:
        for entry in candidates:
            if _valid_results_owner(entry) or entry in exclude:
                continue
            eligible, offender = _bootstrap_eligible(entry)
            if not eligible:
                print(f'PRUNE-SKIPPED {entry.name}: 未知顶层内容 {offender!r}', file=sys.stderr)
                continue
            try:
                shutil.rmtree(entry)
                pruned += 1
            except OSError as exc:
                print(f'PRUNE-SKIPPED {entry.name}: {exc}', file=sys.stderr)
    print(f'PRUNED={pruned} KEPT={kept}', file=sys.stderr)
    return 0


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



# ---- 显式测试域（owned scope）------------------------------------------------
# 路径解析、scope marker 与“管理路径必须在 scope 内”的唯一实现都在
# `scripts/wf_test_paths.py`；这里保留同名委托接口（历史调用方/假树契约不变）。


def create_test_scope(parent=None):
    """建立本 UID 拥有的 owned 临时 scope（唯一实现：wf_test_paths.create_test_scope）。"""
    try:
        return wf_test_paths.create_test_scope(parent)
    except wf_test_paths.PathError as exc:
        raise FixtureError(str(exc)) from exc


def read_scope(root):
    """读出并校验 scope marker；损坏/越界一律抛（不 fallback 生产域）。"""
    try:
        return wf_test_paths.read_scope(root)
    except wf_test_paths.PathError as exc:
        raise FixtureError(str(exc)) from exc


def current_scope():
    try:
        return wf_test_paths.current_scope()
    except wf_test_paths.PathError as exc:
        raise FixtureError(str(exc)) from exc


def results_domain():
    """结果锁域：生产用固定 production 字符串，测试域用 scope 的真实路径。"""
    scope = current_scope()
    return 'production' if scope is None else 'scope:' + str(scope)


def results_lock_path():
    scope = current_scope()
    return Path(PRODUCTION_RESULTS_LOCK) if scope is None else scope / 'locks' / f'results-{os.getuid()}.lock'


def ensure_in_scope(*targets):
    """runner 管理写入口必须在 owned scope 内（生产域不做限制）。

    委托 `wf_test_paths.require_in_scope`：按**路径组件**判定，尚不存在的 `..`、
    父链接、相似前缀与坏链都不能借用字符串前缀通过。
    """
    try:
        wf_test_paths.require_in_scope(*targets)
    except wf_test_paths.PathError as exc:
        raise FixtureError(str(exc)) from exc


def _open_results_lock():
    scope = current_scope()
    if scope is not None:
        (scope / 'locks').mkdir(exist_ok=True)
    path = results_lock_path()
    if path.is_symlink():
        raise FixtureError(f'results lock must not be a symlink: {path}')
    fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    stat = os.fstat(fd)
    if not path.is_file() or stat.st_uid != os.getuid():
        os.close(fd)
        raise FixtureError(f'results lock is not a regular file owned by us: {path}')
    return fd, path


def acquire_results_lock():
    """同域独占、非阻塞；竞争明确 busy。返回 fd。"""
    fd, path = _open_results_lock()
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        os.close(fd)
        raise FixtureError(f'results domain is busy: {path}（同域另一个 run/镜像正持有锁）') from exc
    os.environ['WF_RESULTS_LOCK_FD'] = str(fd)
    os.environ['WF_RESULTS_LOCK_PID'] = str(os.getpid())
    os.environ['WF_RESULTS_LOCK_DOMAIN'] = results_domain()
    os.environ['WF_RESULTS_LOCK_MNT'] = os.readlink('/proc/self/ns/mnt')
    os.set_inheritable(fd, True)
    return fd


def verify_results_lock():
    """核继承来的结果锁：祖先、FD target、inode、kernel flock、mount/scope 域。"""
    try:
        pid = int(os.environ['WF_RESULTS_LOCK_PID'])
        fd = int(os.environ['WF_RESULTS_LOCK_FD'])
        domain = os.environ.get('WF_RESULTS_LOCK_DOMAIN') or ''
        if domain == 'production':
            expected = Path(PRODUCTION_RESULTS_LOCK)
        elif domain.startswith('scope:'):
            # 域标记只定位对象：scope 域必须过 marker 校验，且等于当前活动 scope——
            # 否则任何调用方都能用一段路径字符串把结果锁“继承”到别处。
            scope_path = read_scope(Path(domain[len('scope:'):]))
            active = os.environ.get('WF_TEST_SCOPE_ROOT')
            if not active:
                raise ValueError('scope results domain without an active test scope')
            if Path(active).resolve() != scope_path.resolve():
                raise ValueError('scope results domain does not match the active test scope')
            expected = scope_path / 'locks' / f'results-{os.getuid()}.lock'
        else:
            raise ValueError(f'unknown results lock domain: {domain!r}')
        # 继承优先：祖先若是生产域锁，嵌套的测试 scope 也沿用同一把，不再自建第二把。
        if os.readlink(f'/proc/{pid}/fd/{fd}') != str(expected):
            raise ValueError('results descriptor points at another path')
        current_mnt = os.readlink('/proc/self/ns/mnt')
        if os.environ.get('WF_RESULTS_LOCK_MNT') != current_mnt:
            raise ValueError('results lock was taken in another mount namespace')
        if os.readlink(f'/proc/{pid}/ns/mnt') != current_mnt:
            raise ValueError('results lock holder is in another mount namespace')
        handle = os.open(f'/proc/{pid}/fd/{fd}', os.O_RDONLY)
        try:
            held = os.fstat(handle)
        finally:
            os.close(handle)
        current = os.stat(expected)
        if (held.st_dev, held.st_ino) != (current.st_dev, current.st_ino):
            raise ValueError('results descriptor is not the canonical lock inode')
        with open(f'/proc/{pid}/fdinfo/{fd}', encoding='utf-8') as stream:
            info = stream.read()
        if not any('FLOCK' in line and 'WRITE' in line and f' {pid} ' in line
                   for line in info.splitlines() if line.startswith('lock:')):
            raise ValueError('results flock is not held by the declared ancestor')
        current_pid = os.getpid()
        while current_pid not in (pid, 0, 1):
            with open(f'/proc/{current_pid}/status', encoding='utf-8') as stream:
                status = stream.read()
            current_pid = int(next(line.split()[1] for line in status.splitlines()
                                   if line.startswith('PPid:')))
        if current_pid != pid:
            raise ValueError('results lock owner is not an ancestor')
        return True
    except (KeyError, ValueError, OSError, StopIteration) as exc:
        raise FixtureError(f'invalid inherited results lock: {exc}') from exc


def _lease_fixture():
    inherited = os.environ.get('WF_FIXTURE_LEASE_FD')
    if inherited:
        verify_lease()
        return
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


def _unit_scope_ok():
    if os.environ.get('WF_UNIT_DOMAIN') != 'unit':
        return True
    try:
        return current_scope() is not None
    except FixtureError:
        return False


def lease_domain(command):
    """只取 results 域锁（plan 镜像：不申请 fixture，不反向锁序）。"""
    if not _unit_scope_ok():
        raise FixtureError(
            'unit domain: 没有继承宿主结果锁也没有 owned test scope；不创建私有 /tmp 伪宿主锁')
    if os.environ.get('WF_RESULTS_LOCK_FD'):
        verify_results_lock()
    else:
        acquire_results_lock()
    os.execvp(command[0], command)


def lease_results(command):
    """持有 fixture → results 锁后 exec（已经继承并验证过的锁不重复申请）。"""
    _lease_fixture()
    if not _unit_scope_ok():
        raise FixtureError(
            'unit domain: 没有继承宿主结果锁也没有 owned test scope；不创建私有 /tmp 伪宿主锁')
    if os.environ.get('WF_RESULTS_LOCK_FD'):
        verify_results_lock()
    else:
        acquire_results_lock()
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
    p = sub.add_parser('move')
    p.add_argument('source')
    p.add_argument('target')
    p = sub.add_parser('claim-results')
    p.add_argument('root')
    p = sub.add_parser('prepare-results')
    p.add_argument('root')
    p = sub.add_parser('lease')
    p.add_argument('command', nargs=argparse.REMAINDER)
    sub.add_parser('check-lease')
    sub.add_parser('create-scope')
    sub.add_parser('check-results-lease')
    lease_domain_parser = sub.add_parser('lease-domain')
    lease_domain_parser.add_argument('command', nargs=argparse.REMAINDER)
    lease_results_parser = sub.add_parser('lease-results')
    lease_results_parser.add_argument('command', nargs=argparse.REMAINDER)
    ensure_scope = sub.add_parser('check-scope')
    ensure_scope.add_argument('paths', nargs='+')
    prune = sub.add_parser('prune-results')
    prune.add_argument('root')
    prune.add_argument('--scope', choices=('run', 'repro'), required=True)
    prune.add_argument('--keep', type=int, default=20)
    prune.add_argument('--exclude', action='append', default=[])
    prune.add_argument('--bootstrap', action='store_true',
                       help='额外回收无主但顶层内容全部为运行器已知产物的历史目录（仅手工执行）')
    args = parser.parse_args(argv)
    try:
        if args.operation == 'lease':
            command = args.command[1:] if args.command[:1] == ['--'] else args.command
            if not command:
                raise FixtureError('lease command is required')
            lock_run(command)
        elif args.operation == 'lease-domain':
            command = args.command[1:] if args.command[:1] == ['--'] else args.command
            if not command:
                raise FixtureError('lease-domain command is required')
            lease_domain(command)
        elif args.operation == 'lease-results':
            command = args.command[1:] if args.command[:1] == ['--'] else args.command
            if not command:
                raise FixtureError('lease-results command is required')
            lease_results(command)
        elif args.operation == 'check-lease':
            verify_lease()
        elif args.operation == 'check-results-lease':
            verify_results_lock()
        elif args.operation == 'create-scope':
            print(create_test_scope())
        elif args.operation == 'check-scope':
            ensure_in_scope(*args.paths)
        elif not os.environ.get('WF_FIXTURE_LEASE_FD'):
            lock_run([sys.executable, __file__, *sys.argv[1:]])
        else:
            verify_lease()
            if args.operation == 'clone':
                clone(args.source, args.target)
            elif args.operation == 'move':
                move(args.source, args.target)
            elif args.operation == 'claim-results':
                claim_results(args.root)
            elif args.operation == 'prepare-results':
                prepare_results(args.root)
            elif args.operation == 'prune-results':
                prune_results(args.root, args.scope, args.keep, args.exclude, args.bootstrap)
            else:
                {'reset': reset, 'remove': remove, 'validate': validate}[args.operation](args.root, args.forbid)
        return 0
    except (FixtureError, OSError) as exc:
        print(f'FIXTURE-REFUSED: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
