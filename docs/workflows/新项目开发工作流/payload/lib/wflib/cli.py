"""cli.py — 子命令面、请求信封、代次核验与输出（实现稿 §2、机制稿 §11.1）。

语义层入口：只负责解析请求、核验身份/绑定/写权、分派固定处理器与渲染结果。
"""

from __future__ import annotations

import json
import os
import sys
import traceback

from . import actions, assets, codes, config, lock, records, session as session_mod, writer as writer_mod
from .paths import join


class CliError(Exception):
    def __init__(self, code, facts=None, next_=None, position=None):
        super().__init__(code)
        self.code = code
        self.facts = facts or {}
        self.next = next_
        self.position = position

    def result(self, object_ref=None):
        return codes.result(
            self.code,
            object=object_ref,
            position_=self.position,
            next_=self.next,
            facts=self.facts,
        )


class Args:
    """极简参数解析：`--key value`、`--key=value` 与位置参数。"""

    def __init__(self, argv):
        self.argv = list(argv)
        self.used = set()

    def value(self, name, default=None):
        for index, token in enumerate(self.argv):
            if token == name:
                if index + 1 >= len(self.argv):
                    raise CliError("WF_PATH_INVALID", {"reason": f"{name} requires a value"})
                self.used.update({index, index + 1})
                return self.argv[index + 1]
            if token.startswith(name + "="):
                self.used.add(index)
                return token.split("=", 1)[1]
        return default

    def flag(self, name):
        if name in self.argv:
            self.used.add(self.argv.index(name))
            return True
        return False

    def positional(self):
        return [token for index, token in enumerate(self.argv) if index not in self.used and not token.startswith("--")]

    def rest(self):
        return [token for index, token in enumerate(self.argv) if index not in self.used]


class Context:
    def __init__(self, root, argv):
        self.root = str(root)
        self.args = Args(argv)
        self.json_output = "--json" in argv
        self._envelope = None
        self._session = None
        self._key = None
        self._manifest = None

    # -- 信封 ------------------------------------------------------------
    def envelope(self, required=True):
        if self._envelope is not None:
            return self._envelope
        path = self.args.value("--envelope")
        text = ""
        if path:
            try:
                with open(path, "r", encoding="utf-8") as handle:
                    text = handle.read()
            except OSError as exc:
                raise CliError("WF_IDENTITY_UNRESOLVED", {"reason": f"envelope unreadable: {exc}", "path": path})
        else:
            try:
                if sys.stdin is None or sys.stdin.isatty():
                    # 人手直接跑命令时不要静默挂起：明确要求通过管道/重定向给信封
                    raise CliError("WF_PATH_INVALID",
                                   {"reason": "request envelope must be piped on stdin"})
                text = sys.stdin.read()
            except OSError:
                text = ""
        if not text.strip():
            if not required:
                return None
            raise CliError(
                "WF_IDENTITY_UNRESOLVED",
                {"reason": "request envelope missing", "fields": ["session.provider", "session.identity"]},
                next_="从标准输入或 --envelope 提供会话请求信封",
            )
        try:
            data = records.loads(text)
        except records.RecordInvalid as exc:
            raise CliError("WF_IDENTITY_UNRESOLVED", {"reason": f"envelope invalid: {exc}"})
        if not isinstance(data, dict):
            raise CliError("WF_IDENTITY_UNRESOLVED", {"reason": "envelope is not a JSON object"})
        self._envelope = data
        return data

    def session(self, required=True):
        envelope = self.envelope(required=required)
        if envelope is None:
            return None
        if self._session is not None:
            return self._session
        try:
            self._session = session_mod.validate_session(envelope.get("session"))
        except session_mod.IdentityError as exc:
            raise CliError(
                "WF_IDENTITY_UNRESOLVED",
                {"reason": str(exc), "fields": ["session.provider", "session.identity"]},
                next_="核实宿主身份字段，或改用 wf 签发路径",
            )
        return self._session

    def key(self, required=True):
        session = self.session(required=required)
        if session is None:
            return None
        if self._key is None:
            self._key = session_mod.session_key(
                {"provider": session["provider"], "identity": session["identity"]}
            )
        return self._key

    def inputs(self):
        envelope = self.envelope(required=False) or {}
        value = envelope.get("inputs")
        return value if isinstance(value, dict) else {}

    def activation(self):
        session = self.session(required=False)
        return (session or {}).get("activation")

    def require_activation(self):
        """会话类入口前置：activation 缺失/非法即 WF_NOT_ENABLED（机制稿 §1.4）。"""
        activation = self.activation()
        if not isinstance(activation, dict) or activation.get("enabled") is not True:
            raise CliError(
                "WF_NOT_ENABLED",
                {"reason": "activation missing or not enabled", "session_key": self.key(required=False)},
                next_="人显式调用 /wf-start 重新启用后重试；不从持久绑定补 enabled",
            )
        return activation

    def debug_threshold(self):
        """阈值不可用时抛错：非法值不得静默用缺省继续判断（设计稿 §3）。"""
        config_record, problems = config.load_project_config(self.root, allow_missing=True)
        value, problem = config.value_of(config_record, problems, "debug_repeat_threshold")
        if problem:
            raise CliError("WF_CAPABILITY_UNAVAILABLE",
                           {"reason": problem, "key": "debug_repeat_threshold"},
                           next_="修正 project-config.json 的该键后重试")
        return value

    # -- 安装事实 --------------------------------------------------------
    def manifest(self):
        if self._manifest is None:
            try:
                self._manifest = assets.load_installed_manifest(self.root)
            except assets.AssetError as exc:
                raise CliError("WF_ASSET_DECISION", {"reason": str(exc), "asset": ".wf/install/release-manifest.json"})
        return self._manifest

    def installation(self):
        record = assets.load_installation(self.root)
        if record is None:
            raise CliError("WF_CAPABILITY_UNAVAILABLE", {"missing": ".wf/install/installation.json"})
        return record

    def rule_version(self):
        manifest = self.manifest()
        installation = self.installation()
        entries = assets.installed_asset_entries(manifest, installation, self.root)
        return assets.effective_rule_version(manifest, entries)

    def platforms(self):
        """本项目已安装的平台（唯一身份事实，见机制稿 §1.4 修订后）。"""
        installation = self.installation() or {}
        return [item for item in (installation.get("platforms") or []) if isinstance(item, str)]

    def profile(self):
        return self.installation().get("session_profile")

    # -- 写者 ------------------------------------------------------------
    def writer(self):
        record = writer_mod.load(self.root)
        if record is None:
            raise CliError(
                "WF_CAPABILITY_UNAVAILABLE",
                {"missing": ".wf/writer.json", "reason": "project not installed"},
            )
        writer_mod.require_supported(record, CliError)
        return record

    def require_held(self, *, task=None, run=None):
        """核会话写者身份与代次（不做业务判定）。"""
        key = self.key()
        record = self.writer()
        if record.get("state") != "held":
            raise CliError(
                "WF_WRITER_BUSY",
                {"writer_state": record.get("state"), "holder": record.get("holder")},
                next_="等待写权释放，或走已确认的交接/恢复出口",
            )
        holder = record.get("holder") or {}
        # 代次三处一致：顶层、holder、请求；不一致即所有权事实矛盾，不按「未知字段保留」放行
        top_generation = record.get("generation")
        holder_generation = holder.get("generation")
        if top_generation != holder_generation:
            raise CliError("WF_RECORD_INVALID",
                           {"reason": "writer generation inconsistent",
                            "writer_generation": top_generation, "holder_generation": holder_generation},
                           next_="按受控修复核对写者记录后重试")
        if holder.get("kind") != "session":
            raise CliError("WF_WRITER_BUSY", {"holder": holder, "reason": "maintenance holder"})
        if holder.get("id") != key:
            raise CliError("WF_WRITER_BUSY", {"holder": holder, "reason": "held by another session"})
        scope = holder.get("scope")
        target = task or run
        if target and scope and scope.get("object") and scope["object"].get("id") != target:
            raise CliError("WF_BINDING_MISMATCH", {"writer_scope": scope, "requested": target})
        generation = self.inputs().get("generation")
        if generation is None:
            raise CliError(
                "WF_GENERATION_STALE",
                {"reason": "generation not carried", "current_generation": holder.get("generation")},
            )
        if int(generation) != int(holder.get("generation")):
            raise CliError(
                "WF_GENERATION_STALE",
                {
                    "reason": "generation mismatch",
                    "carried": generation,
                    "current_generation": holder.get("generation"),
                },
            )
        return record, holder


