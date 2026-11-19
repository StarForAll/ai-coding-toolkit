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

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / 'scripts'))
import wf_test_paths  # noqa: E402  （作者侧路径/scope 唯一所有者；本模块只委托）

OWNER = 'wf-test-fixture-v1'
SCOPE_OWNER = wf_test_paths.SCOPE_OWNER
SCOPE_MARKER = wf_test_paths.SCOPE_MARKER
PRODUCTION_RESULTS_LOCK = wf_test_paths.PRODUCTION_RESULTS_LOCK


class FixtureError(wf_test_paths.PathError):
    """Refused a fixture operation before touching its contents."""


def _temporary_roots():
    """允许的临时根：当前进程 TMPDIR + execution.py 记录的宿主根（有界校验）。"""
    current = Path(tempfile.gettempdir()).resolve()
    roots = {current}
    recorded = os.environ.get('WF_HOST_TMPDIR')
    if recorded:
        root = Path(recorded).resolve()
        if root == current:
            return roots
        protected = (Path.home().resolve(), REPO.resolve())
        # 记录的宿主根只能是可信临时目录：拒绝根、受保护路径及其祖先/内部目录。
        if (not root.is_dir() or root == Path(root.anchor)
                or any(root == item or root in item.parents or item in root.parents
                       for item in protected)):
            raise FixtureError(f'WF_HOST_TMPDIR 不是可用的临时根：{root}')
        roots.add(root)
    return roots


def validate(root, forbidden=()):
    root = Path(root).absolute()
    if root != root.resolve():
        raise FixtureError(f'fixture path contains a symlink: {root}')
    # 命令私有 TMPDIR（R3）会把 gettempdir() 指向本命令根；fixture 仍可位于宿主临时存储
    # 或 runner 的测试缓存根，因此把 execution.py 记录的宿主根一并作为允许域。
    temp_roots = _temporary_roots()
    if any(root == temp / 'wf-fixtures' for temp in temp_roots):
        raise FixtureError(f'fixture root must not replace the shared fixture hub: {root}')
    caches = (Path.home() / '.cache' / 'wf-test-run',
              Path.home() / '.cache' / 'wf-fixtures')
    if not (any(temp in root.parents for temp in temp_roots)
            or any(cache in root.parents for cache in caches)):
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
    """计划镜像入口：委托 `resource_lifecycle.claim_plan`（schema2 plan-only owner）。"""
    import resource_lifecycle
    try:
        return resource_lifecycle.claim_plan(root)
    except resource_lifecycle.LifecycleError as exc:
        raise FixtureError(str(exc)) from exc


def begin_run(root, intent="execution", role="full", run_id=None):
    """兼容 delegate：结果初始化唯一实现在 `resource_lifecycle.begin_run`。"""
    import resource_lifecycle
    try:
        return resource_lifecycle.begin_run(root, intent, role, run_id)
    except resource_lifecycle.LifecycleError as exc:
        raise FixtureError(str(exc)) from exc


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


def _validate_cache_root(root):
    root = Path(root)
    if root != root.resolve():
        raise FixtureError(f'prune root 包含符号链接：{root}')
    resolved = root.resolve()
    temp_roots = _temporary_roots()
    if resolved != DEFAULT_CACHE.resolve() and not any(
            temp in resolved.parents for temp in temp_roots):
        raise FixtureError(
            f'prune root 必须是标准缓存根（{DEFAULT_CACHE}）或临时目录之下：{root}')
    return root


def _retention_candidate(directory):
    """本前缀条目是否可进入退役候选报告（finished+cleaned 且无保留/证据完整）。"""
    import resource_lifecycle
    try:
        return resource_lifecycle.classify_result(str(directory))['retention_candidate']
    except (resource_lifecycle.LifecycleError, OSError):
        return False


