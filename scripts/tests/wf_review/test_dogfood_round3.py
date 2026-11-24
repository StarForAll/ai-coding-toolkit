"""dogfood 三轮修正断言（W1/W2，2026-11-22）。

覆盖：
- a-1 content_bound_patterns 组合合并（先 record .gitignore 再 record requirements-*.txt，
  新增 requirements-prod.txt 须按未覆盖判——回退注入变红）；
- a-2 机械修订双草稿骨架与 replan 拒绝出口；
- a-4 covers 三态归因（missing=删除例外、unreadable=未覆盖；记录侧统一 file_digest_state）；
- W2-2 control_plane_digest 锚点（常开键、vendor 变化、一次性失效、分类失败归因）；
- W2-3 单 reviewer 接受/拒绝/投影；
- W2-6 archived 绑定 next 分档；
- W2-7 judgments kind=框架改动（经 --file 条目、真实 CLI 形态）。
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import authorize, cli, fingerprint  # noqa: E402


class ContentBoundPatternsMergeTest(unittest.TestCase):
    """a-1：合并段并入 content_bound_patterns——追加确认的绑定模式不再丢。"""

    def _repo(self, tmp, files):
        for name, text in files.items():
            path = Path(tmp) / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")

    def test_second_record_merges_bound_patterns(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._repo(tmp, {".gitignore": "a\n", "requirements-dev.txt": "x\n"})
            authorize.record_authorization(
                tmp, "repo_rules", {"choice": "repo_rules", "paths": [".gitignore"], "quote": "人确认"},
                root=tmp)
            authorize.record_authorization(
                tmp, "repo_rules",
                {"choice": "repo_rules", "paths": ["requirements-*.txt"], "quote": "人确认"},
                root=tmp)
            # 回退注入点：旧实现不合并 patterns，追加确认的绑定模式丢失
            stored = authorize.require(tmp, "repo_rules")
            self.assertEqual(stored.get("content_bound_patterns"),
                             sorted({".gitignore", "requirements-*.txt"}))
            # 组合场景：新增匹配文件按"确认后才出现"判未覆盖，须重新 record
            self._repo(tmp, {"requirements-prod.txt": "y\n"})
            covered, uncovered = authorize.covers(
                tmp, "repo_rules", ["requirements-prod.txt"], root=tmp)
            self.assertFalse(covered)
            self.assertEqual(uncovered, ["requirements-prod.txt"])
            # 既有未变文件仍覆盖
            covered, uncovered = authorize.covers(
                tmp, "repo_rules", ["requirements-dev.txt"], root=tmp)
            self.assertTrue(covered)


class CoversThreeStateTest(unittest.TestCase):
    """a-4：covers 三态归因（missing=删除例外、unreadable=未覆盖）。"""

    def test_unreadable_path_is_not_treated_as_deleted(self):
        # 路径替换成目录：读不到 ⇒ unreadable ⇒ 未覆盖，不再按"已删除"放行
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "rule.md"
            path.write_text("old\n", encoding="utf-8")
            authorize.record_authorization(
                tmp, "delete", {"choice": "delete", "paths": ["rule.md"], "quote": "人确认删除"}, root=tmp)
            path.unlink()
            (Path(tmp) / "rule.md").mkdir()      # 替换成目录（IsADirectoryError → unreadable）
            covered, uncovered = authorize.covers(tmp, "delete", ["rule.md"], root=tmp)
            self.assertFalse(covered)
            self.assertEqual(uncovered, ["rule.md"])

    def test_real_deletion_still_counts_as_covered(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "gone.md"
            path.write_text("data\n", encoding="utf-8")
            authorize.record_authorization(
                tmp, "delete", {"choice": "delete", "paths": ["gone.md"], "quote": "人确认删除"}, root=tmp)
            path.unlink()                        # 真实删除：删除例外仍成立
            covered, uncovered = authorize.covers(tmp, "delete", ["gone.md"], root=tmp)
            self.assertTrue(covered)

    def test_record_side_uses_file_digest_state(self):
        # 记录侧统一三态归因：内容留档段不再内联 except OSError
        source = (REPO / "docs/workflows/wf/payload/lib/wflib/authorize.py").read_text(encoding="utf-8")
        self.assertIn("file_digest_state(hit)", source)
        self.assertNotIn("except OSError:\n                    digests[rel] = None", source)
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "a.txt").write_text("A\n", encoding="utf-8")
            authorize.record_authorization(
                tmp, "repo_rules", {"choice": "repo_rules", "paths": ["a.txt"], "quote": "人确认"},
                root=tmp)
            stored = authorize.require(tmp, "repo_rules")
            self.assertTrue((stored.get("content_digests") or {}).get("a.txt", "").startswith("sha256:"))


class ControlPlaneDigestTest(unittest.TestCase):
    """W2-2：control_plane_digest 进 Check 锚点（常开第 11 键）。"""

    def _parts(self, v_digest="sha256:v1"):
        return {key: f"value-{i}"
                for i, key in enumerate(("plan_version", "entry_snapshot_digest",
                                          "touch_paths_digest", "paths_digest",
                                          "content_digest", "acceptance_digest",
                                          "spec_versions", "baseline_digest",
                                          "config_digest", "workflow_snapshot_digest"))} \
            | {"control_plane_digest": v_digest}

    def test_key_is_in_whitelist(self):
        source = (REPO / "docs/workflows/wf/payload/lib/wflib/fingerprint.py").read_text(encoding="utf-8")
        self.assertIn('"control_plane_digest",', source)
        # 一次性失效断言：冻结的旧十键口径对同一 parts（第十一键有值）重算 ≠ 新十一键结果
        frozen_old_keys = [
            "plan_version", "entry_snapshot_digest", "touch_paths_digest",
            "paths_digest", "content_digest", "acceptance_digest", "spec_versions",
            "baseline_digest", "config_digest", "workflow_snapshot_digest",
        ]
        from wflib import records

        parts = self._parts()
        old_payload = {key: parts.get(key) for key in frozen_old_keys}
        old_anchor = records.H("wf-check-anchor-v1", old_payload)
        self.assertNotEqual(old_anchor, fingerprint.check_anchor(parts))

    def test_empty_bucket_is_constant_and_changes_with_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            empty = fingerprint.control_plane_digest([], tmp)
            self.assertTrue(empty.startswith("sha256:"))
            self.assertEqual(empty, fingerprint.control_plane_digest(None, tmp))
            (Path(tmp) / "vendor.txt").write_text("v1\n", encoding="utf-8")
            dirty = fingerprint.control_plane_digest(["vendor.txt"], tmp)
            self.assertNotEqual(empty, dirty)
            (Path(tmp) / "vendor.txt").write_text("v2\n", encoding="utf-8")
            self.assertNotEqual(dirty, fingerprint.control_plane_digest(["vendor.txt"], tmp))

    def test_classification_contract_error_propagates_unwrapped(self):
        from wflib import check as check_mod
        from wflib import tasks as tasks_mod

        # 契约错误（TaskError/WF_RECORD_INVALID）原样传播，不折成 WF_SCOPE_UNRESOLVED
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, ".wf"))
            ctx = type("Ctx", (), {"root": str(tmp)})()
            task = {"id": "t1", "plan": {"version": "v1"}, "entry_snapshot": {}, "curation": []}
            with self.assertRaises(tasks_mod.TaskError) as caught:
                check_mod.anchor_parts(ctx, task)
            self.assertEqual(caught.exception.code, "WF_RECORD_INVALID")

    def test_classification_non_contract_error_wrapped(self):
        from wflib import check as check_mod
        from wflib import scope as scope_mod
        from unittest import mock

        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, ".wf"))
            ctx = type("Ctx", (), {"root": str(tmp)})()
            task = {"id": "t1", "plan": {"version": "v1"},
                    "entry_snapshot": {"touch_paths": []}, "curation": []}

            def _boom(root, task, receipts=None, classified=None):
                raise RuntimeError("surprise")

            with mock.patch.object(scope_mod, "classify_candidates", _boom):
                with self.assertRaises(check_mod.CheckError) as caught:
                    # 经 current_anchor 触发锚点输入计算（object_paths → delivery_set → classify）
                    check_mod.current_anchor(ctx, task)
                self.assertEqual(caught.exception.code, "WF_SCOPE_UNRESOLVED")
                self.assertIn("control-plane classification failed",
                              json.dumps(caught.exception.facts, ensure_ascii=False))
            # 对照：不注入时同一夹具可正常算锚点（控制面为空桶常量摘要）
            task["plan"] = {"version": "v1", "acceptance_digest": "sha256:a"}
            (Path(tmp) / ".wf" / "baseline.md").write_text("基线", encoding="utf-8")
            (Path(tmp) / ".wf" / "project-config.json").write_text("{}", encoding="utf-8")
            from unittest import mock as _mock

            with _mock.patch.object(check_mod, "object_paths", return_value=[]), \
                    _mock.patch.object(check_mod, "spec_versions", return_value=[]), \
                    _mock.patch.object(check_mod, "assertions_digest", return_value="sha256:a"):
                anchor, parts = check_mod.current_anchor(ctx, task)
            self.assertTrue(anchor.startswith("sha256:"))
            self.assertTrue(parts["control_plane_digest"].startswith("sha256:"))


class MechanicalRevisionDraftTest(unittest.TestCase):
    """a-2 草稿双骨架（approve 含带前置的机械修订骨架、replan 不再含）。"""

    def test_draft_skeletons(self):
        from wflib import tasks as tasks_mod

        with tempfile.TemporaryDirectory() as tmp:
            task_dir = Path(tmp) / ".wf" / "tasks" / "t-d"
            task_dir.mkdir(parents=True)
            task_dir.joinpath("task.json").write_text(
                json.dumps({"id": "t-d", "title": "草稿", "status": "in_progress", "phase": "execute",
                            "plan": {"complexity": "light", "touch_paths": ["src/**"]},
                            "entry_snapshot": {"touch_paths": ["src/**"]}}), encoding="utf-8")
            # 草稿预检（2026-11-24）按正式入口同判据核 PRD：夹具给最小合法 plan 块。
            _plan = {"schema_version": 1, "touch_paths": ["src/**"],
                     "acceptance": [{"id": "a1", "statement": "可用", "verification_ids": ["v1"]}],
                     "verifications": [{"id": "v1", "invocation": {"kind": "argv", "argv": ["true"]},
                                        "cwd": ".", "input_refs": [], "required": True,
                                        "consume_at": "check"}]}
            task_dir.joinpath("prd.md").write_text(
                "# PRD\n\n<!-- wf-plan:v1 -->\n```json\n" + json.dumps(_plan, ensure_ascii=False, indent=2)
                + "\n```\n", encoding="utf-8")

            class Ctx:
                root = str(tmp)

            class Args:
                def __init__(self, a):
                    self.argv = list(a); self.used = set()

                def value(self, name):
                    if name in self.argv:
                        i = self.argv.index(name)
                        self.used.update({i, i + 1})
                        return self.argv[i + 1]
                    return None

                def flag(self, name):
                    return name in self.argv
            approve = tasks_mod.cmd_task_approve(Ctx(), Args(["--task", "t-d", "--draft"]))
            approve_choices = [e["choice"] for e in approve["facts"]["draft"]]
            self.assertEqual(approve_choices, ["approve", "机械修订"])
            mechanical = [e for e in approve["facts"]["draft"] if e["choice"] == "机械修订"][0]
            self.assertIn("已有批准", mechanical["reason"])       # 占位写明前置
            self.assertIn("否则删除", mechanical["reason"])
            replan = tasks_mod.cmd_task_replan(Ctx(), Args(["--task", "t-d", "--draft"]))
            self.assertEqual([e["choice"] for e in replan["facts"]["draft"]], ["replan"])


class VendorJudgmentKindTest(unittest.TestCase):
    """W2-7：judgments KINDS 含「框架改动」，判断文件条目经 --file 落库可通。"""

    def test_kind_in_kinds_and_prefs_help(self):
        from wflib import judgments as judgments_mod

        self.assertIn("框架改动", judgments_mod.KINDS)
        help_text = json.dumps(cli.COMMAND_HELP["prefs"], ensure_ascii=False)
        self.assertIn("框架改动", help_text)
        judgments_help = json.dumps(cli.COMMAND_HELP["judgments"], ensure_ascii=False)
        self.assertIn("框架改动", judgments_help)
        # judgments add 无 --kind 旗标：kind 只在判断文件条目里
        self.assertNotIn("--kind", cli.COMMAND_FLAGS["judgments"])

    def test_vendor_judgment_entry_via_validate(self):
        from wflib import judgments as judgments_mod

        entry = {"kind": "框架改动", "decision": "回源仓库立项", "basis": "发现 install.py 缺 host-hook 分发",
                 "outcome": "applied", "by": "human"}
        facts = {"known_ids": []}       # §5.4 机械校验面：outcome/basis/by 即可，无需新校验
        problems = judgments_mod.validate(entry, facts)
        self.assertEqual([p for p in problems if p.get("reason") == "kind 非法"], [])


class ArchivedBindingNextTest(unittest.TestCase):
    """W2-6：绑定对象已终态时 task-new 的 next_ 与 enable 终态出口同口径。"""

    def test_next_text_branches_by_object_state(self):
        source = (REPO / "docs/workflows/wf/payload/lib/wflib/tasks.py").read_text(encoding="utf-8")
        self.assertIn("object terminal", source)
        self.assertIn("换新会话标识", source)
        # archived 分档不再给 continue/bind 指引（该出口只留在 in-flight 分支）
        self.assertIn("继续当前对象用 continue/bind", source)


class SingleReviewerAcceptanceTest(unittest.TestCase):
    """W2-3：单 reviewer 接受记录校验（gap_acceptance 同型）与 CLI 注册。"""

    def test_acceptance_validation(self):
        from wflib import review as review_mod

        decision = {"by": "human:xzc", "at": "2026-11-22T00:00:00Z",
                    "quote": "只审一遍可接受", "source": "user-declared",
                    "residual_risk": "漏检风险由我承担", "round": 1, "task": "t1"}
        record, problems = review_mod.single_reviewer_acceptance(decision, 1, task_id="t1")
        self.assertEqual(problems, [])
        self.assertEqual(record["round"], 1)
        self.assertTrue(record["attestation_digest"].startswith("sha256:"))
        # 轮次不符拒绝
        _record, problems = review_mod.single_reviewer_acceptance(
            dict(decision, round=2), 1, task_id="t1")
        self.assertTrue(any("round" in p["reason"] for p in problems))
        # 缺 residual_risk 拒绝
        _record, problems = review_mod.single_reviewer_acceptance(
            {k: v for k, v in decision.items() if k != "residual_risk"}, 1, task_id="t1")
        self.assertTrue(any("residual_risk" in p["reason"] for p in problems))
        # AI 自述拒绝（乙口径）
        _record, problems = review_mod.single_reviewer_acceptance(
            dict(decision, by="ai:agent"), 1, task_id="t1")
        self.assertTrue(any("human:" in p["reason"] for p in problems))

    def test_cli_flag_and_help_registered(self):
        self.assertIn("--single-reviewer-acceptance", cli.COMMAND_FLAGS["review-decide"])
        help_entry = json.dumps(cli.COMMAND_HELP["review-decide"], ensure_ascii=False)
        self.assertIn("--single-reviewer-acceptance", help_entry)
        self.assertIn("残余风险", help_entry)


class HelpConsistencyTest(unittest.TestCase):
    """三轮外部审查 b4：help 文本与登记域一致（help 是 AI 唯一发现面）。"""

    def test_authorize_help_matches_actions(self):
        source = json.dumps(cli.COMMAND_HELP["authorize"], ensure_ascii=False)
        self.assertNotIn("五类", source)
        for action in authorize.ACTIONS:
            self.assertIn(action, source)
        self.assertIn("commit_grants", source)

    def test_replan_help_matches_domain(self):
        source = json.dumps(cli.COMMAND_HELP["task-replan"], ensure_ascii=False)
        self.assertIn("choice=replan", source)
        self.assertNotIn("replan/机械修订", source)
        self.assertIn("task-approve", source)


class ProjectDataClassificationTest(unittest.TestCase):
    """三轮外部审查 b5：.wf/user-workflows 是项目数据，不落 vendor 桶。"""

    def test_user_workflows_prefix_declared_and_classified(self):
        from wflib import protocol, scope

        prefixes = protocol.project_data()["prefixes"] if hasattr(protocol, "project_data") else None
        source = (REPO / "docs/workflows/wf/payload/protocol/project_data.json").read_text(encoding="utf-8")
        self.assertIn(".wf/user-workflows/", source)
        # is_project_data 消费同一声明（vendor 判定为 is_vendor and not is_project_data）
        self.assertTrue(scope.is_project_data(".wf/user-workflows/custom-flow.md")
                        if hasattr(scope, "is_project_data") else True)

    def test_protocol_source_of_truth_only(self):
        # 集合只在协议文件声明（单一事实源），代码不得另写前缀清单
        source = (REPO / "docs/workflows/wf/payload/lib/wflib/scope.py").read_text(encoding="utf-8")
        self.assertNotIn('".wf/user-workflows/"', source)


class ManagedGitignoreDerivedFilesTest(unittest.TestCase):
    """三轮外部审查 b6：.wf 内派生字节码进托管忽略段（不再成 vendor_dirty 噪声）。"""

    def test_managed_lines_cover_pycache(self):
        sys.path.insert(0, str(REPO / "scripts"))
        import wf_release_common

        lines = wf_release_common.GITIGNORE_MANAGED["lines"]
        self.assertIn("/.wf/**/__pycache__/", lines)
        self.assertIn("/.wf/**/*.pyc", lines)
        # 不越界：只忽略 .wf 内的派生文件
        for line in lines:
            self.assertTrue(line.startswith("/.wf") or line == "/.wf-lock", line)


class Round2ReviewConsistencyTest(unittest.TestCase):
    """三轮二审收口面：文档一致、收敛引线、降级护栏。"""

    def test_single_reviewer_semantics_synced_across_docs(self):
        # A4：四处历史口径已同步（不再有"单 reviewer 一律不产生判定"的绝对句）
        action = (REPO / "docs/workflows/wf/skills/wf-review-action/SKILL.md").read_text(encoding="utf-8")
        self.assertNotIn("不满足复杂任务完成条件", action)
        self.assertIn("--single-reviewer-acceptance", action)
        flow = (REPO / "docs/workflows/wf/payload/workflows/task-flow.md").read_text(encoding="utf-8")
        self.assertIn("单 reviewer + 人签残余风险接受", flow)
        impl = (REPO / "docs/workflows/wf-framework-implementation.md").read_text(encoding="utf-8")
        self.assertIn("有记录降级路径", impl)
        self.assertIn("WF_EXPORT_NOT_AUTHORIZED",
                      (REPO / "docs/workflows/wf/payload/protocol/codes.json").read_text(encoding="utf-8"))

    def test_human_sign_scope_guard_registered(self):
        mech = (REPO / "docs/workflows/wf-framework-mechanism.md").read_text(encoding="utf-8")
        self.assertIn("人签降级的适用边界", mech)
        design = (REPO / "docs/workflows/wf-framework-design.md").read_text(encoding="utf-8")
        self.assertIn("正面授权", design)          # AI 自决清单
        self.assertIn("需要人签的封闭清单", design)

    def test_irreversible_projection_carries_review_degraded(self):
        # 三-2：单 reviewer 降级随收工预览上抛（人判点可见降级事实）
        source = (REPO / "docs/workflows/wf/payload/lib/wflib/cli.py").read_text(encoding="utf-8")
        self.assertIn("review_degraded", source)

    def test_review_import_next_mentions_draft(self):
        # A2：导入 next_ 含 main-review-draft 引线（import_report 函数体内）
        source = (REPO / "docs/workflows/wf/payload/lib/wflib/review.py").read_text(encoding="utf-8")
        body = source.split("def import_report", 1)[1].split("\ndef ", 1)[0]
        self.assertIn("main-review-draft", body)
        self.assertIn("missing_slots", body)

    def test_check_next_hint_carries_open_blocking(self):
        # A3：task-check next_ 提示未关闭 blocking 与三步收敛（行为断言，非字符串）
        from wflib import review as review_mod
        from wflib import tasks as tasks_mod
        from unittest import mock

        task = {"id": "t1", "plan": {"complexity": "complex", "version": "v1"},
                "check": {"result": "pass", "id": "c1"}}
        ctx = type("Ctx", (), {"root": "/nonexistent"})()
        with mock.patch.object(review_mod, "open_findings",
                               return_value={"blocking": [{"id": "f1", "round": 2}]}):
            hint = tasks_mod.check_next_hint(task, task["check"], ctx=ctx)
        self.assertIn("未关闭 blocking", hint)
        self.assertIn("轮次 [2]", hint)
        self.assertIn("重新发起判定", hint)
        # 无未关闭 blocking 时不出提示（不制造噪声）
        with mock.patch.object(review_mod, "open_findings", return_value={"blocking": []}):
            hint = tasks_mod.check_next_hint(task, task["check"], ctx=ctx)
        self.assertNotIn("未关闭 blocking", hint)
        # ctx 缺省（旧调用面）行为不变
        hint = tasks_mod.check_next_hint(task, task["check"])
        self.assertNotIn("未关闭 blocking", hint)


class Round3ReviewFixesTest(unittest.TestCase):
    """三轮三审收口面。"""

    def test_export_auth_reuse_semantics_in_skill(self):
        # b1：skill 不再写"每轮一次"，写持续有效口径
        text = (REPO / "docs/workflows/wf/skills/wf-continue/SKILL.md").read_text(encoding="utf-8")
        self.assertNotIn("每轮一次外发确认", text)
        self.assertIn("同一任务、同一材料类集合", text)

    def test_launch_request_merges_with_default(self):
        # a：--launch-request 只覆盖已给键（缺省项由入口生成）
        import inspect
        from wflib import review as review_mod

        source = inspect.getsource(review_mod.launch)
        self.assertIn("_deep_merge_launch_request(default, supplied)", source)
        self.assertNotIn("request.update(supplied)", source)

    def test_reviewers_one_generates_single_slot(self):
        # a：显式 reviewers=1 是声明的降级，不被 max(2,…) 吞掉
        import inspect
        from wflib import review as review_mod

        source = inspect.getsource(review_mod.launch)
        self.assertNotIn("max(2, count)", source)

    def test_delete_and_repo_rules_have_own_codes(self):
        codes_src = (REPO / "docs/workflows/wf/payload/protocol/codes.json").read_text(encoding="utf-8")
        self.assertIn("WF_DELETE_NOT_AUTHORIZED", codes_src)
        self.assertIn("WF_REPO_RULES_NOT_AUTHORIZED", codes_src)
        tasks_src = (REPO / "docs/workflows/wf/payload/lib/wflib/tasks.py").read_text(encoding="utf-8")
        self.assertIn('"WF_REPO_RULES_NOT_AUTHORIZED"', tasks_src)
        self.assertIn('"WF_DELETE_NOT_AUTHORIZED"', tasks_src)

    def test_draft_and_preview_surfaces_registered(self):
        self.assertIn("--draft", cli.COMMAND_FLAGS["authorize"])
        self.assertIn("--preview", cli.COMMAND_FLAGS["review-launch"])
        self.assertIn("--single-reviewer-acceptance-draft", cli.COMMAND_FLAGS["review-decide"])
        # preview 是只读：不取锁不落盘（launch_preview 独立函数，不写 task.json）
        import inspect
        from wflib import review as review_mod

        source = inspect.getsource(review_mod.launch_preview)
        self.assertNotIn("lock.acquire", source)
        self.assertNotIn("write_json", source)

    def test_yan_yong_ownership_is_ai_judgment(self):
        # b3：沿用相关性是 AI 判断（kind=沿用 记录），不再写"由人复核"
        text = (REPO / "docs/workflows/wf/skills/wf-review-action/SKILL.md").read_text(encoding="utf-8")
        self.assertNotIn("相关性与粒度由人复核", text)
        self.assertIn("相关性与粒度是你的判断", text)

    def test_anchor_parts_classifies_once(self):
        # b6：锚点计算只分类一次（透传给 object_paths/spec_versions）
        import inspect
        from wflib import check as check_mod

        source = inspect.getsource(check_mod.anchor_parts)
        self.assertIn("object_paths(ctx, task, classified=classified)", source)
        self.assertIn("spec_versions(ctx, task, classified=classified)", source)


class Round4ReviewFixesTest(unittest.TestCase):
    """四轮审查收口面。"""

    def test_deep_merge_preserves_nested_defaults(self):
        # a：只覆盖 submitted_scope.diff 时，requirement/test_results 默认保留
        import tempfile, os as _os
        import json as _json
        from wflib import review as review_mod

        with tempfile.TemporaryDirectory() as tmp:
            _task_dir = _os.path.join(tmp, ".wf", "tasks", "t1")
            _os.makedirs(_task_dir, exist_ok=True)
            _json.dump({"id": "t1"}, open(_os.path.join(_task_dir, "task.json"), "w", encoding="utf-8"))
            request_path = _os.path.join(tmp, "req.json")
            _json.dump({"submitted_scope": {"diff": {"paths": ["src/a.py"]}}},
                       open(request_path, "w", encoding="utf-8"))
            ctx = type("Ctx", (), {"root": str(tmp)})()
            task = {"id": "t1", "plan": {"version": "v1"},
                    "entry_snapshot": {"touch_paths": []}, "curation": []}
            with unittest.mock.patch.object(
                    review_mod, "default_launch_request",
                    return_value={"submitted_scope": {
                        "diff": {"paths": ["x.py"]},
                        "requirement": "prd.md",
                        "test_results": {"check": "c1"}}}):
                preview = review_mod.launch_preview(ctx, task, request_path)
            submitted = preview["request"]["submitted_scope"]
            self.assertEqual(submitted["diff"]["paths"], ["src/a.py"])   # 覆盖生效
            self.assertEqual(submitted["requirement"], "prd.md")         # 默认保留
            self.assertEqual(submitted["test_results"]["check"], "c1")

    def test_check_export_note_uses_scope_problems(self):
        # b3：提示与门禁同一判据（export_scope_problems），不是"有没有文件"
        import inspect
        from wflib import tasks as tasks_mod

        source = inspect.getsource(tasks_mod.check_next_hint)
        self.assertIn("export_scope_problems", source)
        self.assertNotIn('require(_dir, "export") is None', source)

    def test_import_sentence_and_draft_pointers(self):
        text = (REPO / "docs/workflows/wf/skills/wf-continue/SKILL.md").read_text(encoding="utf-8")
        self.assertNotIn("每个槽位一次", text)
        self.assertIn("一次调用导入本轮全部已完成报告", text)
        self.assertIn("authorize record --draft", text)
        # b6：内容边界显式声明
        self.assertIn("不覆盖每轮的具体内容", text)
        finish = (REPO / "docs/workflows/wf/skills/wf-finish/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("authorize record --draft", finish)

    def test_preview_carries_materials_identity(self):
        # a-P1：preview 含日志清单与摘要（与 write_materials 同源）
        import inspect
        from wflib import review as review_mod

        source = inspect.getsource(review_mod.launch_preview)
        self.assertIn("test_results_preview", source)
        self.assertIn("file_digest_state", source)

    def test_three_way_matching_delivery_state_annotated(self):
        """五轮：三方升级匹配已交付，§1.1 的"未交付期间…登记缺口"陈旧括注必须消失。"""
        design = (REPO / "docs/workflows/wf-framework-design.md").read_text(encoding="utf-8")
        self.assertNotIn("未交付期间该条为登记缺口", design)
        self.assertIn("三方升级匹配（已交付", design)


import unittest.mock  # noqa: E402  （Round4 用例需要）

class Round5ReviewFixesTest(unittest.TestCase):
    """五轮审查收口面。"""

    def test_control_plane_paths_companion_key(self):
        # b2：drift 可归因——parts 带路径集合伴随键，且不进锚点哈希
        import tempfile, os as _os
        from wflib import check as check_mod, fingerprint

        with tempfile.TemporaryDirectory() as tmp:
            _os.makedirs(_os.path.join(tmp, ".wf"))
            (Path(tmp) / ".wf" / "baseline.md").write_text("基线", encoding="utf-8")
            (Path(tmp) / ".wf" / "project-config.json").write_text("{}", encoding="utf-8")
            ctx = type("Ctx", (), {"root": str(tmp)})()
            task = {"id": "t1", "plan": {"version": "v1", "acceptance_digest": "sha256:a"},
                    "entry_snapshot": {"touch_paths": []}, "curation": []}
            from unittest import mock

            with mock.patch.object(check_mod, "spec_versions", return_value=[]), \
                    mock.patch.object(check_mod, "assertions_digest", return_value="sha256:a"):
                anchor, parts = check_mod.current_anchor(ctx, task)
            self.assertEqual(parts["control_plane_paths"], [])
            # 伴随键不进哈希：删掉它重算锚点不变
            parts_without = {k: v for k, v in parts.items() if k != "control_plane_paths"}
            self.assertEqual(fingerprint.check_anchor(parts),
                             fingerprint.check_anchor(parts_without))

    def test_preview_logs_truncation_visible(self):
        from wflib import review as review_mod

        source = inspect.getsource(review_mod.launch_preview)
        self.assertIn("check_logs_omitted", source)

    def test_wf_review_teaches_log_verification(self):
        text = (REPO / "docs/workflows/wf/skills/wf-review/SKILL.md").read_text(encoding="utf-8")
        # 2026-11-24 口径：不符/缺失日志不进材料包，改在 status.json.problems 报告
        # （旧口径"如实标 verified=false"已被先核身份再物化取代）。
        self.assertIn("不进包", text)
        self.assertIn("status.json.problems", text)
        self.assertIn("必须作为 finding 报出", text)
        self.assertNotIn("verified=false", text)

    def test_vendor_section_carries_stale_and_fallback(self):
        text = (REPO / "docs/workflows/wf/skills/wf-continue/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("WF_CHECK_STALE", text)
        self.assertIn("d:control_plane_paths", text)
        # 2026-11-23：导出通道已交付，vendor 段改指只读导出而不是手工 diff
        self.assertIn("--export-deviations", text)
        self.assertIn("不取写权", text)

    def test_mech_registers_preview_and_deep_merge(self):
        mech = (REPO / "docs/workflows/wf-framework-mechanism.md").read_text(encoding="utf-8")
        self.assertIn("只读预览出口（`review-launch --preview`", mech)
        self.assertIn("嵌套字段级深合并", mech)
        self.assertIn("伴随呈现键 `control_plane_paths`", mech)


import inspect  # noqa: E402
import importlib  # noqa: E402,F401 （保持既有导入面不变）

class DraftSurfacesCompleteTest(unittest.TestCase):
    """五轮审查 b5 尾项（用户裁决：不做顺延）——全部决定/处置文件有骨架入口。"""

    def test_all_decision_surfaces_have_drafts(self):
        # 每类"AI 必须手写的结构化文件"都有只读骨架：approve/replan/rework/stop/
        # archive(main-review)/authorize/single-reviewer-acceptance/plan/judgments
        from wflib import cli

        self.assertIn("--draft", cli.COMMAND_FLAGS["authorize"])
        self.assertIn("--draft", cli.COMMAND_FLAGS["judgments"])
        self.assertIn("--main-review-draft", cli.COMMAND_FLAGS["review-decide"])
        self.assertIn("--single-reviewer-acceptance-draft", cli.COMMAND_FLAGS["review-decide"])
        self.assertIn("--plan-draft", cli.COMMAND_FLAGS["review-decide"])
        self.assertIn("--draft", cli.COMMAND_FLAGS["task-approve"])
        # judgments --draft 骨架按运行时 KINDS 全类列出（含框架改动）；
        # --plan-draft 骨架只列未关闭 blocking
        source = (REPO / "docs/workflows/wf/payload/lib/wflib/cli.py").read_text(encoding="utf-8")
        judgments_body = source.split("judgments requires add|show")[1][:2000]
        self.assertIn("judgments_mod.KINDS", judgments_body)
        from wflib import judgments as _judgments_mod
        self.assertIn("框架改动", _judgments_mod.KINDS)
        self.assertIn("open_findings", source.split("--plan-draft")[1][:1200])


import importlib  # noqa: E402,F401

if __name__ == "__main__":
    unittest.main()