# --------------------------------------------------------------------------
# 输出
# --------------------------------------------------------------------------


def emit(payload, json_output=False):
    if payload.pop("__rendered__", False):
        sys.stdout.flush()
        return codes.process_exit(payload["code"])
    if json_output:
        sys.stdout.write(records.canonical(payload) + "\n")
    else:
        sys.stdout.write(render(payload) + "\n")
    sys.stdout.flush()
    return codes.process_exit(payload["code"])


def render(payload) -> str:
    lines = [f"{payload['tier'].upper()}  {payload['code']}"]
    object_ref = payload.get("object")
    if object_ref:
        if isinstance(object_ref, dict):
            name = object_ref.get("name") or object_ref.get("id")
            identifier = object_ref.get("id")
            lines.append(f"对象: {name}（{identifier}）" if name and identifier != name else f"对象: {name}")
        else:
            lines.append(f"对象: {object_ref}")
    position = payload.get("position") or {}
    visible = [f"{key}={value}" for key, value in position.items() if value is not None]
    if visible:
        lines.append("位置: " + " ".join(visible))
    if payload.get("next"):
        lines.append(f"下一步: {payload['next']}")
    if payload.get("facts"):
        lines.append("事实: " + records.canonical(payload["facts"]))
    if payload.get("exit") and payload.get("tier") != "pass":
        lines.append(f"出口: {payload['exit']}")
    if payload.get("prohibited_repairs"):
        lines.append(f"禁止的修复: {payload['prohibited_repairs']}")
    for warning in payload.get("warnings") or []:
        lines.append(f"提示: {warning}")
    return "\n".join(lines)


def ok(facts=None, position=None, next_=None, object_ref=None, warnings=None):
    return codes.result("WF_OK", object=object_ref, position_=position, next_=next_, facts=facts, warnings=warnings)


# --------------------------------------------------------------------------
# 公共辅助
# --------------------------------------------------------------------------


def _lock(root, hint=None):
    try:
        return lock.acquire(root, holder_hint=hint)
    except lock.LockBusy as exc:
        raise CliError("WF_WRITER_BUSY", {"reason": "lock busy", "path": exc.path}, next_="等待或走已确认出口")
    except lock.LockUnavailable as exc:
        raise CliError("WF_CAPABILITY_UNAVAILABLE",
                       dict({"reason": str(exc), "path": exc.path}, **(getattr(exc, "facts", {}) or {})),
                       next_="锁对象不可识别：人工核实后删除该文件并重新运行（普通入口不认领、不覆写）")


def _check_layout(root):
    missing = []
    if not os.path.isdir(join(root, ".wf")):
        missing.append(".wf/")
    if not os.path.isfile(join(root, ".wf/bin/wf.py")):
        missing.append(".wf/bin/wf.py")
    if not os.path.isdir(join(root, ".wf/lib/wflib")):
        missing.append(".wf/lib/wflib/")
    if missing:
        raise CliError(
            "WF_CAPABILITY_UNAVAILABLE",
            {"missing": missing, "root": root},
            next_="按恢复说明重取入口，或用显式 --project 指向真实项目",
        )


def _binding_for(ctx):
    key = ctx.key()
    record = session_mod.load_binding(ctx.root, key)
    return key, record


def _position_for(record, scope):
    if not record:
        return codes.position(scope=scope)
    return codes.position(
        scope=scope,
        phase=record.get("phase"),
        task_id=record.get("id") if scope == "task" else record.get("_task_id"),
        action_id=((record.get("action") or {}) or {}).get("id"),
        action_state=((record.get("action") or {}) or {}).get("state"),
    )


def _write_mark(ctx, operation, owner, generation, before_head, changed_fields, action):
    return {
        "operation": operation,
        "owner": owner,
        "generation": generation,
        "before_head": before_head,
        "changed_fields": changed_fields,
        "action_id": action.get("id"),
        "invocation": {"entry": operation.split(".")[0], "scope_digest": action.get("inputs_digest")},
    }


def _control_assertion(ctx, operation, owner_ref, action, evidence_refs=None):
    projection = actions.control_projection(
        owner_ref,
        action["id"],
        operation,
        action.get("inputs_digest"),
        actions.targets_digest(action.get("targets")),
    )
    rule_version = ctx.rule_version()
    return {
        "step_id": f"control.{operation}",
        "rule_version": rule_version,
        "occurrence": actions.control_occurrence(projection),
        "anchor": actions.control_anchor(rule_version, projection),
        "evidence_refs": evidence_refs or [],
    }


def _owner_ref(holder):
    return writer_mod.owner_ref(holder.get("kind"), holder.get("id"), holder.get("scope"))


def _atomic_writer_action(ctx, record, operation, owner_ref, inputs, steps, mutate, evidence_refs=None):
    """在 writer 主记录上登记并完成一个状态动作。"""
    action = actions.new_action(
        operation,
        owner_ref,
        int(record.get("revision", 0)),
        inputs,
        steps=steps,
        head_before=actions.head_of(ctx.root),
        targets=[{"kind": "writer", "id": "writer"}],
    )
    record = dict(record)
    record["action"] = action
    writer_mod.save(ctx.root, record)
    evidence = mutate(record)
    if evidence is False:
        raise CliError("WF_PERSISTENCE_FAILED", {"operation": operation})
    assertion = _control_assertion(ctx, operation, owner_ref, action, evidence_refs)
    action = actions.complete(action, summary=operation, control_assertion=assertion)
    record = winner = dict(record)
    winner["action"] = action
    winner["write_mark"] = _write_mark(
        ctx,
        operation,
        owner_ref,
        (winner.get("holder") or {}).get("generation"),
        action.get("head_before"),
        sorted(list(inputs.keys())),
        action,
    )
    writer_mod.save(ctx.root, winner)
    return assertion


