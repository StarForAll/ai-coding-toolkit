#!/usr/bin/env python3
"""F1 候选闭环（兜底）：候选安装 → 初始化/普通任务 → 复杂审查 → 归档。

存在理由（方案稿 §7.5 兜底）：Phase 1 里其余 59 个套件仍硬编码源码 `payload/lib`，
`candidate_clean=false`，不能拿来证明候选发行物可用。这个套件只用**候选安装出来的项目**
（`.wf/bin/wf.py` + `.wf/lib`）做断言，因此可以标 `candidate_clean=true`，作为 T3 的最低候选闭环。

断言面：
1. `.wf/install/installation.json` 的 version / release_ref / rules_digest 与候选一致，且不是 `0.0.0-dev`；
2. 初始化闭环产物（baseline / project-config / spec 骨架）；
3. 普通任务闭环（复用 `f1_ordinary.py`）；
4. 复杂审查：两份协议报告 + 主会话复核走真实 `review-launch/import/decide`；
5. 归档并自动释放写权。

只在 candidate/dev 部署的夹具上跑（run_all 的 `--fixture-deploy` 决定来源）；
不读源码 `payload/lib`：wflib 一律来自 `$F/.wf/lib` 或 `WF_TEST_LIB`。
"""
import hashlib
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "repro"))

import _harness as H            # noqa: E402
import _review_flow as F        # noqa: E402
import wfdrive                  # noqa: E402

PROJECT = wfdrive.FIX
RESULTS = []


def rec(name, expected, actual, ok):
    RESULTS.append({"case": name, "expected": expected, "actual": actual, "pass": bool(ok)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {actual}")


def installation():
    path = os.path.join(PROJECT, ".wf/install/installation.json")
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def check_installation():
    record = installation()
    expected_version = os.environ.get("WF_RELEASE_VERSION") or ""
    expected_ref = os.environ.get("WF_RELEASE_REF") or ""
    release_tree = os.environ.get("WF_RELEASE_TREE") or H.RELEASE
    expected_digest = None
    manifest_path = os.path.join(release_tree, "wf-release.json")
    if os.path.isfile(manifest_path):
        with open(manifest_path, encoding="utf-8") as handle:
            expected_digest = (json.load(handle).get("compatibility") or {}).get("rules_digest")
    rec("候选安装记录 version", expected_version or "非空",
        record.get("version"), bool(record.get("version")) and record.get("version") != "0.0.0-dev")
    rec("候选安装记录 release_ref", expected_ref or "非空",
        record.get("release_ref"), bool(record.get("release_ref")))
    if expected_version and expected_ref:
        rec("安装记录与候选一致", f"{expected_version} / {expected_ref}",
            f"{record.get('version')} / {record.get('release_ref')}",
            record.get("version") == expected_version and record.get("release_ref") == expected_ref)
    if expected_digest:
        rec("安装规则摘要与候选一致", expected_digest, record.get("rules_digest"),
            record.get("rules_digest") == expected_digest)


def check_initialized():
    for relative in (".wf/baseline.md", ".wf/project-config.json", ".wf/spec/index.md",
                     ".wf/spec/pre-dev-checklist.md", ".wf/spec/quality-checklist.md"):
        exists = os.path.isfile(os.path.join(PROJECT, relative))
        rec(f"初始化产物 {relative}", "存在", "存在" if exists else "缺失", exists)


def run_ordinary():
    proc = subprocess.run([sys.executable, os.path.join(HERE, "f1_ordinary.py")],
                          capture_output=True, text=True,
                          env={**os.environ, "WF_FIX": PROJECT})
    tail = (proc.stdout or "").strip().splitlines()[-1:] or [""]
    rec("普通任务闭环（f1_ordinary）", "rc=0",
        f"rc={proc.returncode} {tail[0][:60]}", proc.returncode == 0)
    if proc.returncode != 0:
        print((proc.stdout or "")[-1500:])
        print((proc.stderr or "")[-1500:], file=sys.stderr)


def run_complex_review(root):
    task_id, task_dir = F.build_task(PROJECT, root, title="候选闭环：复杂审查",
                                     sid="sess-CAND", complexity="complex")
    pkg = os.path.join(PROJECT, "pkg")
    os.makedirs(pkg, exist_ok=True)
    with open(os.path.join(pkg, "b.py"), "w", encoding="utf-8") as handle:
        handle.write("b\n")
    rc, payload, record = F.run_review(PROJECT, root, task_id, task_dir, ["codex", "pi"],
                                       sid="sess-CAND")
    rec("复杂审查 review-decide", "rc=0", f"rc={rc} code={(payload or {}).get('code')}", rc == 0)
    reviews = record.get("reviews") or {}
    imported = [item for item in (reviews.get("imported") or []) if item.get("round") == 1]
    rec("两份协议报告已入库", "2 slots", f"imported={len(imported)}", len(imported) == 2)
    attempts = reviews.get("attempts") or []
    outcome = attempts[-1].get("outcome") if attempts else None
    rec("审查判定落盘", "pass", str(outcome), outcome == "pass")

    generation = H.generation(PROJECT)
    rc, payload = H.cli(PROJECT, ["sampling", "pick", "--task", task_id, "--freeze", "--json"],
                        sid="sess-CAND", inputs={"generation": generation})
    rec("归档前冻结抽样", "WF_OK", f"rc={rc} code={(payload or {}).get('code')}", rc == 0)
    generation = H.generation(PROJECT)
    rc, payload = H.cli(PROJECT, ["task-knowledge", "--task", task_id, "--decision", "no-update",
                                  "--json"], sid="sess-CAND", inputs={"generation": generation})
    rec("知识处置", "WF_OK", f"rc={rc} code={(payload or {}).get('code')}", rc == 0)
    with open(os.path.join(task_dir, "prd.md"), "rb") as handle:
        digest = "sha256:" + hashlib.sha256(handle.read()).hexdigest()
    decisions = [
        {"source": "human terminal (candidate smoke)", "at": "2026-11-13T00:00:00.000000Z",
         "subject": f"finish {task_id}: 人已了解结果与未核实项", "object_digest": digest,
         "choice": "finish", "reason": "候选闭环：复杂审查通过"},
        {"source": "human terminal (candidate smoke)", "at": "2026-11-13T00:00:00.000000Z",
         "subject": "pkg/a.py,pkg/b.py", "object_digest": digest,
         "choice": "commit", "reason": "授权提交本任务交付路径"},
    ]
    path = os.path.join(root, "candidate-archive.json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(decisions, handle, ensure_ascii=False)
    generation = H.generation(PROJECT)
    rc, payload = H.cli(PROJECT, ["archive", "--task", task_id, "--decision", path, "--json"],
                        sid="sess-CAND", inputs={"generation": generation})
    rec("归档", "WF_OK", f"rc={rc} code={(payload or {}).get('code')}", rc == 0)
    if rc != 0:
        print(json.dumps(payload, ensure_ascii=False)[:4000])
    released = ((payload or {}).get("facts") or {}).get("write_release") or {}
    rec("归档自动释放写权", "released", str(released.get("released")), bool(released.get("released")))


def main():
    import tempfile

    root = tempfile.mkdtemp(prefix="wf-candidate-smoke-")
    check_installation()
    check_initialized()
    run_ordinary()
    run_complex_review(root)
    with open(os.path.join(root, "candidate-smoke.json"), "w", encoding="utf-8") as handle:
        json.dump(RESULTS, handle, ensure_ascii=False, indent=2)
    failed = [item for item in RESULTS if not item["pass"]]
    print("saved", len(RESULTS), "checks;", len(RESULTS) - len(failed), "passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
