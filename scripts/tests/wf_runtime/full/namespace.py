#!/usr/bin/env python3
"""Expose only shared results and read-only inputs inside a private worker /tmp.

Mount namespace 边界（design §4.3 / AC14）：
- 覆盖 `/tmp` 之前记录宿主 mount 域（`/proc/self/ns/mnt`）与仍有效的宿主 FD 事实；
- 覆盖之后**只关闭本 worker 继承的宿主结果/发行 FD 副本**（不 unlock，父仍持有的
  open-file-description 不受影响），并显式清除相应 locator 与内部 frame 变量——同名 `/tmp` 路径
  不再代表宿主锁；
- 挂载给该单元的结果输出路径是父委派的写入范围，不据此重取任何宿主锁；
- 设置 unit 执行域标记：生产 results/release 锁 helper 在域不符时先拒绝，不建私有伪宿主锁。
  显式测试 scope 单元可以只在自己的 scope 内建本地测试锁（fake harness），但不能声称继承宿主锁。
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

HOST_LOCATORS = (
    'WF_FIXTURE_LEASE_FD', 'WF_FIXTURE_LEASE_PID',
    'WF_RESULTS_LOCK_FD', 'WF_RESULTS_LOCK_PID', 'WF_RESULTS_LOCK_DOMAIN', 'WF_RESULTS_LOCK_MNT',
    'WF_TEST_RELEASE_LEASE_FD', 'WF_TEST_RELEASE_LEASE_PID', 'WF_TEST_RELEASE_ROOT',
    'WF_TEST_RELEASE_LEASE_MNT',
    'WF_RUNNER_ENTRY_PID', 'WF_RUNNER_CONTROL_PID',
    'WF_FRAME_ENTRY_PID', 'WF_FRAME_RESULTS_ROOT', 'WF_FRAME_RESULTS_EXPLICIT',
    'WF_FRAME_SCOPE_ROOT', 'WF_FRAME_PLAN_FILE', 'WF_FRAME_PLAN_SHA256', 'WF_FRAME_PLAN_SIZE',
    'WF_FRAME_CONTEXT_FILE', 'WF_FRAME_CONTEXT_SHA256', 'WF_FRAME_CONTEXT_SIZE',
    'WF_TEST_SCOPE_ROOT',
    # 宿主 state/cache locator：同名 `/tmp` 路径在挂载后不再代表宿主状态，必须一并清掉；
    # 否则单元会按残留字符串去读/写宿主 repro-state 或结果缓存轮转根。
    'WF_TEST_RUN_CACHE', 'WF_RESULTS_CACHE', 'WF_PLAN_LOG',
)


def scrub_state_locators(environ=None):
    """清掉宿主 locator（含 state/cache 派生路径）；返回被清掉的键，便于断言与排障。"""
    environ = os.environ if environ is None else environ
    removed = []
    for key in HOST_LOCATORS:
        if environ.pop(key, None) is not None:
            removed.append(key)
    return removed


def bind(source, target, readonly=False):
    target.mkdir(parents=True, exist_ok=True)
    subprocess.run(['mount', '--bind', str(source), str(target)], check=True)
    if readonly:
        subprocess.run(['mount', '-o', 'remount,bind,ro', str(target)], check=True)


def close_host_descriptors():
    """关闭本 worker 继承的宿主 FD 副本；只 close 自己的 ofd，不动父的锁。"""
    for key in ('WF_RESULTS_LOCK_FD', 'WF_TEST_RELEASE_LEASE_FD'):
        value = os.environ.get(key)
        if value is None:
            continue
        try:
            os.close(int(value))
        except (ValueError, OSError):
            pass


def main():
    results = Path(os.environ['RESULTS_DIR']).resolve()
    release = Path(os.environ['SHARED_RELEASE']).resolve()
    template = Path(os.environ['WF_TEMPLATE']).resolve() if os.environ.get('WF_TEMPLATE_READY') == '1' else None
    # run 内模板位于结果目录内，需要在结果目录的可写 bind 之后补一个只读 remount；
    # 跨 run 缓存条目在结果目录之外（只经 /mnt 只读挂入），没有这个嵌套关系。
    template_relative = None
    if template is not None:
        try:
            template_relative = template.relative_to(results)
        except ValueError:
            template_relative = None
    shared = Path('/mnt/wf-test-runner')
    host_mnt = os.readlink('/proc/self/ns/mnt')
    try:
        subprocess.run(['mount', '-t', 'tmpfs', 'tmpfs', '/mnt'], check=True)
        bind(results, shared / 'results')
        bind(release, shared / 'release', readonly=True)
        if template is not None:
            bind(template, shared / 'template', readonly=True)
            if template_relative is not None:
                bind(template, shared / 'results' / template_relative, readonly=True)
        subprocess.run(['mount', '-t', 'tmpfs', 'tmpfs', '/tmp'], check=True)
        # Never expose the host fixture parent: each worker has private state.
        Path(os.environ['FIX']).parent.mkdir(parents=True, exist_ok=True)
        bind(shared / 'results', results)
        bind(shared / 'release', release, readonly=True)
        bind(shared / 'release', Path('/tmp/wf-fixtures/release-repo'), readonly=True)
        if template is not None:
            if template_relative is not None:
                # Restore the nested read-only mount after its writable parent mount.
                bind(shared / 'template', template, readonly=True)
            os.environ['WF_TEMPLATE_SOURCE'] = str(template)
            os.environ['WF_TEMPLATE'] = str(shared / 'template')
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f'NAMESPACE-FAILED: {exc}', file=sys.stderr)
        return 1
    close_host_descriptors()
    scrub_state_locators()
    os.environ['WF_UNIT_DOMAIN'] = 'unit'
    os.environ['WF_HOST_MNT_ID'] = host_mnt
    os.environ['WF_NAMESPACE_READY'] = '1'
    # The host runner keeps the global lease. A private worker lease lets its
    # subprocesses verify a lock owned in this user namespace, without reading
    # host process descriptors that user namespaces deliberately protect.
    import fixture_scope
    fixture_scope.lock_run(sys.argv[1:])


if __name__ == '__main__':
    raise SystemExit(main())