# --------------------------------------------------------------------------
# 只读命令
# --------------------------------------------------------------------------


def cmd_version(ctx, args):
    _check_layout(ctx.root)
    manifest = ctx.manifest()
    installation = ctx.installation()
    facts = {
        "version": manifest.get("version"),
        "release_ref": installation.get("release_ref"),
        "manifest_digest": installation.get("manifest_digest"),
        "rules_digest": (manifest.get("compatibility") or {}).get("rules_digest"),
        "python_min": (manifest.get("compatibility") or {}).get("python_min"),
    }
    return ok(facts=facts, next_="wf-start（人显式调用）")


def cmd_status(ctx, args):
    _check_layout(ctx.root)
    record = ctx.writer()
    facts = {
        "writer_state": record.get("state"),
        "generation": record.get("generation"),
        "holder": record.get("holder"),
    }
    position = codes.position(scope="maintenance" if (record.get("holder") or {}).get("kind") == "maintenance" else None)
    key = ctx.key(required=False)
    if key:
        binding = session_mod.load_binding(ctx.root, key)
        if binding:
            object_ref = binding.get("object") or {}
            task_id = object_ref.get("id") if object_ref.get("kind") == "task" else None
            facts["binding"] = {"object": object_ref, "instance_id": binding.get("instance_id")}
            if task_id:
                from . import tasks as tasks_mod

                task = tasks_mod.load_task(ctx.root, task_id)
                if task is None:
                    raise CliError("WF_RECORD_INVALID", {"missing_task": task_id, "binding": object_ref})
                position = _position_for(task, "task")
                from . import tasks as tasks_mod  # noqa: F811  (上面已局部导入)
                facts["startup"] = tasks_mod.startup_check(ctx, task)
                facts["task"] = {
                    "status": task.get("status"),
                    "phase": task.get("phase"),
                    "paused": task.get("paused"),
                    "suspended": task.get("suspended"),
                    "terminal": task.get("terminal"),
                    "title": task.get("title"),
                }
            else:
                from . import runs as runs_mod

                run = runs_mod.load_run(ctx.root, object_ref.get("id"))
                if run is None:
                    raise CliError("WF_RECORD_INVALID", {"missing_run": object_ref.get("id")})
                cursor = run.get("cursor") or {}
                position = codes.position(
                    scope="run",
                    step_id=cursor.get("step_id"),
                    task_id=cursor.get("task_id"),
                    action_id=(run.get("action") or {}).get("id"),
                    action_state=(run.get("action") or {}).get("state"),
                )
    if "startup" not in facts:
        from . import tasks as tasks_mod

        facts["startup"] = tasks_mod.startup_check(ctx)
    return ok(facts=facts, position=position, next_="按 position 与绑定继续")


def cmd_gate(ctx, args):
    due = args.value("--due")
    if due not in ("before_execute", "before_check", "before_archive"):
        raise CliError("WF_PATH_INVALID", {"reason": "gate requires --due before_execute|before_check|before_archive"})
    from . import gates as gates_mod

    return gates_mod.evaluate_cli(ctx, due)


def cmd_inspect(ctx, args):
    from . import tasks as tasks_mod

    return tasks_mod.inspect(ctx)


# --------------------------------------------------------------------------
# 会话启用与绑定
# --------------------------------------------------------------------------


TRELLIS_INSTRUCTION_FILES = ("AGENTS.md", "CLAUDE.md", "CONTEXT.md")
# 宿主 → 该宿主的 hook/配置文件落点（含目录形式）；用于区分「当前宿主可适用」与「适用性未知」
TRELLIS_HOST_CONFIGS = {
    "claude": (".claude/settings.json", ".claude/hooks"),
    "codex": (".codex/hooks.json", ".codex/config.toml"),
    "dsh": (".dsh/hooks.json", ".dsh/settings.json", ".dsh/plugins"),
}


def _mentions_trellis(path):
    """只读判断落点是否出现 Trellis 线索；目录按其下文件逐个看。"""
    def hit(text):
        return "trellis" in text.lower()

    try:
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8", errors="replace") as handle:
                return hit(handle.read())
        if os.path.isdir(path):
            for base, _dirs, files in os.walk(path):
                for name in files:
                    try:
                        with open(os.path.join(base, name), "r", encoding="utf-8", errors="replace") as handle:
                            if hit(handle.read()):
                                return True
                    except OSError:
                        continue
    except OSError:
        return False
    return False


def _trellis_state(root, host_id):
    """返回托管块、数据线索与宿主配置文件三类事实（设计稿 §3 的「线索 ≠ 激活」）。"""
    blocks = []
    for name in TRELLIS_INSTRUCTION_FILES:
        path = join(root, name)
        if not os.path.isfile(path):
            continue
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as handle:
                if "TRELLIS:START" in handle.read():
                    blocks.append(name)
        except OSError:
            continue
    data = [".trellis/"] if os.path.isdir(join(root, ".trellis")) else []
    host_files = []
    for host, paths in TRELLIS_HOST_CONFIGS.items():
        for relative in paths:
            path = join(root, relative)
            if os.path.exists(path) and _mentions_trellis(path):
                host_files.append({"path": relative, "host": host})
    return {"blocks": blocks, "data": data, "host_files": host_files, "host_id": host_id}


def cmd_enable(ctx, args):
    _check_layout(ctx.root)
    session = ctx.session()
    state = _trellis_state(ctx.root, (ctx.session().get("identity") or {}).get("host_id"))
    host_id = state["host_id"]
    applicable = [item for item in state["host_files"] if item["host"] == host_id]
    unknown = [item for item in state["host_files"] if item["host"] != host_id]
    # 「已确认有效」需本会话确实加载：只有人声明本次已加载 Trellis 指令才按冲突阻断（机制稿 §2.1）
    loaded = bool((ctx.inputs() or {}).get("trellis_loaded"))
    if applicable and loaded:
        raise CliError(
            "WF_FLOW_CONFLICT",
            {"trellis_host_config": applicable, "host_id": host_id, "trellis_loaded": True,
             "trellis_managed_blocks": state["blocks"], "trellis_data": state["data"]},
            next_="清理 Trellis 有效指令后在新会话重新启用；不以人工豁免继续混跑",
        )
    if state["blocks"] or unknown or applicable:
        raise CliError(
            "WF_SEMANTIC_DECISION",
            {"trellis_managed_blocks": state["blocks"], "trellis_other_host_config": unknown,
             "trellis_host_config": applicable, "host_id": host_id, "trellis_data": state["data"],
             "trellis_loaded": loaded,
             "exits": ["核实该托管块/配置对当前宿主是否生效并清理后换新会话",
                       "确认仅是残留数据与历史引用后重入"]},
            next_="人核实适用性；已确认激活则清理后换新会话，仅残留可继续",
        )
    code, profile_facts = session_mod.check_platforms(ctx.platforms(), session)
    if code:
        raise CliError(code, profile_facts, next_="install --platform <当前宿主> 后重试，或换用已安装的宿主")
    warnings = []
    if state["data"]:
        warnings.append({"clue": state["data"], "note": "仅数据线索；不构成当前激活指令"})
    # 首次启用时调用方通常还没带 activation：这里给出**可直接缓存的模板**，
    # 由适配层在后续每次请求里重放（机制稿 §1.4：由宿主/skill 按本次真实调用形成缓存）
    activation = ctx.activation()
    template = activation or {
        "enabled": True,
        "start_source": "human:enable",
        "enabled_at": records.now_str(),
    }
    return ok(
        facts={
            "session_key": ctx.key(),
            "activation": template,
            "activation_source": "carried" if activation else "formed_by_enable",
            "cache_hint": "把 facts.activation 原样缓存进本会话，并随每次请求放入 session.activation",
            "platforms": ctx.platforms(),
            "trellis_data": state["data"],
        },
        position=codes.position(scope="session"),
        next_="人显式选择对象：task-new 或 bind（第二轮为 run create）",
        warnings=warnings,
    )


