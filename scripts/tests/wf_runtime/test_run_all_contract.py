"""`run_all.sh` 的端到端契约（慢，默认跳过）：真子集、计划模式、失败传播、scope 隔离与成本账目。

跑法是**独占**的（`run_all.sh` 独占 fixture lease 与发行缓存），所以要显式开
`WF_SLOW_TESTS=1` 才执行；默认单元层只跑快测试。

隔离口径（design §3.1，AC3/AC4）：
- 整个 class 只有一个 owned scope（`fixture_scope.create_test_scope()`）+ 空 pool 布局；
- 每个 case 有自己的 `state`，同一 case 的多次调用共用 state（dev red→candidate auto）；
- 每次 runner 调用有独立的 `results`/`fixture`/`pycache`；
- **HOME 保持宿主值**：被测 SUT 的 check/归档判据依赖用户级环境（git 身份、执行器确认），
  A/B 实测把 HOME 指到 scope 内会让候选流程的 `task-check` 变成 `WF_CHECK_STALE`——
  改用假 HOME 会改变被测语义，所以隔离只施加在 runner 管理的写入口上，用户 cache 用快照断言证明未被触碰；
- 生产结果锁与用户 cache 只做快照比对（存在性 + inode/mtime），运行前后必须一致。

成本与 deadline（design §3.3，AC5/AC6）：每个 case 一个 900 秒单调 deadline，子调用按剩余
时间收紧超时；class/case 墙钟、cold/warm、release 构建状态、模板构建序列、取消窗口与清理
时间都写进 `<scope>/evidence/class-cost.json`（`WF_CONTRACT_KEEP_SCOPE=1` 时保留现场）。
"""

import atexit
import fcntl
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
FULL = REPO / "scripts" / "tests" / "wf_runtime" / "full"
RUN_ALL = FULL / "run_all.sh"
REPRO_RUN = FULL / "repro" / "run.sh"
sys.path.insert(0, str(FULL))
import fixture_scope  # noqa: E402
import host_snapshot  # noqa: E402

SLOW = os.environ.get("WF_SLOW_TESTS") == "1"
CLASS_DEADLINE_SECONDS = 900.0
CALL_TIMEOUT = 600
CANCEL_LOG_WAIT = 15.0
CANCEL_CLEANUP_WAIT = 5.0
PRODUCTION_PATHS = (Path.home() / ".cache" / "wf-test-release",
                    Path.home() / ".cache" / "wf-test-run",
                    Path.home() / ".cache" / "wf-candidate-repo",
                    Path("/tmp") / f"wf-test-results-{os.getuid()}.lock")
REQUIRED_ENV = ("WF_TEST_SCOPE_ROOT", "WF_TEST_RELEASE_CACHE", "WF_RESULTS_CACHE",
                "WF_TEST_RUN_CACHE", "WF_PYCACHE", "WF_RESULTS_DIR", "WF_FIX")


def fingerprint(path):
    try:
        stat = Path(path).stat()
    except OSError:
        return None
    return (stat.st_dev, stat.st_ino, stat.st_mtime_ns)


def production_snapshot():
    """逐调用轻量定位证据：存在性 + 顶层 inode/mtime（不是终态证明）。"""
    return {str(path): fingerprint(path) for path in PRODUCTION_PATHS}


def production_manifest():
    """类级终态证据：只读树清单（相对路径/类型/权限/字节摘要/链接目标）。"""
    return {str(path): host_snapshot.manifest(path) for path in PRODUCTION_PATHS}


def lines(path):
    try:
        return [line for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]
    except OSError:
        return []


def entries(path):
    try:
        return sorted(os.listdir(path))
    except OSError:
        return []


def tree_bytes(root):
    """整树（含链接目标）字节与相对路径快照，用于证明历史材料零触碰。"""
    root = Path(root)
    snapshot = {}
    if not root.exists():
        return snapshot
    for base, dirs, files in os.walk(root, followlinks=False):
        for name in sorted(dirs + files):
            path = Path(base) / name
            relative = str(path.relative_to(root))
            if path.is_symlink():
                snapshot[relative] = "link:" + os.readlink(path)
            elif path.is_dir():
                snapshot[relative + "/"] = "dir"
            else:
                snapshot[relative] = path.read_bytes()
    return snapshot


class CaseBudget:
    """一个逻辑 case 的 900 秒单调 deadline：子调用递减，耗尽即失败（不重置、不加时）。"""

    def __init__(self, seconds=CLASS_DEADLINE_SECONDS):
        self.deadline = time.monotonic() + seconds

    def remaining(self):
        return self.deadline - time.monotonic()

    def timeout(self, cap):
        left = self.remaining()
        if left <= 0:
            raise AssertionError("case deadline exhausted（900 秒分摊用完，不加时）")
        return min(left, cap)


class CaseWorkspace:
    """一个逻辑 case 的独立 state 与逐次调用的 results/fixture/pycache（HOME 保持宿主值）。"""

    def __init__(self, scope, name):
        self.scope = Path(scope)
        self.name = name
        self.root = self.scope / "cases" / name
        self.state = self.root / "state"
        self.private = self.scope / "private" / name
        self.private.mkdir(parents=True, exist_ok=True)
        self.calls = 0
        # 一个逻辑 case 的 prepare/warmup/主请求共享同一个单调 deadline（design §3.3 / AC6）。
        self.budget = CaseBudget()

    def env(self, **extra):
        self.calls += 1
        call = self.root / "calls" / f"{self.calls:02d}"
        for sub in ("results", "fixture", "pycache"):
            (call / sub).mkdir(parents=True, exist_ok=True)
        self.state.mkdir(parents=True, exist_ok=True)
        self.private.mkdir(parents=True, exist_ok=True)
        env = {
            "WF_TEST_SCOPE_ROOT": str(self.scope),
            "WF_TEST_RELEASE_CACHE": str(self.scope / "pool" / "test-release"),
            "WF_RESULTS_CACHE": str(self.scope / "pool" / "results-cache"),
            "WF_TEST_RUN_CACHE": str(self.state),
            "WF_PYCACHE": str(call / "pycache"),
            "WF_RESULTS_DIR": str(call / "results"),
            "WF_FIX": str(call / "fixture"),
        }
        missing = [key for key in REQUIRED_ENV if not env.get(key)]
        if missing:
            raise AssertionError("scope env 注入不完整：" + " ".join(missing))
        env.update(extra)
        return env


