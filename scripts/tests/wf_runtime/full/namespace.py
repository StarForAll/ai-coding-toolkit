#!/usr/bin/env python3
"""Expose only shared results and read-only inputs inside a private worker /tmp."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


def bind(source, target, readonly=False):
    target.mkdir(parents=True, exist_ok=True)
    subprocess.run(['mount', '--bind', str(source), str(target)], check=True)
    if readonly:
        subprocess.run(['mount', '-o', 'remount,bind,ro', str(target)], check=True)


def main():
    results = Path(os.environ['RESULTS_DIR']).resolve()
    release = Path(os.environ['SHARED_RELEASE']).resolve()
    template = Path(os.environ['WF_TEMPLATE']).resolve() if os.environ.get('WF_TEMPLATE_READY') == '1' else None
    shared = Path('/mnt/wf-test-runner')
    try:
        subprocess.run(['mount', '-t', 'tmpfs', 'tmpfs', '/mnt'], check=True)
        bind(results, shared / 'results')
        bind(release, shared / 'release', readonly=True)
        if template is not None:
            bind(template, shared / 'template', readonly=True)
            bind(template, shared / 'results' / template.relative_to(results), readonly=True)
        subprocess.run(['mount', '-t', 'tmpfs', 'tmpfs', '/tmp'], check=True)
        # Never expose the host fixture parent: each worker has private state.
        Path(os.environ['FIX']).parent.mkdir(parents=True, exist_ok=True)
        bind(shared / 'results', results)
        bind(shared / 'release', release, readonly=True)
        bind(shared / 'release', Path('/tmp/wf-fixtures/release-repo'), readonly=True)
        if template is not None:
            # Restore nested read-only mounts after their writable parent mount.
            bind(shared / 'template', template, readonly=True)
            os.environ['WF_TEMPLATE_SOURCE'] = str(template)
            os.environ['WF_TEMPLATE'] = str(shared / 'template')
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f'NAMESPACE-FAILED: {exc}', file=sys.stderr)
        return 1
    os.environ['WF_NAMESPACE_READY'] = '1'
    # The host runner keeps the global lease. A private worker lease lets its
    # subprocesses verify a lock owned in this user namespace, without reading
    # host process descriptors that user namespaces deliberately protect.
    for key in ('WF_FIXTURE_LEASE_FD', 'WF_FIXTURE_LEASE_PID'):
        os.environ.pop(key, None)
    import fixture_scope
    fixture_scope.lock_run(sys.argv[1:])


if __name__ == '__main__':
    raise SystemExit(main())