def _eligible_task_bind(ctx, task):
    """独立接续资格（机制稿 §6.1）的绑定面。"""
    if task.get("status") == "archived":
        raise CliError("WF_BINDING_MISMATCH", {"reason": "task archived", "task": task.get("id")})
    run_id = task.get("run_id")
    if not run_id:
        return None
    from . import runs as runs_mod

    run = runs_mod.load_run(ctx.root, run_id)
    if run is None:
        raise CliError("WF_HISTORY_UNRESOLVED", {"reason": "run record missing", "run_id": run_id})
    terminal = run.get("terminal")
    if terminal == "normal":
        raise CliError("WF_BINDING_MISMATCH", {"reason": "run ended normally", "run_id": run_id})
    if terminal == "abnormal":
        permission = task.get("independent_resume") or {}
        if permission.get("decision") and permission.get("termination_action"):
            return permission
        raise CliError(
            "WF_BINDING_MISMATCH",
            {"reason": "no independent resume permission", "run_id": run_id},
        )
    raise CliError(
        "WF_BINDING_MISMATCH",
        {"reason": "task belongs to an in-flight run; bind the run instead", "run_id": run_id},
        next_="由绑定该实例的会话推进当前任务",
    )



def _resume_bind(ctx, key, session, object_ref, target, kind, record):
    """本会话遗留的 session.bind 意图：补完绑定/运行态与结案，返回同一对象。

    目标一律取自意图本身（`normalized_inputs` 固定目标）；请求目标不符即拒绝，
    不允许"用旧意图结案、绑到另一个对象"（机制稿 §5.1/§5.2）。
    """
    action = record.get("action") or {}
    if action.get("kind") != "session.bind" or action.get("state") == "done":
        return None
    holder = record.get("holder") or {}
    if holder.get("id") != key:
        return None
    intended = [item for item in (action.get("targets") or [])
                if isinstance(item, dict) and item.get("kind") in ("task", "run")]
    wanted = intended[0].get("id") if intended else None
    if wanted and target and wanted != target:
        raise CliError("WF_SEMANTIC_DECISION",
                       {"reason": "resume target differs from the recorded intent",
                        "intended": wanted, "requested": target},
                       next_="按原意图续做同一对象；换对象需先结束当前绑定")
    instance_id = session.get("instance_id") or session_mod.new_instance_id()
    binding = session_mod.load_binding(ctx.root, key)
    if binding is None:
        binding = {
            "schema_version": 1,
            "id": key,
            "revision": 0,
            "created_at": records.now_str(),
            "updated_at": records.now_str(),
            "write_mark": None,
            "action": None,
            "identity": {"provider": session["provider"], "value": session["identity"]},
            "instance_id": instance_id,
            "object": object_ref,
            "bound_at": records.now_str(),
        }
        session_mod.save_binding(ctx.root, key, binding)
    session_mod.write_runtime(
        ctx.root,
        key,
        {
            "binding_digest": records.plain_digest(binding),
            "instance_id": binding.get("instance_id"),
            "object": object_ref,
            "current_task": target if kind == "task" else None,
            "cursor": None,
        },
    )
    assertion = _control_assertion(ctx, "session.bind", _owner_ref(holder), action,
                                   [f".wf/session-bindings/{key}.json"])
    done = actions.complete(action, summary="session.bind", control_assertion=assertion)
    record = dict(record)
    record["action"] = done
    writer_mod.save(ctx.root, record)
    return ok(
        facts={"binding": binding, "resumed": True, "control_assertion": assertion},
        position=codes.position(scope=object_ref.get("kind"), task_id=target),
        next_="继续当前对象",
    )

