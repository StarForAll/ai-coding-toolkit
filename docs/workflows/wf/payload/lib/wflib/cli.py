"""cli.py — 子命令面、请求信封、代次核验与输出（实现稿 §2、机制稿 §11.1）。

语义层入口：只负责解析请求、核验身份/绑定/写权、分派固定处理器与渲染结果。
"""

from __future__ import annotations

import json
import os
import re
import sys
import traceback
import uuid

from . import actions, assets, attestation as attestation_mod, codes, config, decisions as decisions_mod, lock, protocol as protocol_mod, records, session as session_mod, writer as writer_mod
from .paths import join

# 身份出口的唯一文案（机制稿 §1.4）：显式 `provider=wf` 信封**会被拒**（无本地证据），
# 唯一可用的显式通道是 `provider=host` 且宿主能给出稳定 `session_id`。
# 此前四处出口写「用显式信封」而未点明 provider，读者会以为 wf 信封可行（实现稿 §2.3.11 文案债）。
EXPLICIT_ENVELOPE_EXIT = (
    "改用 provider=host 的显式信封（--envelope/stdin，需宿主提供 session_id；"
    "provider=wf 的显式信封会被拒）"
)


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


ENVELOPE_CACHE_DIR = ".wf/.runtime/envelopes"


def envelope_cache_dir(root):
    return os.path.join(str(root), *ENVELOPE_CACHE_DIR.split("/"))


def envelope_cache_path(root, session_id):
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", str(session_id or "unknown"))[:64]
    return os.path.join(envelope_cache_dir(root), f"{safe}.json")


def envelope_cache_candidates(root):
    directory = envelope_cache_dir(root)
    if not os.path.isdir(directory):
        return []
    return sorted(os.path.join(directory, name) for name in os.listdir(directory) if name.endswith(".json"))


def remember_envelope(root, envelope, payload):
    """把本次生效的信封与回显事实写回缓存（会话内免重复拼装，2026-11-07）。

    只缓存"身份 + activation + instance_id + generation"，不缓存业务输入；
    目录 `.wf/.runtime/` 已在安装器的 gitignore 托管段里，不会被提交。
    """
    if not isinstance(envelope, dict):
        return
    facts = (payload or {}).get("facts") or {}
    session = dict(envelope.get("session") or {})
    if isinstance(facts.get("activation"), dict):
        session["activation"] = facts["activation"]
    if isinstance(facts.get("generation"), int):
        inputs = dict(envelope.get("inputs") or {})
        inputs["generation"] = facts["generation"]
        envelope = dict(envelope, inputs=inputs)
    if isinstance(facts.get("instance_id"), str) and facts["instance_id"]:
        session["instance_id"] = facts["instance_id"]
    merged = dict(envelope, session=session)
    session_id = (session.get("identity") or {}).get("session_id") or "unknown"
    try:
        path = envelope_cache_path(root, session_id)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(merged, handle, ensure_ascii=False, indent=2)
            handle.write(chr(10))
    except OSError:
        # 缓存不可写不影响业务结果：下一次显式给信封即可
        return


