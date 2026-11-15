#!/usr/bin/env python3
"""Bound test commands, retain logs and interpret legacy assertion output once.

## 套件输出契约（verdict 是唯一解释点）

套件/流程脚本的人类可读输出遵循以下行文法，`verdict()` 是它们唯一的地方解释器
（run_all.sh 只消费结果 JSON 的 assertion_result，不在 shell 里复制判定）：

- PASS 行：`[PASS] ...`、`PASS ...`、`[<标签>]: PASS ...`（三种前缀形态）；
- FAIL 行：`[FAIL] ...` 或 `... FAIL ...`（作 failures 计数）；
- 汇总行（suite kind 的尾行，三种格式）：
  1. `saved <good> / <total>`；
  2. `saved <total> cases; <good> passed`；
  3. `saved <total> cases`（此时要求 passed 行计数 == total）；
- steps 型输出：逐行 `[<步骤>] exit=<rc> code=WF_OK`，尾行 `TASK_ID <id>`；
- repro 型输出：`PASS green|red: <detail>`；detail 可以跨行（随后跟着原因块），
  因此按**任一行**匹配判定，不要求它是尾行。

新增套件输出格式时改 verdict（唯一实现），不要在调用点新增判定。
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile
import time


class Cancelled(Exception):
    def __init__(self, signum):
        self.signum = signum


def kill_descendants(pid, include_parent=True):
    """Include children that started new sessions (nested runner commands)."""
    children = {}
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit():
            continue
        try:
            fields = (entry / 'stat').read_text().rsplit(')', 1)[1].split()
            children.setdefault(int(fields[1]), []).append(int(entry.name))
        except (OSError, ValueError, IndexError):
            continue
    descendants = []
    pending = [pid]
    while pending:
        child = pending.pop()
        descendants.append(child)
        pending.extend(children.get(child, []))
    for child in reversed(descendants):
        if child == os.getpid() or (child == pid and not include_parent):
            continue
        try:
            os.kill(child, signal.SIGKILL)
        except ProcessLookupError:
            pass


def write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent,
                                         prefix='.' + path.name, delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(payload, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def run(argv, log_path, *, timeout, cwd=None, env=None, inherit_output=False, pass_fds=()):
    """Run one process group; timeout/cancellation applies even during pipe reads."""
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError('command timeout must be positive and finite')
    log_path = Path(log_path).absolute()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    result = {'schema_version': 1, 'argv': list(map(str, argv)),
              'cwd': str(Path(cwd or Path.cwd()).absolute()), 'log_path': str(log_path),
              'rc': 1, 'status': 'failed', 'reason': ''}
    process = None
    handlers = {}

    def cancel(signum, _frame):
        raise Cancelled(signum)

    try:
        for signum in (signal.SIGINT, signal.SIGTERM):
            handlers[signum] = signal.signal(signum, cancel)
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW
        with os.fdopen(os.open(log_path, flags, 0o600), 'wb') as stream:
            try:
                process = subprocess.Popen(result['argv'], cwd=cwd, env=env,
                                           stdout=None if inherit_output else stream,
                                           stderr=None if inherit_output else subprocess.STDOUT,
                                           start_new_session=True,
                                           pass_fds=tuple(int(fd) for fd in pass_fds))
                result['rc'] = process.wait(timeout=timeout)
                result['status'] = 'passed' if result['rc'] == 0 else 'failed'
            except subprocess.TimeoutExpired:
                result.update(rc=124, status='timeout', reason=f'TIMEOUT after {timeout:g}s')
            except Cancelled as exc:
                result.update(rc=128 + exc.signum, status='cancelled', reason=f'cancelled by signal {exc.signum}')
            except OSError as exc:
                result.update(rc=127, status='failed', reason=f'cannot launch command: {exc}')
            finally:
                if process is not None:
                    kill_descendants(process.pid)
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    process.wait()
                if result['reason']:
                    stream.write(('\n' + result['reason'] + '\n').encode())
    finally:
        for signum, handler in handlers.items():
            signal.signal(signum, handler)
        result['seconds'] = round(time.monotonic() - started, 6)
    return result


def verdict(log_path, rc, kind, expected=None):
    """Interpret actual assertions, never arbitrary occurrences of PASS."""
    text = Path(log_path).read_text(encoding='utf-8', errors='replace')
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    tail = lines[-1] if lines else ''
    failures = sum(bool(re.search(r'\[FAIL\]|(?:^|:\s*)FAIL(?:\b|$)', line)) for line in lines)
    passed = sum(bool(re.search(r'^\[PASS\](?:\s|$)|^PASS(?:\s|$)|^\[[^]]+\].*:\s*PASS(?:\s|$)', line)) for line in lines)
    if kind == 'suite' and re.fullmatch(r'TASK_ID [a-zA-Z0-9-]+', tail):
        kind = 'steps'
    evidence = passed
    # 「用例数」的唯一观测点：PASS 行形态数（raw/suite/flow/repro），步骤型输出则是
    # 通过的 step 行数——它与 `expect` 预算比较；`passed` 仍保持 PASS 行计数以兼容既有消费者。
    observed = passed
    if kind == 'suite':
        summary = re.fullmatch(r'(?:saved|total)\s+(\d+)\s*/\s*(\d+)', tail)
        alternative = re.fullmatch(r'saved\s+(\d+)\s+(?:cases|checks);\s*(\d+)\s+passed', tail)
        count = re.fullmatch(r'saved\s+(\d+)\s+cases', tail)
        if summary:
            good, total = map(int, summary.groups())
            evidence = total if total > 0 and good == total else 0
        elif alternative:
            total, good = map(int, alternative.groups())
            evidence = total if total > 0 and good == total else 0
        elif count:
            total = int(count.group(1))
            evidence = total if passed == total and total > 0 else 0
        else:
            evidence = 0
    elif kind == 'steps':
        steps = [line for line in lines if re.match(r'^\[[^]]+\] exit=', line)]
        evidence = len(steps) if steps and re.fullmatch(r'TASK_ID [a-zA-Z0-9-]+', tail) else 0
        if any(not re.fullmatch(r'\[[^]]+\] exit=0 code=WF_OK', line) for line in steps):
            evidence = 0
        observed = evidence
    elif kind == 'repro':
        # detail 之后还可能跟着多行原因块：只要出现过 PASS 相位行就算有证据。
        evidence = int(any(re.match(r'PASS (?:green|red): .+', line) for line in lines))
    elif kind == 'raw':
        evidence = 1
    ok = rc == 0 and failures == 0 and evidence > 0
    if expected is not None:
        ok = ok and observed == expected
    return {'ok': ok, 'assertions': evidence, 'passed': passed, 'observed': observed,
            'tail': tail,
            'reason': '' if ok else f'rc={rc} observed={observed} failures={failures} expected={expected}'}


def isolated_user(log_path):
    """Test-only user state: real bootstrap validation, synthetic fixture consent."""
    import fixture_scope
    root = fixture_scope.reset(str(log_path) + '.home')
    spec = importlib.util.spec_from_file_location('wf_test_bootstrap',
            Path(__file__).resolve().parents[4] / 'docs/workflows/wf/payload/bin/wf.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # These are fixture records, never copies of the real user's confirmation set.
    scope, value, error = module.resolve_candidate(str(root), 'system')
    if error:
        raise RuntimeError(error)
    candidate, error = module.candidate_path(str(root), value)
    if error:
        raise RuntimeError(error)
    size, mtime = module.stat_tuple(candidate)
    write_json(root / '.wf/interpreters.json', {'interpreters': [{
        'scope': scope, 'project_id': None, 'key': 'python_executable',
        'config_value': value, 'path_identity': module.path_identity(value, str(root)),
        'size': size, 'mtime_ns': mtime, 'python_version': module.probe_version(candidate),
        'confirmed_at': 'test-fixture'}]})
    return root


def cleanup_cancelled_run(results):
    import fixture_scope
    root = Path(results)
    plan_path = root / 'plan.json'
    if plan_path.is_file():
        plan = json.loads(plan_path.read_text())
        if plan.get('fix'):
            fixture_scope.remove(plan['fix'])
            fixture_scope.remove(plan['fix'] + '.legacy')
    for path in root.iterdir():
        if path.is_dir() and fixture_scope.marker(path).is_file():
            fixture_scope.remove(path)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--log')
    parser.add_argument('--cancel-parent-children', action='store_true',
                        help='cancel sibling commands when the calling shell is interrupted')
    parser.add_argument('--result')
    parser.add_argument('--name', default='command')
    parser.add_argument('--kind', choices=('raw', 'suite', 'flow', 'steps', 'repro'), default='raw')
    parser.add_argument('--expected', type=int)
    parser.add_argument('--isolated-user', action='store_true', help='use disposable test user configuration')
    parser.add_argument('--runner-control', action='store_true',
                        help='inherit console output and clean runner fixtures on cancellation')
    parser.add_argument('--timeout', type=float, default=float(os.environ.get('WF_COMMAND_TIMEOUT', 180)))
    parser.add_argument('--pass-fds', default='', help='逗号分隔的 FD 白名单（显式继承，不依赖 Popen 默认）')
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    if args.cancel_parent_children:
        kill_descendants(os.getppid(), include_parent=False)
        return 0
    if not args.log:
        parser.error('--log is required for command execution')
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not command:
        parser.error('command is required')
    user_root = isolated_user(args.log) if args.isolated_user else None
    try:
        env = {**os.environ, 'HOME': str(user_root)} if user_root else None
        pass_fds = [item for item in (args.pass_fds or '').split(',') if item]
        result = run(command, args.log, timeout=args.timeout, env=env,
                     inherit_output=args.runner_control, pass_fds=pass_fds)
    finally:
        if user_root:
            import fixture_scope
            fixture_scope.remove(user_root)
    check = verdict(args.log, result['rc'], args.kind, args.expected)
    result.update(name=args.name, kind=args.kind, assertion_result=check,
                  isolated_user=bool(user_root))
    if not check['ok'] and result['rc'] == 0:
        result.update(rc=1, status='failed', reason=check['reason'])
    if args.result:
        write_json(args.result, result)
    if args.runner_control and result['status'] in ('cancelled', 'timeout'):
        try:
            cleanup_cancelled_run(Path(args.log).parent)
        except (OSError, ValueError) as exc:
            print(f'RUNNER-CLEANUP-FAILED: {exc}', file=sys.stderr)
    sys.stdout.write(Path(args.log).read_text(encoding='utf-8', errors='replace'))
    if not check['ok']:
        print(f'EXECUTION-FAILED: {args.name} {result["reason"] or check["reason"]}; log={args.log}', file=sys.stderr)
    return result['rc'] if 0 <= result['rc'] <= 255 else 1


if __name__ == '__main__':
    raise SystemExit(main())