def cmd_bind(ctx, args, kind="task"):
    _check_layout(ctx.root)
    target = args.value("--task") or args.value("--run")
    if not target:
        raise CliError("WF_PATH_INVALID", {"reason": "bind requires --task <id> or --run <id>"})
    session = ctx.session()
    key = ctx.key()
    code, profile_facts = session_mod.check_platforms(ctx.platforms(), session)
    if code:
        raise CliError(code, profile_facts, next_="先完成身份能力核实")
    existing = session_mod.load_binding(ctx.root, key)
    if existing:
        # 已有绑定：与日常写入口同一契约——实例标识必须携带且匹配（缺失进需人裁决）
        _require_instance_match(ctx, existing)
        # R50-04：绑定已写但动作未结案时，重入必须续做并结案，不能提前返回成功
        live = ctx.writer()
        resumed = _resume_bind(ctx, key, session, existing.get("object") or {}, target, kind, live)
        if resumed is not None:
            return resumed
        object_ref = existing.get("object") or {}
        if object_ref.get("id") != target:
            raise CliError(
                "WF_BINDING_MISMATCH",
                {"bound": object_ref, "requested": target},
                next_="同会话终身不能换对象；原对象结束后由新会话选择",
            )
        return ok(
            facts={"binding": existing},
            position=codes.position(scope=object_ref.get("kind"), task_id=target),
            next_="继续当前对象",
        )
    if kind == "task":
        from . import tasks as tasks_mod

        task = tasks_mod.load_task(ctx.root, target)
        if task is None:
            raise CliError("WF_TARGET_COLLISION", {"reason": "task not found", "task": target})
        _eligible_task_bind(ctx, task)
        object_ref = {"kind": "task", "id": target}
    else:
        from . import runs as runs_mod

        run = runs_mod.load_run(ctx.root, target)
        if run is None:
            raise CliError("WF_TARGET_COLLISION", {"reason": "run not found", "run": target})
        object_ref = {"kind": "run", "id": target}
    with _lock(ctx.root, hint="bind"):
        # 同对象接续允许进入核验路径（保留 WIP 随响应交回新会话）；其他对象仍阻断
        assert_no_foreign_wip(ctx, exclude_id=(object_ref or {}).get("id"))
        record = ctx.writer()
        # 中断恢复：本会话已有未完成的 session.bind 时续做，不报 WRITER_BUSY
        resumed = _resume_bind(ctx, key, session, object_ref, target, kind, record)
        if resumed is not None:
            return resumed
        if record.get("state") != "idle":
            raise CliError("WF_WRITER_BUSY", {"holder": record.get("holder")})
        generation = record.get("generation")
        if isinstance(generation, bool) or not isinstance(generation, int) or generation < 0:
            raise CliError("WF_HISTORY_UNRESOLVED", {"reason": "writer generation not readable",
                                                     "generation": generation})
        owner_scope = {"object": object_ref, "preparation": None}
        updated = writer_mod.acquire(
            record,
            kind="session",
            ident=key,
            scope=owner_scope,
            checkpoint={"step": "bound", "at": records.now_str()},
        )
        # R50-03：写权授予与动作意图**同一次写入**——不再有"已取写权、无意图"的窗口
        bind_inputs = {"task": target if kind == "task" else None,
                       "run": target if kind == "run" else None, "session_key": key}
        bind_targets = [{"kind": "writer", "id": "writer"},
                        {"kind": kind, "id": target}]
        updated = dict(updated)
        updated["action"] = actions.new_action(
            "session.bind",
            _owner_ref(updated.get("holder") or {}),
            int(updated.get("revision", 0)),
            bind_inputs,
            steps=["binding", "writer_grant"],
            head_before=actions.head_of(ctx.root),
            targets=bind_targets,
        )
        updated["action"]["steps"] = [{"id": step, "state": "pending"} for step in ["binding", "writer_grant"]]
        writer_mod.save(ctx.root, updated)
        instance_id = session.get("instance_id") or session_mod.new_instance_id()
        binding = {
            "schema_version": 1,
            "id": key,
            "revision": 0,
            "created_at": records.now_str(),
            "updated_at": records.now_str(),
            "write_mark": None,
            "action": None,
            "identity": {"provider": session["provider"], "value": session["identity"]},
            "instance_id": instance_id,
            "object": object_ref,
            "bound_at": records.now_str(),
        }

        def _write_binding(_current):
            # 意图（session.bind 动作）已先写进 writer 主记录，这里才做跨记录写入
            session_mod.save_binding(ctx.root, key, binding)
            session_mod.write_runtime(
                ctx.root,
                key,
                {
                    "binding_digest": records.plain_digest(binding),
                    "instance_id": instance_id,
                    "object": object_ref,
                    "current_task": target if kind == "task" else None,
                    "cursor": None,
                },
            )
            return f".wf/session-bindings/{key}.json"

        holder = updated.get("holder") or {}
        evidence = _write_binding(updated)
        if evidence is False:
            raise CliError("WF_PERSISTENCE_FAILED", {"operation": "session.bind"})
        assertion = _control_assertion(ctx, "session.bind", _owner_ref(holder),
                                       updated.get("action") or {}, [evidence])
        action_done = actions.complete(updated.get("action") or {}, summary="session.bind",
                                       control_assertion=assertion)
        winner = dict(updated)
        winner["action"] = action_done
        winner["write_mark"] = _write_mark(
            ctx, "session.bind", _owner_ref(holder),
            (holder.get("generation")), (action_done.get("head_before")),
            sorted(list(bind_inputs.keys())), action_done,
        )
        writer_mod.save(ctx.root, winner)
    inherited = None
    if kind == "task":
        from . import tasks as tasks_mod

        bound_task = tasks_mod.load_task(ctx.root, target)
        if bound_task:
            retained = tasks_mod.wip_paths(bound_task)
            registered = bool(retained)
            if not retained:
                # 未登记的脏改动同样交回新会话核对（与授予前置同一判据）
                from . import scope as scope_mod

                try:
                    classified = scope_mod.classify_candidates(ctx.root, bound_task, receipts=())
                    dirty = set(scope_mod.uncommitted_paths(ctx.root))
                    retained = sorted(set(classified["buckets"]["e"]) & dirty)
                except Exception:
                    retained = []
            if retained:
                inherited = {"task": target, "paths": retained, "registered": registered,
                             "wip": (bound_task.get("handoff") or {}).get("wip")}
    return ok(
        facts={
            "binding": binding,
            "generation": updated.get("generation"),
            "instance_id": instance_id,
            "control_assertion": assertion,
            "inherited_wip": inherited,
        },
        position=codes.position(scope=kind, task_id=target),
        next_=("按对象状态继续（task-approve / task-start 等）；若带保留 WIP，先核验指纹与归属"
               if inherited else "按对象状态继续（task-approve / task-start 等）"),
    )


# --------------------------------------------------------------------------
# 写权
# --------------------------------------------------------------------------


def cmd_writer(ctx, args):
    sub = (args.positional() or [None])[0]
    if sub == "acquire":
        return _writer_acquire(ctx)
    if sub == "release":
        return _writer_release(ctx)
    raise CliError("WF_PATH_INVALID", {"reason": "writer requires acquire|release"})


def retained_wip(task):
    """读任务真实保留的 WIP：stop --choice keep 写入 handoff.wip，另有 disposition.pending。"""
    from . import tasks as tasks_mod

    wip = ((task.get("handoff") or {}).get("wip")) or {}
    return {"paths": tasks_mod.wip_paths(task),
            "pending": (task.get("disposition") or {}).get("pending") or [],
            "resolved": wip.get("resolved"), "step_id": wip.get("step_id"), "has_wip": bool(wip)}


def wip_blockers(root, exclude_id=None):
    """其他活动任务里仍未处置的保留 WIP：路径仍留在工作树差异中，或 disposition.pending 非空。"""
    from . import scope as scope_mod
    from . import tasks as tasks_mod

    dirty = set(scope_mod.uncommitted_paths(root))
    tasks = [task for _directory, task in tasks_mod.iter_tasks(root)
             if task.get("status") != "archived"]
    # 已保存的 WIP 归属优先于 glob 重叠：显式记录过的路径不再算到别的任务头上
    explicit = {}
    for task in tasks:
        for path in tasks_mod.wip_paths(task):
            explicit.setdefault(path, task.get("id"))
    blocked = []
    for other in tasks:
        if other.get("id") == exclude_id:
            continue
        own_id = other.get("id")
        info = retained_wip(other)
        remaining = [path for path in info["paths"]
                     if path in dirty and explicit.get(path, own_id) == own_id]
        owned_dirty = []
        try:
            classified = scope_mod.classify_candidates(root, other, receipts=())
            owned_dirty = sorted(path for path in set(classified["buckets"]["e"]) & dirty
                                 if explicit.get(path, own_id) == own_id)
        except Exception:  # 分类失败不放大为阻断，按登记事实处理
            owned_dirty = []
        paths = sorted(set(remaining) | set(owned_dirty))
        if paths or info["pending"]:
            blocked.append({"task": own_id, "paths": paths, "pending": info["pending"],
                            "registered": bool(remaining)})
    return blocked


def assert_no_foreign_wip(ctx, exclude_id=None):
    """授予写权的统一前置：其他对象的保留 WIP 未处置时不得授予（机制稿 §6.4）。"""
    blocked = wip_blockers(ctx.root, exclude_id=exclude_id)
    if blocked:
        raise CliError("WF_WORKSPACE_UNRESOLVED",
                       {"reason": "other tasks keep un-disposed WIP", "blocked": blocked},
                       next_="先按各任务的实际处置落实保留 WIP，再授予写权")