class Context:
    def __init__(self, root, argv):
        self.root = str(root)
        self.args = Args(argv)
        self.json_output = "--json" in argv
        self._envelope = None
        self._session = None
        self._key = None
        self._manifest = None

    # -- 自动身份模式（R3）------------------------------------------------
    def identity_path(self) -> str:
        """身份兜底证据策略（`identity_path`，机制稿 §8.1；缺省 P1）。

        只在宿主未提供会话标识时才起作用：P1 覆盖终端/单聊天与为每聊天派生独立 shell 的
        多聊天，P2 处置 l1-drift，P3 用于 tmux（只认 L1）。非法值按 WF_RECORD_INVALID，
        不静默取 P1（机制稿 §8.1「未知/非法项仅阻断依赖该项的判断」）。
        """
        from . import config as config_mod

        config, problems = config_mod.load_project_config(self.root, allow_missing=True)
        value, problem = config_mod.value_of(config, problems, "identity_path")
        if problem:
            raise CliError("WF_RECORD_INVALID", {"key": "identity_path", "reason": problem})
        return value or "P1"

    def _auto_resolve(self):
        """从锚点解析当前会话：返回 (session_key, attachment) 或 (None, None)。

        只做"命中"判定（§2.2b #1/#2/#3）；未命中时返回 (None, None)，由调用方决定
        是建立新会话（enable）还是拒绝（其它命令）。
        """
        from . import identity_store as store

        candidates = session_mod.candidates()
        if not candidates:
            return None, None
        keys = [session_mod.anchor_key(item) for item in candidates]
        routes = store.load_routes(self.root)
        path = self.identity_path()
        current_root = candidates[-1] if candidates[-1]["kind"] == "pid" else candidates[0]

        l1_owners = store.owners_of(routes, keys[0]) if candidates[0]["kind"] == "sid" else []
        l2_owners = []
        for key, item in zip(keys, candidates):
            if item["kind"] == "pid":          # 锚点 kind 是 pid；路由 via 才叫 proc
                l2_owners = store.owners_of(routes, key)

        if len(l1_owners) == 1:                       # #1 / #2：L1 单主命中即以此为准
            return l1_owners[0], store.load_attachment(self.root, l1_owners[0])
        if l2_owners:
            states = []
            for owner in l2_owners:
                attachment = store.load_attachment(self.root, owner)
                if attachment is None:
                    continue
                states.append(attachment)
            if not states:
                raise CliError("WF_HISTORY_UNRESOLVED",
                               {"reason": "route exists but attachment missing",
                                "owners": l2_owners},
                               next_="按 §3.5 的附件恢复流程重跑 /wf-start")
            verdict = session_mod.adjudicate(states, current_root, path)
            if verdict["verdict"] == session_mod.USE:
                owner = verdict["session_key"]
                return owner, store.load_attachment(self.root, owner)
            raise CliError("WF_IDENTITY_UNRESOLVED",
                           {"reason": verdict["reason"], "facts": verdict.get("facts"),
                            "owners": l2_owners,
                            "exits": ["人调 /wf-start 显式登记当前调用者",
                                      "结束另一个调用者后重试",
                                      EXPLICIT_ENVELOPE_EXIT]},
                           next_="按 facts.reason 的出口处置后重试")
        return None, None

    def auto_session(self, establish=False):
        """自动身份模式：返回合成 session（`source="auto"`）或 None。"""
        from . import identity_store as store

        key, attachment = self._auto_resolve()
        if key is None:
            if not establish:
                return None
            return None
        session = {"provider": "wf",
                   "identity": (attachment or {}).get("identity") or {},
                   "instance_id": (attachment or {}).get("instance_expected"),
                   "activation": (attachment or {}).get("activation"),
                   "source": "auto"}
        if attachment and attachment.get("activation_stale"):
            raise CliError("WF_NOT_ENABLED",
                           {"reason": "activation_stale", "session_key": key,
                            "roots": attachment.get("roots")},
                           next_="人重新调用 /wf-start（旧调用者已停或无法核实）")
        self._auto_attachment = attachment
        self._auto_key = key
        self._auto_root = next((item for item in session_mod.candidates()
                                if item["kind"] == "pid"), None) or \
                               (session_mod.candidates() or [None])[-1]
        return session

    # -- 信封 ------------------------------------------------------------
    def envelope(self, required=True):
        data = self._read_explicit(required=required)
        if data is not None:
            return data
        if not required:
            return None
        # 没有任何显式信道时交给自动模式：由 session() 从锚点解析
        auto = self.auto_session()
        if auto is not None:
            self._session = auto
            return {"session": None, "inputs": {}}
        raise CliError(
            "WF_IDENTITY_UNRESOLVED",
            {"reason": "request envelope missing",
             "fields": ["session.provider", "session.identity"],
             "exits": ["在保留的终端里重跑 /wf-start（自动身份模式）",
                       "或从标准输入 / --envelope 提供会话请求信封"]},
            next_="人调 /wf-start 建立执行会话后重试",
        )

    def _read_explicit(self, required=True):
        """读取显式信封（stdin/--envelope/--envelope-last）；没有信道时返回 None。"""
        if self._envelope is not None:
            return self._envelope
        path = self.args.value("--envelope")
        if not path and self.args.flag("--envelope-last"):
            # 缓存按会话分文件（2026-11-07）：同一项目里主会话与多个 reviewer 会话并存，
            # 单一"最后写入者"的缓存会让 A 用上 B 的身份（实测可复现）。
            session_id = self.args.value("--session")
            candidates = envelope_cache_candidates(self.root)
            if session_id:
                path = envelope_cache_path(self.root, session_id)
                if not os.path.isfile(path):
                    raise CliError("WF_IDENTITY_UNRESOLVED",
                                   {"reason": "no cached envelope for this session", "session": session_id,
                                    "known": [os.path.basename(item) for item in candidates]},
                                   next_="先成功调用一次该会话的命令，或用 --envelope/stdin 提供")
            elif len(candidates) == 1:
                path = candidates[0]
            elif not candidates:
                raise CliError("WF_IDENTITY_UNRESOLVED",
                               {"reason": "no cached envelope yet", "expected": envelope_cache_dir(self.root)},
                               next_="先成功调用一次带完整信封的命令（会缓存），或用 --envelope/stdin 提供")
            else:
                raise CliError("WF_IDENTITY_UNRESOLVED",
                               {"reason": "multiple cached sessions; pass --session <id>",
                                "known": [os.path.basename(item) for item in candidates]},
                               next_="用 --session <会话 id> 指定要复用哪个会话的信封")
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
                    # 人手直接跑命令时不要静默挂起：没有显式信道 ⇒ 交给自动模式判定
                    return None
                text = sys.stdin.read()
            except OSError:
                text = ""
        if not text.strip():
            return None
        try:
            data = records.loads(text)
        except records.RecordInvalid as exc:
            raise CliError("WF_IDENTITY_UNRESOLVED", {"reason": f"envelope invalid: {exc}"})
        if not isinstance(data, dict):
            raise CliError("WF_IDENTITY_UNRESOLVED", {"reason": "envelope is not a JSON object"})
        self._envelope = data
        return data

    def explicit_session(self):
        """显式模式：信封里**有 session 对象**（无则返回 None，交给自动模式）。"""
        envelope = self._read_explicit(required=False)
        if not isinstance(envelope, dict):
            return None
        payload = envelope.get("session")
        if not isinstance(payload, dict):
            return None
        try:
            return session_mod.validate_session(payload)
        except session_mod.IdentityError as exc:
            raise CliError(
                "WF_IDENTITY_UNRESOLVED",
                {"reason": str(exc), "fields": ["session.provider", "session.identity"]},
                next_="核实宿主身份字段，或改用 wf 签发路径",
            )

    def session(self, required=True):
        explicit = self.explicit_session()
        if explicit is not None:
            self._session = explicit
            return explicit
        if self._session is None:
            self._session = self.auto_session()
            if self._session is not None and self._needs_roots():
                self._enforce_roots()
        if self._session is None and required:
            raise CliError(
                "WF_IDENTITY_UNRESOLVED",
                {"reason": "no execution boundary resolved",
                 "exits": ["在保留的终端里重跑 /wf-start", EXPLICIT_ENVELOPE_EXIT]},
                next_="人调 /wf-start 建立执行会话后重试",
            )
        return self._session

    # 需要 activation 且参与 roots 的写业务命令（§4.2b 四分类）
    ROOTS_COMMANDS = frozenset({
        "task-new", "task-approve", "task-start", "task-check", "stop", "archive",
        "bind", "writer", "writer-handover", "dep", "spec-update", "definition",
        "run", "baseline-apply", "task-knowledge", "review-launch", "review-import",
        "review-decide",
    })

    def _needs_roots(self) -> bool:
        return getattr(self, "command", "") in self.ROOTS_COMMANDS

    def _enforce_roots(self):
        """§3.4：snapshot → 判定 → 维护；阻断时**不 upsert**，并给出结构化出口。"""
        from . import identity_store as store

        attachment = getattr(self, "_auto_attachment", None)
        root = getattr(self, "_auto_root", None)
        if not isinstance(attachment, dict) or root is None:
            return
        verdict = store.maintain_roots(attachment, root, self.identity_path())
        store.save_attachment(self.root, self._auto_key, attachment)
        self._auto_attachment = attachment
        if verdict["action"] == "block":
            reason = verdict["reason"]
            facts = dict(verdict.get("facts") or {})
            facts["reason"] = reason
            if reason == store.CONCURRENT_CALLER:
                facts["exits"] = ["人调 /wf-start 显式登记当前调用者",
                                  "结束另一个调用者后重试"]
                next_ = "按 C2 分级：未登记的调用者不得自动继承会话"
            else:
                facts["exits"] = ["人核实旧调用者是否停止；确认后 repair --mark-root-gone",
                                  EXPLICIT_ENVELOPE_EXIT]
                next_ = "证据未知：先人核实再重试"
            raise CliError("WF_IDENTITY_UNRESOLVED", facts, next_=next_)
        if verdict["action"] == "stale":
            facts = dict(verdict.get("facts") or {})
            facts["reason"] = "activation_stale"
            raise CliError("WF_NOT_ENABLED", facts, next_="人重新调用 /wf-start")

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
            holder = record.get("holder") or {}
            if record.get("state") == "idle" and not holder:
                # 空闲但没持有：这不是"被别人占着"，给一条能直接执行的出口
                # （审查询问过：绑定了任务、writer 空闲时 AI 只能靠读源码猜出路）
                hint = f"writer acquire --task {task}" if task else "writer acquire --task <id>"
                raise CliError(
                    "WF_SEMANTIC_DECISION",
                    {"writer_state": "idle", "reason": "写权空闲且本会话未持有",
                     "exits": [f"先取得写权：`wf {hint}` 后重入"]},
                    next_=f"`wf {hint}` 取得写权后重入本条命令",
                )
            raise CliError(
                "WF_WRITER_BUSY",
                {"writer_state": record.get("state"), "holder": holder},
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
            from . import identity_store as store

            facts["lease"] = {
                "state": store.lease_state(record, key, store.load_attachment(ctx.root, key), binding),
            }
            if task_id:
                from . import tasks as tasks_mod
                from . import taskfiles as task_files_mod

                task = tasks_mod.load_task(ctx.root, task_id)
                if task is None:
                    raise CliError("WF_RECORD_INVALID", {"missing_task": task_id, "binding": object_ref})
                position = _position_for(task, "task")
                from . import tasks as tasks_mod  # noqa: F811  (上面已局部导入)
                facts["startup"] = tasks_mod.startup_check(ctx, task)
                if ctx.args.flag("--short"):
                    # 只回"我该知道什么"，避免整份 task.json 进上下文（dogfood：13 次全量 cat）。
                    # ⑥：四条件 + `exits`（原样，含 round）+ 与 D4 预检**同一个函数**给出的确定阻断。
                    from . import review as review_mod

                    plan = task.get("plan") or {}
                    # D4 预检只在 finish 阶段求值：其他阶段它会把"还没做"报成"确定阻断"，
                    # 等于用 status 试归档探路（wf-repair-loop 明令禁止）。
                    precheck = (tasks_mod.archive_precheck(ctx, task)
                                if task.get("phase") == "finish" else {"blocking": []})
                    return ok(facts={"task": {"id": task_id, "title": task.get("title"),
                                              "status": task.get("status"), "phase": task.get("phase"),
                                              "complexity": plan.get("complexity"), "tdd": plan.get("tdd"),
                                              **_short_check(ctx, task)},
                                     "repair_scope": _short_repair(
                                         review_mod.repair_scope(ctx, task), precheck,
                                         review_mod.acceptance_echo(task)),
                                     # A6 裁定：缺登记摘要的遗留记录不计入 C3 阻断，单列在 status
                                     "legacy_unverifiable": review_mod.legacy_unverifiable(ctx, task)},
                              position=position,
                              next_=protocol_mod.states().next_for(
                                  task.get("status"), task.get("phase"),
                                  paused=bool(task.get("paused")), suspended=bool(task.get("suspended"))))
                facts["task"] = {
                    "files": task_files_mod.summary(ctx.root, task_id),
                    "status": task.get("status"),
                    "phase": task.get("phase"),
                    "paused": task.get("paused"),
                    "suspended": task.get("suspended"),
                    "terminal": task.get("terminal"),
                    "title": task.get("title"),
                }
                # ⑥：修复态事实集（纯派生，不落盘）+ 当前生效的放行清单（强制回显）
                from . import review as review_mod

                facts["repair_scope"] = review_mod.repair_scope(ctx, task)
                facts["unknown_acceptances"] = review_mod.acceptance_echo(task)
                facts["legacy_unverifiable"] = review_mod.legacy_unverifiable(ctx, task)
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
    task_facts = facts.get("task") or {}
    return ok(facts=facts, position=position,
              next_=protocol_mod.states().next_for(
                  task_facts.get("status"), task_facts.get("phase"),
                  paused=bool(task_facts.get("paused")), suspended=bool(task_facts.get("suspended"))))


def _short_repair(scope, precheck, acceptances=()):
    """`--short` 的修复态投影：四条件 + `exits` 原样 + D4 预检的确定阻断。

    不重新推导任何判据：条件取自 `repair_scope`（本身来自共享子判定），`exits` 原样过滤。
    """
    conclusion = scope.get("conclusion") or {}
    unreleased = [item for item in scope.get("unverifiable") or [] if not item.get("released")]
    conditions = {
        "C1_check_valid": bool(conclusion.get("check_valid")),
        "C2_no_open_blocking": not scope.get("open_blocking"),
        "C3_no_unreleased_evidence": not unreleased,
        "C4_review_bound_pass": (not scope.get("review_required")) or (
            conclusion.get("verdict") == "pass" and bool(conclusion.get("binding"))),
    }
    return {"conditions": conditions,
            "exits": scope.get("exits") or [],
            "blocking": precheck.get("blocking") or [],
            "blocking_scope": "finish",
            "open_blocking": scope.get("open_blocking") or [],
            "unverifiable": scope.get("unverifiable") or [],
            "rounds": [{"round": item.get("round"), "verdict": item.get("verdict"),
                        "inferred": bool(item.get("inferred"))}
                       for item in scope.get("rounds") or []],
            # 放行清单是"强制回显"（§6 cli ④/#46），--short 也列（by/at/quote 都很短）
            "unknown_acceptances": list(acceptances)}


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
# 平台名与 `installation.platforms` 同一取值域（2026-11-05 修正：原先只扫 3 个宿主、
# 且用 "claude" 而非平台名 "claudecode"，导致 cursor/geminicli/copilot 与 claudecode 的
# "仅 hook 激活、无托管块"场景漏检并直接放行，属互斥检查的假阴性）。
TRELLIS_HOST_CONFIGS = {
    "claudecode": (".claude/settings.json", ".claude/settings.local.json", ".claude/hooks"),
    "codex": (".codex/hooks.json", ".codex/config.toml"),
    "dsh": (".dsh/hooks.json", ".dsh/settings.json", ".dsh/plugins"),
    "cursor": (".cursor/hooks.json", ".cursor/mcp.json", ".cursor/rules"),
    "geminicli": (".gemini/settings.json", ".gemini/hooks"),
    "copilot": (".github/copilot-instructions.md", ".github/instructions"),
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


def _sync_attachment_instance(ctx, key, instance_id):
    """把（首次）绑定的 instance_id 写回自动模式的附件（§3.6）。

    只在自动模式下有附件；显式模式没有附件，直接跳过。
    若附件里已有不同值 ⇒ 保留差异（由 §3.5 的 S1/S2 处置），不覆盖。
    """
    from . import identity_store as store

    attachment = store.sync_attachment_instance(ctx.root, key, instance_id)
    if not isinstance(attachment, dict):
        return
    if getattr(ctx, "_auto_key", None) == key:
        ctx._auto_attachment = attachment
    if getattr(ctx, "_session", None) is not None:
        ctx._session["instance_id"] = instance_id


def _establish_auto_session(ctx):
    """自动模式首次启用：签发身份、写附件、登记路由（§3.1/§2.2a）。

    只在"当前锚点没有任何路由"时调用；已有路由由 `_auto_resolve` 命中，不走这里。
    """
    from . import identity_store as store

    candidates = session_mod.candidates()
    if not candidates:
        raise CliError(
            "WF_IDENTITY_UNRESOLVED",
            {"reason": "no execution boundary resolved",
             "exits": ["在保留的终端里重试", EXPLICIT_ENVELOPE_EXIT]},
            next_="换到支持的终端形态后重跑 /wf-start",
        )
    issued_id = uuid.uuid4().hex
    identity_value = {"issued_id": issued_id}
    session_key = records.sha256_hex(
        records.canonical_bytes({"provider": "wf", "identity": identity_value}))
    current_root = candidates[-1]
    at = records.now_str()
    activation = {"enabled": True, "start_source": "human:enable", "enabled_at": at}
    attachment = store.new_attachment(identity_value, "wf", session_key, current_root, activation, at)
    l1 = next((item for item in candidates if item["kind"] == "sid"), None)
    if l1:
        attachment["attached_l1"] = {"kind": "sid", "boot": l1["boot"], "sid": l1["sid"],
                                     "sid_start": l1["sid_start"]}
    routes = store.load_routes(ctx.root)
    for item in candidates:
        key = session_mod.anchor_key(item)
        store.register(routes, key, session_key,
                       "session" if item["kind"] == "sid" else "proc", item["boot"], at)
    store.save_attachment(ctx.root, session_key, attachment)   # ① 先写附件
    store.save_routes(ctx.root, routes)                        # ② 再提交路由（组原子）
    ctx._auto_key = session_key
    ctx._auto_attachment = attachment
    ctx._session = {"provider": "wf", "identity": identity_value,
                    "instance_id": None, "activation": activation, "source": "auto"}
    ctx._envelope = {"session": None, "inputs": {}}
    return {"session_key": session_key, "issued_id": issued_id, "roots": attachment["roots"]}


def _identity_facts(ctx, session_key):
    """K1：宿主会话标识优先、进程锚只作冲突判据；缺宿主标识时显式报告看不见 /clear。"""
    from . import identity_store as store

    explicit = ctx.explicit_session()
    anchor_keys = [session_mod.anchor_key(item) for item in session_mod.candidates()]
    facts = {
        "source": "host" if explicit is not None else "anchor",
        "host_identity_absent": explicit is None,
        "anchor_candidates": len(anchor_keys),
        "anchor_conflict": store.conflicting_owners(store.load_routes(ctx.root), anchor_keys, session_key),
    }
    if explicit is None:
        # 只有进程锚时，同一进程内新开的会话（宿主自带的新会话命令如 /clear、或同一终端再开一个聊天）
        # 不换进程 ⇒ 框架无法区分（设计稿 §1.3 的已知限制）。措辞不绑定具体宿主命令：
        # 各宿主是否提供会话标识、其 /clear 是否改变标识，由部署表的 session_identity 声明。
        facts["new_session_indistinguishable"] = True
    return facts


def _pin_identity(ctx, session_key, facts):
    """把"以宿主标识为准"钉进本会话附件（runtime 层，S10）；钉住是人的一次性决定。"""
    from . import identity_store as store

    attachment = store.load_attachment(ctx.root, session_key)
    if attachment is None:
        raise CliError("WF_HISTORY_UNRESOLVED",
                       {"reason": "attachment missing", "session_key": session_key},
                       next_="按 repair 出口核对附件后重试；不新建伪附件")
    attachment["identity_pin"] = {
        "choice": "host",
        "at": records.now_str(),
        "conflict_with": list(facts.get("anchor_conflict") or []),
    }
    store.save_attachment(ctx.root, session_key, attachment)


def cmd_enable(ctx, args):
    _check_layout(ctx.root)
    # 自动模式且尚无路由 ⇒ 本次 enable 就是"建立执行会话"（§3.1）
    if ctx.explicit_session() is None:
        key, _attachment = ctx._auto_resolve()
        if key is None:
            _establish_auto_session(ctx)
    session = ctx.session()
    session_key = ctx.key(required=False)
    identity_facts = _identity_facts(ctx, session_key)
    choice = (args.value("--identity") or "").strip() or None
    if choice is not None and choice != "host":
        raise CliError("WF_PATH_INVALID",
                       {"reason": "--identity accepts only 'host'", "known": ["host"], "actual": choice},
                       next_="用 --identity host 确认以宿主标识为准，或换新会话")
    if identity_facts["anchor_conflict"] and choice is None:
        raise CliError(
            "WF_IDENTITY_UNRESOLVED",
            {"host_session_key": session_key, "anchor_conflict": identity_facts["anchor_conflict"],
             "exits": ["wf enable --identity host（确认以宿主标识为准并钉住）",
                       "换新终端/新会话后重试"]},
            next_="人确认本次会话身份来源；不以锚点或环境变量猜",
        )
    if choice == "host":
        _pin_identity(ctx, session_key, identity_facts)
        identity_facts["pinned"] = True
    state = _trellis_state(ctx.root, (ctx.session().get("identity") or {}).get("host_id"))
    host_id = state["host_id"]
    applicable = [item for item in state["host_files"] if item["host"] == host_id]
    unknown = [item for item in state["host_files"] if item["host"] != host_id]
    # 「已确认有效」需本会话确实加载：只有人声明本次已加载 Trellis 指令才按冲突阻断（机制稿 §2.1）
    loaded = bool((ctx.inputs() or {}).get("trellis_loaded"))
    # 设计稿 §3 的「停用」分支：人核实「有效性已移除/停用」后可以继续（此前无输入通道，不可达）
    disabled = bool((ctx.inputs() or {}).get("trellis_disabled_confirmed"))
    if applicable and loaded:
        raise CliError(
            "WF_FLOW_CONFLICT",
            {"trellis_host_config": applicable, "host_id": host_id, "trellis_loaded": True,
             "trellis_managed_blocks": state["blocks"], "trellis_data": state["data"]},
            next_="清理 Trellis 有效指令后在新会话重新启用；不以人工豁免继续混跑",
        )
    if state["blocks"] or unknown or (applicable and not disabled):
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
    if identity_facts["host_identity_absent"]:
        warnings.append({"reason": "host_identity_absent",
                         "note": ("本会话身份只能由进程锚派生；该宿主未提供会话标识，"
                                  "框架无法区分同一进程内的新会话（宿主自带的新会话命令、或同终端新开聊天），"
                                  "换会话请开新终端"),
                         "new_session_indistinguishable": True})
    if state["data"]:
        warnings.append({"clue": state["data"], "note": "仅数据线索；不构成当前激活指令"})
    if applicable and disabled:
        warnings.append({"reason": "trellis_files_present_but_disabled_confirmed", "host_id": host_id,
                         "trellis_host_config": applicable,
                         "note": "人已确认这些配置在本宿主不生效（停用/残留）；日后重新启用前必须先清理"})
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
            "identity": identity_facts,
            "identity_mode": (session or {}).get("source") == "auto" and "auto" or "explicit",
            "activation": template,
            "activation_source": "carried" if activation else "formed_by_enable",
            "cache_hint": "把 facts.activation 原样缓存进本会话，并随每次请求放入 session.activation",
            "platforms": ctx.platforms(),
            "trellis_data": state["data"],
            "trellis_disabled_confirmed": disabled,
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
        _sync_attachment_instance(ctx, key, instance_id)   # §3.6：首次绑定写回附件
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
    if kind == "task" and args.value("--run"):
        kind = "run"      # `--run` 走实例分支（此前该分支不可达，属死代码）
    if kind == "run":
        # 实例绑定属第二轮：必须在绑定/恢复分支之前拒绝，否则已绑定的会话
        # 会以 WF_OK 走通并写出错误对象类型的运行态（第十九轮复审 N19-3）。
        raise CliError("WF_CAPABILITY_UNAVAILABLE",
                       {"capability": "bind --run", "round": 2, "target": args.value("--run")},
                       next_="实例绑定等第二轮交付；首轮用 bind --task <id>")
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
        # R50-04：绑定已写但动作未结案时，重入必须续做并结案，不能提前返回成功。
        # 该恢复路径会写 writer.json，必须与写权动作同处一个原子互斥（设计稿 §4.4）：
        # 与 `_writer_release` 同款「锁外快检 + 锁内重核」。
        live = ctx.writer()
        action_ref = (live.get("action") or {})
        if isinstance(action_ref, dict) and action_ref.get("kind") == "session.bind":
            with _lock(ctx.root, hint="bind-resume"):
                fresh = ctx.writer()
                resumed = _resume_bind(ctx, key, session, existing.get("object") or {},
                                       target, kind, fresh)
                if resumed is not None:
                    return resumed
        # 走到这里说明 writer 上没有未结案的 session.bind（上面的快检已排除），
        # 不需要重复调用 `_resume_bind`（第十二轮复审：该 else 分支恒为死逻辑）。

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
            raise CliError("WF_TARGET_MISSING", {"reason": "task not found", "task": target})
        _eligible_task_bind(ctx, task)
        object_ref = {"kind": "task", "id": target}
    else:  # 兜底：正常路径已在入口拒绝 `--run`
        raise CliError("WF_CAPABILITY_UNAVAILABLE",
                       {"capability": "bind --run", "round": 2, "target": target},
                       next_="实例绑定等第二轮交付；首轮用 bind --task <id>")
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
        ctx.require_activation()   # 模型可调入口同样先确认本会话已启用（机制稿 §1.3）
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
        # 接收方也要核真实工作区：外来未处置 WIP 不得随交接一并接收（设计稿 §4.4）
        assert_no_foreign_wip(ctx, exclude_id=(object_ref or {}).get("id"))
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
    if not choices:
        # 空决定文件是业务输入错误，不能走到 IndexError/退出 70（第二十五轮复审外部 2）
        raise CliError("WF_SEMANTIC_DECISION", {"reason": "收工决定文件为空，需要一条 choice",
                                                "choices": [],
                                                "accepted": list(decisions_mod.domain("stop_choice"))})
    if not decisions_mod.accepts("stop_choice", choices[0]):
        raise CliError("WF_SEMANTIC_DECISION", {"choices": choices, "reason": "收工选择必须是 commit/keep/reverse/transfer"})
    if args.flag("--preview"):
        # 只读预览（设计稿 §4.4）：逐路径给出归属/状态/待验证项，不写任何记录
        from . import scope as scope_mod

        binding = session_mod.load_binding(ctx.root, ctx.key())
        object_ref = (binding or {}).get("object") or {}
        if object_ref.get("kind") != "task":
            raise CliError("WF_BINDING_MISMATCH", {"reason": "no task binding for stop preview"})
        from . import tasks as tasks_mod

        task = tasks_mod.load_task(ctx.root, object_ref.get("id"))
        if task is None:
            raise CliError("WF_RECORD_INVALID", {"missing_task": object_ref.get("id")})
        classified = scope_mod.classify_candidates(ctx.root, task)
        facts = {
            "task": {"id": task.get("id"), "phase": task.get("phase"), "title": task.get("title")},
            "choice": choices[0],
            "buckets": classified.get("buckets"),
            "uncommitted": sorted(scope_mod.uncommitted_paths(ctx.root)),
            "note": "预览只读；本次未写入任何记录",
        }
        return ok(facts=facts, position=codes.position(scope="task", phase=task.get("phase"),
                                                       task_id=task.get("id")),
                  next_="按预览结果选定处置后去掉 --preview 重跑")
    from . import tasks as tasks_mod

    return tasks_mod.stop_work(ctx, decisions, choices[0])


def cmd_ready(ctx, args):
    """就绪视图（设计稿 §5.6 / §5.1）：无绑定新会话按创建时间给出最早就绪建议。

    只读：不写任何判定字段。每个活动/暂停任务给出 eligible（独立接续资格）、
    ready（能否直接开工）与 blockers；suggested 取 ready 中创建时间最早的一个。
    """
    from . import tasks as tasks_mod

    entries = []
    for _path, task in tasks_mod.iter_tasks(ctx.root):
        if task.get("status") == "archived":
            continue
        blockers = []
        try:
            _eligible_task_bind(ctx, task)
        except CliError as exc:
            blockers.append(exc.code)
        if not tasks_mod._is_approved_plan(task, ctx.root):
            blockers.append("WF_APPROVAL_MISSING")
        # 「进行中且未暂停」不是可接续对象：它仍被原会话推进（设计稿 §5.6）
        if task.get("status") == "in_progress" and not (task.get("paused") or task.get("suspended")):
            blockers.append("in_progress")
        record = ctx.writer()
        holder = (record.get("holder") or {}) if isinstance(record, dict) else {}
        if isinstance(record, dict) and record.get("state") == "held" and holder.get("id") != ctx.key(required=False):
            blockers.append("WF_WRITER_BUSY")
        entries.append({
            "id": task.get("id"),
            "title": task.get("title"),
            "status": task.get("status"),
            "phase": task.get("phase"),
            "created_at": task.get("created_at"),
            "eligible": not any(str(item).startswith("WF_") for item in blockers),
            "ready": not blockers,
            "blockers": blockers,
        })
    entries.sort(key=lambda item: (str(item.get("created_at") or ""), str(item.get("id") or "")))
    suggested = next((item["id"] for item in entries if item.get("ready")), None)
    return ok(
        facts={"tasks": entries, "suggested": suggested},
        position=codes.position(scope="session"),
        next_="用 bind --task <id> 绑定建议对象；或按 blockers 先解除阻断",
    )


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
    if budget_problem or not budget or budget <= 0:  # 0 也是非法（正整数键）
        # 配置错误不是"能力未交付"：用记录/配置类原因码，避免误导到"等轮次交付"
        raise CliError("WF_RECORD_INVALID",
                       {"reason": budget_problem or "spec_output_codepoints must be a positive integer",
                        "key": "spec_output_codepoints", "file": ".wf/project-config.json"},
                       next_="修正 project-config.json 的该键（正整数）后重试")
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

    # 交付轮次标记（机制/实现 2026-11-05 人裁 B）：安装自检据此判定
    # "清单声明本轮已交付、但承接命令仍是桩" 的情形，不再只核对命令名存在。
    handler.wf_delivery_round = round_no
    handler.wf_capability = capability
    return handler


def _review_command(kind):
    def handler(ctx, args):
        from . import review as review_mod, tasks as tasks_mod

        task_id = args.value("--task")
        if not task_id:
            raise CliError("WF_PATH_INVALID", {"reason": f"review-{kind} requires --task <id>"})
        task = tasks_mod.load_task(ctx.root, task_id)
        if task is None:
            raise CliError("WF_TARGET_MISSING", {"reason": "task not found", "task": task_id})
        if kind == "launch":
            request = args.value("--launch-request")
            if not request:
                raise CliError("WF_PATH_INVALID", {"reason": "review-launch requires --launch-request <path>"})
            try:
                return review_mod.launch(ctx, task, request,
                                         implementation_cli=args.value("--implementation-cli"))
            except review_mod.ReviewError as exc:
                raise CliError(exc.code, exc.facts)
        if kind == "context":
            round_no = args.value("--round")
            try:
                return review_mod.context(ctx, task, int(round_no) if round_no else None,
                                          reset=args.flag("--reset"), as_value=args.value("--as"))
            except review_mod.ReviewError as exc:
                raise CliError(exc.code, exc.facts)
        if kind == "import":
            # 2026-11-07：--round/--slot/--report 全部可省（身份取文件名，轮次取当前轮）
            round_no = args.value("--round")
            try:
                return review_mod.import_report(ctx, task, int(round_no) if round_no else None,
                                                args.value("--slot"), args.value("--report"),
                                                as_value=args.value("--as"),
                                                restore=args.flag("--restore"))
            except review_mod.ReviewError as exc:
                raise CliError(exc.code, exc.facts)
        round_no = args.value("--round")
        try:
            return review_mod.decide(ctx, task, int(round_no) if round_no else None,
                                     args.value("--plan"), args.value("--unavailable"),
                                     register_only=args.flag("--register-only"))
        except review_mod.ReviewError as exc:
            raise CliError(exc.code, exc.facts)

    return handler


def cmd_confirm_executor(ctx, args):
    raise CliError(
        "WF_CAPABILITY_UNAVAILABLE",
        {"reason": "confirm-executor is handled by the bootstrap layer (.wf/bin/wf.py)"},
        next_="直接运行 wf.py confirm-executor --scope system|global|project",
    )


COMMAND_HELP = {
    "task-new": {
        "purpose": "建任务（ordinary/initialize/bootstrap）并取得写权与绑定",
        "args": {"--kind": "ordinary|initialize|bootstrap（必填）", "--title": "标题（必填）",
                 "--template": "<项目根>/.wf/templates/task（必填）"},
        "example": "wf.py task-new --kind ordinary --title \"补边界用例\" --template .wf/templates/task --json",
    },
    "task-approve": {
        "purpose": "记录人的规划批准（含复杂度与 TDD 的人工确认）",
        "args": {"--task": "任务 id（必填）", "--decision": "决定文件（必填，JSON 数组）"},
        "inputs": {"decision[]": {"source": "人答复来源（必填）", "at": "时间（必填）",
                                  "subject": "必须含任务 id 或对象摘要（必填）",
                                  "object_digest": "当前 PRD 的 sha256（必填）",
                                  "choice": "approve|approve-light|approve-complex|mechanical（必填）",
                                  "生成代次": "inputs.generation 必填（从上条命令回显 facts.generation 取；"
                                            "过期会报 WF_GENERATION_STALE 并在 facts 给 current_generation）",
                                  "plan-q 答复": "PRD 里每个 plan-q-<n> 要一条 choice=\"plan-q\" 且 subject 含该编号的答复"
                                               "（旧夹具的 choice=\"是\" 已不再接受）",
                                  "reason": "理由（必填）",
                                  "plan": "可选：{complexity: light|complex, tdd: bool, downgrade: {reason, evidence}}——"
                                          "复杂分级必须由人在此确认，未登记的键会原样留痕进 plan.human_inputs"}},
        "example": "wf.py task-approve --task <id> --decision approve.json --json",
        "example_file": [{"source": "human:terminal", "at": "2026-11-07T00:00:00.000000Z",
                          "subject": "approve <id>", "object_digest": "sha256:<PRD 摘要>",
                          "choice": "approve", "reason": "范围清楚",
                          "plan": {"complexity": "complex", "tdd": False}}],
    },
    "task-start": {"purpose": "开工（需要已批准规划与写权）",
                   "args": {"--task": "任务 id（必填）"},
                   "example": "wf.py task-start --task <id> --json"},
    "task-check": {
        "purpose": "按批准验证实际执行并写 check 结果（复杂任务还需双轴内部审查）",
        "args": {"--task": "任务 id（必填）", "--review-notes": "双轴内部审查结论（复杂任务必填）",
                 "--decision": "可选：人工验收决定"},
        "inputs": {"--review-notes": {"standard": {"conclusion": "pass|fail|undecided", "basis": "依据"},
                                      "requirement": {"conclusion": "pass|fail|undecided", "basis": "依据"}}},
        "example": "wf.py task-check --task <id> --review-notes notes.json --json",
    },
    "task-knowledge": {"purpose": "记录知识处置（可判无更新）",
                       "args": {"--task": "任务 id（必填）", "--decision": "no-update|updated",
                                "--no-update": "简写：等价于 --decision no-update",
                                "--changes": "updated 时的知识变更清单 JSON 数组"},
                       "example": "wf.py task-knowledge --task <id> --decision no-update --json"},
    "stop": {"purpose": "收工：先 --preview 看逐路径归属，再按处置执行",
             "args": {"--decision": "决定文件（必填）", "--preview": "只读预览（不写任何记录）"},
             "inputs": {"decision[]": {"choice": "commit|keep|reverse|transfer",
                                       "subject": "路径或承接对象", "reason": "理由",
                                       "object_digest": "可选"}},
             "example": "wf.py stop --decision stop.json --preview --json"},
    "archive": {"note": "commit 的 subject 可写数组，或用逗号/分号/换行/空格分隔的多路径字符串",
"purpose": "正常归档（最终门禁 + 提交授权）",
                "args": {"--task": "任务 id（必填）", "--decision": "决定文件（必填）"},
                "inputs": {"decision[]": "至少一条 choice=finish；提交需 choice=commit 的授权条目"},
                "example": "wf.py archive --task <id> --decision finish.json --json"},
    "baseline-apply": {"purpose": "把已批准提案成组应用到基线/配置/spec",
                       "args": {"--task": "任务 id（必填）",
                                "--files": "逗号分隔的路径（推荐：由入口读工作树生成提案）",
                                "--decision": "人的批准决定文件（与 --files 一起用）",
                                "--proposal": "既有格式的提案 JSON（可选，兼容）"},
                       "inputs": {"--proposal": {"files": "[{path, before, content}]",
                                                 "approval": "{choice, subject} 人的批准引用"}},
                       "example": "wf.py baseline-apply --task <id> --proposal proposal.json --json"},
    "spec-update": {"purpose": "spec 增改删/合并/停用，并同步三段索引",
                    "args": {"--task": "任务 id（必填）", "--changes": "变更数组（必填）"},
                    "inputs": {"--changes[]": {"operation": "add|update|merge|rename|delete|disable",
                                               "new_paths": "新路径（数组或逗号/分号/空白分隔的字符串，单条可直写字符串）",
                                               "old_paths": "旧路径（同上：数组或分隔字符串）",
                                               "content": "add/update 时的完整正文（含 frontmatter）"}},
                    "example": "wf.py spec-update --task <id> --changes changes.json --json"},
    "review-launch": {"purpose": "发起一轮审查（默认要两份；实施 CLI 由 --implementation-cli 声明）",
                      "args": {"--task": "任务 id（必填）", "--launch-request": "请求 JSON（必填）",
                               "--implementation-cli": "本次实施所用 CLI（必填，异种审查的判定输入）"},
                      "inputs": {"--launch-request": {"export_decision": "外发授权决定（必填）",
                                                      "submitted_scope": "{diff,requirement,test_results} 三个布尔（必填）",
                                                      "reviewers": "可选：要几份审查（默认 2）"}},
                      "example": "wf.py review-launch --task <id> --launch-request launch.json "
                                 "--implementation-cli codex --json"},
    "review-context": {"purpose": "reviewer 侧唯一入口：占位 + 物化材料 + 给出报告路径",
                       "args": {"--task": "任务 id（必填）", "--round": "轮次（缺省＝当前轮）",
                                "--reset": "清掉本 agent 本轮的占位/报告"},
                       "args_extra": {"--as": "本次审查的 CLI（自动身份模式必填）"},
                       "example": "wf.py review-context --task <id> --round 1 --as pi --json"},
    "review-import": {"purpose": "导入本轮已完成的报告（按文件名发现，免路径）",
                      "args": {"--task": "任务 id（必填）", "--round": "可选", "--slot": "可选（指定某个 agent）",
                               "--report": "可选（显式路径，兼容旧槽位制）",
                               "--restore": "只在恢复**已存在的记录**时用（缺登记摘要的遗留记录重导）"},
                      "example": "wf.py review-import --task <id> --json"},
    "project": {"purpose": "可重建投影（K8）：open-items / attribution / audit / skeleton；--check 断言等值",
                "args": {"--kind": "投影类型（必填）", "--task": "任务 id（必填）", "--check": "断言重建等值"},
                "example": "wf.py project --kind open-items --task 2026-xxxx --check --json"},
    "verify": {"purpose": "未核实项处置（S8/S5b）：resolve 收窄口径或记录人工核验",
               "args": {"resolve": "子命令", "--task": "任务 id", "--id": "验收项 id",
                        "--kind": "narrow|inspection", "--evidence": "证据",
                        "--reason/--impact/--compensation": "收窄四项（narrow 必填）"},
               "example": "wf.py verify resolve --task 2026-xxxx --id a5 --kind narrow --evidence ... --json"},
    "authorize": {"purpose": "K6 五类不可逆动作的确认入口：record 落盘（脱敏入库）/ show 查看已确认",
                  "args": {"record|show": "子命令", "--task": "任务 id（必填）",
                           "--file": "决定文件（record 必填，每条含 choice∈五类 + quote）"},
                  "example": "wf.py authorize record --task 2026-xxxx --file decisions.json --json"},
    "prefs": {"purpose": "判断偏好（只在本机）：ask_always 强制交人 / ai_decides 自己定",
              "args": {"set|show": "子命令", "--kind": "判断类（归属/关闭/沿用/扩面/标准变更/缺口/未核实/规模）",
                       "--value": "ask_always|ai_decides"},
              "example": "wf.py prefs set --kind 标准变更 --value ask_always --json"},
    "sampling": {"purpose": "试点期判断抽样：pick 冻结事件集与种子并选样 / report 出按类统计",
                  "args": {"pick|report": "子命令", "--task": "任务 id（pick 必填）",
                           "--freeze": "首次选样前冻结事件集与种子（写任务记录）"},
                  "example": "wf.py sampling pick --task 2026-xxxx --freeze --json"},
    "judgments": {"purpose": "判断清单：add 追加一条（append-only）/ show 渲染收工预览",
                  "args": {"add|show": "子命令", "--task": "任务 id（必填）", "--file": "判断 JSON（add 必填）"},
                  "example": "wf.py judgments show --task 2026-xxxx --json",
                  # v42 §4：判断指引写进 SKILL 与 help，不写进代码逻辑。
                  # 这里只放"去哪读 + 十条的清单"，正文在 skill `wf-judging`，避免两份漂移。
                  "guidance": {
                      "where": "skill `wf-judging`（十条，每条：目标/判断什么/留什么依据/人怎么挑战/本项目反例）",
                      "topics": ["4.1 交付面：哪些文件算本次交付",
                                 "4.2 blocking 关闭：证据要指回那个问题",
                                 "4.3 影响面：缺口能不能接受风险（required 不行）",
                                 "4.4 扩面：碰批准面之外的文件（先确认再改）",
                                 "4.5 标准变更：改的是尺子还是判断",
                                 "4.6 变化规模：一次看见累计量（首任务必确认）",
                                 "4.7 报告有效性：沿用必须点名 d: 位置",
                                 "4.8 标准缺失：检索范围 + 影响 + 建议",
                                 "4.9 未核实项：收窄要四项依据，required 不得接受风险",
                                 "4.10 与用户限制冲突：停下报告，不自行取舍"],
                      "escalate": "判断不了就 write outcome=escalated + 一个具体问题；人回答后用新条目 supersedes 收口"}},
    "lint": {"purpose": "报告一次性全量预检（格式/轴/verdict 一致性/引用/回执），不是门禁",
             "args": {"report": "子命令（唯一支持值）", "--file": "报告路径", "--task": "任务 id（给定时可核批准集合与规则状态）"},
             "example": "wf.py lint report --file review/draft.md --task 2026-xxxx --json"},
    "review-status": {"purpose": "查看本轮审查到位状态（只读：已到 n/2、缺哪份、文件状态）",
                      "args": {"--task": "任务 id（必填）", "--round": "轮次（缺省取最新已发起轮）"},
                      "example": "wf.py review-status --task 2026-xxxx --json"},
    "review-decide": {"purpose": "判定本轮审查（人数/异种按报告文件名，实施 CLI 取本会话）",
                      "args": {"--task": "任务 id（必填）", "--round": "缺省＝当前轮",
                               "--plan": "逐条 finding 处置", "--unavailable": "不可用声明（与 --plan 互斥）",
                               "--register-only": "只登记复核关闭：不产生结论、不校验人数/异种"
                                                  "（仍需 --plan；关闭的硬条件照旧）"},
                      "example": "wf.py review-decide --task <id> --json"},
}


def cmd_project(ctx, args):
    """`project --kind open-items|attribution|audit|skeleton --task [--check]`（K8 投影，`--check` 断言等值）。"""
    from . import projection as projection_mod, tasks as tasks_mod

    kind = args.value("--kind")
    if kind not in ("open-items", "attribution", "audit", "skeleton"):
        raise CliError("WF_PATH_INVALID", {"reason": "unknown projection kind", "kind": kind,
                                          "known": ["open-items", "attribution", "audit", "skeleton"]})
    task_id = args.value("--task")
    if not task_id:
        raise CliError("WF_PATH_INVALID", {"reason": "project requires --task <id>"})
    task = tasks_mod.load_task(ctx.root, task_id)
    if task is None:
        raise CliError("WF_TARGET_MISSING", {"reason": "task not found", "task": task_id})
    if not args.flag("--check"):
        return codes.result("WF_OK", object={"id": task_id, "name": task.get("title")},
                            position_=codes.position(scope="task", phase=task.get("phase"), task_id=task_id),
                            next_="投影由记录派生、不落盘；`--check` 可断言重建等值",
                            facts={"kind": kind, "projection": projection_mod.build(ctx, task, kind)})
    facts = projection_mod.check(ctx, task, kind)
    code = "WF_OK" if facts["equal"] else "WF_TARGET_COLLISION"
    return codes.result(code, object={"id": task_id, "name": task.get("title")},
                        position_=codes.position(scope="task", phase=task.get("phase"), task_id=task_id),
                        next_="等值即投影未漂移；不等值说明缓存/记录已分叉" if facts["equal"]
                        else "按 problems 核对缓存或记录后再重算",
                        facts=facts)


def cmd_verify(ctx, args):
    """`verify resolve --task --id --kind narrow|inspection`（S8/S5b 未核实项处置）。"""
    from . import projection as projection_mod, tasks as tasks_mod

    sub = (args.positional() or [None])[0]
    if sub != "resolve":
        raise CliError("WF_PATH_INVALID", {"reason": "verify requires resolve", "known": ["resolve"]})
    task_id = args.value("--task")
    acceptance_id = args.value("--id")
    if not task_id or not acceptance_id:
        raise CliError("WF_PATH_INVALID", {"reason": "verify resolve requires --task <id> --id <acceptance-id>"})
    task = tasks_mod.load_task(ctx.root, task_id)
    if task is None:
        raise CliError("WF_TARGET_MISSING", {"reason": "task not found", "task": task_id})
    with _lock(ctx.root, hint="verify resolve"):
        _record, holder = ctx.require_held(task=task_id)
        directory = tasks_mod.task_dir(ctx.root, task_id)
        fresh = records.load_json(os.path.join(directory, "task.json"))
        record, problems = projection_mod.resolve(
            fresh, acceptance_id, kind=args.value("--kind"), evidence=args.value("--evidence"),
            reason=args.value("--reason"), impact=args.value("--impact"),
            compensation=args.value("--compensation"), by=args.value("--by") or "human")
        if problems:
            raise CliError("WF_SEMANTIC_DECISION",
                           {"problems": problems,
                            "exits": ["补齐四项依据后重跑（required 不接受『接受风险』结案）",
                                      "按设计稿 §5.6 异常归档"]})
        fresh, action_ref = tasks_mod._start_task_action(
            ctx, directory, fresh, "task.verify.resolve", holder,
            {"task": task_id, "acceptance": acceptance_id}, ["resolve"])
        fresh, assertion = tasks_mod._finish_task_action(
            ctx, directory, fresh, "task.verify.resolve", holder,
            {"task": task_id, "acceptance": acceptance_id}, action_ref,
            evidence_refs=[str(acceptance_id)])
    return codes.result("WF_OK", object={"id": task_id, "name": fresh.get("title")},
                        position_=codes.position(scope="task", phase=fresh.get("phase"), task_id=task_id),
                        next_="继续推进；required 未结案会阻断归档",
                        facts={"resolution": record, "control_assertion": assertion})


def cmd_authorize(ctx, args):
    """`authorize record --task <id> --file <决定.json>` / `authorize show --task <id>`。

    K6 五类不可逆动作的**人执行确认入口**：决定文件是人写的，入口把每一类落成
    `authorization-<action>.json`（脱敏后进任务目录=committed，敏感原文留 runtime）。
    守卫（vendor/delete/expand/repo_rules/export）只认这些文件，不认"模型说的已获授权"。
    """
    from . import authorize as authorize_mod, tasks as tasks_mod

    sub = (args.positional() or [None])[0]
    task_id = args.value("--task")
    if not task_id:
        raise CliError("WF_PATH_INVALID", {"reason": "authorize requires --task <id>"})
    task = tasks_mod.load_task(ctx.root, task_id)
    if task is None:
        raise CliError("WF_TARGET_MISSING", {"reason": "task not found", "task": task_id})
    directory = tasks_mod.task_dir(ctx.root, task_id)
    if sub == "show":
        found = {action: (authorize_mod.require(directory, action) or {}).get("original_digest")
                 for action in authorize_mod.ACTIONS}
        return codes.result("WF_OK", object={"id": task_id, "name": task.get("title")},
                            position_=codes.position(scope="task", phase=task.get("phase"), task_id=task_id),
                            next_="缺哪一类就用 authorize record 补哪一类",
                            facts={"recorded": {name: digest for name, digest in found.items() if digest},
                                   "actions": dict(authorize_mod.ACTIONS)})
    if sub != "record":
        raise CliError("WF_PATH_INVALID", {"reason": "authorize requires record|show",
                                          "known": ["record", "show"]})
    file_value = args.value("--file")
    if not file_value:
        raise CliError("WF_PATH_INVALID", {"reason": "authorize record requires --file <决定.json>"})
    loaded = records.load_json(file_value if os.path.isabs(file_value) else join(ctx.root, file_value))
    entries = loaded if isinstance(loaded, list) else [loaded]
    recorded = []
    with _lock(ctx.root, hint="authorize record"):
        _record, holder = ctx.require_held(task=task_id)
        fresh = records.load_json(os.path.join(directory, "task.json"))
        for entry in entries:
            if not isinstance(entry, dict):
                raise CliError("WF_PATH_INVALID", {"reason": "each entry must be an object"})
            action = entry.get("choice") or entry.get("action")
            if action not in authorize_mod.ACTIONS:
                raise CliError("WF_PATH_INVALID",
                               {"reason": "unknown action in decision file", "action": action,
                                "known": sorted(authorize_mod.ACTIONS)})
            if not str(entry.get("quote") or "").strip():
                raise CliError("WF_SEMANTIC_DECISION",
                               {"reason": "确认必须带人的 quote（谁在什么范围确认了什么）",
                                "action": action})
            # 乙口径：K6 的信任根不能只靠"决定文件里有 quote"。要求显式的来源声明
            # （`source: user-declared` + `by: human:<来源>`），并在入库副本里留下摘要可审计。
            _problems = attestation_mod.problems_of(
                {"by": entry.get("by") or (entry.get("source") and "human:" + str(entry.get("source"))),
                 "at": entry.get("at"), "quote": entry.get("quote"),
                 "source": entry.get("source") or "user-declared"}, action=action)
            if _problems:
                raise CliError("WF_SEMANTIC_DECISION",
                               {"reason": '授权确认要能指明"谁给的"（乙口径：by=human:<来源>）',
                                "action": action, "problems": _problems,
                                "exits": ["在决定文件里补 by: human:<来源> 与 source: user-declared",
                                          "由人重写该决定文件（AI 不得代写）"]})
            info = authorize_mod.record_authorization(
                directory, action, entry,
                raw_copy_dir=join(ctx.root, ".wf/.runtime/decisions"))
            recorded.append({"action": action, "path": os.path.relpath(info["path"], str(ctx.root)),
                             "digest": info["digest"]})
        fresh, action_ref = tasks_mod._start_task_action(
            ctx, directory, fresh, "task.authorize", holder, {"task": task_id}, ["record"])
        fresh, assertion = tasks_mod._finish_task_action(
            ctx, directory, fresh, "task.authorize", holder, {"task": task_id}, action_ref,
            evidence_refs=[item["path"] for item in recorded])
    return codes.result("WF_OK", object={"id": task_id, "name": fresh.get("title")},
                        position_=codes.position(scope="task", phase=fresh.get("phase"), task_id=task_id),
                        next_="按需要继续推进；守卫会认这些确认",
                        facts={"recorded": recorded, "control_assertion": assertion})


def cmd_sampling(ctx, args):
    """`sampling pick --task`（冻结事件集 + 选样）/ `sampling report`（试点期统计，只读）。"""
    from . import judgments as judgments_mod, sampling as sampling_mod, tasks as tasks_mod

    sub = (args.positional() or [None])[0]
    if sub == "report":
        tasks = [task for _directory, task in tasks_mod.iter_tasks(ctx.root)]
        history = sampling_mod.history_from_tasks(tasks)
        return codes.result("WF_OK", position_=codes.position(scope="task"),
                            next_="按统计决定保留/降频/取消；样本不足时门槛不激活",
                            facts={"report": sampling_mod.report(history), "history": history})
    if sub == "evaluate":
        task_id = args.value("--task")
        file_value = args.value("--file")
        if not task_id or not file_value:
            raise CliError("WF_PATH_INVALID",
                           {"reason": "sampling evaluate requires --task <id> --file <评价.json>"})
        task = tasks_mod.load_task(ctx.root, task_id)
        if task is None:
            raise CliError("WF_TARGET_MISSING", {"reason": "task not found", "task": task_id})
        evaluations = records.load_json(file_value if os.path.isabs(file_value) else join(ctx.root, file_value))
        selection = sampling_mod.selection(task)
        if not selection["picks"]:
            raise CliError("WF_SEMANTIC_DECISION",
                           {"reason": "还没有落盘的选样：先跑 sampling pick --freeze",
                            "exits": ["跑 `wf sampling pick --task %s --freeze` 后重入" % task_id]})
        with _lock(ctx.root, hint="sampling evaluate"):
            _record, holder = ctx.require_held(task=task_id)
            directory = tasks_mod.task_dir(ctx.root, task_id)
            task = records.load_json(os.path.join(directory, "task.json"))
            _payload, _digest, _problems = attestation_mod.load(
                args.value("--attestation"), action="sampling.evaluate")
            if _problems:
                raise CliError("WF_SEMANTIC_DECISION",
                               {"reason": "抽样评价要有人确认（否则等于 AI 给自己打分）",
                                "problems": _problems,
                                "exits": ["让人确认评价结果后用 --attestation 传入确认文件",
                                          "没有人确认就不写结果：未评价的选样不会计入样本（不会变成假成功）"]},
                               next_="由人给出确认文件后再执行本命令")
            evaluations = dict(evaluations or {})
            evaluations["__attestation__"] = attestation_mod.stamp(_payload, _digest)
            state = sampling_mod.record_result(task, sampling_mod.selection(task)["picks"],
                                               evaluations if isinstance(evaluations, dict) else {})
            task, action = tasks_mod._start_task_action(
                ctx, directory, task, "task.sampling.evaluate", holder,
                {"task": task_id}, ["record_evaluations"])
            records.write_json(os.path.join(directory, "task.json"), task)
            task, _assertion = tasks_mod._finish_task_action(
                ctx, directory, task, "task.sampling.evaluate", holder,
                {"task": task_id}, action)
        return codes.result("WF_OK", object={"id": task_id, "name": task.get("title")},
                            position_=codes.position(scope="task", phase=task.get("phase"), task_id=task_id),
                            next_="强化期由人的声明结束（sampling reviewed）",
                            facts={"results": state.get("results")})
    if sub == "confirm":
        # 4.6/S6：规模确认此前**没有任何入口**（`scale.record` 是死代码，`history_max` 永远为 None，
        # 预览永远提示"首个任务收工须确认一次"却无从确认）。这里补上唯一的写入路径。
        task_id = args.value("--task")
        if not task_id:
            raise CliError("WF_PATH_INVALID", {"reason": "sampling confirm requires --task <id>"})
        task = tasks_mod.load_task(ctx.root, task_id)
        if task is None:
            raise CliError("WF_TARGET_MISSING", {"reason": "task not found", "task": task_id})
        with _lock(ctx.root, hint="sampling confirm"):
            _record, holder = ctx.require_held(task=task_id)
            directory = tasks_mod.task_dir(ctx.root, task_id)
            task = records.load_json(os.path.join(directory, "task.json"))
            from . import scale as scale_mod

            current = scale_mod.changes_since(ctx, task)
            payload = scale_mod.record(task, current, by="human",
                                       quote=args.value("--quote") or "人在预览中确认本次规模")
            task, action = tasks_mod._start_task_action(
                ctx, directory, task, "task.scale.confirm", holder,
                {"net": payload.get("confirmed_net")}, ["record_confirm"])
            records.write_json(os.path.join(directory, "task.json"), task)
            task, _assertion = tasks_mod._finish_task_action(
                ctx, directory, task, "task.scale.confirm", holder,
                {"net": payload.get("confirmed_net")}, action)
            task = records.load_json(os.path.join(directory, "task.json"))
        return codes.result("WF_OK", facts={"cumulative": payload})

    if sub == "reviewed":
        task_id = args.value("--task")
        if not task_id:
            raise CliError("WF_PATH_INVALID", {"reason": "sampling reviewed requires --task <id>"})
        task = tasks_mod.load_task(ctx.root, task_id)
        if task is None:
            raise CliError("WF_TARGET_MISSING", {"reason": "task not found", "task": task_id})
        with _lock(ctx.root, hint="sampling reviewed"):
            _record, holder = ctx.require_held(task=task_id)
            directory = tasks_mod.task_dir(ctx.root, task_id)
            task = records.load_json(os.path.join(directory, "task.json"))
            _payload, _digest, _problems = attestation_mod.load(
                args.value("--attestation"), action="sampling.reviewed")
            if _problems:
                raise CliError("WF_SEMANTIC_DECISION",
                               {"reason": "'人已看过预览'必须由人给出确认文件（乙口径）",
                                "problems": _problems,
                                "exits": ["让人把确认写成 JSON（by/at/quote/source）后用 --attestation 传入",
                                          "无人可确认时不要结束强化期：按 §0.2 顺手记失败并写根因"]},
                               next_="由人给出确认文件后再执行本命令")
            declaration = sampling_mod.mark_reviewed(
                task, quote=_payload.get("quote"),
                attestation=attestation_mod.stamp(_payload, _digest))
            task, action = tasks_mod._start_task_action(
                ctx, directory, task, "task.sampling.reviewed", holder,
                {"task": task_id}, ["record_review"])
            records.write_json(os.path.join(directory, "task.json"), task)
            task, _assertion = tasks_mod._finish_task_action(
                ctx, directory, task, "task.sampling.reviewed", holder,
                {"task": task_id}, action)
        return codes.result("WF_OK", object={"id": task_id, "name": task.get("title")},
                            position_=codes.position(scope="task", phase=task.get("phase"), task_id=task_id),
                            next_="强化期由本次人声明结束", facts={"reviewed": declaration})
    if sub != "pick":
        raise CliError("WF_PATH_INVALID", {"reason": "sampling requires pick|report|evaluate|reviewed|confirm",
                                          "known": ["pick", "report", "evaluate", "reviewed", "confirm"]})
    task_id = args.value("--task")
    if not task_id:
        raise CliError("WF_PATH_INVALID", {"reason": "sampling pick requires --task <id>"})
    task = tasks_mod.load_task(ctx.root, task_id)
    if task is None:
        raise CliError("WF_TARGET_MISSING", {"reason": "task not found", "task": task_id})
    facts = judgments_mod.skeleton(ctx, task)
    state = sampling_mod.frozen(task)
    if not state.get("seed"):
        if not args.flag("--freeze"):
            raise CliError("WF_SEMANTIC_DECISION",
                           {"reason": "事件集与种子尚未冻结：收工预览时先冻结再抽",
                            "exits": ["加 --freeze 冻结事件集与种子后选样"]},
                           next_="冻结写进任务记录（committed），此后 AI 改 judgments 不影响选样")
        with _lock(ctx.root, hint="sampling freeze"):
            _record, holder = ctx.require_held(task=task_id)
            directory = tasks_mod.task_dir(ctx.root, task_id)
            task = records.load_json(os.path.join(directory, "task.json"))
            facts = judgments_mod.skeleton(ctx, task)
            state = sampling_mod.freeze(task, facts)
            task, action = tasks_mod._start_task_action(
                ctx, directory, task, "task.sampling.freeze", holder,
                {"task": task_id}, ["freeze_events"])
            records.write_json(os.path.join(directory, "task.json"), task)
            task, _assertion = tasks_mod._finish_task_action(
                ctx, directory, task, "task.sampling.freeze", holder,
                {"task": task_id}, action)
    _all_tasks = [item for _directory, item in tasks_mod.iter_tasks(ctx.root)]
    history = sampling_mod.history_from_tasks(_all_tasks)
    open_items = __import__("wflib.review", fromlist=["review"]).open_findings(ctx, task)
    picks = sampling_mod.select_for(task, history, first_task=sampling_mod.is_first_task(_all_tasks),
                                    open_blocking=bool(open_items["blocking"]))
    # 选样必须落盘：门禁 `task.sampled` 读的是记录里的 picks，只回显等于没抽（P1 死锁根因）
    if (picks or {}).get("picks") and not sampling_mod.selection(task)["picks"]:
        with _lock(ctx.root, hint="sampling picks"):
            _record, holder = ctx.require_held(task=task_id)
            directory = tasks_mod.task_dir(ctx.root, task_id)
            task = records.load_json(os.path.join(directory, "task.json"))
            sampling_mod.record_picks(task, picks["picks"])
            task, action = tasks_mod._start_task_action(
                ctx, directory, task, "task.sampling.freeze", holder,
                {"task": task_id}, ["freeze_events", "record_picks"])
            records.write_json(os.path.join(directory, "task.json"), task)
            task, _assertion = tasks_mod._finish_task_action(
                ctx, directory, task, "task.sampling.freeze", holder,
                {"task": task_id}, action, evidence_refs=[str(len(picks["picks"]))])
            state = sampling_mod.frozen(task)
    return codes.result("WF_OK", object={"id": task_id, "name": task.get("title")},
                        position_=codes.position(scope="task", phase=task.get("phase"), task_id=task_id),
                        next_="人只评抽到的这两条（结论对/错 × 依据充分/不充分）；用 --evaluate 落结果",
                        facts={"seed": state.get("seed"), "selection": picks,
                               "backfill": sampling_mod.backfill_status(
                                   (picks or {}).get("picks") or [], task.get("judgments") or []),
                               "preview_line": "本次抽样：" + "、".join(
                                   f"{item['class']}（{item['rule']}）" for item in (picks or {}).get("picks") or [])})


def cmd_prefs(ctx, args):
    """`prefs set --kind <类> --value ask_always|ai_decides` / `prefs show`（偏好只在本机）。"""
    from . import judgments as judgments_mod

    sub = (args.positional() or [None])[0]
    if sub == "show":
        prefs = judgments_mod.load_prefs(ctx.root)
        return codes.result("WF_OK", position_=codes.position(scope="task"),
                            next_="缺失的类按默认（ai_decides）处理；ask_always 的类一律交人",
                            facts={"prefs": prefs, "kinds": list(judgments_mod.KINDS),
                                   "path": judgments_mod.prefs_path(ctx.root)})
    if sub != "set":
        raise CliError("WF_PATH_INVALID", {"reason": "prefs requires set|show", "known": ["set", "show"]})
    kind = args.value("--kind")
    value = args.value("--value")
    if not kind or not value:
        raise CliError("WF_PATH_INVALID", {"reason": "prefs set requires --kind <类> --value <值>"})
    try:
        prefs = judgments_mod.set_pref(ctx.root, kind, value)
    except ValueError as exc:
        raise CliError("WF_PATH_INVALID", {"reason": str(exc), "kinds": list(judgments_mod.KINDS),
                                          "values": list(judgments_mod.PREFS)})
    return codes.result("WF_OK", position_=codes.position(scope="task"),
                        next_="偏好只在本机，不入库；ask_always 的类会强制交人",
                        facts={"prefs": prefs})


def cmd_judgments(ctx, args):
    """`judgments add --task <id> --file <json>` / `judgments show --task <id>`（只读渲染）。"""
    from . import judgments as judgments_mod, tasks as tasks_mod

    sub = (args.positional() or [None])[0]
    task_id = args.value("--task")
    if not task_id:
        raise CliError("WF_PATH_INVALID", {"reason": "judgments requires --task <id>"})
    task = tasks_mod.load_task(ctx.root, task_id)
    if task is None:
        raise CliError("WF_TARGET_MISSING", {"reason": "task not found", "task": task_id})
    if sub == "show":
        facts = judgments_mod.skeleton(ctx, task)
        from . import review as review_mod, sampling as sampling_mod

        state = sampling_mod.frozen(task)
        sampling_line = None
        if state.get("seed"):
            _all = [item for _d, item in tasks_mod.iter_tasks(ctx.root)]
            picked = sampling_mod.select_for(
                task, sampling_mod.history_from_tasks(_all),
                first_task=sampling_mod.is_first_task(_all),
                open_blocking=bool(review_mod.open_findings(ctx, task)["blocking"]))
            if picked and picked.get("picks"):
                sampling_line = "本次抽样：" + "、".join(
                    f"{item['class']}（{item['rule']}）" for item in picked["picks"])
        else:
            sampling_line = "本次抽样：尚未冻结事件集与种子（收工前用 `sampling pick --freeze` 冻结后再抽）"
        if state.get("seed"):
            backfill = sampling_mod.backfill_status((picked or {}).get("picks") or [],
                                                    task.get("judgments") or [])
            if backfill["missing"]:
                sampling_line += (f"\n[补写]    抽到 {backfill['count']} 条无对应判断（漏报失败）："
                                  "需补写两条（漏报说明 + 该类判断，带 backfill，原失败记录保留）")
            if backfill["over_limit"]:
                sampling_line += "\n[二次失败] 补写超过 2 条：记失败 + 写根因，由人裁"
        return codes.result(
            "WF_OK", object={"id": task_id, "name": task.get("title")},
            position_=codes.position(scope="task", phase=task.get("phase"), task_id=task_id),
            next_="按预览逐条核对；被驳回未处置项只能 resolved 或由你 waived",
            facts={"preview": judgments_mod.render_preview(task, facts, sampling_line=sampling_line,
                                                                    root=ctx.root),
                   "judgments": task.get("judgments") or [], "skeleton": facts},
        )
    if sub != "add":
        raise CliError("WF_PATH_INVALID", {"reason": "judgments requires add|show", "known": ["add", "show"]})
    path_value = args.value("--file")
    if not path_value:
        raise CliError("WF_PATH_INVALID", {"reason": "judgments add requires --file <json>"})
    entry = records.load_json(path_value if os.path.isabs(path_value) else join(ctx.root, path_value))
    if not isinstance(entry, dict):
        raise CliError("WF_PATH_INVALID", {"reason": "judgment file must be a JSON object", "path": path_value})
    with _lock(ctx.root, hint="judgments add"):
        _record, holder = ctx.require_held(task=task_id)
        directory = tasks_mod.task_dir(ctx.root, task_id)
        fresh = records.load_json(os.path.join(directory, "task.json"))
        facts = judgments_mod.skeleton(ctx, fresh)
        # 豁免要带人给出的确认摘要（乙口径）：`waived_by: human:` 只是字符串约定
        if isinstance(entry, dict) and str(entry.get("waived_by") or "").startswith("human:"):
            _payload, _digest, _problems = attestation_mod.load(
                args.value("--attestation"), action="waive")
            if _problems:
                raise CliError("WF_SEMANTIC_DECISION",
                               {"reason": "豁免必须由人给出确认文件（乙口径）",
                                "problems": _problems,
                                "exits": ["让人把确认写成 JSON（by/at/quote/source）后用 --attestation 传入",
                                          "人认为无需豁免就删掉 waived_by 字段"]},
                               next_="由人给出确认文件后重跑本命令")
            entry = dict(entry)
            entry["waiver"] = attestation_mod.stamp(_payload, _digest)
        record, problems = judgments_mod.append(fresh, entry, facts)
        if problems:
            raise CliError("WF_SEMANTIC_DECISION",
                           {"problems": problems,
                            "exits": ["按 problems 改字段或改引用（引用只能取骨架里的 id）",
                                      "判断不了就把 outcome 改成 escalated 并写清问题"]},
                           next_="补齐后重跑；框架不判断 decision 对不对，只核对引用与字段")
        fresh, action = tasks_mod._start_task_action(ctx, directory, fresh, "task.judge", holder,
                                                     {"task": task_id, "judgment": record.get("id")},
                                                     ["append"])
        fresh, assertion = tasks_mod._finish_task_action(ctx, directory, fresh, "task.judge", holder,
                                                         {"task": task_id, "judgment": record.get("id")},
                                                         action)
    return codes.result(
        "WF_OK", object={"id": task_id, "name": fresh.get("title")},
        position_=codes.position(scope="task", phase=fresh.get("phase"), task_id=task_id),
        next_="继续判断或收工时看 `judgments show`",
        facts={"judgment": record, "control_assertion": assertion},
    )


def cmd_lint(ctx, args):
    """`lint report --file <path> [--task <id>]`：一次性全量预检（不是门禁）。"""
    from . import review as review_mod, tasks as tasks_mod

    what = (args.positional() or [None])[0]
    if what != "report":
        raise CliError("WF_PATH_INVALID", {"reason": "lint requires `report`", "known": ["report"]})
    path = args.value("--file")
    if not path:
        raise CliError("WF_PATH_INVALID", {"reason": "lint report requires --file <path>"})
    target = path if os.path.isabs(path) else join(ctx.root, path)
    try:
        with open(target, "r", encoding="utf-8") as handle:
            text_value = handle.read()
    except FileNotFoundError:
        raise CliError("WF_TARGET_MISSING", {"reason": "report file not found", "path": path})
    except OSError as exc:
        raise CliError("WF_PATH_INVALID", {"reason": f"report unreadable: {exc}", "path": path})
    task = None
    task_id = args.value("--task")
    if task_id:
        task = tasks_mod.load_task(ctx.root, task_id)
        if task is None:
            raise CliError("WF_TARGET_MISSING", {"reason": "task not found", "task": task_id})
    facts = review_mod.lint_report(ctx, task, text_value)
    return codes.result(
        "WF_OK" if facts["ok"] else "WF_REVIEW_INVALID",
        object={"id": (task or {}).get("id"), "name": (task or {}).get("title"), "file": path},
        position_=codes.position(scope="task", phase=(task or {}).get("phase")),
        next_="按 problems 一次改全后重跑；lint 通过不等于门禁通过（锚点/材料/人数在导入与判定处核）",
        facts=facts,
    )


def cmd_review_accept_unknown(ctx, args):
    """人裁放行（⑥）：决定文件整批提交或撤销；只标记，不删除。"""
    from . import review as review_mod
    from . import tasks as tasks_mod

    task_id = args.value("--task")
    if not task_id:
        raise CliError("WF_PATH_INVALID", {"reason": "review-accept-unknown requires --task <id>"})
    task = tasks_mod.load_task(ctx.root, task_id)
    if task is None:
        raise CliError("WF_TARGET_MISSING", {"reason": "task not found", "task": task_id})
    round_no = args.value("--round")
    try:
        return review_mod.accept_unknown(
            ctx, task, args.value("--file"),
            revoke=bool(args.flag("--revoke")), batch=args.value("--batch"),
            round_no=int(round_no) if round_no not in (None, "") else None,
            slot=args.value("--slot"), digest=args.value("--digest"))
    except review_mod.ReviewError as exc:
        raise CliError(exc.code, exc.facts)


def _short_check(ctx, task):
    """`--short` 的 check 投影（B2）：报"能不能用"，不报记录的 `result`。

    记录的 `result` 是**当时**的结论；锚点漂移/失效之后它仍是 `pass`，直接显示会与事实
    矛盾。派生值来自 `gates.check_validity`（与门禁同一个函数），原始值另列 `check_result`
    供追溯。
    """
    from . import gates as gates_mod

    validity = gates_mod.check_validity(ctx, task)
    if validity["valid"]:
        token = "usable"
    else:
        token = ((validity.get("blockers") or [None])[0]
                 or validity.get("code") or "invalid")
    return {"check": token, "check_result": (task.get("check") or {}).get("result")}


def cmd_review_status(ctx, args):
    """`review-status`：审查到位状态（S9；只读，人不必再当传声筒）。"""
    from . import review as review_mod, tasks as tasks_mod

    task_id = args.value("--task")
    if not task_id:
        raise CliError("WF_PATH_INVALID", {"reason": "review-status requires --task <id>"})
    task = tasks_mod.load_task(ctx.root, task_id)
    if task is None:
        raise CliError("WF_TARGET_MISSING", {"reason": "task not found", "task": task_id})
    round_no = args.value("--round")
    try:
        facts = review_mod.status_of_round(ctx, task, int(round_no) if round_no else None)
    except review_mod.ReviewError as exc:
        raise CliError(exc.code, exc.facts)
    # A9：无法归属到精确身份的历史处置**不关闭**任何 finding，在这里单列待人裁
    facts["pending_dispositions"] = review_mod.open_findings(ctx, task)["ambiguous"]
    # B1：status 只报材料与资格，不承诺判定资格（结论只能由 review-decide 产生）
    if not facts["material_ready"]:
        next_ = (f"材料未齐（已到 {facts['arrived']}/{facts['required']}）："
                 "等 reviewer 产出后 review-import")
    elif facts["eligibility"]["problems"]:
        next_ = ("材料已齐，但判定资格不足："
                 + "；".join(item["reason"] for item in facts["eligibility"]["problems"]))
    else:
        next_ = "材料已齐、资格检查通过：下一步 review-decide（结论以判定为准）"
    return codes.result(
        "WF_OK",
        object={"id": task.get("id"), "name": task.get("title")},
        position_=codes.position(scope="task", phase=task.get("phase"), task_id=task.get("id")),
        next_=next_,
        facts=facts,
    )


def cmd_help(ctx, args):
    """`help [<命令>]`：输出该命令的输入结构、最小示例与常见出口（只读）。"""
    name = None
    for token in args.argv:
        if not token.startswith("-"):
            name = token
            break
    if name is None:
        return ok(facts={"commands": sorted(COMMAND_HELP),
                         "hint": "wf.py help <命令> 看输入结构与最小示例"},
                  position=codes.position(scope="session"),
                  next_="按需要查看具体命令")
    entry = COMMAND_HELP.get(name)
    if entry is None:
        raise CliError("WF_PATH_INVALID", {"reason": "unknown command for help", "command": name,
                                           "known": sorted(COMMAND_HELP)})
    facts = dict(entry)
    facts["command"] = name
    facts["envelope"] = "所有业务命令都从 stdin 或 --envelope <file> 收请求信封（provider=host + identity.host_id + session_id）"
    return ok(facts=facts, position=codes.position(scope="session"), next_="按 example 调用")


COMMANDS = {
    "status": cmd_status,
    "help": cmd_help,
    "ready": cmd_ready,
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
    # v42 §4 要求删除 `task-rework`，但机制稿 §6.2 与 `workflows/instance-flow.md` 仍把
    # `control.task.rework` 声明为 [required] 的两轮交付步骤；删命令会让部署自检
    # （handler entry 必须存在）失败。属权威冲突，先保留桩并登记待裁，不单方面删步骤。
    "task-rework": _unavailable(2, "task rework (D07)"),
    "task-replace": _unavailable(2, "task replace (D07)"),
    "review-context": _review_command("context"),
    "review-launch": _review_command("launch"),
    "review-import": _review_command("import"),
    "review-decide": _review_command("decide"),
    "review-accept-unknown": cmd_review_accept_unknown,
    "review-status": cmd_review_status,
    "lint": cmd_lint,
    "judgments": cmd_judgments,
    "sampling": cmd_sampling,
    "prefs": cmd_prefs,
    "authorize": cmd_authorize,
    "project": cmd_project,
    "verify": cmd_verify,
    "definition": _unavailable(2, "definition prepare/validate (D03/D11)"),
    "run": _unavailable(2, "workflow instances (D03/D11/D12/D13)"),
    "upgrade": _unavailable(3, "upgrade --apply / release identity (D22/D37)"),
}


ACTIVATION_REQUIRED = frozenset({
    "task-approve", "task-start", "task-replan", "task-pause", "task-resume", "task-curate",
    "task-check", "task-knowledge", "task-retrospect", "task-attribute", "task-abandon",
    "task-reassess", "archive", "baseline-apply", "spec-update", "stop",
    "review-launch", "review-import", "review-decide", "review-accept-unknown",
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
    ctx.command = command
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
    if (payload or {}).get("code") == "WF_OK" and command != "review-context":
        # reviewer 的身份不需要被后续复用；不写缓存可避免与主会话互相覆盖
        remember_envelope(ctx.root, ctx._envelope, payload)
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