def prune_results(root, scope, keep=20, exclude=(), bootstrap=False):
    """结果轮转：**只报告**退役候选，不删除任何目录。

    - root：标准缓存根（DEFAULT_CACHE）；scope：'run'|'repro' 前缀隔离，run_all 与
      独立 repro 入口互不越界报告对方产物；
    - keep：按最近完成时间保留的合格条目数（`--keep` 语义保留，但只影响报告分类）；
    - bootstrap：额外把无主/非终态条目列为待复核（同样只报告）；
    - 删除只经精确退役入口（inventory-results → retire-results），并需具体内容授权。
    输出 `PRUNE-CANDIDATES=<n> PRUNE-KEPT=<m>`，每个候选一行 `PRUNE-CANDIDATE <name>`。
    """
    root = _validate_cache_root(root)
    if scope not in ('run', 'repro'):
        raise FixtureError(f'--scope 只接受 run|repro（收到 {scope!r}）')
    if keep < 0:
        raise FixtureError('--keep 不能为负')
    if not root.exists():
        # 缓存根尚未建立（冷启动）：没有可报告条目，不是错误，也不创建目录。
        print('PRUNE-CANDIDATES=0 PRUNE-KEPT=0', file=sys.stderr)
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
    # 深度检索只对合格条目发生：轮转报告不递归扫描、不取锁。
    eligible = [entry for entry in candidates if _retention_candidate(entry)]
    eligible.sort(key=lambda entry: (results_marker(entry).stat().st_mtime), reverse=True)
    kept = eligible[:keep]
    retire = eligible[keep:]
    for entry in retire:
        print(f'PRUNE-CANDIDATE {entry.name}: finished+cleaned → inventory-results 后 retire-results',
              file=sys.stderr)
    if bootstrap:
        for entry in candidates:
            if entry in exclude or entry in eligible:
                continue
            print(f'PRUNE-REVIEW {entry.name}: 无主/非终态，需精确盘点后人工确认', file=sys.stderr)
    print(f'PRUNE-CANDIDATES={len(retire)} PRUNE-KEPT={len(kept)}', file=sys.stderr)
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
    inventory = sub.add_parser('inventory-results')
    inventory.add_argument('--cache-root', default=None)
    inventory.add_argument('--results-root', action='append', default=[])
    inventory.add_argument('--fixture', action='append', default=[])
    inventory.add_argument('--format', choices=('json', 'sh'), default='json')
    retire = sub.add_parser('retire-results')
    retire.add_argument('--selection', required=True)
    retire.add_argument('--retirement-mode', required=True,
                        choices=('safe-legacy', 'manual-retained'))
    retire.add_argument('--confirm-retirement', action='store_true', required=True)
    retire.add_argument('--report', required=True)
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
            elif args.operation == 'inventory-results':
                report = inventory_results(args.cache_root, args.results_root, args.fixture)
                if args.format == 'json':
                    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
                else:
                    print('INVENTORY_STATUS=' + report.get('status', 'partial'))
                    print('INVENTORY_ENTRIES=' + str(len(report.get('entries') or [])))
                return 0 if report.get('status') in ('complete', 'absent') else 1
            elif args.operation == 'retire-results':
                return retire_results(args)
            elif args.operation == 'prune-results':
                prune_results(args.root, args.scope, args.keep, args.exclude, args.bootstrap)
            else:
                {'reset': reset, 'remove': remove, 'validate': validate}[args.operation](args.root, args.forbid)
        return 0
    except (FixtureError, OSError) as exc:
        print(f'FIXTURE-REFUSED: {exc}', file=sys.stderr)
        return 1


# ---- C3：结果/夹具盘点与退役（父任务 design §4.2）-----------------------------

DOMAIN = "results"


def _tree_projection(path, precise):
    """精确模式返回整树快照与摘要；浅扫模式返回 None（退役前必须再精确盘点）。"""
    import resource_lifecycle
    if not precise or not os.path.isdir(path):
        return None, None
    entries = resource_lifecycle.tree_snapshot(os.path.realpath(path))
    return entries, resource_lifecycle.snapshot_digest(entries)


def _identity_digest(path):
    """owner/run-state 摘要：根级身份摘要，只用于展示，不是删除授权。"""
    import hashlib
    try:
        blob = b""
        for name in (".wf-results-owner.json", "run-state.json"):
            candidate = Path(path) / name
            if candidate.is_symlink():
                continue
            if candidate.is_file() and candidate.stat().st_size <= 1024 * 1024:
                blob += name.encode() + b"\0" + candidate.read_bytes() + b"\0"
        return "sha256:" + hashlib.sha256(blob).hexdigest() if blob else None
    except OSError:
        return None