def _require_instance_match(ctx, binding):
    """实例标识与身份能力状态：缺失/不同/未核实都不继续依赖它的写入（机制稿 §1.4）。"""
    carried = (ctx.session(required=False) or {}).get("instance_id")
    stored = binding.get("instance_id")
    if not stored:
        raise CliError("WF_RECORD_INVALID", {"reason": "binding lost instance_id", "session_key": ctx.key()})
    if not carried:
        raise CliError("WF_IDENTITY_UNRESOLVED",
                       {"reason": "instance_id not carried by request", "bound_instance": stored},
                       next_="由人核实会话实例并重新 wf-start 恢复原对象")
    if carried != stored:
        raise CliError("WF_BINDING_MISMATCH",
                       {"reason": "instance_id differs from binding", "carried": carried, "bound": stored},
                       next_="新会话请走受控恢复/交接，不改绑既有对象")
    code, platform_facts = session_mod.check_platforms(ctx.platforms(), ctx.session())
    if code:
        raise CliError(code, platform_facts, next_="install --platform <当前宿主> 后重试")


def _writer_acquire(ctx):
    key = ctx.key()
    binding = session_mod.load_binding(ctx.root, key)
    if not binding:
        raise CliError("WF_BINDING_MISMATCH", {"reason": "no persistent binding", "session_key": key},
                       next_="先由人选择对象（bind / task-new）")
    session = ctx.session()
    code, profile_facts = session_mod.check_platforms(ctx.platforms(), session)
    if code:
        raise CliError(code, profile_facts)
    _require_instance_match(ctx, binding)
    object_ref = binding.get("object") or {}
    with _lock(ctx.root, hint="writer acquire"):
        assert_no_foreign_wip(ctx, exclude_id=object_ref.get("id"))
        record = ctx.writer()
        if record.get("state") != "idle":
            raise CliError("WF_WRITER_BUSY", {"holder": record.get("holder")})
        updated = writer_mod.acquire(
            record,
            kind="session",
            ident=key,
            scope={"object": object_ref, "preparation": None},
            checkpoint={"step": "acquired", "at": records.now_str()},
        )
        writer_mod.save(ctx.root, updated)
        holder = updated.get("holder") or {}
        assertion = _atomic_writer_action(
            ctx,
            updated,
            "writer.acquire",
            _owner_ref(holder),
            {"session_key": key, "object": object_ref.get("id")},
            ["verify_identity", "grant"],
            lambda current: True,
        )
    return ok(
        facts={"generation": updated.get("generation"), "holder": updated.get("holder"), "control_assertion": assertion},
        position=codes.position(scope=object_ref.get("kind"), task_id=object_ref.get("id")),
        next_="继续当前对象步骤",
    )


def _writer_release(ctx):
    record, holder = ctx.require_held()
    key = ctx.key()
    bind = session_mod.load_binding(ctx.root, key) or {}
    if bind:
        _require_instance_match(ctx, bind)
    object_ref = bind.get("object") or {}
    if object_ref.get("kind") == "task":
        from . import tasks as tasks_mod

        task = tasks_mod.load_task(ctx.root, object_ref.get("id"))
        if task is None:
            raise CliError("WF_RECORD_INVALID", {"missing_task": object_ref.get("id")})
        tasks_mod.ensure_releasable(task, ctx.root)
    else:
        raise CliError("WF_BINDING_MISMATCH", {"reason": "release for run requires instance capability (round 2)"})
    with _lock(ctx.root, hint="writer release"):
        # 锁内重新执行完整核验：状态、持有者、范围与代次（机制稿 §4.2）
        ctx.require_held()
        record = ctx.writer()
        updated = writer_mod.release(record)
        writer_mod.save(ctx.root, updated)
        assertion = _atomic_writer_action(
            ctx,
            updated,
            "writer.release",
            _owner_ref(holder),
            {"session_key": key},
            ["verify_scope", "release"],
            lambda current: True,
        )
    return ok(
        facts={"generation": updated.get("generation"), "control_assertion": assertion},
        position=codes.position(scope=object_ref.get("kind"), task_id=object_ref.get("id")),
        next_="写权已空闲；下一对象需在新会话选择",
    )


def cmd_writer_handover(ctx, args):
    sub = (args.positional() or [None])[0]
    if sub == "begin":
        return _handover_begin(ctx, args)
    if sub == "accept":
        return _handover_accept(ctx)
    raise CliError("WF_PATH_INVALID", {"reason": "writer-handover requires begin --to <session-key>|accept"})


def _handover_begin(ctx, args):
    receiver = args.value("--to")
    decision_path = args.value("--decision")
    if not receiver or not decision_path:
        raise CliError("WF_PATH_INVALID", {"reason": "handover begin requires --to <session-key> --decision <path>"})
    decision = _load_decision(decision_path)
    record, holder = ctx.require_held()
    _require_instance_match(ctx, session_mod.load_binding(ctx.root, ctx.key()) or {})
    object_ref = (holder.get("scope") or {}).get("object") or {}
    if object_ref.get("kind") == "task":
        from . import tasks as tasks_mod

        task = tasks_mod.load_task(ctx.root, object_ref.get("id"))
        if task is None:
            raise CliError("WF_RECORD_INVALID", {"missing_task": object_ref.get("id")})
        if task.get("status") == "archived":
            raise CliError("WF_BINDING_MISMATCH", {"reason": "object already archived"})
        saved = bool(task.get("paused")) or bool((task.get("handoff") or {}).get("wip"))
        if not saved:
            raise CliError(
                "WF_SEMANTIC_DECISION",
                {"reason": "交接前须先保存进度、暂停与 WIP 处置", "task": task.get("id"),
                 "paused": task.get("paused"), "wip": (task.get("handoff") or {}).get("wip")},
                next_="先 task-pause 或记录 WIP，再发起 handover begin",
            )
    with _lock(ctx.root, hint="handover begin"):
        ctx.require_held()
        record = ctx.writer()
        updated = writer_mod.handover_begin(
            record,
            to_session_key=receiver,
            object_ref=object_ref,
            decision=decision,
        )
        writer_mod.save(ctx.root, updated)
    return ok(
        facts={"writer_state": updated.get("state"), "handover": updated.get("handover")},
        position=codes.position(scope="session"),
        next_="接收会话在新会话执行 writer-handover accept",
    )