def write_class_cost(scope, cost):
    """teardown 证据写失败必须可见：返回错误字符串（None=成功），绝不以空报告掩盖。"""
    evidence = Path(scope) / "evidence" / "class-cost.json"
    try:
        evidence.parent.mkdir(parents=True, exist_ok=True)
        evidence.write_text(json.dumps(cost, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                            encoding="utf-8")
    except OSError as exc:
        return f"{evidence}: {exc}"
    return None


def should_keep_scope(leftovers, open_fds, host_changes, evidence_error, keep_env):
    """任何未闭合现场/宿主变化/证据失败都保留 scope，供人工复核。"""
    return bool(keep_env or leftovers or open_fds or host_changes or evidence_error)


@unittest.skipUnless(SLOW, "WF_SLOW_TESTS=1 才跑 run_all 端到端（独占夹具）")
class RunAllContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scope = fixture_scope.create_test_scope()
        # 单 scope 不是"随手建了就算"：marker 必须能被 read_scope 验回（AC3/AC10）。
        if fixture_scope.read_scope(cls.scope) != cls.scope:
            raise AssertionError("scope marker 不可验回")
        for relative in ("pool/results-cache", "pool/test-release", "cases", "private", "evidence"):
            (cls.scope / relative).mkdir(parents=True, exist_ok=True)
        # 空 pool：不允许沿用上一轮遗留的发行/模板条目来"借快路径"（AC3/AC17）。
        if entries(cls.scope / "pool" / "test-release"):
            raise AssertionError("pool/test-release 不是空的")
        if (cls.scope / "pool" / "results-cache" / "template").exists():
            raise AssertionError("pool/results-cache/template 不是空的")
        cls.production_before = production_manifest()
        cls.class_started = time.monotonic()
        cls.cost = {"schema_version": 1, "scope": str(cls.scope), "class_seconds": 0.0,
                    "cases": {}, "teardown_seconds": 0.0, "class_deadline_remaining": None,
                    "cancel_log_wait_seconds": None, "cleanup_seconds": None}

    @classmethod
    def tearDownClass(cls):
        # 先完成进程/FD/宿主保护断言，再决定是否回收 scope（AC10：证据写失败不得吞掉）。
        started = time.monotonic()
        leftovers = cls._scope_processes()
        open_in_scope = cls._own_descriptors_in_scope()
        cls.production_after = production_manifest()
        host_differences = {path: host_snapshot.compare(cls.production_before[path],
                                                        cls.production_after[path])
                            for path in cls.production_before}
        changed = {path: diff for path, diff in host_differences.items() if diff["changed"]}
        cls.cost["host_protection"] = host_differences
        remaining = CLASS_DEADLINE_SECONDS - (time.monotonic() - cls.class_started)
        cls.cost["teardown_seconds"] = round(time.monotonic() - started, 2)
        cls.cost["class_seconds"] = round(time.monotonic() - cls.class_started, 2)
        cls.cost["class_deadline_remaining"] = round(remaining, 2)
        cls.cost["longest_case_seconds"] = max(
            (sum(call["seconds"] for call in entry.get("calls") or [])
             + entry.get("candidate_prepare_seconds", 0.0))
            for entry in (cls.cost["cases"].values() or [{}]))
        evidence_error = write_class_cost(cls.scope, cls.cost)
        if evidence_error:
            cls.cost["evidence_write_error"] = evidence_error
            print(f"TEARDOWN-EVIDENCE-FAILED: {evidence_error}", file=sys.stderr)
        print("class-cost: " + json.dumps({key: cls.cost[key] for key in
                                           ("class_seconds", "teardown_seconds",
                                            "class_deadline_remaining", "longest_case_seconds",
                                            "cancel_log_wait_seconds", "cleanup_seconds")},
                                          ensure_ascii=False, sort_keys=True))
        for pid, cmdline in leftovers:
            print(f"LEFTOVER-PROCESS {pid}: {cmdline}", file=sys.stderr)
        for fd, target in open_in_scope:
            print(f"LEFTOVER-FD {fd}: {target}", file=sys.stderr)
        keep = should_keep_scope(leftovers, open_in_scope, changed, evidence_error,
                                 os.environ.get("WF_CONTRACT_KEEP_SCOPE") == "1")
        if keep:
            print(f"contract scope kept: {cls.scope}")
        else:
            shutil.rmtree(cls.scope, ignore_errors=True)
        problems = []
        if leftovers:
            problems.append(f"tearDownClass 仍有 {len(leftovers)} 个引用 scope 的进程残留")
        if open_in_scope:
            problems.append(f"tearDownClass 仍有 {len(open_in_scope)} 个指向 scope 的 FD 残留")
        if changed:
            problems.append("宿主缓存/生产结果锁的终态与类入口清单不一致："
                            + json.dumps(changed, ensure_ascii=False, sort_keys=True))
        if evidence_error:
            problems.append(f"teardown 证据写失败：{evidence_error}")
        if problems:
            raise AssertionError("; ".join(problems))

    @classmethod
    def _own_descriptors_in_scope(cls):
        """本进程（测试本体）不得仍持有 scope 内文件的 FD（AC3“无 FD 遗留”）。"""
        found = []
        for entry in Path("/proc/self/fd").iterdir():
            try:
                target = os.readlink(entry)
            except OSError:
                continue
            if str(cls.scope) in target:
                found.append((entry.name, target))
        return found

    @classmethod
    def _scope_processes(cls):
        """引用该 scope 的残留进程：cmdline **或环境**任一命中即算。

        只查 cmdline 是不够的：unit worker 的 argv 是 `bash run_one.sh <record>`，
        scope 只出现在它的环境里（`WF_TEST_SCOPE_ROOT`）。因此两个面都要查，
        并用 `test_scope_process_detector_sees_env_only_references` 证明检测器不是恒空。
        """
        marker = f"WF_TEST_SCOPE_ROOT={cls.scope}".encode()
        found, own = [], {os.getpid(), os.getppid()}
        for entry in Path("/proc").iterdir():
            if not entry.name.isdigit() or int(entry.name) in own:
                continue
            try:
                raw = (entry / "cmdline").read_bytes()
            except OSError:
                continue
            cmdline = raw.replace(b"\0", b" ").decode("utf-8", "replace").strip()
            detail = cmdline if str(cls.scope) in cmdline else ""
            if not detail:
                try:
                    environ = (entry / "environ").read_bytes()
                except OSError:
                    environ = b""
                if marker in environ.split(b"\0"):
                    detail = "(scope in environ) " + cmdline
            if detail:
                found.append((entry.name, detail))
        return found

    def test_scope_process_detector_sees_env_only_references(self):
        """检测器自证：只在环境里带 scope 的子进程也必须被判为残留。"""
        proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"],
                                env={**os.environ, "WF_TEST_SCOPE_ROOT": str(self.scope),
                                     "PYTHONPYCACHEPREFIX": "/tmp/wf-unit-pycache"})
        try:
            deadline = time.monotonic() + 5
            found = []
            while time.monotonic() < deadline and proc.poll() is None:
                found = [item for item in self._scope_processes() if item[0] == str(proc.pid)]
                if found:
                    break
                time.sleep(0.05)
            self.assertTrue(found, "只在 environ 里引用 scope 的子进程未被检测到")
            self.assertIn("environ", found[0][1])
        finally:
            proc.kill()
            proc.wait(timeout=5)

    def test_teardown_decision_keeps_the_scope_on_unclosed_facts(self):
        """证据失败/残留/宿主变化必须保留 scope，且与清理顺序无关。"""
        self.assertTrue(should_keep_scope([], [], {}, "disk full", False))
        self.assertTrue(should_keep_scope([("1", "x")], [], {}, None, False))
        self.assertTrue(should_keep_scope([], [("3", "x")], {}, None, False))
        self.assertTrue(should_keep_scope([], [], {"p": {}}, None, False))
        self.assertTrue(should_keep_scope([], [], {}, None, True))
        self.assertFalse(should_keep_scope([], [], {}, None, False))

    def test_class_cost_write_failure_is_reported_not_swallowed(self):
        with tempfile.TemporaryDirectory(prefix="wf-contract-cost-") as root:
            path = Path(root) / "evidence" / "class-cost.json"
            path.parent.mkdir()
            path.mkdir()  # 目录占位：write_text 必然失败
            error = write_class_cost(root, {"schema_version": 1})
            self.assertIsNotNone(error)
            self.assertIn("class-cost.json", error)

    # ---- 基座 ---------------------------------------------------------------
    def case(self, name):
        return CaseWorkspace(self.scope, name)

    def run_runner(self, case, args, env_extra=None, budget=None, timeout=CALL_TIMEOUT):
        budget = budget or case.budget
        env = case.env(**(env_extra or {}))
        before = production_snapshot()
        started = time.monotonic()
        completed = subprocess.run(["bash", str(RUN_ALL), *args], capture_output=True, text=True,
                                   cwd=str(REPO), env={**os.environ, **env},
                                   timeout=budget.timeout(timeout))
        seconds = round(time.monotonic() - started, 2)
        self.assertEqual(production_snapshot(), before,
                         "契约运行不得触碰生产结果锁/用户 cache（只读快照必须不变）")
        self.record(case, args, seconds, env, budget)
        return completed, seconds, env

    def record(self, case, args, seconds, env, budget):
        results = Path(env["WF_RESULTS_DIR"])
        summary = {}
        summary_path = results / "summary.json"
        if summary_path.is_file():
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
        entry = self.cost["cases"].setdefault(case.name, {"calls": []})
        entry["calls"].append({
            "args": list(args),
            "seconds": seconds,
            "cold": len(entry.get("calls") or []) == 0,
            "release_build": summary.get("release_build"),
            "template_build_sequences": summary.get("template_build_sequences"),
            "stages": lines(results / "stages"),
            "plan_calls": len(lines(results / "plan-calls")),
            "deadline_remaining": round(budget.remaining(), 2),
        })
        entry["deadline_remaining"] = round(budget.remaining(), 2)

    def test_case_budget_shares_one_deadline_and_refuses_exhaustion(self):
        """一个 case 一个单调 deadline：递减、耗尽即失败（不重置、不加时）。"""
        case = self.case("budget")
        self.assertLessEqual(case.budget.timeout(600), CLASS_DEADLINE_SECONDS)
        budget = CaseBudget(seconds=0.2)
        time.sleep(0.25)
        with self.assertRaises(AssertionError) as caught:
            budget.timeout(600)
        self.assertIn("deadline exhausted", str(caught.exception))
        # 同一 case 的后续调用必须消费同一个预算对象（不是每调用新建）。
        self.assertLess(case.budget.remaining(), CLASS_DEADLINE_SECONDS)
        self.assertIs(case.budget, case.budget)

    def assert_scope_locks_reacquirable(self):
        """取消之后：scope 结果锁与 fixture lease 必须能立刻重新获取（AC3/AC11）。"""
        saved = {key: os.environ.get(key) for key in
                 ("WF_TEST_SCOPE_ROOT", "WF_RESULTS_LOCK_FD", "WF_RESULTS_LOCK_PID",
                  "WF_RESULTS_LOCK_DOMAIN", "WF_RESULTS_LOCK_MNT", "WF_FIXTURE_LEASE_FD",
                  "WF_FIXTURE_LEASE_PID")}
        for key in ("WF_RESULTS_LOCK_FD", "WF_RESULTS_LOCK_PID", "WF_RESULTS_LOCK_DOMAIN",
                    "WF_RESULTS_LOCK_MNT", "WF_FIXTURE_LEASE_FD", "WF_FIXTURE_LEASE_PID"):
            os.environ.pop(key, None)
        os.environ["WF_TEST_SCOPE_ROOT"] = str(self.scope)
        try:
            fd = fixture_scope.acquire_results_lock()
            try:
                self.assertTrue(fixture_scope.verify_results_lock())
            finally:
                fcntl.flock(fd, fcntl.LOCK_UN)
                os.close(fd)
            lease = Path("/tmp") / f"wf-test-fixtures-{os.getuid()}.lock"
            lease_fd = os.open(lease, os.O_CREAT | os.O_RDWR, 0o600)
            try:
                fcntl.flock(lease_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            finally:
                fcntl.flock(lease_fd, fcntl.LOCK_UN)
                os.close(lease_fd)
        finally:
            for key, value in saved.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def counting_shim(self, case, target, name):
        """测试专用调用计数：记录 argv 后 exec 真实入口（不劫持 PATH、不改被测语义）。

        入口按 `[PY, <cli>, ...]` 调用，所以 shim 本身必须是 Python 脚本。
        """
        log = case.private / name
        shim = case.private / (name + ".py")
        shim.write_text(
            "import os, sys\n"
            f"with open({str(log)!r}, 'a', encoding='utf-8') as handle:\n"
            "    handle.write(' '.join(sys.argv[1:]) + '\\n')\n"
            f"os.execv(sys.executable, [sys.executable, {str(target)!r}] + sys.argv[1:])\n",
            encoding="utf-8")
        return shim, log

    def prepare_candidate(self, case, name="candidate", tamper=False):
        started = time.monotonic()
        manifest = json.loads((REPO / "docs/workflows/wf-release/wf-release.json").read_text())
        version = manifest["version"]
        candidate = case.private / name
        prepare = subprocess.run([
            sys.executable, str(FULL / "prepare_candidate_repo.py"),
            "--tree", str(REPO / "docs/workflows/wf-release"), "--version", version,
            "--out", str(candidate)], capture_output=True, text=True)
        self.assertEqual(prepare.returncode, 0, prepare.stdout + prepare.stderr)
        if tamper:
            install = candidate / "install.py"
            install.write_text(install.read_text() + "\n", encoding="utf-8")
        self.cost["cases"].setdefault(case.name, {"calls": []})["candidate_prepare_seconds"] = \
            round(time.monotonic() - started, 2)
        return candidate, version

    # ---- 计划面：零 warmup --------------------------------------------------
    def test_plan_only_runs_no_warmup_inside_the_scope(self):
        case = self.case("plan-only")
        release_cache = case.private / "release-cache"
        results_cache = case.private / "results-cache"
        result, _, env = self.run_runner(case, ["--list"],
                                         {"WF_TEST_RELEASE_CACHE": str(release_cache),
                                          "WF_RESULTS_CACHE": str(results_cache)})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "", "plan 摘要一律走 stderr，stdout 只放可 eval 赋值")
        self.assertEqual(entries(release_cache), [], "plan-only 不得构建测试发行")
        self.assertFalse((results_cache / "template").exists(), "plan-only 不得建模板缓存")
        self.assertEqual(entries(Path(env["WF_FIX"])), [], "plan-only 不得建夹具")

    def test_dry_run_only_mirrors_the_plan(self):
        case = self.case("dry-run")
        result, _, env = self.run_runner(case, ["--dry-run"], {"WF_SUITES": "r70_tests"})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("计划执行单元: 1", result.stderr)
        self.assertEqual(result.stdout.strip(), "")
        plan = json.loads((Path(env["WF_RESULTS_DIR"]) / "plan.json").read_text(encoding="utf-8"))
        self.assertEqual(plan["mode"], "subset")
        self.assertEqual([unit["name"] for unit in plan["units"]], ["r70_tests"])
        self.assertEqual(plan["repro_enabled"], 0)
        self.assertEqual(entries(Path(env["WF_RESULTS_DIR"])),
                         sorted([".wf-results-owner.json", "plan.json"]),
                         "显式镜像只允许 plan 与 owner marker")

    def test_conflicting_modes_exit_nonzero_without_touching_the_scope(self):
        case = self.case("conflict")
        result, _, env = self.run_runner(case, ["--full", "--subset"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("模式互斥", result.stderr)
        self.assertFalse((Path(env["WF_RESULTS_DIR"]) / "stages").exists(),
                         "计划期失败不得进入任何执行阶段")

    # ---- 真实子集：stage/plan 计数与成本账目（AC5/AC6）-----------------------
    def test_subset_runs_one_unit_and_reports_stages_plans_and_cost(self):
        # 冷建账目用 private 池：共享池可能已被别的 case 预热，built/reused 与模板首建不可判。
        case = self.case("subset")
        release_cache = case.private / "release-cache"
        results_cache = case.private / "results-cache"
        cold = {"WF_SUITES": "r70_tests", "WF_TEST_RELEASE_CACHE": str(release_cache),
                "WF_RESULTS_CACHE": str(results_cache)}
        result, _, env = self.run_runner(case, [], cold)
        self.assertEqual(result.returncode, 0, result.stdout[-2000:] + result.stderr[-2000:])
        self.assertIn("执行单元 1", result.stdout)
        self.assertIn("GATE-OK", result.stdout)
        self.assertNotIn("REPRO_TOTAL", result.stdout)
        self.assertNotIn("CLEANUP-UNKNOWN", result.stdout + result.stderr,
                         "正常 root started 不得被误报成 child unknown")
        results = Path(env["WF_RESULTS_DIR"])
        self.assertEqual(lines(results / "stages"), ["public", "lease", "execute"],
                         "一次真实 run = 3 个阶段（发行准备与锁都由 controller 持有）")
        self.assertFalse((results / "cancel-request").exists(),
                         "干净启动不得创建取消标记")
        self.assertEqual(len(lines(results / "plan-calls")), 2,
                         "一次真实 run = 2 次计划计算（preflight + final）")
        summary = json.loads((results / "summary.json").read_text(encoding="utf-8"))
        self.assertEqual(summary["suite_ran"], 1)
        self.assertEqual(summary["repro_ran"], 0)
        self.assertEqual(summary["flow_ran"], 0)
        self.assertTrue(summary["template_reused"], "默认应共用同一夹具源")
        self.assertIn(summary["template_source"], ("run-build", "cache"))
        self.assertEqual(summary["schema_version"], 4)
        self.assertEqual(summary["failure_kind"], None)
        control = json.loads((results / ".runner.json").read_text())
        self.assertEqual(control["control"]["schema_version"], 2)
        self.assertNotIn("observe", control["control"],
                         "默认执行不得观察历史材料")
        self.assertNotIn("success", control, "控制记录不再复制整次结论")
        self.assertEqual(control["control"]["assessment"]["evidence_state"], "complete")
        self.assertEqual(control["control"]["cleanup"]["cleanup_state"], "cleaned")
        state = json.loads((results / "run-state.json").read_text())
        self.assertEqual((state["state"], state["cleanup_state"], state["evidence_state"]),
                         ("finished", "cleaned", "complete"))
        self.assertEqual(state["run_id"], control["run_id"])
        self.assertEqual(summary["run_id"], control["run_id"])
        self.assertEqual(set(summary["input_evidence"]),
                         {"metrics", "plan", "context", "lines", "units", "repro"})
        self.assertEqual(summary["units_total"],
                         summary["suite_ran"] + summary["flow_ran"] + summary["repro_ran"])
        self.assertIn("budget", summary)
        self.assertGreaterEqual(summary["template_seconds"], 0)
        # 默认只建本代私有发行：不写、不恢复共享测试发行缓存。
        self.assertEqual(summary["release_build"], "built")
        self.assertEqual(entries(release_cache), [],
                         "默认执行不得写共享测试发行缓存（--no-build 才显式消费）")
        self.assertEqual(entries(results_cache / "template"), [],
                         "默认执行不得写跨 run 模板缓存（--template-cache 才显式申请）")
        self.assertEqual(summary["template_build_sequences"], 0,
                         "未申请跨 run 缓存时不发布模板条目")

        warm, _, warm_env = self.run_runner(case, [], cold)
        self.assertEqual(warm.returncode, 0, warm.stdout[-2000:])
        summary = json.loads((Path(warm_env["WF_RESULTS_DIR"]) / "summary.json").read_text(encoding="utf-8"))
        self.assertEqual(summary["release_build"], "built", "每次默认调用构建本代私有发行")
        self.assertEqual(summary["template_source"], "run-build")
        self.assertFalse(summary["template_cache_hit"])
        # 每调用独立 results/fixture/pycache：两次调用不得复用同一目录（AC3）。
        self.assertNotEqual(Path(env["WF_RESULTS_DIR"]), Path(warm_env["WF_RESULTS_DIR"]))
        self.assertNotEqual(Path(env["WF_FIX"]), Path(warm_env["WF_FIX"]))
        self.assertNotEqual(Path(env["WF_PYCACHE"]), Path(warm_env["WF_PYCACHE"]))
        entry = self.cost["cases"]["subset"]
        self.assertEqual([call["cold"] for call in entry["calls"]], [True, False],
                         "同一 case 的首次调用是 cold，后续是 warm")
        # 一个 case 共享同一个 900 秒 deadline：后续调用的剩余量必须更小（AC6）。
        self.assertLess(entry["calls"][1]["deadline_remaining"],
                        entry["calls"][0]["deadline_remaining"],
                        "case 级 deadline 必须跨调用递减")
        # 重复使用同一结果目录：执行不得接管已有产物；拒绝发生在写 owner/plan 之前。
        before_files = sorted(os.listdir(results))
        reused, _, _ = self.run_runner(case, [], dict(cold, WF_RESULTS_DIR=str(results)))
        self.assertNotEqual(reused.returncode, 0, reused.stdout[-2000:])
        self.assertIn("RESULTS-INIT-FAILED", reused.stdout + reused.stderr)
        self.assertEqual(sorted(os.listdir(results)), before_files,
                         "拒绝不得改写或清理已有结果")
        # 显式申请跨 run 模板缓存：首次发布、同输入第二次命中，命中不重建条目。
        cache_env_extra = dict(cold, WF_NO_TEMPLATE_CACHE="", WF_TEMPLATE_CACHE="1")
        publish, _, publish_env = self.run_runner(case, ["--template-cache"],
                                                  cache_env_extra)
        self.assertEqual(publish.returncode, 0, publish.stdout[-2000:])
        first = json.loads((Path(publish_env["WF_RESULTS_DIR"]) / "summary.json").read_text())
        self.assertEqual(first["template_source"], "cache")
        self.assertFalse(first["template_cache_hit"], "首次显式缓存申请发布条目")
        warm_cache, _, cache_env = self.run_runner(case, ["--template-cache"],
                                                  cache_env_extra)
        self.assertEqual(warm_cache.returncode, 0, warm_cache.stdout[-2000:])
        cached = json.loads((Path(cache_env["WF_RESULTS_DIR"]) / "summary.json").read_text())
        self.assertEqual(cached["template_source"], "cache")
        self.assertTrue(cached["template_cache_hit"])
        self.assertEqual(cached["template_build_sequences"], 0)
        self.assertNotEqual(entries(results_cache / "template"), [],
                            "显式模板缓存条目必须建在 scope 内")

    def test_default_run_leaves_history_and_shared_caches_untouched(self):
        """R1/A1：默认执行只写本次材料；历史结果/共享发行/模板/证明缓存零触碰。"""
        case = self.case("history-zero-touch")
        env = case.env(WF_SUITES="r70_tests")
        results_cache = Path(env["WF_RESULTS_CACHE"])
        release_cache = Path(env["WF_TEST_RELEASE_CACHE"])
        run_cache = Path(env["WF_TEST_RUN_CACHE"])
        template_cache = results_cache / "template"
        legacy = results_cache / "run-legacy"
        (legacy / "logs").mkdir(parents=True)
        (legacy / "hand-written.json").mkdir()
        (legacy / "logs" / "manual.log").write_text("manual\n")
        (legacy / "summary.json").write_text('{"status": "ok", "manual": true}\n')
        (legacy / "run-state.json").write_text('{"hand": "written"}\n')
        (template_cache / "old-slot").mkdir(parents=True)
        (template_cache / "old-slot" / "payload.txt").write_text("template\n")
        (release_cache / "0.0.0-old").mkdir(parents=True)
        (release_cache / "0.0.0-old" / "install.py").write_text("raise SystemExit(0)\n")
        (run_cache / "repro-state.json").write_text('{"schema_version": 5, "cases": {}}\n')
        (run_cache / "proof.json").write_text('{"proven": true}\n')
        template_before = tree_bytes(template_cache)
        before = {path: tree_bytes(path) for path in
                  (results_cache, release_cache, run_cache)}
        result, _, env_used = self.run_runner(case, [], {"WF_SUITES": "r70_tests"})
        self.assertEqual(result.returncode, 0, result.stdout[-2000:] + result.stderr[-2000:])
        for path, snapshot in before.items():
            self.assertEqual(tree_bytes(path), snapshot,
                             f"默认执行触碰了历史/共享材料：{path}")
        summary = json.loads((Path(env_used["WF_RESULTS_DIR"]) / "summary.json").read_text())
        self.assertEqual(summary["release_build"], "built")
        private_release = Path(env_used["WF_RESULTS_DIR"]) / "release"
        self.assertFalse(private_release.exists(), "本代私有发行在收尾后回收")
        # 正向对照：显式 --template-cache 才写跨 run 模板缓存。
        cached_run, _, _ = self.run_runner(case, ["--template-cache"],
                                           {"WF_SUITES": "r70_tests"})
        self.assertEqual(cached_run.returncode, 0,
                         cached_run.stdout[-2000:] + cached_run.stderr[-2000:])
        self.assertNotEqual(tree_bytes(template_cache), template_before,
                             "显式缓存入口必须真的写入模板条目")
        # 正向对照：--no-build 显式消费预备好的共享发行（只读 check，不删除）。
        shared_version = "0.1.0"
        shared = release_cache / shared_version
        prepared = subprocess.run(
            [sys.executable, str(REPO / "scripts" / "tests" / "wf_test_release.py"),
             "--ensure", "--version", shared_version, "--root", str(shared)],
            capture_output=True, text=True, env={**os.environ, **env}, cwd=str(REPO))
        self.assertEqual(prepared.returncode, 0, prepared.stdout[-1000:] + prepared.stderr[-1000:])
        consumed, _, consumed_env = self.run_runner(
            case, ["--no-build"], {"WF_SUITES": "r70_tests",
                                   "WF_TEST_RELEASE_VERSION": shared_version})
        self.assertEqual(consumed.returncode, 0, consumed.stdout[-2000:] + consumed.stderr[-2000:])
        summary = json.loads((Path(consumed_env["WF_RESULTS_DIR"]) / "summary.json").read_text())
        self.assertEqual(summary["release_build"], "checked")
        self.assertTrue(shared.exists(), "共享发行只释放消费租约，不得删除")

    def test_template_can_be_disabled_for_determinism(self):
        case = self.case("no-template")
        result, _, env = self.run_runner(case, [], {"WF_SUITES": "r70_tests",
                                                    "WF_NO_TEMPLATE": "1"})
        self.assertEqual(result.returncode, 0, result.stdout[-2000:])
        summary = json.loads((Path(env["WF_RESULTS_DIR"]) / "summary.json").read_text())
        self.assertFalse(summary["template_reused"], "WF_NO_TEMPLATE=1 时逐套件重建夹具")
        self.assertGreater(summary["init_seconds"], 0)
        self.assertEqual(summary["template_build_sequences"], 0)

    def test_fake_runner_contract_propagates_failure_budget_and_serial_gaps(self):
        """原 R67 假树断言：失败传播、零退出、期望用例数预算、串行段证据缺口。"""
        from scripts.tests.wf_runtime import fake_runner_contract
        records = fake_runner_contract.run(str(self.scope))
        self.assertEqual(len(records), 4, records)
        for name, record in records.items():
            self.assertTrue(record["ok"], f"{name}: {record['actual']}")

    def test_failing_suite_makes_the_gate_fail(self):
        # f1_candidate_smoke 在 dev 部署下必须失败（安装记录是 0.0.0-dev）
        case = self.case("gate-fail")
        result, _, _ = self.run_runner(case, [], {"WF_SUITES": "f1_candidate_smoke"})
        self.assertNotEqual(result.returncode, 0, result.stdout[-2000:])
        self.assertIn("GATE-FAIL", result.stdout + result.stderr)

    def test_stale_test_release_is_refused_in_a_private_pool(self):
        case = self.case("stale-release")
        private_cache = case.private / "empty-cache"
        private_cache.mkdir()
        shared = self.scope / "pool" / "test-release"
        before = entries(shared)
        result, _, _ = self.run_runner(case, ["--no-build"],
                                       {"WF_SUITES": "r70_tests",
                                        "WF_TEST_RELEASE_CACHE": str(private_cache)})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("TEST-RELEASE-STALE", result.stdout + result.stderr)
        self.assertEqual(entries(shared), before, "private 池的失败不得污染共享池")

    # ---- candidate 面 -------------------------------------------------------
    def test_candidate_representative_from_empty_state_has_owned_flow_fixtures(self):
        case = self.case("candidate-representative")
        candidate, version = self.prepare_candidate(case)
        shim, log = self.counting_shim(case, FULL / "prepare_candidate_repo.py", "validator-calls")
        release_shim, release_log = self.counting_shim(
            case, REPO / "scripts" / "tests" / "wf_test_release.py", "release-calls")
        result, _, env = self.run_runner(
            case, ["--representative", "--fixture-deploy", "candidate",
                   "--release-root", str(candidate), "--release-version", version,
                   "--release-ref", f"refs/tags/wf-v{version}", "--repro", "green",
                   "--repro-group", "install"],
            {"WF_CANDIDATE_VALIDATOR": str(shim), "WF_TEST_RELEASE_CLI": str(release_shim)})
        self.assertEqual(result.returncode, 0, result.stdout[-3000:] + result.stderr[-2000:])
        summary = json.loads((Path(env["WF_RESULTS_DIR"]) / "summary.json").read_text())
        self.assertEqual(summary["flow_ran"], 2)
        self.assertEqual(summary["fail"], 0)
        calls = lines(log)
        self.assertEqual(len(calls), 2, "candidate validator 必须在起始与结束 barrier 各调用一次")
        self.assertTrue(all("--check" in call for call in calls))
        self.assertEqual(lines(release_log), [],
                         "candidate 模式不得构建 dev 测试发行（AC5）")

    def test_candidate_worker_cancel_cleans_fixtures_and_releases_leases(self):
        """R3/A3：候选 worker 启动后取消——仍按本代事实清理夹具，候选根只释放租约。"""
        case = self.case("candidate-cancel")
        candidate, version = self.prepare_candidate(case)
        env = case.env(WF_JOBS="1")
        results = Path(env["WF_RESULTS_DIR"])
        proc = subprocess.Popen(
            ["bash", str(RUN_ALL), "--representative", "--fixture-deploy", "candidate",
             "--release-root", str(candidate), "--release-version", version,
             "--release-ref", f"refs/tags/wf-v{version}", "--repro", "none"],
            cwd=str(REPO), env={**os.environ, **env},
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            deadline = time.monotonic() + CANCEL_LOG_WAIT
            while time.monotonic() < deadline:
                if any(results.glob("*.test.log")):
                    break
                if proc.poll() is not None:
                    break
                time.sleep(0.05)
            self.assertTrue(any(results.glob("*.test.log")), "候选 worker 未启动")
            proc.terminate()
            stdout, stderr = proc.communicate(timeout=CANCEL_CLEANUP_WAIT)
        finally:
            if proc.poll() is None:
                proc.kill()
            proc.communicate(timeout=CANCEL_CLEANUP_WAIT)
        output = (stdout or b"").decode(errors="replace") + (stderr or b"").decode(errors="replace")
        self.assertNotEqual(proc.returncode, 0, output[-2000:])
        control = json.loads((results / ".runner.json").read_text())
        self.assertEqual(control["control"]["cleanup"]["cleanup_state"], "cleaned")
        target = control["control"]["target"]["status"]
        self.assertIn(target, ("cancelled", "failed"), output[-2000:])
        if (results / "summary.json").exists():
            summary = json.loads((results / "summary.json").read_text())
            self.assertEqual(summary["status"], "failed")
            self.assertEqual(summary["failure_kind"], "cancelled")
            self.assertNotIn("GATE-OK", output)
        plan = json.loads((results / "plan.json").read_text())
        self.assertFalse(Path(plan["fix"]).exists(), "已确认的本代夹具必须回收")
        self.assertFalse(Path(plan["fix"] + ".legacy").exists())
        self.assertTrue(candidate.exists(), "候选根只释放消费租约，不得删除")
        self.assert_scope_locks_reacquirable()
        # 新目录重跑：取消没有留下不可再取的租约/现场。
        rerun, _, _ = self.run_runner(
            case, ["--representative", "--fixture-deploy", "candidate",
                   "--release-root", str(candidate), "--release-version", version,
                   "--release-ref", f"refs/tags/wf-v{version}", "--repro", "none"],
            {"WF_JOBS": "1"})
        self.assertEqual(rerun.returncode, 0, rerun.stdout[-2000:] + rerun.stderr[-2000:])
        self.assertIn("GATE-OK", rerun.stdout)

    def test_candidate_final_check_cancel_is_attributed_without_success(self):
        """R3/A3：终核阶段取消——归因为未完成/取消，仍清理且不产生候选通过。"""
        case = self.case("candidate-final-cancel")
        candidate, version = self.prepare_candidate(case)
        log = case.private / "validator-calls"
        shim = case.private / "validator-cancel.py"
        shim.write_text(
            "import os, sys\n"
            f"log = {str(log)!r}\n"
            "with open(log, 'a', encoding='utf-8') as handle:\n"
            "    handle.write(' '.join(sys.argv[1:]) + '\\n')\n"
            f"count = len(open(log, encoding='utf-8').read().splitlines())\n"
            "if count >= 2:\n"
            "    cancel = os.environ.get('WF_CANCEL_FILE')\n"
            "    if cancel and not os.path.exists(cancel):\n"
            "        open(cancel, 'x', encoding='utf-8').write('final-check cancel\\n')\n"
            "    raise SystemExit(1)\n"
            f"os.execv(sys.executable, [sys.executable, {str(FULL / 'prepare_candidate_repo.py')!r}] + sys.argv[1:])\n",
            encoding="utf-8")
        result, _, env = self.run_runner(
            case, ["--representative", "--fixture-deploy", "candidate",
                   "--release-root", str(candidate), "--release-version", version,
                   "--release-ref", f"refs/tags/wf-v{version}", "--repro", "none"],
            {"WF_CANDIDATE_VALIDATOR": str(shim), "WF_JOBS": "1"})
        output = result.stdout + result.stderr
        self.assertNotEqual(result.returncode, 0, output[-2000:])
        self.assertIn("CANDIDATE-FINAL-INCOMPLETE", output)
        self.assertNotIn("GATE-OK", output)
        results = Path(env["WF_RESULTS_DIR"])
        control = json.loads((results / ".runner.json").read_text())
        self.assertEqual(control["control"]["cleanup"]["cleanup_state"], "cleaned")
        self.assertIn("failure", control["control"])
        if (results / "summary.json").exists():
            summary = json.loads((results / "summary.json").read_text())
            self.assertEqual((summary["status"], summary["failure_kind"]),
                             ("failed", "cancelled"))
        plan = json.loads((results / "plan.json").read_text())
        self.assertFalse(Path(plan["fix"]).exists())

    def test_candidate_dirty_worktree_fails_the_start_barrier_without_workers(self):
        case = self.case("candidate-dirty")
        candidate, version = self.prepare_candidate(case, tamper=True)
        shim, log = self.counting_shim(case, FULL / "prepare_candidate_repo.py", "validator-calls")
        result, _, env = self.run_runner(
            case, ["--representative", "--fixture-deploy", "candidate",
                   "--release-root", str(candidate), "--release-version", version,
                   "--release-ref", f"refs/tags/wf-v{version}", "--repro", "none"],
            {"WF_CANDIDATE_VALIDATOR": str(shim)})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("CANDIDATE-REPO-INVALID", result.stdout + result.stderr)
        results = Path(env["WF_RESULTS_DIR"])
        self.assertEqual(len(lines(log)), 1, "坏候选只走到起始 barrier")
        self.assertEqual(lines(results / "stages"), ["public", "lease"],
                         "起始 barrier 失败不得进入 execute（worker 不启动）")
        self.assertEqual(entries(results / "logs"), ["release-prepare.log"],
                         "起始 barrier 只留下本次准备命令的证据日志，没有 worker 日志")

    def test_candidate_mode_requires_a_valid_candidate_repo(self):
        case = self.case("candidate-bogus")
        bogus = case.private / "bogus"
        bogus.mkdir()
        # canonical sidecar 存在但仓库本身不是候选产物：起始 validator 必须在 worker 前拒绝。
        Path(str(bogus) + ".meta.json").write_text("{}\n", encoding="utf-8")
        result, _, env = self.run_runner(
            case, ["--representative", "--fixture-deploy", "candidate",
                   "--release-root", str(bogus), "--release-ref", "refs/tags/wf-v9.9.9",
                   "--release-version", "9.9.9"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("CANDIDATE-REPO-INVALID", result.stdout + result.stderr)
        self.assertNotIn("execute", lines(Path(env["WF_RESULTS_DIR"]) / "stages"),
                         "坏候选不得进入 execute")

    def test_candidate_mode_rejects_red_repro_at_plan_time(self):
        case = self.case("candidate-red")
        candidate, version = self.prepare_candidate(case)
        result, _, env = self.run_runner(
            case, ["--representative", "--fixture-deploy", "candidate",
                   "--release-root", str(candidate), "--release-version", version,
                   "--release-ref", f"refs/tags/wf-v{version}", "--repro", "both"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("candidate 模式只允许 --repro green|auto", result.stderr + result.stdout)
        self.assertFalse((Path(env["WF_RESULTS_DIR"]) / "plan.json").exists(),
                         "计划期拒绝不得落 plan")

    def test_candidate_auto_requires_and_then_uses_matching_dev_red(self):
        """AC7 真实正反例：无 dev red 时拒绝，同内容/version/ref 的 dev red 后执行 candidate green。"""
        case = self.case("candidate-auto")
        candidate, version = self.prepare_candidate(case)
        candidate_args = ["--representative", "--fixture-deploy", "candidate",
                          "--release-root", str(candidate), "--release-version", version,
                          "--release-ref", f"refs/tags/wf-v{version}",
                          "--repro", "auto", "--repro-group", "install"]
        release_shim, release_log = self.counting_shim(
            case, REPO / "scripts" / "tests" / "wf_test_release.py", "release-calls")
        missing, _, _ = self.run_runner(case, candidate_args,
                                        {"WF_TEST_RELEASE_VERSION": version,
                                         "WF_TEST_RELEASE_CLI": str(release_shim)})
        self.assertEqual(lines(release_log), [],
                         "candidate 计划期拒绝不得触碰 dev 发行 CLI")
        self.assertNotEqual(missing.returncode, 0)
        self.assertIn("缺少同名主体的有效 dev red", missing.stdout + missing.stderr)
        red_dir = case.root / "red"
        env = case.env(WF_TEST_RELEASE_VERSION=version, WF_TEST_RELEASE_CLI=str(release_shim))
        red = subprocess.run(
            [sys.executable, str(FULL / "fixture_scope.py"), "lease-results", "--",
             "bash", str(REPRO_RUN), "--mode", "both", "--group", "install",
             "--results-dir", str(red_dir)],
            capture_output=True, text=True, env={**os.environ, **env},
            cwd=str(REPO), timeout=case.budget.timeout(CALL_TIMEOUT))
        self.assertEqual(red.returncode, 0, red.stdout[-2000:] + red.stderr[-2000:])
        self.assertEqual(len(lines(release_log)), 1,
                         "独立 repro 入口按自身请求 ensure/check 恰好一次")
        positive, _, _ = self.run_runner(case, candidate_args,
                                         {"WF_TEST_RELEASE_VERSION": version,
                                          "WF_TEST_RELEASE_CLI": str(release_shim)})
        self.assertEqual(positive.returncode, 0,
                         positive.stdout[-2000:] + positive.stderr[-2000:])
        self.assertIn("repro 用例：3/3", positive.stdout)
        self.assertEqual(len(lines(release_log)), 1,
                         "candidate green 复用 dev red 证明时不得再建 dev 发行")

    # ---- 证据注入点（AC9）--------------------------------------------------
    def test_embedded_repro_does_not_rebuild_the_release(self):
        case = self.case("embedded-repro")
        shim, log = self.counting_shim(case, REPO / "scripts" / "tests" / "wf_test_release.py",
                                       "release-calls")
        result, _, _ = self.run_runner(
            case, ["--repro", "green", "--repro-group", "install"],
            {"WF_SUITES": "r70_tests", "WF_WITH_REPRO": "1", "WF_TEST_RELEASE_CLI": str(shim)})
        self.assertEqual(result.returncode, 0, result.stdout[-3000:] + result.stderr[-2000:])
        self.assertEqual(len(lines(log)), 1,
                         "内嵌 repro 不得再 ensure/check（只剩 controller 准备的一次）")
        self.assertFalse((Path(self.scope) / "cases" / "embedded-repro" / "state"
                          / "repro-state.json").exists(), "green 运行不得读写共享 proof")

    def test_repro_concurrent_with_no_build_uses_the_inherited_frame(self):
        case = self.case("repro-concurrent")
        warm, _, _ = self.run_runner(case, [], {"WF_SUITES": "r70_tests"})
        self.assertEqual(warm.returncode, 0, warm.stdout[-2000:])
        # --no-build 是显式消费预备好的共享发行：先由维护入口准备。
        version = "0.1.0"
        shared = Path(self.scope / "pool" / "test-release" / version)
        prepared = subprocess.run(
            [sys.executable, str(REPO / "scripts" / "tests" / "wf_test_release.py"),
             "--ensure", "--version", version, "--root", str(shared)],
            capture_output=True, text=True, env={**os.environ, **case.env()},
            cwd=str(REPO))
        self.assertEqual(prepared.returncode, 0, prepared.stdout[-1000:] + prepared.stderr[-1000:])
        shim, log = self.counting_shim(case, REPO / "scripts" / "tests" / "wf_test_release.py",
                                       "release-calls")
        result, _, _ = self.run_runner(
            case, ["--repro", "green", "--repro-group", "install", "--repro-concurrent",
                   "--no-build"],
            {"WF_SUITES": "r70_tests", "WF_WITH_REPRO": "1",
             "WF_TEST_RELEASE_CLI": str(shim), "WF_TEST_RELEASE_VERSION": version})
        self.assertEqual(result.returncode, 0, result.stdout[-3000:] + result.stderr[-2000:])
        self.assertIn("repro 与主池并发", result.stdout)
        self.assertEqual(len(lines(log)), 1, "--no-build 只在 controller 准备阶段 check 一次")

    def test_unreadable_head_falls_back_to_a_run_owned_template(self):
        case = self.case("head-unreadable")
        warm, _, _ = self.run_runner(case, [], {"WF_SUITES": "r70_tests"})
        self.assertEqual(warm.returncode, 0, warm.stdout[-2000:])
        cache = self.scope / "pool" / "results-cache" / "template"
        before = entries(cache)
        shim = case.private / "git-broken.sh"
        shim.write_text("#!/bin/bash\nexit 1\n", encoding="utf-8")
        shim.chmod(0o755)
        result, _, env = self.run_runner(case, ["--no-build", "--template-cache"],
                                         {"WF_SUITES": "r70_tests", "WF_GIT_BIN": str(shim)})
        self.assertEqual(result.returncode, 0, result.stdout[-3000:] + result.stderr[-2000:])
        self.assertIn("dev HEAD 不可读", result.stdout)
        summary = json.loads((Path(env["WF_RESULTS_DIR"]) / "summary.json").read_text())
        self.assertEqual(summary["template_source"], "run-build")
        self.assertFalse(summary["template_cache_hit"])
        self.assertEqual(entries(cache), before, "HEAD 不可读时不得读写跨 run 模板缓存")

    # ---- controller / finalize / 发布故障（AC02/AC10/AC14）-------------------
    def _fault_run(self, name, fault, extra=None):
        case = self.case(name)
        env = {"WF_SUITES": "r70_tests", "WF_JOBS": "1",
               "WF_TEST_FAULT_INJECTION": "1", "WF_RUNNER_FINALIZE_FAULT": fault}
        env.update(extra or {})
        result, _, env_used = self.run_runner(case, [], env)
        return result, Path(env_used["WF_RESULTS_DIR"])

    def test_controller_and_finalize_faults_never_sign_success(self):
        for fault in ("assess-exception", "assess-none", "assess-empty", "assess-malformed",
                      "assess-contradictory", "delete-oserror", "control-write-oserror",
                      "summary-exception", "summary-malformed"):
            with self.subTest(fault=fault):
                result, results = self._fault_run("fault-" + fault, fault)
                output = result.stdout + result.stderr
                self.assertNotEqual(result.returncode, 0, output[-1500:])
                self.assertNotIn("GATE-OK", output)
                state_path = results / "run-state.json"
                if state_path.exists():
                    state = json.loads(state_path.read_text())
                    if fault == "summary-malformed":
                        # 提交点之前的记录已写；落盘的摘要必须不是可读的通过对象。
                        written = json.loads((results / "summary.json").read_text())
                        self.assertNotEqual(written.get("status"), "ok")
                    else:
                        self.assertFalse(state.get("state") == "finished"
                                         and state.get("cleanup_state") == "cleaned",
                                         f"{fault}: 不得写 finished-cleaned")
                plan = json.loads((results / "plan.json").read_text())
                if fault in ("assess-exception", "assess-none", "assess-empty",
                             "assess-malformed", "assess-contradictory", "delete-oserror"):
                    self.assertTrue(Path(plan["fix"]).exists(),
                                    f"{fault}: 清理未确认/失败时必须保留现场")

    def test_delete_after_first_reports_exact_partial_completion(self):
        result, results = self._fault_run("fault-delete-after-first", "delete-after-first")
        output = result.stdout + result.stderr
        self.assertNotEqual(result.returncode, 0, output[-1500:])
        self.assertNotIn("GATE-OK", output)
        plan = json.loads((results / "plan.json").read_text())
        self.assertFalse(Path(plan["fix"]).exists(), "第一项 owned 资源已删除")
        self.assertTrue(Path(plan["fix"] + ".legacy").exists(), "第二项必须保留")
        control = json.loads((results / ".runner.json").read_text())
        cleanup = control["control"]["cleanup"]
        self.assertEqual(cleanup["cleanup_state"], "failed")
        self.assertEqual(cleanup["removed"], ["FIX"])
        self.assertEqual(cleanup["failed"], ["LEGACY_FIXTURE_ROOT"])
        self.assertEqual(cleanup["retained_paths"], [plan["fix"] + ".legacy"])
        state = json.loads((results / "run-state.json").read_text())
        self.assertEqual(state["state"], "finished")
        self.assertEqual(state["cleanup_state"], "failed",
                         "删除失败必须如实记为 failed（不得降成 unknown 或 cleaned）")

    def test_state_finish_failure_keeps_the_run_active(self):
        result, results = self._fault_run("fault-state-finish", "state-finish-oserror")
        output = result.stdout + result.stderr
        self.assertNotEqual(result.returncode, 0, output[-1500:])
        self.assertNotIn("GATE-OK", output)
        state = json.loads((results / "run-state.json").read_text())
        self.assertEqual(state["state"], "active", "run-state 终写失败必须保留 active")
        # 下一次运行不得自动复用 active 现场。
        case = self.case("fault-state-finish-retry")
        retry, _, _ = self.run_runner(case, [], {"WF_SUITES": "r70_tests", "WF_JOBS": "1",
                                                 "WF_RESULTS_DIR": str(results)})
        self.assertNotEqual(retry.returncode, 0)
        self.assertIn("RESULTS-INIT-FAILED", retry.stdout + retry.stderr)

    def test_metrics_handoff_faults_are_rejected_by_the_reader(self):
        for fault in ("metrics-write-oserror", "metrics-missing", "metrics-truncated",
                      "metrics-old-run", "metrics-input-mismatch"):
            with self.subTest(fault=fault):
                result, results = self._fault_run("metrics-" + fault, fault)
                output = result.stdout + result.stderr
                self.assertNotEqual(result.returncode, 0, output[-1500:])
                self.assertNotIn("GATE-OK", output)
                state = json.loads((results / "run-state.json").read_text())
                self.assertFalse(state.get("state") == "finished"
                                 and state.get("cleanup_state") == "cleaned",
                                 f"{fault}: metrics 失败不得写 finished-cleaned")
                if (results / "summary.json").exists():
                    summary = json.loads((results / "summary.json").read_text())
                    self.assertNotEqual(summary.get("status"), "ok")

    def test_metric_fault_selectors_do_not_leak_into_units(self):
        result, results = self._fault_run("metrics-no-leak", "metrics-missing")
        for name in ("r70_tests.out",):
            text = (results / name).read_text(encoding="utf-8", errors="replace")
            self.assertNotIn("WF_METRICS_FAULT", text)

    # ---- 模板事务真实入口（AC04/AC19）-------------------------------------
    def test_repro_state_writer_failure_blocks_the_inner_success_exit(self):
        # proof writer 现在是 controller 的唯一一次提交：写失败必须阻断成功出口，
        # 但仍如实收口真实清理事实（资源已释放、证据不完整），不伪造状态文件。
        case = self.case("repro-state-fail")
        state = case.private / "readonly-state"
        state.mkdir()
        state.chmod(0o555)
        self.addCleanup(lambda: state.chmod(0o755))
        # green 不写共享 proof；写失败只能用含 red 相位的合格证明来触发。
        result, _, env = self.run_runner(
            case, ["--repro", "both", "--repro-group", "install"],
            {"WF_SUITES": "r70_tests", "WF_WITH_REPRO": "1", "WF_REPRO_JOBS": "1",
             "WF_TEST_RUN_CACHE": str(state)})
        output = result.stdout + result.stderr
        self.assertNotEqual(result.returncode, 0, output[-2000:])
        self.assertNotIn("GATE-OK", output)
        self.assertIn("RUNNER-FINALIZE-FAILED", output + result.stderr)
        self.assertEqual(entries(state), [], "写失败不得留下 proof 或临时文件")
        results = Path(env["WF_RESULTS_DIR"])
        control = json.loads((results / ".runner.json").read_text())
        self.assertEqual(control["control"]["cleanup"]["cleanup_state"], "cleaned",
                         "真实清理事实保留在控制记录里")
        run_state = json.loads((results / "run-state.json").read_text())
        self.assertNotIn("status", run_state)
        self.assertEqual(run_state["cleanup_state"], "unknown",
                         "失败 run 不得留下 finished-cleaned 签名")
        self.assertEqual(run_state["evidence_state"], "incomplete")
        if (results / "summary.json").exists():
            summary = json.loads((results / "summary.json").read_text())
            self.assertNotEqual(summary.get("status"), "ok")

    def test_template_window_recovers_through_the_real_run_all_entry(self):
        case = self.case("template-window")
        env_extra = {"WF_SUITES": "r70_tests"}
        first, _, env = self.run_runner(case, ["--template-cache"], env_extra)
        self.assertEqual(first.returncode, 0, first.stdout[-2000:] + first.stderr[-2000:])
        results = Path(env["WF_RESULTS_DIR"])
        cache = Path(env["WF_RESULTS_CACHE"]) / "template"
        self.assertTrue(entries(cache), "显式模板缓存的首次真实 run 必须发布条目")
        fault = dict(env_extra, WF_TEST_FAULT_INJECTION="1",
                     WF_TEMPLATE_TXN_REBUILD="1",
                     WF_TEMPLATE_TXN_STOP_AFTER="after-journal")
        failed, _, _ = self.run_runner(case, ["--template-cache"], fault)
        self.assertNotEqual(failed.returncode, 0)
        self.assertIn("TEMPLATE-CACHE-FAILED", failed.stdout + failed.stderr)
        recovered, _, env = self.run_runner(case, ["--template-cache"], env_extra)
        self.assertEqual(recovered.returncode, 0,
                         recovered.stdout[-2000:] + recovered.stderr[-2000:])
        self.assertIn("TEMPLATE-CACHE-RECOVERED: rolled-back", recovered.stderr)
        self.assertIn("GATE-OK", recovered.stdout)
        # 显式维护入口（inventory）证明恢复后无未完成 journal/待恢复条目。
        inventory = subprocess.run(
            [sys.executable, str(FULL / "template_cache.py"), "inventory",
             "--cache-root", str(cache), "--format", "json"],
            capture_output=True, text=True, cwd=str(REPO))
        report = json.loads(inventory.stdout or "{}")
        self.assertEqual([item for item in report.get("entries") or []
                          if item["kind"] == "journal"], [],
                         "恢复后不得残留未完成事务")
        self.assertFalse([name for name in entries(cache) if name.endswith(".journal.json")],
                         "真实入口恢复后不得残留 journal")

    # ---- 初始化真死亡（AC08/AC09）-----------------------------------------
    def _seed_cleaned_results(self, case):
        env_extra = {"WF_SUITES": "r70_tests"}
        result, _, env = self.run_runner(case, [], env_extra)
        self.assertEqual(result.returncode, 0, result.stdout[-2000:] + result.stderr[-2000:])
        return env_extra, Path(env["WF_RESULTS_DIR"])

    def _plane_owner(self, results):
        return json.loads((results / ".wf-results-owner.json").read_text())

    def test_init_checkpoint_death_leaves_identity_and_blocks_reuse(self):
        """空/不存在目的地 × 三个点：helper os._exit(97)，shell 原样退出，现场不被重做。"""
        points = ("after-owner-intent", "after-run-state-before-dirs",
                  "after-dirs-before-controller")
        for index, point in enumerate(points):
            with self.subTest(point=point):
                case = self.case(f"init-first-{index}")
                results = Path(case.env()["WF_RESULTS_DIR"])
                fault = {"WF_SUITES": "r70_tests", "WF_RESULTS_DIR": str(results),
                         "WF_TEST_FAULT_INJECTION": "1",
                         "WF_RESULTS_INIT_STOP_AFTER": point}
                proc, _, _ = self.run_runner(case, [], fault)
                self.assertEqual(proc.returncode, 97,
                                 proc.stdout[-1000:] + proc.stderr[-1000:])
                self.assertIn("WF-RESULTS-INIT-STOP", proc.stderr)
                self.assertNotIn("RUN_ID=", proc.stdout, "死亡窗口不得给成功 run_id")
                self.assertFalse((results / ".runner.json").exists(),
                                 "helper 死后不得启动本代 controller")
                owner = self._plane_owner(results)
                self.assertEqual((owner["schema_version"], owner["intent"]),
                                 (2, "execution"))
                state_path = results / "run-state.json"
                if point == "after-owner-intent":
                    self.assertFalse(state_path.exists(), "本代 state 尚未写")
                else:
                    self.assertTrue(state_path.exists())
                # 新入口不得把死亡现场降级成 plan-only/legacy；也不得自动删现场。
                retry, _, _ = self.run_runner(
                    case, [], dict(fault, WF_TEST_FAULT_INJECTION="0",
                                   WF_RESULTS_INIT_STOP_AFTER=""))
                self.assertNotEqual(retry.returncode, 0)
                self.assertIn("RESULTS-INIT-FAILED", (retry.stdout + retry.stderr))
                self.assertTrue((results / ".wf-results-owner.json").exists())
                # 锁必须真实释放：scope 结果锁与 fixture lease 均可再次获取。
                self.assert_scope_locks_reacquirable()

    def test_plan_only_and_finished_destinations_are_refused_before_checkpoint(self):
        case = self.case("init-refuse")
        env_extra = {"WF_SUITES": "r70_tests"}
        mirror_dir = Path(case.env(**env_extra)["WF_RESULTS_DIR"])
        mirror, _, _ = self.run_runner(case, ["--list"], dict(env_extra,
                                                             WF_RESULTS_DIR=str(mirror_dir)))
        self.assertEqual(mirror.returncode, 0, mirror.stderr)
        owner_before = (mirror_dir / ".wf-results-owner.json").read_bytes()
        plan_before = (mirror_dir / "plan.json").read_bytes()
        proc, _, _ = self.run_runner(case, [], dict(env_extra, WF_RESULTS_DIR=str(mirror_dir)))
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("RESULTS-INIT-FAILED", proc.stdout + proc.stderr)
        self.assertEqual((mirror_dir / ".wf-results-owner.json").read_bytes(), owner_before,
                         "已有计划镜像不得被改写")
        self.assertEqual((mirror_dir / "plan.json").read_bytes(), plan_before)
        # 已完成的正式结果：执行/预览均不接管；字节与目录项保持不变。
        seed_case = self.case("init-refuse-finished")
        _, results = self._seed_cleaned_results(seed_case)
        before = sorted(os.listdir(results))
        before_bytes = {name: (results / name).read_bytes()
                        for name in before if (results / name).is_file()}
        second, _, _ = self.run_runner(seed_case, [],
                                       dict(env_extra, WF_RESULTS_DIR=str(results)))
        self.assertNotEqual(second.returncode, 0)
        self.assertIn("RESULTS-INIT-FAILED", second.stdout + second.stderr)
        self.assertEqual(sorted(os.listdir(results)), before)
        for name, data in before_bytes.items():
            self.assertEqual((results / name).read_bytes(), data, f"{name} 被改写")

    def test_controller_holds_the_release_lease_for_the_whole_run(self):
        """R1：发行消费锁由 root controller 从准备持有到收尾，正常结束后可重获。"""
        case = self.case("release-lease")
        warm, _, _ = self.run_runner(case, [], {"WF_SUITES": "r70_tests", "WF_JOBS": "1"})
        self.assertEqual(warm.returncode, 0, warm.stdout[-2000:])
        env = case.env(WF_SUITES="r68_tests", WF_JOBS="1")
        results = Path(env["WF_RESULTS_DIR"])
        proc = subprocess.Popen(["bash", str(RUN_ALL)], cwd=str(REPO),
                                env={**os.environ, **env},
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            deadline = time.monotonic() + CANCEL_LOG_WAIT
            while not (results / "release-context.json").exists() and time.monotonic() < deadline:
                if proc.poll() is not None:
                    break
                time.sleep(0.02)
            self.assertTrue((results / "release-context.json").exists(),
                            "没等到已核 context，无法在运行中核发行锁")
            plan = json.loads((results / "plan.json").read_text())
            root = plan["test_release_root"]
            contender = subprocess.run([sys.executable, str(REPO / "scripts" / "release_lock.py"),
                                        "--acquire", "--root", root],
                                       capture_output=True, text=True)
            self.assertEqual(contender.returncode, 75,
                             "运行中另一进程必须 busy：" + contender.stdout + contender.stderr)
            stdout, stderr = proc.communicate(timeout=case.budget.timeout(CALL_TIMEOUT))
            self.assertEqual(proc.returncode, 0, stdout.decode()[-2000:] + stderr.decode()[-2000:])
            reacquired = subprocess.run([sys.executable, str(REPO / "scripts" / "release_lock.py"),
                                         "--acquire", "--root", root],
                                        capture_output=True, text=True)
            self.assertEqual(reacquired.returncode, 0, "正常结束后同一 inode 必须可重获")
        finally:
            if proc.poll() is None:
                proc.kill()
            proc.communicate(timeout=CANCEL_CLEANUP_WAIT)

    # ---- 取消面（AC3/AC11）-------------------------------------------------
    def test_interrupting_root_runner_cleans_its_command_and_fixtures(self):
        case = self.case("cancel")
        warm, _, _ = self.run_runner(case, [], {"WF_SUITES": "r70_tests", "WF_JOBS": "1"})
        self.assertEqual(warm.returncode, 0, warm.stdout[-2000:])   # 显式 warmup，先证 cache ready
        env = case.env(WF_SUITES="r68_tests", WF_JOBS="1")
        results = Path(env["WF_RESULTS_DIR"])
        before = production_snapshot()
        proc = subprocess.Popen(["bash", str(RUN_ALL)], cwd=str(REPO),
                                env={**os.environ, **env},
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        log_path = results / "r68_tests.test.log"
        started = time.monotonic()
        try:
            deadline = time.monotonic() + CANCEL_LOG_WAIT
            while not log_path.exists() and time.monotonic() < deadline:
                if proc.poll() is not None:
                    break
                time.sleep(0.05)
            self.cost["cancel_log_wait_seconds"] = round(time.monotonic() - started, 2)
            self.assertIsNone(proc.poll(), "runner 在取消探针之前就退出了")
            self.assertTrue(log_path.exists(), "15 秒窗口内没等到 worker 日志")
            proc.terminate()
            cleanup_started = time.monotonic()
            stdout, stderr = proc.communicate(timeout=CANCEL_CLEANUP_WAIT)
            self.cost["cleanup_seconds"] = round(time.monotonic() - cleanup_started, 2)
            self.assertNotEqual(proc.returncode, 0, stdout.decode() + stderr.decode())
            control = json.loads((results / ".runner.json").read_text())
            self.assertEqual(control["control"]["target"]["status"], "cancelled")
            self.assertNotIn("success", control, "取消结论由摘要/退出码表达，不复制到控制记录")
            self.assertEqual(control["state"], "finished")
            self.assertEqual(control["control"]["cleanup"]["cleanup_state"], "cleaned")
            if (results / "summary.json").exists():
                summary = json.loads((results / "summary.json").read_text())
                self.assertEqual(summary["status"], "failed")
                self.assertEqual(summary["failure_kind"], "cancelled")
            state = json.loads((results / "run-state.json").read_text())
            self.assertNotIn("status", state, "run-state 只记录生命周期/清理/证据事实")
            self.assertEqual(state["cleanup_state"], "cleaned",
                             "取消完成清理后必须如实记录清理事实")
            self.assertEqual(state["evidence_state"], "incomplete",
                             "取消导致证据不完整；复用由证据门禁阻断，不靠篡改 cleanup")
            plan = json.loads((results / "plan.json").read_text())
            self.assertFalse(Path(plan["fix"]).exists(), "取消后夹具必须回收")
            self.assertFalse((results / "template").exists(), "取消后 run 内模板必须回收")
            self.assert_scope_locks_reacquirable()
        finally:
            if proc.poll() is None:
                proc.kill()
            proc.communicate(timeout=CANCEL_CLEANUP_WAIT)
        self.assertEqual(production_snapshot(), before,
                         "取消不得触碰生产结果锁/用户 cache")

    def test_pre_published_cancel_request_is_kept_and_cancels_the_run(self):
        """R3：内层只发布、不删除/改写请求；已存在的请求必须保字节与 inode。"""
        case = self.case("cancel-marker")
        warm, _, _ = self.run_runner(case, [], {"WF_SUITES": "r70_tests", "WF_JOBS": "1"})
        self.assertEqual(warm.returncode, 0, warm.stdout[-2000:])
        env = case.env(WF_REPRO_JOBS="1")
        results = Path(env["WF_RESULTS_DIR"])
        proc = subprocess.Popen(
            [sys.executable, str(FULL / "fixture_scope.py"), "lease-results", "--",
             "bash", str(REPRO_RUN), "--mode", "green", "--group", "install",
             "--results-dir", str(results)],
            cwd=str(REPO), env={**os.environ, **env},
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        marker = results / "cancel-request"
        try:
            deadline = time.monotonic() + CANCEL_LOG_WAIT
            while not (results / "release-context.json").exists() and time.monotonic() < deadline:
                if proc.poll() is not None:
                    break
                time.sleep(0.02)
            self.assertTrue((results / "release-context.json").exists(),
                            "没等到已核 context，取消探针无法在准备完成后发布请求")
            marker.write_text("human cancel request\n", encoding="utf-8")
            before = (marker.stat().st_ino, marker.read_bytes())
            stdout, stderr = proc.communicate(timeout=case.budget.timeout(CALL_TIMEOUT))
            self.assertNotEqual(proc.returncode, 0, stdout.decode()[-2000:] + stderr.decode()[-2000:])
            after = (marker.stat().st_ino, marker.read_bytes())
            self.assertEqual(after, before, "已发布的取消请求不得被删除或改写")
            control = json.loads((results / ".runner.json").read_text())
            self.assertEqual(control["control"]["target"]["status"], "cancelled")
            self.assertNotIn("success", control)
            state = json.loads((results / "run-state.json").read_text())
            if (results / "summary.json").exists():
                summary = json.loads((results / "summary.json").read_text())
                self.assertEqual((summary["status"], summary["failure_kind"]),
                                 ("failed", "cancelled"))
            self.assertEqual(state["evidence_state"], "incomplete")
            self.assertFalse((Path(env["WF_TEST_RUN_CACHE"]) / "repro-state.json").exists(),
                             "取消到达成功边界前不得发布 proof")
        finally:
            if proc.poll() is None:
                proc.kill()
            proc.communicate(timeout=CANCEL_CLEANUP_WAIT)

    def test_cleanup_unknown_preserves_the_fixture_site(self):
        """AC08：命令级 cleanup unknown 时保留夹具现场，不删除、不重试、不签成功。"""
        case = self.case("cleanup-unknown")
        result, _, env = self.run_runner(
            case, [], {"WF_SUITES": "r70_tests", "WF_JOBS": "1",
                       "WF_TEST_FAULT_INJECTION": "1", "WF_UNIT_FAULT": "kill"})
        self.assertNotEqual(result.returncode, 0, result.stdout[-2000:])
        self.assertIn("CLEANUP-UNKNOWN", result.stdout + result.stderr)
        self.assertIn("GATE-FAIL", result.stdout + result.stderr)
        results = Path(env["WF_RESULTS_DIR"])
        summary = json.loads((results / "summary.json").read_text())
        self.assertEqual(summary["cleanup_state"], "unknown")
        plan = json.loads((results / "plan.json").read_text())
        self.assertTrue(Path(plan["fix"]).exists(),
                        "命令级清理未知时必须保留夹具现场，不得删除")

    # ---- AC18：SUT 级 escape（只覆盖“资产落点越界”这一向量）------------------
    def test_install_refuses_a_symlink_asset_target_outside_the_project(self):
        """AC18/AC19：**资产落点本身**是指向项目外的符号链接 → 整批拒绝，项目外零写入。

        向量 = `proj/.wf/bin/wf.py -> outside/evil.py`（destination symlink）；这里直接走
        安装产物的真实 CLI，`plan_writes()` 的项目→基址→资产两层校验负责拒绝。
        """
        case = self.case("sut-escape")
        env = case.env()
        ensure = subprocess.run(
            [sys.executable, str(REPO / "scripts" / "tests" / "wf_test_release.py"), "--ensure",
             "--json", "--root", str(self.scope / "pool" / "test-release" / "0.1.0")],
            capture_output=True, text=True, env={**os.environ, **env}, cwd=str(REPO),
            timeout=case.budget.timeout(CALL_TIMEOUT))
        self.assertEqual(ensure.returncode, 0, ensure.stdout + ensure.stderr)
        release = json.loads(ensure.stdout)["root"]
        version = json.loads(ensure.stdout)["version"]
        project = Path(env["WF_FIX"]) / "proj"
        outside = Path(env["WF_FIX"]) / "outside"
        project.mkdir(parents=True)
        outside.mkdir(parents=True)
        sentinel = outside / "evil.py"
        sentinel.write_text("sentinel\n", encoding="utf-8")
        (project / ".wf" / "bin").mkdir(parents=True)
        os.symlink(sentinel, project / ".wf" / "bin" / "wf.py")   # 落点被带出项目
        result = subprocess.run(
            [sys.executable, os.path.join(release, "install.py"), "--target", str(project),
             "--source", release, "--release-ref", f"refs/tags/wf-v{version}",
             "--platform", "claude", "--confirm", "--json"],
            capture_output=True, text=True, env={**os.environ, **env}, cwd=str(REPO),
            timeout=case.budget.timeout(CALL_TIMEOUT))
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertRegex(result.stdout, r"WF_(ASSET_DECISION|PATH_INVALID)",
                         "SUT 必须用受控错误码拒绝越界写入")
        self.assertEqual(entries(outside), ["evil.py"], "outside 兄弟目录不得被写入任何内容")
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "sentinel\n", "项目外文件不得被改写")

    def test_install_refuses_a_symlinked_skill_root_outside_the_project(self):
        """AC19：技能根（或其它祖先）指向项目外 → install.py 整批拒绝，不写穿。

        几何关系（刻意不污染宿主）：`proj` 与 `outside` 都是本 case 的 `WF_FIX`
        （owned scope）下兄弟目录；逃逸目标仍在 owned scope 内，只是位于“项目”之外。
        产品修复前此处会写进 `outside/` 13 个技能目录；现在必须返回拒绝码且外部不变。
        """
        case = self.case("sut-skill-root-boundary")
        env = case.env()
        ensure = subprocess.run(
            [sys.executable, str(REPO / "scripts" / "tests" / "wf_test_release.py"), "--ensure",
             "--json", "--root", str(self.scope / "pool" / "test-release" / "0.1.0")],
            capture_output=True, text=True, env={**os.environ, **env}, cwd=str(REPO),
            timeout=case.budget.timeout(CALL_TIMEOUT))
        self.assertEqual(ensure.returncode, 0, ensure.stdout + ensure.stderr)
        release = json.loads(ensure.stdout)["root"]
        version = json.loads(ensure.stdout)["version"]
        project = Path(env["WF_FIX"]) / "proj-skills"
        outside = Path(env["WF_FIX"]) / "outside-skills"
        project.mkdir(parents=True)
        outside.mkdir(parents=True)
        (outside / "sentinel.txt").write_text("keep\n", encoding="utf-8")
        (project / ".claude").mkdir()
        os.symlink(outside, project / ".claude" / "skills")
        gap = subprocess.run(
            [sys.executable, os.path.join(release, "install.py"), "--target", str(project),
             "--source", release, "--release-ref", f"refs/tags/wf-v{version}",
             "--platform", "claude", "--confirm", "--json"],
            capture_output=True, text=True, env={**os.environ, **env}, cwd=str(REPO),
            timeout=case.budget.timeout(CALL_TIMEOUT))
        self.assertNotEqual(gap.returncode, 0, gap.stdout + gap.stderr)
        self.assertRegex(gap.stdout, r"WF_(ASSET_DECISION|PATH_INVALID)",
                         "技能根越界必须用受控错误码整批拒绝")
        self.assertEqual(entries(outside), ["sentinel.txt"], "项目外目标不得被写入任何内容")
        self.assertEqual((outside / "sentinel.txt").read_text(encoding="utf-8"), "keep\n")

if __name__ == "__main__":
    unittest.main()
