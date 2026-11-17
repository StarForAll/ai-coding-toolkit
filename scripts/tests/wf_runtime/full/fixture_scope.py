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


def prepare_results(root):
    """只在 begin_run 的旧代许可内清理；不提供独立“继续清理 active 目录”入口。"""
    import resource_lifecycle
    raise FixtureError(
        'prepare-results 不再是公共入口：结果身份与准备统一由 resource_lifecycle.begin-run '
        '在持有结果锁时完成；请换新结果目录或按盘点/退役流程处置旧现场')


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
    temp = Path(tempfile.gettempdir()).resolve()
    if resolved != DEFAULT_CACHE.resolve() and temp not in resolved.parents:
        raise FixtureError(
            f'prune root 必须是标准缓存根（{DEFAULT_CACHE}）或临时目录之下：{root}')
    return root


def _valid_results_owner(directory):
    """新协议 owner 由 resource_lifecycle 判定；只有 finished+cleaned 可自动轮转。"""
    import resource_lifecycle
    try:
        return resource_lifecycle.classify_result(str(directory))['automatic_prune']
    except (resource_lifecycle.LifecycleError, OSError):
        return False


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
    review = []
    if bootstrap:
        # 无主目录不再凭“顶层看起来都是已知产物”删除：只报告待退役复核。
        for entry in candidates:
            if entry in exclude or any(entry == item for item in owned):
                continue
            print(f'PRUNE-KEPT {entry.name}: needs-retirement-review（无主/非终态，见盘点退役流程）',
                  file=sys.stderr)
            review.append(entry.name)
    print(f'PRUNED={pruned} KEPT={kept}', file=sys.stderr)
    if review:
        print('PRUNE-REVIEW=' + ' '.join(sorted(review)), file=sys.stderr)
        return 1
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
            elif args.operation == 'prepare-results':
                prepare_results(args.root)
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


def _result_entry(path, root_label):
    import resource_lifecycle
    info = resource_lifecycle.classify_result(path)
    entry = {"root": root_label, "path": os.path.realpath(path), "kind": "result-root",
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
             "reusable": info["reusable"], "blocked": None if info["reusable"] else info["reason"],
             "uid": os.stat(path).st_uid if os.path.exists(path) else None,
             "owner": (info.get("owner") or {}).get("kind"),
             "state": (info.get("state") or {}).get("kind"),
             "retained_paths": ((info.get("state") or {}).get("payload") or {}).get(
                 "retained_paths") or [],
             "reasons": ((info.get("state") or {}).get("payload") or {}).get(
                 "reasons") or [],
             "allowed": (["safe-legacy"] if info["kind"] == "legacy-owned" else
                         (["manual-retained"] if info["kind"] in
                          ("finished-cleaned", "active", "incomplete-new", "plan-only", "empty")
                          else [])),
             "digest": None}
    identity = Path(path) / ".wf-results-owner.json"
    try:
        import hashlib
        blob = b""
        for name in (".wf-results-owner.json", "run-state.json"):
            candidate = Path(path) / name
            if candidate.is_symlink():
                continue
            if candidate.is_file() and candidate.stat().st_size <= 1024 * 1024:
                blob += name.encode() + b"\0" + candidate.read_bytes() + b"\0"
        entry["digest"] = "sha256:" + hashlib.sha256(blob).hexdigest() if blob else None
    except OSError:
        entry["digest"] = None
    return entry


def _fixture_entry(path, root_label):
    path = os.path.realpath(path)
    marker = Path(path).parent / ("." + Path(path).name + ".wf-owner.json")
    try:
        record = json.loads(marker.read_text())
    except (OSError, ValueError):
        record = None
    owned = (record == {"owner": OWNER, "root": path}
             and (not os.path.exists(path) or os.stat(path).st_uid == os.getuid()))
    return {"root": root_label, "path": path, "kind": "fixture",
            "class": "fixture-owned" if owned else "fixture-unowned",
            "provenance": "owned" if owned else "unowned",
            "blocked": None if owned else "no matching fixture marker",
            "uid": os.stat(path).st_uid if os.path.exists(path) else None,
            "marker": str(marker) if marker.is_file() else None,
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
                "entries": entries, "unknown": unknown, "capacity": "not-measured"}
    label = "precise"
    for path in results_roots:
        entries.append(_result_entry(path, label))
    for path in fixtures:
        entries.append(_fixture_entry(path, label))
    return {"schema_version": 1, "domain": DOMAIN, "root": label, "status": "complete",
            "entries": entries, "unknown": [], "capacity": "not-measured"}