def _handover_accept(ctx):
    key = ctx.key()
    session = ctx.session()
    code, profile_facts = session_mod.check_platforms(ctx.platforms(), session)
    if code:
        raise CliError(code, profile_facts)
    with _lock(ctx.root, hint="handover accept"):
        record = ctx.writer()
        if record.get("state") != "recovering":
            raise CliError("WF_WRITER_BUSY", {"writer_state": record.get("state")})
        handover = record.get("handover") or {}
        if handover.get("receiver_session_key") != key:
            raise CliError("WF_BINDING_MISMATCH", {"reason": "not the declared receiver", "handover": handover})
        object_ref = handover.get("object_or_preparation") or {}
        binding = session_mod.load_binding(ctx.root, key)
        if binding:
            # 接收入口同样核实例标识与能力状态（统一实现，不在个别入口补检查）
            _require_instance_match(ctx, binding)
        if binding and (binding.get("object") or {}).get("id") not in (None, object_ref.get("id")):
            raise CliError("WF_BINDING_MISMATCH", {"binding": binding.get("object"), "handover": object_ref})
        updated = writer_mod.handover_accept(
            record,
            session_key=key,
            scope={"object": object_ref, "preparation": None},
        )
        writer_mod.save(ctx.root, updated)
        if not binding:
            updated_binding = {
                "schema_version": 1,
                "id": key,
                "revision": 0,
                "created_at": records.now_str(),
                "updated_at": records.now_str(),
                "write_mark": None,
                "action": None,
                "identity": {"provider": session["provider"], "value": session["identity"]},
                "instance_id": session.get("instance_id") or session_mod.new_instance_id(),
                "object": object_ref,
                "bound_at": records.now_str(),
            }
            session_mod.save_binding(ctx.root, key, updated_binding)
    return ok(
        facts={"generation": updated.get("generation"), "object": object_ref},
        position=codes.position(scope=object_ref.get("kind"), task_id=object_ref.get("id")),
        next_="按原对象记录继续",
    )


# --------------------------------------------------------------------------
# 人的决定输入
# --------------------------------------------------------------------------


def _load_decision(path):
    try:
        data = records.load_json(path)
    except records.RecordInvalid as exc:
        raise CliError("WF_RECORD_INVALID", {"reason": f"decision file invalid: {exc}", "path": path})
    except OSError as exc:
        raise CliError("WF_PATH_INVALID", {"reason": f"decision unreadable: {exc}", "path": path})
    if data is None:
        raise CliError("WF_PATH_INVALID", {"reason": "decision file missing", "path": path})
    items = data if isinstance(data, list) else [data]
    decisions = []
    for item in items:
        if not isinstance(item, dict):
            raise CliError("WF_RECORD_INVALID", {"reason": "decision must be an object or array of objects"})
        missing = [key for key in ("source", "at", "subject", "object_digest", "choice", "reason") if key not in item]
        if missing:
            raise CliError("WF_RECORD_INVALID", {"reason": "decision missing fields", "missing": missing})
        if not item.get("choice"):
            raise CliError("WF_RECORD_INVALID", {"reason": "decision choice is empty"})
        decisions.append(item)
    return decisions


def cmd_stop(ctx, args):
    path = args.value("--decision")
    if not path:
        raise CliError("WF_PATH_INVALID", {"reason": "stop requires --decision <path>"})
    decisions = _load_decision(path)
    choices = [item.get("choice") for item in decisions]
    if choices[0] not in ("commit", "keep", "reverse", "transfer"):
        raise CliError("WF_SEMANTIC_DECISION", {"choices": choices, "reason": "收工选择必须是 commit/keep/reverse/transfer"})
    from . import tasks as tasks_mod

    return tasks_mod.stop_work(ctx, decisions, choices[0])


def cmd_spec(ctx, args):
    path = args.value("--file")
    if not path:
        raise CliError("WF_PATH_INVALID", {"reason": "spec requires --file <RepoPath>"})
    key = ctx.key()
    from . import spec as spec_mod

    try:
        from .paths import normalize

        relative = normalize(path)
    except Exception as exc:
        raise CliError("WF_PATH_INVALID", {"reason": str(exc), "path": path})
    loaded_meta = spec_mod.load_spec(ctx.root, relative)
    if loaded_meta.get("violation"):
        raise CliError("WF_PATH_INVALID",
                       {"reason": loaded_meta["violation"], "path": relative},
                       next_="spec 只能读取项目根内、且不跨越嵌套仓库的真实文件")
    if loaded_meta["digest"] is None:
        raise CliError("WF_PATH_INVALID", {"reason": "spec file missing", "path": relative})
    config_record, config_problems = config_mod().load_project_config(ctx.root, allow_missing=True)
    budget, budget_problem = config_mod().value_of(config_record, config_problems, "spec_output_codepoints")
    if budget_problem:
        raise CliError("WF_CAPABILITY_UNAVAILABLE",
                       {"reason": budget_problem, "key": "spec_output_codepoints"},
                       next_="修正 project-config.json 的该键后重试")
    if not budget or budget <= 0:  # 0 也是非法（正整数键）
        raise CliError("WF_CAPABILITY_UNAVAILABLE",
                       {"reason": "spec_output_codepoints must be a positive integer",
                        "key": "spec_output_codepoints"})
    try:
        loaded = spec_mod.load_one_with_budget(ctx.root, relative, budget)
    except OSError as exc:
        raise CliError("WF_PATH_INVALID", {"reason": f"unreadable: {exc}", "path": relative})
    sidecar = spec_mod.record_read(
        ctx.root, key, relative,
        complete=True,
        deliver_codepoints=loaded["codepoints"],
        budget=budget,
    )
    warnings = []
    if loaded["over_budget"]:
        warnings.append({"path": relative, "note": "超预算完整读取", "codepoints": loaded["codepoints"],
                         "budget": budget})
    if loaded_meta["problems"]:
        warnings.append({"path": relative, "note": "metadata not parseable", "problems": loaded_meta["problems"]})
    payload = ok(
        facts={
            "path": relative,
            "digest": loaded_meta["digest"],
            "codepoints": loaded["codepoints"],
            "budget": budget,
            "complete": True,
            "metadata": loaded_meta["metadata"],
            # 正文两路都交付：读取留痕记「完整读取」就必须真的把正文交出去，
            # 不能只给摘要却留下成功读取事实（设计稿 §6.2 读取留痕）
            "content": loaded["text"],
            "sidecar": sidecar,
        },
        position=codes.position(scope="session"),
        next_="按正文执行；Check 期会核对读取记录与版本",
        warnings=warnings,
    )
    if not ctx.json_output:
        sys.stdout.write(loaded["text"])
        if not loaded["text"].endswith("\n"):
            sys.stdout.write("\n")
        sys.stderr.write(
            f"{relative}  {loaded_meta['digest']}  codepoints={loaded['codepoints']}"
            f"{'  超预算完整读取' if loaded['over_budget'] else ''}\n"
        )
        payload["__rendered__"] = True
    return payload


def config_mod():
    from . import config as config_mod

    return config_mod


def _task_command(name):
    def handler(ctx, args):
        from . import tasks as tasks_mod

        return getattr(tasks_mod, name)(ctx, args)

    return handler


def _unavailable(round_no, capability):
    def handler(ctx, args):
        from . import assets

        raise assets.CapabilityUnavailable(capability, round_no)

    return handler