def _result_entry(path, root_label, precise=False):
    import resource_lifecycle
    info = resource_lifecycle.classify_result(path)
    entries, digest = _tree_projection(path, precise)
    import resource_lifecycle as lifecycle
    empty_shell = bool(entries is not None and lifecycle.is_empty_shell(entries))
    allowed = []
    if entries is not None:
        if not entries or empty_shell:
            allowed.append("safe-legacy")
        if info["kind"] != "unowned":
            allowed.append("manual-retained")
    try:
        import results_summary
        history = results_summary.historical_conclusion(path)
    except Exception as exc:  # 历史结论只作报告；读不到就是 unknown，不猜
        history = {"status": "unknown", "reason": str(exc), "schema_version": None}
    return {"root": root_label, "path": os.path.realpath(path), "kind": "result-root",
            "history": history,
            "class": info["kind"], "provenance": {
                "legacy-owned": "legacy-owned",
                "finished-cleaned": "owned",
                "plan-only": "owned",
                "empty": "owned",
                "active": "owned",
                "incomplete-new": "owned",
                "unknown": "unknown-entry",
                "unowned": "unowned",
                "absent": "unknown-entry",
                "unreadable": "unowned",
            }.get(info["kind"], "unknown-entry"),
            "claimable": info["claimable"],
            "blocked": None if info["claimable"] else info["reason"],
            "uid": os.stat(path).st_uid if os.path.exists(path) else None,
            "owner": (info.get("owner") or {}).get("kind"),
            "state": (info.get("state") or {}).get("kind"),
            "retained_paths": ((info.get("state") or {}).get("payload") or {}).get(
                "retained_paths") or [],
            "reasons": ((info.get("state") or {}).get("payload") or {}).get(
                "reasons") or [],
            "allowed": allowed,
            "empty_shell": empty_shell if entries is not None else None,
            "entries": entries,
            "snapshot_digest": digest,
            "digest": _identity_digest(path)}


def _fixture_entry(path, root_label, precise=False):
    path = os.path.realpath(path)
    marker = Path(path).parent / ("." + Path(path).name + ".wf-owner.json")
    try:
        record = json.loads(marker.read_text())
    except (OSError, ValueError):
        record = None
    owned = (record == {"owner": OWNER, "root": path}
             and (not os.path.exists(path) or os.stat(path).st_uid == os.getuid()))
    entries, digest = _tree_projection(path, precise) if os.path.exists(path) else (None, None)
    import resource_lifecycle
    empty_shell = bool(entries is not None and resource_lifecycle.is_empty_shell(entries))
    allowed = []
    if owned:
        if entries is not None:
            if not entries:
                allowed.append("safe-legacy")
            allowed.append("manual-retained")
    return {"root": root_label, "path": path, "kind": "fixture",
            "class": "fixture-owned" if owned else "fixture-unowned",
            "provenance": "owned" if owned else "unowned",
            "blocked": None if owned else "no matching fixture marker",
            "uid": os.stat(path).st_uid if os.path.exists(path) else None,
            "marker": str(marker) if marker.is_file() else None,
            "entries": entries,
            "snapshot_digest": digest,
            "empty_shell": empty_shell if entries is not None else None,
            "allowed": allowed,
            "digest": None}


def inventory_results(cache_root=None, results_roots=(), fixtures=()):
    """只读盘点：cache 模式扫描直接子项；精确模式逐项核 owner/marker（互斥）。"""
    precise = bool(results_roots or fixtures)
    if cache_root and precise:
        raise FixtureError("cache 模式与精确结果/夹具模式互斥")
    if not cache_root and not precise:
        raise FixtureError("inventory-results 至少给 --cache-root 或 --results-root/--fixture")
    entries, unknown = [], []
    if cache_root:
        root = os.path.realpath(os.path.abspath(cache_root))
        try:
            names = sorted(os.listdir(root))
        except FileNotFoundError:
            return {"schema_version": 1, "domain": DOMAIN, "root": root,
                    "status": "absent", "entries": [], "unknown": []}
        except OSError as exc:
            return {"schema_version": 1, "domain": DOMAIN, "root": root,
                    "status": "partial", "error": str(exc), "entries": [], "unknown": []}
        for name in names:
            path = os.path.join(root, name)
            if os.path.islink(path):
                unknown.append({"path": path, "reason": "symlink（不跟随）"})
                continue
            if not os.path.isdir(path):
                unknown.append({"path": path, "reason": "未知文件"})
                continue
            if not (name.startswith("run-") or name.startswith("repro-")):
                unknown.append({"path": path, "reason": "非 run-/repro- 前缀（不推断归属）"})
                continue
            entries.append(_result_entry(path, root))
        return {"schema_version": 1, "domain": DOMAIN, "root": root,
                "status": "partial" if unknown else "complete",
                "entries": entries, "unknown": unknown, "capacity": "not-measured",
                "precision": "shallow"}
    label = "precise"
    for path in results_roots:
        entries.append(_result_entry(path, label, precise=True))
    for path in fixtures:
        entries.append(_fixture_entry(path, label, precise=True))
    return {"schema_version": 1, "domain": DOMAIN, "root": label, "status": "complete",
            "entries": entries, "unknown": [], "capacity": "not-measured",
            "precision": "precise"}


def _results_guard():
    """fixture lease + 结果域锁；两者都非阻塞取，忙则拒绝。"""
    _lease_fixture()
    if os.environ.get("WF_RESULTS_LOCK_FD"):
        verify_results_lock()
        return
    acquire_results_lock()