def observe_results(root, exclude=()):
    """root controller 维护前一次浅扫（排除当前 results 与父子目录）。"""
    report = inventory_results(cache_root=root)
    excluded = {os.path.realpath(item) for item in exclude}
    counts = {}
    for item in report.get("entries") or []:
        if item["path"] in excluded:
            continue
        key = item.get("class") or "unknown"
        counts[key] = counts.get(key, 0) + 1
    return {"root": report.get("root"), "status": report.get("status", "complete"),
            "counts": counts, "capacity": "not-measured",
            "inventory_hint": f"python3 {os.path.abspath(__file__)} inventory-results "
                              f"--cache-root {report.get('root')} --format json"}


def _results_guard():
    """fixture lease + 结果域锁；两者都非阻塞取，忙则拒绝。"""
    _lease_fixture()
    if os.environ.get("WF_RESULTS_LOCK_FD"):
        verify_results_lock()
        return
    acquire_results_lock()


def _delete_results_entry(item):
    import resource_lifecycle
    path = item["path"]
    if item["kind"] == "fixture":
        remove(path)
        return
    if os.path.islink(path) or not os.path.isdir(path):
        raise OSError(f"结果根不是真实目录：{path}")
    import shutil
    shutil.rmtree(path)
    if os.path.lexists(path):
        raise OSError(f"结果根删除失败：{path}")


def retire_results(args):
    import resource_lifecycle
    document_path = Path(args.selection)
    try:
        document = json.loads(document_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise FixtureError(f"selection 不可读：{exc}") from exc
    selected = resource_lifecycle.selection_entries(document, DOMAIN)
    # 重扫描：cache/precise 由 selection 的 root 字段决定；不信任输入提供的 digest 作为权限。
    roots = {item.get("root") for item in selected}
    if roots == {document.get("root")} and document.get("root") not in (None, "precise"):
        current = inventory_results(cache_root=document["root"])
    else:
        results_roots = [item["path"] for item in selected if item["kind"] == "result-root"]
        fixtures = [item["path"] for item in selected if item["kind"] == "fixture"]
        current = inventory_results(results_roots=results_roots, fixtures=fixtures)
    current_by_path = {os.path.realpath(item["path"]): item for item in current["entries"]}
    chosen = []
    for item in selected:
        found = current_by_path.get(os.path.realpath(item["path"]))
        if found is None or found["kind"] != item["kind"]:
            raise FixtureError(f"selection 项不存在/漂移：{item['path']}")
        if item.get("provenance") and found.get("provenance") != item["provenance"]:
            raise FixtureError(f"selection provenance 漂移：{item['path']}")
        if found["kind"] == "result-root" and found.get("provenance") not in ("owned", "legacy-owned"):
            raise FixtureError(f"结果根没有可验证 wf owner，拒绝退役：{item['path']}")
        chosen.append(found)
    for item in chosen:
        live = resource_lifecycle.live_references(item["path"])
        if live:
            raise FixtureError(f"存在活引用（{live[0]['pid']}）拒绝删除：{item['path']}")
    if args.retirement_mode == "safe-legacy":
        for item in chosen:
            if item["kind"] == "result-root" and item.get("provenance") != "legacy-owned":
                raise FixtureError(f"safe-legacy 只接受严格旧格式 owner：{item['path']}")
            if item["kind"] == "fixture" and item.get("provenance") != "owned":
                raise FixtureError(f"safe-legacy 只接受可验证 fixture marker：{item['path']}")
    report = resource_lifecycle.execute_retirement(
        DOMAIN, document.get("root") or "precise", chosen,
        args.retirement_mode, args.report, _delete_results_entry, _results_guard, False)
    print(json.dumps({"state": "retired", "mode": args.retirement_mode,
                      "report": os.path.abspath(args.report),
                      "entries": len(report["results"])}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