def _review_command(kind):
    def handler(ctx, args):
        from . import review as review_mod, tasks as tasks_mod

        task_id = args.value("--task")
        if not task_id:
            raise CliError("WF_PATH_INVALID", {"reason": f"review-{kind} requires --task <id>"})
        task = tasks_mod.load_task(ctx.root, task_id)
        if task is None:
            raise CliError("WF_TARGET_COLLISION", {"reason": "task not found", "task": task_id})
        if kind == "launch":
            request = args.value("--launch-request")
            if not request:
                raise CliError("WF_PATH_INVALID", {"reason": "review-launch requires --launch-request <path>"})
            try:
                return review_mod.launch(ctx, task, request)
            except review_mod.ReviewError as exc:
                raise CliError(exc.code, exc.facts)
        if kind == "import":
            round_no = args.value("--round")
            slot = args.value("--slot")
            report = args.value("--report")
            if not (round_no and slot and report):
                raise CliError("WF_PATH_INVALID", {"reason": "review-import requires --round --slot --report"})
            try:
                return review_mod.import_report(ctx, task, int(round_no), slot, report)
            except review_mod.ReviewError as exc:
                raise CliError(exc.code, exc.facts)
        round_no = args.value("--round")
        if not round_no:
            raise CliError("WF_PATH_INVALID", {"reason": "review-decide requires --round <n>"})
        try:
            return review_mod.decide(ctx, task, int(round_no), args.value("--plan"), args.value("--unavailable"))
        except review_mod.ReviewError as exc:
            raise CliError(exc.code, exc.facts)

    return handler


def cmd_confirm_executor(ctx, args):
    raise CliError(
        "WF_CAPABILITY_UNAVAILABLE",
        {"reason": "confirm-executor is handled by the bootstrap layer (.wf/bin/wf.py)"},
        next_="直接运行 wf.py confirm-executor --scope system|global|project",
    )


COMMANDS = {
    "status": cmd_status,
    "gate": cmd_gate,
    "spec": cmd_spec,
    "inspect": cmd_inspect,
    "version": cmd_version,
    "enable": cmd_enable,
    "bind": cmd_bind,
    "writer": cmd_writer,
    "writer-handover": cmd_writer_handover,
    "stop": cmd_stop,
    "confirm-executor": cmd_confirm_executor,
    "task-new": _task_command("cmd_task_new"),
    "task-approve": _task_command("cmd_task_approve"),
    "task-start": _task_command("cmd_task_start"),
    "task-replan": _task_command("cmd_task_replan"),
    "task-pause": _task_command("cmd_task_pause"),
    "task-resume": _task_command("cmd_task_resume"),
    "task-curate": _task_command("cmd_task_curate"),
    "task-check": _task_command("cmd_task_check"),
    "task-knowledge": _task_command("cmd_task_knowledge"),
    "task-retrospect": _task_command("cmd_task_retrospect"),
    "task-attribute": _task_command("cmd_task_attribute"),
    "task-abandon": _task_command("cmd_task_abandon"),
    "task-reassess": _task_command("cmd_task_reassess"),
    "archive": _task_command("cmd_archive"),
    "baseline-apply": _task_command("cmd_baseline_apply"),
    "spec-update": _task_command("cmd_spec_update"),
    "dep": _unavailable(2, "dependency edges (D07)"),
    "task-rework": _unavailable(2, "task rework (D07)"),
    "task-replace": _unavailable(2, "task replace (D07)"),
    "review-launch": _review_command("launch"),
    "review-import": _review_command("import"),
    "review-decide": _review_command("decide"),
    "definition": _unavailable(2, "definition prepare/validate (D03/D11)"),
    "run": _unavailable(2, "workflow instances (D03/D11/D12/D13)"),
    "upgrade": _unavailable(3, "upgrade --apply / release identity (D22/D37)"),
}


ACTIVATION_REQUIRED = frozenset({
    "task-approve", "task-start", "task-replan", "task-pause", "task-resume", "task-curate",
    "task-check", "task-knowledge", "task-retrospect", "task-attribute", "task-abandon",
    "task-reassess", "archive", "baseline-apply", "spec-update", "stop",
    "review-launch", "review-import", "review-decide",
})


# start 路由里会建立绑定/写权的入口：同样要求本会话已启用（设计稿 §1.3）
ACTIVATION_REQUIRED_ROUTING = frozenset({"bind", "task-new"})


def _needs_activation(command, argv):
    """业务写入与 start 路由的绑定入口都需 activation；纯只读查询不需要。"""
    if command in ACTIVATION_REQUIRED or command in ACTIVATION_REQUIRED_ROUTING:
        return True
    sub = (argv[1:2] or [None])[0]
    if command == "writer":
        return sub in ("release", "acquire")
    if command == "writer-handover":
        return sub == "begin"
    return False


def dispatch(ctx, argv):
    if not argv:
        raise CliError("WF_PATH_INVALID", {"reason": "missing subcommand", "commands": sorted(COMMANDS)})
    command = argv[0]
    handler = COMMANDS.get(command)
    if handler is None:
        raise CliError(
            "WF_PATH_INVALID",
            {"reason": f"unknown subcommand: {command}", "commands": sorted(COMMANDS)},
        )
    if _needs_activation(command, argv):
        ctx.require_activation()
    ctx.args = Args(argv[1:])
    payload = handler(ctx, ctx.args)
    if payload is None:
        raise CliError("WF_PERSISTENCE_FAILED", {"reason": "handler returned no result"})
    return payload


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    root = os.environ.get("WF_PROJECT_ROOT")
    if not root:
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    ctx = Context(root, argv)
    try:
        payload = dispatch(ctx, argv)
    except CliError as exc:
        payload = exc.result()
    except assets.CapabilityUnavailable as exc:
        payload = codes.result(
            "WF_CAPABILITY_UNAVAILABLE",
            next_=f"等第 {exc.round_no} 轮交付，或改用已交付路径",
            facts=dict(exc.facts, capability=exc.capability, round=exc.round_no),
        )
    except records.RecordInvalid as exc:
        payload = codes.result("WF_RECORD_INVALID", facts={"reason": str(exc)})
    except lock.LockBusy as exc:
        payload = codes.result("WF_WRITER_BUSY", facts={"reason": str(exc), "path": exc.path})
    except lock.LockUnavailable as exc:
        # 锁对象内容不可识别/初始化未完成：机制稿 §4.1 指定 WF_CAPABILITY_UNAVAILABLE，不覆盖、不认领
        payload = codes.result("WF_CAPABILITY_UNAVAILABLE",
                               facts=dict({"reason": str(exc), "path": exc.path},
                                          **(getattr(exc, "facts", {}) or {})))
    except Exception as exc:  # 子模块的领域错误按各自原因码输出；其余为实现内部错误（70）
        code = getattr(exc, "code", None)
        if isinstance(code, str) and code.startswith("WF_") and code in codes.CODES:
            payload = codes.result(
                code,
                next_=getattr(exc, "next", None) or getattr(exc, "exit_hint", None),
                facts=getattr(exc, "facts", {}) or {},
            )
        else:
            sys.stderr.write(f"internal error: {exc}\n")
            if os.environ.get("WF_DEBUG"):
                traceback.print_exc()
            return codes.INTERNAL_ERROR_EXIT
    return emit(payload, json_output="--json" in argv)