def _delete_results_entry(item):
    """逐项删除：只删除确认快照里的条目（结果树与夹具树同一规则）。"""
    import resource_lifecycle
    path = item["path"]
    entries = item.get("entries")
    if not isinstance(entries, list):
        raise OSError(f"缺少精确快照，拒绝删除：{path}")
    if os.path.islink(path) or not os.path.isdir(path):
        raise OSError(f"删除根不是真实目录：{path}")
    resource_lifecycle.delete_confirmed_tree(path, entries)
    if item["kind"] == "fixture":
        marker = Path(path).parent / ("." + Path(path).name + ".wf-owner.json")
        marker.unlink(missing_ok=True)
    if os.path.lexists(path):
        raise OSError(f"删除后根仍存在：{path}")


def _precise_entry(path, kind, root_label):
    if kind == "fixture":
        return _fixture_entry(path, root_label, precise=True)
    return _result_entry(path, root_label, precise=True)


def _verify_selected(resource_lifecycle, selected, snapshot_mode):
    """按已核选择重新精确盘点；返回带快照的条目。任何漂移/无归属都拒绝。"""
    chosen = []
    for item in selected:
        found = _precise_entry(item["path"], item["kind"], "precise")
        if found["kind"] != item["kind"]:
            raise FixtureError(f"selection 项类型漂移：{item['path']}")
        if item.get("provenance") and found.get("provenance") != item["provenance"]:
            raise FixtureError(f"selection provenance 漂移：{item['path']}")
        if found["kind"] == "result-root":
            if found.get("provenance") not in ("owned", "legacy-owned"):
                raise FixtureError(f"结果根没有可验证 wf owner，拒绝退役：{item['path']}")
            if found.get("snapshot_digest") is None:
                raise FixtureError(f"结果根不是可精确盘点的真实目录：{item['path']}")
        else:
            if found.get("provenance") != "owned":
                raise FixtureError(f"夹具没有可验证 marker，拒绝退役：{item['path']}")
            if found.get("snapshot_digest") is None:
                raise FixtureError(f"夹具不是可精确盘点的真实目录：{item['path']}")
        if snapshot_mode == "manual-retained":
            if item.get("snapshot_digest") and item["snapshot_digest"] != found["snapshot_digest"]:
                raise FixtureError(f"selection 内容快照漂移（重新盘点后再确认）：{item['path']}")
            if item.get("entries") and item["entries"] != found["entries"]:
                raise FixtureError(f"selection 条目清单漂移：{item['path']}")
        chosen.append(found)
    for item in chosen:
        live = resource_lifecycle.live_references(item["path"])
        if live:
            raise FixtureError(f"存在活引用（{live[0]['pid']}）拒绝删除：{item['path']}")
    return chosen


def retire_results(args):
    import resource_lifecycle
    document_path = Path(args.selection)
    try:
        document = json.loads(document_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise FixtureError(f"selection 不可读：{exc}") from exc
    selected = resource_lifecycle.selection_entries(document, DOMAIN)
    if args.retirement_mode == "safe-legacy":
        # 只做可单独证明的空壳收尾：内容清单必须为空或只有根身份记录。
        for item in selected:
            found = _precise_entry(item["path"], item["kind"], "precise")
            if "safe-legacy" not in (found.get("allowed") or []):
                raise FixtureError(
                    f"safe-legacy 只接受空目录或只有根身份记录的空壳；"
                    f"存在其他条目的树须用 manual-retained 逐项确认：{item['path']}")
        chosen = _verify_selected(resource_lifecycle, selected, "safe-legacy")
    else:
        # manual-retained：先精确盘点到具体条目与快照，再由 TTY 授权这份清单。
        chosen = _verify_selected(resource_lifecycle, selected, "manual-retained")

    def revalidate_after_confirm():
        # 确认之后、删除之前：归属/活引用/精确快照再核一次；变化即取消整次删除。
        again = _verify_selected(resource_lifecycle, selected, "manual-retained")
        for before, after in zip(chosen, again):
            if before["snapshot_digest"] != after["snapshot_digest"]:
                raise resource_lifecycle.RetireError(
                    f"内容在确认后变化，取消整次删除：{before['path']}")

    report = resource_lifecycle.execute_retirement(
        DOMAIN, document.get("root") or "precise", chosen,
        args.retirement_mode, args.report, _delete_results_entry, _results_guard, False,
        revalidate=(revalidate_after_confirm if args.retirement_mode == "manual-retained"
                    else None))
    print(json.dumps({"state": "retired", "mode": args.retirement_mode,
                      "report": os.path.abspath(args.report),
                      "entries": len(report["results"])}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
