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


def resolve_generation(ctx, key):
    """写权代次的来源解析（唯一实现）：显式请求 → 本会话运行态 → `(None, None)`。

    代次属于**会话运行态**：取得写权时由 `writer.save` 记进该会话侧车（机制稿 §1.4）。
    这里的侧车值是"本会话取得写权时拿到的代次"，不是 writer 的当前值——侧车陈旧仍会被拦。
    """
    generation = ctx.inputs().get("generation")
    if generation is not None:
        return generation, "request"
    runtime = session_mod.load_runtime(ctx.root, key) or {}
    return runtime.get("writer_generation"), "session-runtime"


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
    # 缓存按会话分文件：host 用 session_id，wf 用 issued_id；两者都没有时宁可不缓存，
    # 也不共用 `unknown.json`（两个会话会互相读到对方的身份/activation）。
    identity = session.get("identity") or {}
    session_id = identity.get("session_id") or identity.get("issued_id")
    if not session_id:
        return
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
        """四态解析（W3-2，三轮 P0-1）——返回**单一结构**，三处消费不重判。

        `{state, key, attachment, evidence, host_identity_present}`：
        - `host_resume`（①）：映射命中且 host 会话有附件 → 续用；
        - `inflight_reuse`（②）：映射命中、host 无附件、锚点路由有在途会话
          （有附件 + 绑定文件存在可读 + 实例标识匹配 + 对象未终态）→ 续用该会话，
          不改写不接管——在途会话的身份不因 hook 上线/换聊天被夺走；
        - `host_establish`（③）：映射命中、host 无附件、路由无在途会话 → 由
          `cmd_enable` 以 host 身份建立并接管路由（本结构只报状态）；
        - `anchor_resume`（④）：无映射时按锚点路由解析（既有语义不变）；
        - `no_session`：无锚点/无路由可命中；
        - `unresolved`：绑定不可读/实例标识与附件不符——**只在写/推进入口阻断**
          （抛错由消费方决定），只读面降级为 facts 可见事实继续运行。
        """
        from . import identity_store as store

        resolution = self._auto_resolve_inner()
        self._resolution = resolution
        return resolution

    def _auto_resolve_inner(self):
        from . import identity_store as store

        candidates = session_mod.candidates()
        if not candidates:
            return {"state": "no_session", "key": None, "attachment": None,
                    "evidence": {"reason": "no execution boundary"},
                    "host_identity_present": False}
        keys = [session_mod.anchor_key(item) for item in candidates]
        routes = store.load_routes(self.root)
        path = self.identity_path()
        current_root = candidates[-1] if candidates[-1]["kind"] == "pid" else candidates[0]

        # 宿主映射前置查询（W3-2）：命中即宿主提供了会话标识。
        mapping = store.load_host_map(self.root, keys)
        host_present = mapping["status"] == "hit"
        if host_present:
            payload = mapping["payload"]
            host_id = str(payload.get("host_id"))
            installed = self.platforms()
            if host_id not in [item for item in installed if isinstance(item, str)]:
                # host_id 按安装记录 platforms 清单校验（设计 §3.2.1③）——不在清单即
                # 无法核实宿主身份来源，回落锚点路由（④）并在 facts 如实报告，
                # 不因映射不可核而丢掉锚点上仍可续用的会话。
                resolution = self._anchor_resolve(candidates, keys, routes, path, current_root,
                                                  host_present=False, import_error=False)
                resolution["evidence"] = dict(resolution.get("evidence") or {},
                                              host_mapping_rejected="host_id not in installed platforms",
                                              host_id=host_id)
                return resolution
            host_key = session_mod.session_key(
                {"provider": "host",
                 "identity": {"host_id": host_id, "session_id": str(payload.get("session_id"))}})
            host_attachment = store.load_attachment(self.root, host_key)
            if host_attachment is not None:
                # ① 映射命中 + host 身份有附件：按既有解析续用该 host 会话。
                return {"state": "host_resume", "key": host_key, "attachment": host_attachment,
                        "evidence": {"host_mapping": "hit", "session_id": payload.get("session_id"),
                                     "host_id": host_id},
                        "host_identity_present": True}
            # ②/③ 分流：查锚点路由上的在途会话（绑定文件存在且可读、实例标识匹配、
            # 绑定对象未终态——paused/suspended 都算在途）。
            inflight = self._inflight_session(routes, keys)
            if inflight["state"] == "inflight_reuse":
                return {"state": "inflight_reuse", "key": inflight["key"],
                        "attachment": inflight["attachment"],
                        "evidence": dict(inflight["evidence"],
                                         host_mapping="hit",
                                         host_session_id=payload.get("session_id"),
                                         note="宿主会话标识已变化；当前边界按既有在途会话续用",
                                         exits=["继续当前对象",
                                                "完成/放弃对象后 `wf enable --new-session` 换新会话（暂停不解除在途绑定）"]),
                        "host_identity_present": True}
            if inflight["state"] == "unresolved":
                return {"state": "unresolved", "key": None, "attachment": None,
                        "evidence": dict(inflight["evidence"],
                                         host_mapping="hit",
                                         host_session_id=payload.get("session_id")),
                        "host_identity_present": True}
            # ③ 映射命中、host 无附件、路由无在途会话（全部终态/无附件）：
            # 建立 host 身份会话并接管路由——由 enable 承载；非 enable 命令按"无会话"处理。
            return {"state": "host_establish", "key": None, "attachment": None,
                    "evidence": {"host_mapping": "hit", "host_id": host_id,
                                 "session_id": payload.get("session_id"),
                                 "host_session_key": host_key,
                                 "reason": "no inflight session on this boundary"},
                    "host_identity_present": True}

        # ④ 无映射：锚点路由解析（既有语义原样保留）。
        return self._anchor_resolve(candidates, keys, routes, path, current_root,
                                    host_present=host_present,
                                    import_error=mapping["status"] == "import-error")

    def _anchor_resolve(self, candidates, keys, routes, path, current_root,
                        *, host_present=False, import_error=False):
        """④：锚点路由命中判定（原 `_auto_resolve` 主体，语义不变）。"""
        from . import identity_store as store

        l1_owners = store.owners_of(routes, keys[0]) if candidates[0]["kind"] == "sid" else []
        l2_owners = []
        for key, item in zip(keys, candidates):
            if item["kind"] == "pid":          # 锚点 kind 是 pid；路由 via 才叫 proc
                l2_owners = store.owners_of(routes, key)

        base = {"host_identity_present": host_present,
                "evidence": {"host_mapping_import_error": True} if import_error else {}}
        if len(l1_owners) == 1:                       # #1 / #2：L1 单主命中即以此为准
            return dict(base, state="anchor_resume", key=l1_owners[0],
                        attachment=store.load_attachment(self.root, l1_owners[0]))
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
                return dict(base, state="anchor_resume", key=owner,
                            attachment=store.load_attachment(self.root, owner))
            raise CliError("WF_IDENTITY_UNRESOLVED",
                           {"reason": verdict["reason"], "facts": verdict.get("facts"),
                            "owners": l2_owners,
                            "exits": ["人调 /wf-start 显式登记当前调用者",
                                      "结束另一个调用者后重试",
                                      EXPLICIT_ENVELOPE_EXIT]},
                           next_="按 facts.reason 的出口处置后重试")
        return dict(base, state="no_session", key=None, attachment=None,
                    evidence=dict(base["evidence"], reason="no route matched"))

    def _inflight_session(self, routes, keys):
        """② 的边界输入判定：锚点路由上有无**在途会话**（W3-2）。

        在途 = 路由命中的会话有附件、绑定文件存在且可读、实例标识匹配
        （`instance_expected ∈ {None, "", binding.instance_id}`——None/空以
        binding.instance_id 回填附件，`sync_attachment_instance` 唯一写回实现）、
        且绑定对象未终态（task 非 archived / run terminal 为 null；paused/suspended
        都算在途）。绑定文件缺失 ⇒ 启用未绑定 ⇒ **不算在途**（没有要保护的对象）；
        绑定不可读 / 实例已有不同值 ⇒ `unresolved`（需人裁，只读面降级可见）。
        """
        from . import identity_store as store
        from . import session as session_mod_
        from . import tasks as tasks_mod

        seen_owners = []
        for key in keys:
            for owner in store.owners_of(routes, key):
                if owner not in seen_owners:
                    seen_owners.append(owner)
        for owner in seen_owners:
            attachment = store.load_attachment(self.root, owner)
            if attachment is None:
                continue
            binding = session_mod_.load_binding(self.root, owner)
            if binding is None:
                continue          # 启用未绑定：没有要保护的对象，不算在途
            if not isinstance(binding, dict) or not isinstance(binding.get("object"), dict):
                return {"state": "unresolved",
                        "evidence": {"reason": "binding_unreadable", "session_key": owner}}
            expected = attachment.get("instance_expected")
            bound_instance = binding.get("instance_id")
            if expected not in (None, "", bound_instance):
                return {"state": "unresolved",
                        "evidence": {"reason": "instance_mismatch",
                                     "session_key": owner,
                                     "instance_expected": expected,
                                     "binding_instance_id": bound_instance}}
            if expected in (None, "") and bound_instance:
                # 历史会话 instance_expected 为空：以 binding.instance_id 回填附件
                # （既有唯一写回实现）——否则 auto_session 把 None 作 instance_id，
                # 写入口因 carried 缺失拒绝。
                store.sync_attachment_instance(self.root, owner, bound_instance)
                attachment["instance_expected"] = bound_instance
            obj = binding.get("object") or {}
            obj_kind, obj_id = obj.get("kind"), str(obj.get("id"))
            if obj_kind == "task":
                record = tasks_mod.load_task(self.root, obj_id)
                if record is not None and isinstance(record, dict) and record.get("status"):
                    if record.get("status") == "archived":
                        continue      # 已终态：不算在途
                    evidence = {"task_status": record.get("status"), "binding_id": obj_id,
                                "session_key": owner}
                else:
                    # 记录缺失/不可解析：对象已不在，没有要保护的东西——不算在途
                    continue
            elif obj_kind == "run":
                from . import runs as runs_mod

                run = runs_mod.load_run(self.root, obj_id)
                if run is not None and isinstance(run, dict):
                    if run.get("terminal") is not None:
                        continue      # 已终态：不算在途
                    evidence = {"run_terminal": run.get("terminal"), "binding_id": obj_id,
                                "session_key": owner}
                else:
                    continue
            else:
                continue              # 未知对象类别：不猜，不算在途
            return {"state": "inflight_reuse", "key": owner, "attachment": attachment,
                    "evidence": evidence}
        return {"state": "none", "evidence": {"reason": "no inflight session"}}

    def auto_session(self, establish=False):
        """自动身份模式：返回合成 session（`source="auto"`）或 None。

        只消费 `_auto_resolve` 的单一结构，不重判四态（W3-2 单实现纪律）。
        `host_establish`/`no_session`：非 establish 返回 None（由调用方报"需 /wf-start"）；
        establish 时也返回 None——建立由 `cmd_enable`/`_establish_auto_session` 承载。
        `unresolved`：返回 None 并把证据挂到 `self._resolution` 供 facts 投影
        （只读面不在此抛错——写入口的阻断由 `session(required=True)` 的既有路径给出）。
        """
        resolution = self._auto_resolve()
        state = resolution["state"]
        if state in ("host_resume", "inflight_reuse", "anchor_resume"):
            key, attachment = resolution["key"], resolution["attachment"]
            session = {"provider": (attachment or {}).get("provider") or "wf",
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
        return None

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
                hint = "writer acquire"      # writer 不收 --task（对象来自会话绑定），2026-11-21 修正误导文案
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
        generation, source = resolve_generation(self, key)
        if generation is None:
            raise CliError(
                "WF_GENERATION_STALE",
                {"reason": "generation not carried (neither request nor session runtime)",
                 "current_generation": holder.get("generation"),
                 "exits": ["显式携带一次 inputs.generation（值取 writer 记录 holder.generation）后重试；"
                           "成功后本会话侧车自动建立",
                           "或 `wf writer release` 后重新 `wf writer acquire`，让侧车记录新代次"]},
                next_="按 exits 补齐代次来源后重试",
            )
        if int(generation) != int(holder.get("generation")):
            raise CliError(
                "WF_GENERATION_STALE",
                {
                    "reason": "generation mismatch",
                    "carried": generation,
                    "generation_source": source,
                    "current_generation": holder.get("generation"),
                },
            )
        if source == "request":
            # 升级前已持权的会话没有侧车：一次显式携带成功后幂等补齐（不改变判定）。
            writer_mod.sync_session_generation(self.root, record)
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
    # W3-2 可见性：宿主映射状态投影（hit/absent/import-error）——映射缺失/导入失败
    # 不再不可见；只读 facts，不参与判定。
    try:
        from . import identity_store as _store_mod

        _keys = [session_mod.anchor_key(item) for item in session_mod.candidates()]
        mapping = _store_mod.load_host_map(ctx.root, _keys)
        facts["host_mapping"] = {"status": mapping["status"],
                                 "session_id": (mapping["payload"] or {}).get("session_id"),
                                 "host_id": (mapping["payload"] or {}).get("host_id"),
                                 "import_error": (mapping["payload"] or {}).get("error")
                                 if mapping["status"] == "import-error" else None}
    except Exception:   # noqa: BLE001 — 投影失败不阻断只读状态页
        pass
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

                # 手工验证/收尾确认要绑定"人看到的交付内容"：这里给出与 Check 同源的
                # 内容摘要（`object_digest` 写它）。只读事实，不参与判定。
                try:
                    from . import check as check_mod, fingerprint as fingerprint_mod

                    delivery = check_mod.object_paths(ctx, task)
                    facts["delivery"] = {
                        "paths": len(delivery),
                        "content_digest": fingerprint_mod.content_digest(
                            fingerprint_mod.items(ctx.root, delivery)),
                    }
                except Exception as exc:      # noqa: BLE001 — 只读投影失败不阻断状态页
                    facts["delivery"] = {"error": str(exc)}
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
            # 收窄审查材料是判断，必须在人看的一屏里可见；不是新的门禁
            "launch_scope": [{"round": item.get("round"), "scope": item.get("scope")}
                             for item in scope.get("launches") or []
                             if isinstance(item, dict) and item.get("scope")],
            # 放行清单是"强制回显"（§6 cli ④/#46），--short 也列（by/at/quote 都很短）
            "unknown_acceptances": list(acceptances)}


def cmd_gate(ctx, args):
    due = args.value("--due")
    if due not in ("before_execute", "before_check", "before_archive"):
        raise CliError("WF_USAGE_INVALID", {"reason": "gate requires --due before_execute|before_check|before_archive"})
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


def _establish_auto_session(ctx, host_establish=None, identity=None):
    """自动模式首次启用：签发身份、写附件、登记路由（§3.1/§2.2a）。

    只在"当前锚点没有任何路由"时调用；已有路由由 `_auto_resolve` 命中，不走这里。
    W3-2③：`host_establish` 非空（映射命中且路由无在途会话）时以 **host 身份**建立——
    `session_key = H({provider:"host", identity:{host_id, session_id}})`，host_id 按
    安装记录 platforms 清单核过；建立前对同锚点既有其他 owner 先 `replace_owner`
    组更新（否则 sid 锚点撞 register 的 L1 单主 StoreError）；接管启用未绑定的会话时
    facts 点明"旧会话路由已让出，后续要重新 enable"，不静默丢弃。
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
    at = records.now_str()
    if identity is not None:
        # 调用方已经算好身份（enable 要在写盘前用同一把会话 key 核锚点冲突）：
        # 生成身份是纯计算，抽到调用点不改变落盘语义。
        provider, identity_value = identity
        issued_id = identity_value.get("issued_id")
    elif host_establish is not None:
        identity_value = {"host_id": host_establish["host_id"],
                          "session_id": host_establish["session_id"]}
        provider = "host"
        issued_id = None
    else:
        issued_id = uuid.uuid4().hex
        identity_value = {"issued_id": issued_id}
        provider = "wf"
    session_key = records.sha256_hex(
        records.canonical_bytes({"provider": provider, "identity": identity_value}))
    current_root = candidates[-1]
    activation = {"enabled": True, "start_source": "human:enable", "enabled_at": at}
    attachment = store.new_attachment(identity_value, provider, session_key, current_root, activation, at)
    l1 = next((item for item in candidates if item["kind"] == "sid"), None)
    if l1:
        attachment["attached_l1"] = {"kind": "sid", "boot": l1["boot"], "sid": l1["sid"],
                                     "sid_start": l1["sid_start"]}
    routes = store.load_routes(ctx.root)
    took_over = []
    for item in candidates:
        key = session_mod.anchor_key(item)
        for other in store.owners_of(routes, key):
            if other != session_key and other not in took_over:
                took_over.append(other)
    # ③ 接管路由：同锚点既有其他 owner 先 replace_owner 组更新（轮换=组更新，
    # 且必须先于 register——L1 单主 register 撞既有 owner 会抛 StoreError）。
    # 旧附件/绑定保留为历史，不改写。
    for other in took_over:
        store.replace_owner(routes, other, session_key)
    for item in candidates:
        key = session_mod.anchor_key(item)
        store.register(routes, key, session_key,
                       "session" if item["kind"] == "sid" else "proc", item["boot"], at)
    store.save_attachment(ctx.root, session_key, attachment)   # ① 先写附件
    store.save_routes(ctx.root, routes)                        # ② 再提交路由（组原子）
    ctx._auto_key = session_key
    ctx._auto_attachment = attachment
    ctx._session = {"provider": provider, "identity": identity_value,
                    "instance_id": None, "activation": activation, "source": "auto"}
    ctx._envelope = {"session": None, "inputs": {}}
    facts = {"session_key": session_key, "roots": attachment["roots"]}
    if provider == "host":
        facts["issued_id"] = None
        facts["host_id"] = host_establish["host_id"]
        facts["host_session_id"] = host_establish["session_id"]
    else:
        facts["issued_id"] = identity_value["issued_id"]
    if took_over:
        # 接管启用未绑定的会话：旧会话路由已让出——没有绑定对象要保护，
        # 但旧会话下次想用时须重新 enable（诚实可见，不静默丢弃）。
        unbound_taken = [other for other in took_over
                         if session_mod.load_binding(ctx.root, other) is None]
        facts["route_taken_over_from"] = took_over
        if unbound_taken:
            facts["note"] = "旧会话路由已让出；旧会话后续要重新 enable"
    return facts


def _rotate_session(ctx):
    """W3-1：`enable --new-session` —— 同边界显式换新会话身份（宿主无关）。

    前置：本边界已有可续用会话；其绑定对象已终态（或绑定为空）——在途时
    `WF_BINDING_MISMATCH`（完成/放弃对象后重试；暂停不解除在途绑定，不给 bind 之类不成立指引）。
    写权语义：轮换不触碰写权——对象终态但写权未释放 ⇒ 拒绝并给 release 出口
    （防把在途写权带进新会话）。
    动作：签发新 `issued_id`，`replace_owner(old, new)` 组更新（既有"轮换=组更新"），
    旧附件/绑定保留为历史（结束不解除绑定）；同锚点的宿主映射条目一并移除
    （适配层通道状态：不移除会让下一次映射命中把旧身份接回来，轮换形同虚设）。
    """
    from . import identity_store as store
    from . import writer as writer_mod

    resolution = ctx._auto_resolve()
    if resolution["state"] in ("no_session", "host_establish"):
        # 锚点无路由（或仅待建立）＝普通 enable（等价首次启用），不存在"旧身份"可轮换。
        if ctx.explicit_session() is not None:
            raise CliError("WF_SEMANTIC_DECISION",
                           {"reason": "--new-session 只在自动身份模式下轮换本边界会话；"
                                      "显式信封会话由宿主承载，不经本命令"},
                           next_="自动模式直接跑 enable；显式模式换信封身份即可")
        evidence = resolution.get("evidence") or {}
        host_establish = None
        if resolution["state"] == "host_establish":
            host_establish = {"host_id": evidence.get("host_id"),
                              "session_id": evidence.get("session_id")}
        # 首次启用等价的这条路也要过同一套前置（Trellis 互斥、平台），不因走的是
        # `--new-session` 就少核。这两态 `ctx.session()` 还是 None，按将要签发的身份合成
        # （与 `cmd_enable` 同一构造）。
        guard_session = ({"provider": "host", "identity": dict(host_establish), "source": "auto"}
                         if host_establish is not None
                         else {"provider": "wf", "identity": {}, "source": "auto"})
        first_guards = _enable_guards(ctx, guard_session)
        facts = _establish_auto_session(ctx, host_establish=host_establish)
        facts["rotated"] = False
        facts["note"] = "本边界此前无会话：本次为首次启用，不属轮换"
        # 与轮换/普通启用同一份自述面：身份能力与 Trellis 线索不能只在这个分支缺席
        first_identity = _identity_facts(ctx, facts["session_key"])
        first_applicable = [item for item in first_guards["trellis"]["host_files"]
                            if item["host"] == first_guards["trellis"]["host_id"]]
        first_disabled = bool((ctx.inputs() or {}).get("trellis_disabled_confirmed"))
        facts["identity"] = first_identity
        facts["trellis_data"] = first_guards["trellis"]["data"]
        facts["trellis_disabled_confirmed"] = first_disabled
        first_warnings = _identity_warnings(first_identity, first_guards["trellis"],
                                            first_applicable, first_disabled)
        return codes.result("WF_OK", position_=codes.position(scope="session"),
                             next_="新会话已启用；继续 task-new 选择对象",
                             facts=facts, warnings=first_warnings)
    if resolution["state"] == "unresolved":
        raise CliError("WF_IDENTITY_UNRESOLVED",
                       dict(resolution.get("evidence") or {},
                            exits=["按 §5.4/repair 修复绑定/附件后重试",
                                   "人核实对象终态后走 enable --new-session"]),
                       next_="绑定不可读或实例不符：先修复再轮换")
    # 前置在**写任何记录之前**：轮换与普通 enable 共用一套（此前轮换整段前置都不跑）。
    # 身份取自解析出的附件，不经 `ctx.session()`——stale 激活会让它在核对完轮换资格前就拒。
    old_key = resolution["key"]
    current_attachment = resolution.get("attachment") or {}
    guards = _enable_guards(ctx, _session_like(current_attachment.get("provider"),
                                               current_attachment.get("identity")))
    binding = session_mod.load_binding(ctx.root, old_key)
    if binding is not None:
        # 非 dict（形状坏了）也算有绑定但对象未知：helper 返回 unknown ⇒ 按未知拒绝。
        raw_obj = binding.get("object") if isinstance(binding, dict) else None
        obj = raw_obj if isinstance(raw_obj, dict) else {}
        # 终态判据与普通 enable 同一个实现（session.object_terminal_state）：
        # 找不到绑定对象记录既不是终态也不是在途，须先核对，不能当成"可以换会话"。
        state = session_mod.object_terminal_state(ctx.root, binding)
        if state == "unknown":
            raise CliError("WF_BINDING_MISMATCH",
                           {"reason": "绑定对象记录缺失或不可读：无法证明已到终态，不得轮换会话身份",
                            "object": obj, "session_key": old_key,
                            "exits": ["`wf status` 或 `wf repair --diagnose` 核对绑定对象记录后重试",
                                      "确认对象记录已丢失时按 repair 恢复；不要直接换会话把原对象丢在旧身份上",
                                      "对象确实存在且未结束时继续当前对象后再轮换"]},
                           next_="先核对绑定对象记录（status/repair），再重试 enable --new-session")
        if state != "terminal":
            raise CliError("WF_BINDING_MISMATCH",
                           {"reason": "绑定对象仍在途，不得轮换会话身份",
                            "object": obj, "session_key": old_key,
                            # 暂停不解除在途绑定（门禁同口径）：不给"暂停后重试"的无效出口
                            "exits": ["继续当前对象直至完成/归档后重试",
                                      "task-abandon 放弃对象后重试",
                                      "新开终端/新执行边界（换边界即换会话）"]},
                           next_="完成/放弃当前对象后重试 enable --new-session（暂停不解除在途绑定）")
    # 写权语义：轮换不触碰写权；对象终态但写权未释放 ⇒ 拒绝并给 release 出口。
    writer_record = writer_mod.load(ctx.root) or {}
    if writer_record.get("state") != "idle":
        raise CliError("WF_WRITER_BUSY",
                       {"reason": "写权仍在持有（对象终态但未释放）——不得把在途写权带进新会话",
                        "holder": writer_record.get("holder")},
                       next_="先 `writer release` 释放写权，再重试 enable --new-session")
    # 续期放在轮换资格全部核完之后：被拒的轮换不该顺手改启用状态（旧会话是否"已重新启用"
    # 必须与命令结果一致）。后面只剩纯计算与写入块。
    _renewed_attachment, renewed = _renew_activation(ctx, old_key, current_attachment)
    candidates = session_mod.candidates()
    keys = [session_mod.anchor_key(item) for item in candidates]
    at = records.now_str()
    issued_id = uuid.uuid4().hex
    identity_value = {"issued_id": issued_id}
    new_key = records.sha256_hex(
        records.canonical_bytes({"provider": "wf", "identity": identity_value}))
    routes = store.load_routes(ctx.root)
    store.replace_owner(routes, old_key, new_key)
    attachment = store.new_attachment(identity_value, "wf", new_key,
                                      candidates[-1] if candidates else None,
                                      {"enabled": True, "start_source": "human:new-session",
                                       "enabled_at": at}, at)
    store.save_attachment(ctx.root, new_key, attachment)
    store.save_routes(ctx.root, routes)
    removed_mapping = store.remove_host_map(ctx.root, keys)
    ctx._auto_key = new_key
    ctx._auto_attachment = attachment
    ctx._session = {"provider": "wf", "identity": identity_value, "instance_id": None,
                    "activation": attachment["activation"], "source": "auto"}
    facts = {"rotated": True, "old_session_key": old_key, "session_key": new_key,
             "issued_id": issued_id,
             "old_binding_preserved": binding is not None,
             "removed_host_mapping": removed_mapping}
    if removed_mapping:
        facts["note"] = "宿主映射条目已随轮换移除；下次宿主 SessionStart 会按新会话标识重建"
    # 与普通 enable 同口径的事实面（身份能力、Trellis 线索、停用确认）：轮换也要如实报
    # 「这个宿主看不见同进程新会话」这类边界，否则两个入口的自述面分叉。
    trellis_state = guards["trellis"]
    applicable = [item for item in trellis_state["host_files"]
                  if item["host"] == trellis_state["host_id"]]
    disabled = bool((ctx.inputs() or {}).get("trellis_disabled_confirmed"))
    identity_facts = _identity_facts(ctx, new_key)
    facts["identity"] = identity_facts
    if renewed:
        facts["identity"] = dict(identity_facts, activation_renewed=True)
    facts["trellis_data"] = trellis_state["data"]
    facts["trellis_disabled_confirmed"] = disabled
    return codes.result("WF_OK", position_=codes.position(scope="session"),
                         next_="新会话已生效；旧附件/绑定保留为历史，新对象用 task-new 选择",
                         facts=facts,
                         warnings=_identity_warnings(identity_facts, trellis_state, applicable, disabled))


def _identity_facts(ctx, session_key):
    """K1：宿主会话标识优先、进程锚只作冲突判据；缺宿主标识时显式报告看不见 /clear。

    W3-2（三轮 P0-1）拆两字段、不覆盖 `source`：
    - `host_identity_present`：显式信封**或**宿主映射命中即 true（宿主是否提供会话标识的客观事实）；
    - `session_provider`：**实际解析到的会话身份**的 provider（②续用时是 wf，不得报 host）；
    - `source`：保持实际来源语义（host=显式信封 / anchor=自动解析）。
    "无法区分 /clear"警告只在 host_identity_present=false 时出现。
    """
    from . import identity_store as store

    explicit = ctx.explicit_session()
    resolution = getattr(ctx, "_resolution", None) or {}
    host_present = explicit is not None or bool(resolution.get("host_identity_present"))
    anchor_keys = [session_mod.anchor_key(item) for item in session_mod.candidates()]
    facts = {
        "source": "host" if explicit is not None else "anchor",
        "host_identity_present": host_present,
        "host_identity_absent": not host_present,
        "anchor_candidates": len(anchor_keys),
        "anchor_conflict": store.conflicting_owners(store.load_routes(ctx.root), anchor_keys, session_key),
    }
    session = (ctx.session(required=False) or {}) if hasattr(ctx, "session") else {}
    facts["session_provider"] = session.get("provider")
    if host_present and resolution.get("state") == "inflight_reuse":
        facts["host_session_changed"] = True
        facts["inflight_reuse"] = resolution.get("evidence") or {}
    if not host_present:
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


def _transfer_stub():
    """W4-1/W4-2：upgrade 经引导层转交，不经本层用法校验（help 一致性保留该注册条目）。"""
    def _handler(ctx, args):
        raise CliError(
            "WF_CAPABILITY_UNAVAILABLE",
            {"reason": "upgrade 经引导层转交：本层不实现升级判定",
             "transfer": ".wf/bin/wf.py upgrade --release <检出根> --release-ref <ref> "
                         "[--apply | --export-deviations --out <目录>] [--keep <路径>] [--restore <路径>]",
             "direct": "<检出根>/install.py --upgrade --target <项目> "
                      "--release-ref refs/tags/wf-vX.Y.Z --source <检出根> [--apply | --export-deviations --out <目录>]"},
            next_="终端直接运行 wf.py upgrade（引导层转交）或 install.py --upgrade；"
                  "应用升级须交互终端预览令牌，模型不代跑；--export-deviations 是只读导出，不取令牌、"
                  "不暂停任务、不改安装记录（未接受偏离也导出并标 pending）",
        )
    return _handler


def _enable_guards(ctx, session_like):
    """启用前置（唯一实现）：Trellis 互斥 + 平台可用性。**只读，两个启用入口共用**。

    必须在写任何记录之前跑完：此前普通 `enable` 先写附件/路由再查冲突，命令拒绝了却留下
    `activation.enabled=true`，后续命令的 `require_activation` 就会放行；`--new-session`
    则整段前置都不跑。`session_like` 只需 `{provider, identity, source}`——会话还没建立时
    由调用方按将要签发的身份合成。
    """
    state = _trellis_state(ctx.root, (session_like.get("identity") or {}).get("host_id"))
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
    code, profile_facts = session_mod.check_platforms(ctx.platforms(), session_like)
    if code:
        raise CliError(code, profile_facts, next_="install（已装齐全部平台）后重试，或换用已安装的宿主")
    return {"trellis": state, "platforms": profile_facts}


def _renew_activation(ctx, key, attachment):
    """人重新 enable 即"重新启用"：`activation_stale` 由本命令清掉并刷新 activation。

    此前 stale 只把出口写成"重新调用 /wf-start"，而 enable 自己的 `ctx.session()` 也会
    撞同一标记 ⇒ 出口走不通（等于死锁）。续期只清这一个标记，roots 维护照旧。
    """
    from . import identity_store as store

    if not isinstance(attachment, dict) or not attachment.get("activation_stale"):
        return attachment, False
    attachment = dict(attachment)
    attachment["activation"] = {"enabled": True, "start_source": "human:enable",
                                "enabled_at": records.now_str()}
    attachment["activation_stale"] = False
    store.save_attachment(ctx.root, key, attachment)
    ctx._auto_attachment = attachment
    return attachment, True


def _session_like(provider, identity):
    return {"provider": provider, "identity": dict(identity or {}), "source": "auto"}


def _anchor_conflict(ctx, key):
    """本会话 key 在现有路由上的同锚点冲突（写盘前的身份门禁用）。"""
    from . import identity_store as store

    keys = [session_mod.anchor_key(item) for item in session_mod.candidates()]
    return store.conflicting_owners(store.load_routes(ctx.root), keys, key)


def _identity_warnings(identity_facts, state, applicable, disabled):
    """身份类警告（事实不是门禁）：两个启用入口共用同一份，避免轮换少了自述面。"""
    warnings = []
    if identity_facts.get("host_identity_absent"):
        warnings.append({"reason": "host_identity_absent",
                         "note": ("本会话身份只能由进程锚派生；该宿主未提供会话标识，"
                                  "框架无法区分同一进程内的新会话（宿主自带的新会话命令、或同终端新开聊天），"
                                  "换会话请开新终端"),
                         "new_session_indistinguishable": True})
    if state.get("data"):
        warnings.append({"clue": state["data"], "note": "仅数据线索；不构成当前激活指令"})
    if applicable and disabled:
        warnings.append({"reason": "trellis_files_present_but_disabled_confirmed",
                         "host_id": state["host_id"],
                         "trellis_host_config": applicable,
                         "note": "人已确认这些配置在本宿主不生效（停用/残留）；日后重新启用前必须先清理"})
    return warnings


def cmd_enable(ctx, args):
    """启用本会话：**所有拒绝都在写盘之前**（被拒时不留 `enabled=true`）。"""
    _check_layout(ctx.root)
    # W3-1：`--new-session` —— 人在当前执行边界显式换新会话身份（宿主无关）。
    if args.flag("--new-session"):
        return _rotate_session(ctx)
    # 纯参数校验也前移：`--identity` 打错是首次启用最常见的拒绝形态，不能先写后拒。
    choice = (args.value("--identity") or "").strip() or None
    if choice is not None and choice != "host":
        raise CliError("WF_PATH_INVALID",
                       {"reason": "--identity accepts only 'host'", "known": ["host"], "actual": choice},
                       next_="用 --identity host 确认以宿主标识为准，或换新会话")
    # 自动模式且尚无可续用会话 ⇒ 本次 enable 就是"建立执行会话"（§3.1）。
    # W3-2③：映射命中且路由无在途会话时也走建立（以 host 身份接管路由）。
    established_facts = None
    pending = None
    resolution = None
    explicit = ctx.explicit_session()
    if explicit is None:
        resolution = ctx._auto_resolve()
        if resolution["state"] == "no_session":
            pending = _session_like("wf", {"issued_id": uuid.uuid4().hex})
        elif resolution["state"] == "host_establish":
            evidence = resolution.get("evidence") or {}
            pending = _session_like("host", {"host_id": evidence.get("host_id"),
                                             "session_id": evidence.get("session_id")})
    if pending is not None:
        # 首次/接管形态：前置在写盘前跑；锚点冲突不阻断——建立本来就接管同锚点路由
        # （`established.route_taken_over_from` 如实报让出来源）。
        guards = _enable_guards(ctx, pending)
        host_establish = None
        if pending["provider"] == "host":
            host_establish = dict(pending["identity"])
        established_facts = _establish_auto_session(
            ctx, host_establish=host_establish,
            identity=(pending["provider"], pending["identity"]))
        renewed = False
    else:
        # 续用分支：身份来自显式信封，或解析出的附件；stale 激活由本命令续期。
        base = explicit or (resolution or {}).get("attachment") or {}
        session_key = (session_mod.session_key(explicit) if explicit is not None
                       else (resolution or {}).get("key"))
        guards = _enable_guards(ctx, _session_like(base.get("provider"), base.get("identity")))
        conflict = _anchor_conflict(ctx, session_key)
        if conflict and choice is None:
            raise CliError(
                "WF_IDENTITY_UNRESOLVED",
                {"host_session_key": session_key, "anchor_conflict": conflict,
                 "exits": ["wf enable --identity host（确认以宿主标识为准并钉住）",
                           "换新终端/新会话后重试"]},
                next_="人确认本次会话身份来源；不以锚点或环境变量猜",
            )
        attachment, renewed = _renew_activation(ctx, session_key, base)
    session = ctx.session()
    session_key = ctx.key(required=False)
    identity_facts = _identity_facts(ctx, session_key)
    if renewed:
        identity_facts["activation_renewed"] = True
    if choice == "host":
        _pin_identity(ctx, session_key, identity_facts)
        identity_facts["pinned"] = True
    state = guards["trellis"]
    host_id = state["host_id"]
    applicable = [item for item in state["host_files"] if item["host"] == host_id]
    disabled = bool((ctx.inputs() or {}).get("trellis_disabled_confirmed"))
    warnings = _identity_warnings(identity_facts, state, applicable, disabled)
    # 首次启用时调用方通常还没带 activation：这里给出**可直接缓存的模板**，
    # 由适配层在后续每次请求里重放（机制稿 §1.4：由宿主/skill 按本次真实调用形成缓存）
    binding = session_mod.load_binding(ctx.root, session_key)
    # 绑定文件形状可能被写坏（字符串 / 非对象）：存在即算"有绑定"，对象事实按未知报，
    # 不把形状问题落成 AttributeError。`_bound` 才是可安全读的视图。
    _bound = binding if isinstance(binding, dict) else {}
    activation = ctx.activation()
    template = activation or {
        "enabled": True,
        "start_source": "human:enable",
        "enabled_at": records.now_str(),
    }
    # 终态绑定出口（2026-11-21）：绑定对象已到终态是可机械判定的事实——
    # 不让 AI 再查一次 status/run locate 才知道本会话没有可推进对象（dogfood 会话 3/4 卡点）。
    # 任务看 status=archived；实例看 terminal（normal/abnormal 均为终态，四阶段设计稿 §5.9）。
    # 探测失败时标记 unknown 并如实说明，不冒充"未结束"。
    binding_terminal = False
    binding_terminal_unknown = False
    if binding is not None:
        # 与轮换同一判据（session.object_terminal_state）：unknown 只表示无法证明，
        # 出口是核对/恢复，不冒充"已结束"。
        terminal_state = session_mod.object_terminal_state(ctx.root, binding)
        binding_terminal = terminal_state == "terminal"
        binding_terminal_unknown = terminal_state == "unknown"
    return ok(
        facts={
            "session_key": ctx.key(),
            "identity": identity_facts,
            "identity_mode": (session or {}).get("source") == "auto" and "auto" or "explicit",
            "activation": template,
            "activation_source": "carried" if activation else "formed_by_enable",
            "cache_hint": "把 facts.activation 原样缓存进本会话，并随每次请求放入 session.activation",
            "binding": ({"object": _bound.get("object"),
                         "instance_id": _bound.get("instance_id"),
                         "terminal": binding_terminal,
                         "terminal_state": ("archived-or-terminated" if binding_terminal
                                            else "unknown" if binding_terminal_unknown else "active")}
                        if binding is not None else None),
            "platforms": ctx.platforms(),
            "trellis_data": state["data"],
            "trellis_disabled_confirmed": disabled,
            # W3-2③：建立/接管事实透传（旧会话路由让出须可见，不静默丢弃）
            **({"established": established_facts} if established_facts else {}),
        },
        position=codes.position(scope="session"),
        next_=(("绑定的对象已到终态：本会话不能继续推进它。"
                "同边界开新对象用 `wf enable --new-session` 换新会话后 task-new；"
                "或开新执行边界/新会话（同进程无法区分时开新终端）" if binding_terminal else
                "绑定对象状态暂无法确认：先跑 `status`（任务）或 `run locate`（实例）核实后再决定；"
                "不据猜测推进" if binding_terminal_unknown else
                "已绑定对象：继续当前对象；要开新任务请在新执行边界/新会话里选择"
                "（同进程内无法区分时开新终端）") if binding is not None
               else "人显式选择对象：task-new、bind --task，或 run create"),
        warnings=warnings,
    )


def _runtime_current_task(ctx, kind, target):
    """运行态缓存里的 `current_task`：任务绑定就是它本身；实例绑定取实例游标所指的任务。"""
    if kind == "task":
        return target
    from . import runs as runs_mod

    run = runs_mod.load_run(ctx.root, target) or {}
    return (run.get("cursor") or {}).get("task_id")


def _eligible_run_bind(ctx, run_id):
    """实例绑定的资格（机制稿 §6.1 的绑定面）：实例存在、未终态。

    不核 `cursor.task_id`——那是**推进**的前置（`tasks.bind_task_for_write` 在写入口核），
    绑定只确认"这个会话要接的是哪个在途实例"。已结束的实例不给绑定：正常结束只回报结果，
    异常结束要在新会话绑定**保留任务**（`independent_resume`），不是重新绑这个实例。
    """
    from . import runs as runs_mod

    run = runs_mod.load_run(ctx.root, run_id)
    if not isinstance(run, dict):
        raise CliError("WF_HISTORY_UNRESOLVED",
                       {"reason": "run record missing or unreadable", "run": run_id},
                       next_="只读核对实例记录；不新建同名实例覆盖")
    if run.get("terminal") == "normal":
        raise CliError("WF_BINDING_MISMATCH",
                       {"reason": "run ended normally", "run": run_id},
                       next_="正常结束的实例只回报结果；下一个对象由新会话选择")
    if run.get("terminal") == "abnormal":
        raise CliError("WF_BINDING_MISMATCH",
                       {"reason": "run ended abnormally; bind its retained task instead",
                        "run": run_id, "terminal": "abnormal"},
                       next_="在新会话绑定保留任务（其 task.independent_resume 记录了许可）")
    return {"kind": "run", "id": run_id}


def _eligible_task_bind(ctx, task):
    """独立接续资格（机制稿 §6.1）的绑定面。

    判定本体在 `runs.binding_state`（唯一实现）：本函数只把状态映射成原因码与出口，
    `cmd_ready` 用同一状态做归组与阻断项，两处不各写一套「在途/保留/无许可」的判断。
    """
    from . import runs as runs_mod

    if task.get("status") == "archived":
        raise CliError("WF_BINDING_MISMATCH", {"reason": "task archived", "task": task.get("id")})
    state = runs_mod.binding_state(ctx.root, task)
    kind = state["state"]
    if kind == runs_mod.BINDING_NONE:
        return None
    if kind == runs_mod.BINDING_MISSING:
        raise CliError("WF_HISTORY_UNRESOLVED",
                       {"reason": "run record missing", "run_id": state["run_id"]})
    if kind == runs_mod.BINDING_NORMAL:
        raise CliError("WF_BINDING_MISMATCH",
                       {"reason": "run ended normally", "run_id": state["run_id"]})
    if kind == runs_mod.BINDING_ABNORMAL_LICENSED:
        return state["permission"]
    if kind == runs_mod.BINDING_ABNORMAL_UNLICENSED:
        raise CliError("WF_BINDING_MISMATCH",
                       {"reason": "no independent resume permission", "run_id": state["run_id"]})
    raise CliError(
        "WF_BINDING_MISMATCH",
        {"reason": "task belongs to an in-flight run; bind the run instead", "run_id": state["run_id"]},
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
    session_mod.update_runtime(
        ctx.root,
        key,
        binding_digest=records.plain_digest(binding),
        instance_id=binding.get("instance_id"),
        object=object_ref,
        current_task=_runtime_current_task(ctx, kind, target),
        cursor=None,
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
    target = args.value("--task") or args.value("--run")
    if not target:
        raise CliError("WF_USAGE_INVALID", {"reason": "bind requires --task <id> or --run <id>"})
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
    else:  # 实例绑定：新会话接续在途实例（机制稿 §6.1 的绑定面）
        object_ref = _eligible_run_bind(ctx, target)
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
            session_mod.update_runtime(
                ctx.root,
                key,
                binding_digest=records.plain_digest(binding),
                instance_id=instance_id,
                object=object_ref,
                current_task=_runtime_current_task(ctx, kind, target),
                cursor=None,
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
    raise CliError("WF_USAGE_INVALID", {"reason": "writer requires acquire|release"})


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
        raise CliError(code, platform_facts, next_="install（已装齐全部平台）后重试")


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


def _ensure_run_releasable(ctx, run_id):
    """实例写权释放的前置（机制稿 §4.4 的同一口径）：实例已暂停或已终态，且当前任务无保留 WIP。"""
    from . import runs as runs_mod, tasks as tasks_mod

    run = runs_mod.load_run(ctx.root, run_id)
    if not isinstance(run, dict):
        raise CliError("WF_HISTORY_UNRESOLVED", {"reason": "run record missing", "run": run_id})
    if not run.get("terminal") and not run.get("paused"):
        raise CliError("WF_SEMANTIC_DECISION",
                       {"reason": "release requires a paused or ended instance",
                        "run": run_id, "paused": bool(run.get("paused")),
                        "terminal": run.get("terminal")},
                       next_="先 run pause（或 run terminate / run finish）再释放写权")
    task_id = (run.get("cursor") or {}).get("task_id")
    if not task_id:
        return
    task = tasks_mod.load_task(ctx.root, task_id) or {}
    retained = tasks_mod.wip_paths(task)
    if retained:
        from . import scope as scope_mod

        dirty = set(scope_mod.uncommitted_paths(ctx.root))
        still = [path for path in retained if path in dirty]
        if still:
            raise CliError("WF_WORKSPACE_UNRESOLVED",
                           {"reason": "run task keeps undisposed WIP", "task": task_id,
                            "paths": still},
                           next_="先处置这些路径（提交/反向修正/承接）再释放")


def _release_writer_locked(ctx, holder):
    """释放写权并登记 `writer.release` 动作；调用方必须已持有项目锁。"""
    record = ctx.writer()
    updated = writer_mod.release(record)
    writer_mod.save(ctx.root, updated)
    assertion = _atomic_writer_action(
        ctx,
        updated,
        "writer.release",
        _owner_ref(holder),
        {"session_key": ctx.key()},
        ["verify_scope", "release"],
        lambda current: True,
    )
    return updated, assertion


def _writer_release(ctx):
    # 释放是幂等的：正常归档成功后入口已自动释放，调用方再跑一次不应变成
    # "写权空闲且本会话未持有"的需人裁决。空闲时只回报事实，不写记录。
    current = ctx.writer()
    if current.get("state") == "idle":
        return ok(
            facts={"already_idle": True, "generation": current.get("generation")},
            next_="写权已空闲；下一对象需在新会话选择",
        )
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
    elif object_ref.get("kind") == "run":
        _ensure_run_releasable(ctx, object_ref.get("id"))
    else:
        raise CliError("WF_BINDING_MISMATCH",
                       {"reason": "bound object is neither task nor run", "object": object_ref})
    with _lock(ctx.root, hint="writer release"):
        # 锁内重新执行完整核验：状态、持有者、范围与代次（机制稿 §4.2）
        ctx.require_held()
        updated, assertion = _release_writer_locked(ctx, holder)
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
    raise CliError("WF_USAGE_INVALID", {"reason": "writer-handover requires begin --to <session-key>|accept"})


def _handover_begin(ctx, args):
    receiver = args.value("--to")
    decision_path = args.value("--decision")
    if not receiver or not decision_path:
        raise CliError("WF_USAGE_INVALID", {"reason": "handover begin requires --to <session-key> --decision <path>"})
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

# 决定文件的必填键（唯一事实源，2026-11-21 从 _load_decision 局部元组上升为模块常量）：
# 预检、草稿生成（archive --draft）与帮助断言共用；测试不再 import 私有函数或抄清单。
DECISION_FIELDS = ("source", "at", "subject", "object_digest", "choice", "reason")


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
        missing = [key for key in DECISION_FIELDS if key not in item]
        if missing:
            raise CliError("WF_RECORD_INVALID", {
                "reason": "decision missing fields", "missing": missing,
                "field_notes": {"at": f"人答复时刻（ISO8601）；无法确知时写当前时刻 {records.now_str()}",
                                "artifacts": "批准类必填：{路径: 摘要}，取 task-approve --draft 的预填值；"
                                             "缺或与当前产物不符都会被拒（expected_artifacts 为准）",
                                "object_digest": "按决定语义填写（task-approve 是当前 PRD 的 sha256，"
                                                 "值必填——缺/不符即 WF_APPROVAL_MISSING；"
                                                 "archive/stop 仅要求字段存在）"},
                "required_fields": list(DECISION_FIELDS),
            })
        if not item.get("choice"):
            raise CliError("WF_RECORD_INVALID", {"reason": "decision choice is empty"})
        # 值形态校验（2026-11-21 五轮审查 P2-11）：占位文案照抄进记录会污染时间排序与摘要比对。
        at_value = str(item.get("at") or "")
        if not re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$", at_value):
            raise CliError("WF_RECORD_INVALID", {
                "reason": "decision at must be ISO8601 (YYYY-MM-DDTHH:MM:SS…)",
                "value": at_value[:80],
                "exits": [f"写人答复时刻；无法确知时写当前时刻 {records.now_str()}"]})
        digest_value = str(item.get("object_digest") or "")
        if digest_value and not re.match(r"^sha256:[0-9a-f]{64}$", digest_value):
            raise CliError("WF_RECORD_INVALID", {
                "reason": "decision object_digest must be 'sha256:' + 64 hex chars (or empty when the command allows)",
                "value": digest_value[:80],
                "exits": ["按决定语义填写：approve=PRD 摘要（错误回显 expected_prd_digest）",
                          "archive/stop 可留空"]})
        if not str(item.get("reason") or "").strip():
            raise CliError("WF_RECORD_INVALID", {"reason": "decision reason is empty",
                                                 "exits": ["写明为什么这样处置（人可读的理由）"]})
        # 十轮审查 P2-3：草稿占位（TODO 前缀）不得照抄进决定——
        # "人已了解结果与未核实项 / 为什么这样处置"正是决定存在的理由，占位句不算人签字。
        todo_fields = [key for key in DECISION_FIELDS
                       if str(item.get(key) or "").strip().startswith("TODO")]
        if todo_fields:
            raise CliError("WF_RECORD_INVALID",
                           {"reason": "decision still carries draft placeholders (TODO)",
                            "todo_fields": todo_fields,
                            "exits": ["把 TODO 占位逐项替换为人的真实表述后重试",
                                      "来源写 human:<来源>；理由/结论写人可读的原文"]})
        decisions.append(item)
    return decisions


def _irreversible_projection(root, task):
    """本次拟提交会触发的 K6 不可逆确认与缺口（与归档门禁同源，预览/草稿共用）。

    十轮审查 P1-1：输入集合与归档守卫一致——守卫核的是 `grant_paths`（提交授权路径）
    的规则文件命中与未提交删除；预览尚无决定文件时按"待提交路径 ∪ 已登记提交授权"
    投影同一集合（repo_rule_paths / _deleted_paths 同一实现，不另写口径）。
    计算失败显式标 unavailable（不与"确实没有"混同，§1.5 降级可见）。
    """
    from . import authorize as authorize_mod
    from . import tasks as tasks_mod

    unavailable = []
    try:
        _pending = tasks_mod.pending_delivery_paths(
            type("C", (), {"root": str(root)})(), task) or []
        grant_paths = sorted(set(_pending) | set(tasks_mod.commit_grant_paths(task) or []))
    except Exception as exc:  # noqa: BLE001 — 只读投影失败不阻断预览，但必须可见
        return {"repo_rule_files": [], "deleted_paths": [], "missing_authorizations": [],
                "unavailable": f"拟提交路径不可得：{exc}",
                "exits": ["先跑 `status`/`stop --preview` 的 buckets 确认交付面后重试"]}
    rule_hits, deleted = [], []
    try:
        # 真上下文（十一轮 a P1-1 附带）：不传 None——helper 现在恰好不读 ctx，
        # 一旦读取会被外层 except 折成"不可得"预览静默降级。
        rule_hits = authorize_mod.repo_rule_paths(
            type("C", (), {"root": str(root)})(), grant_paths)
    except Exception as exc:  # noqa: BLE001
        unavailable.append(f"规则文件命中不可得：{exc}")
    try:
        deleted = tasks_mod._deleted_paths(str(root), grant_paths)
    except Exception as exc:  # noqa: BLE001
        unavailable.append(f"删除路径不可得：{exc}")
    missing = []
    task_dir = tasks_mod.task_dir(str(root), task.get("id"))
    if rule_hits:
        covered, uncovered = authorize_mod.covers(task_dir, "repo_rules", rule_hits, root=str(root))
        if not covered:
            missing.append({"action": "repo_rules", "paths": uncovered,
                            "exits": ["把人的确认写成文件（choice=repo_rules + paths + quote/by/source），"
                                      "经 `wf authorize record --task <id> --file <文件>` 登记后重入"]})
    if deleted:
        covered, uncovered = authorize_mod.covers(task_dir, "delete", deleted, root=str(root))
        if not covered:
            missing.append({"action": "delete", "paths": uncovered,
                            "exits": ["删除须在删除前确认：`authorize record` 一条 choice=delete"
                                      "（paths 覆盖被删路径，绑定被删内容）"]})
    payload = {"repo_rule_files": rule_hits, "deleted_paths": deleted,
               "missing_authorizations": missing}
    if unavailable:
        payload["unavailable"] = "; ".join(unavailable)
    # 三轮二审：单 reviewer 留痕降级随收工预览上抛——人判点必须看到"这轮是接受过
    # 残余风险的单 reviewer 审查"，不能只看 verdict=pass（与放行清单 unknown_acceptances 同型）。
    try:
        _result = ((task.get("reviews") or {}).get("result") or {})
        if (_result.get("verdict") in ("pass", "fail")
                and (_result.get("facts") or {}).get("degraded") == "single-provider"):
            payload["review_degraded"] = {
                "kind": "single-provider",
                "accepted": (_result.get("facts") or {}).get("single_reviewer_accepted"),
                "note": "本轮审查为人签残余风险接受的单 reviewer 留痕降级（非两异种 reviewer）",
            }
    except Exception:   # noqa: BLE001 — 投影失败不阻断预览
        pass
    return payload


def cmd_stop(ctx, args):
    path = args.value("--decision")
    if args.flag("--draft"):
        # 十六轮批V：收工决定草稿——commit 条目的 subject 预填待提交路径，
        # choice/reason 由人定（TODO 占位，照抄会被预检拒）；不要求写权，只读绑定。
        import os as _os

        binding = session_mod.load_binding(ctx.root, ctx.key())
        object_ref = (binding or {}).get("object") or {}
        if object_ref.get("kind") != "task":
            raise CliError("WF_BINDING_MISMATCH",
                           {"reason": "no task binding for stop draft",
                            "exits": ["先由人调用 start/`wf.py enable` 建立会话并绑定任务"]})
        from . import tasks as _tasks_mod

        task = _tasks_mod.load_task(ctx.root, object_ref.get("id"))
        if task is None:
            raise CliError("WF_RECORD_INVALID", {"missing_task": object_ref.get("id")})
        pending = _tasks_mod.pending_delivery_paths(
            type("C", (), {"root": ctx.root})(), task) or []
        entry = {"source": "TODO human:<来源>", "at": records.now_str(),
                 "subject": pending or "TODO（人填写：处置对象或路径）",
                 "object_digest": "", "choice": "TODO（人选一个：commit|keep|reverse|transfer）",
                 "reason": "TODO（人填写：为什么这样处置）"}
        return ok(facts={"draft": [entry],
                         "note": "草稿只读；choice 是人的选择，照抄 TODO 会被预检拒绝",
                         "pilot_sampling_pending": None},
                  position=codes.position(scope="task", phase=task.get("phase"),
                                         task_id=task.get("id")),
                  next_="草稿只打印不落盘；人确认后把内容写成决定文件，去掉 --draft 重跑")
    if args.flag("--preview"):
        # 只读预览（设计稿 §4.4）：**免决定**——预览与决定的顺序是"先看再定"，
        # 对齐 archive --draft 的只读语义（在 _load_decision 之前返回，不写任何记录、
        # 不要求写权）。带了 --decision 时一并显示拟用处置；不带则 choice 为 null。
        choice = None
        if path:
            decisions = _load_decision(path)
            _choices = [item.get("choice") for item in decisions]
            if not _choices:
                raise CliError("WF_SEMANTIC_DECISION", {"reason": "收工决定文件为空，需要一条 choice",
                                                        "choices": [],
                                                        "accepted": list(decisions_mod.domain("stop_choice"))})
            if not decisions_mod.accepts("stop_choice", _choices[0]):
                raise CliError("WF_SEMANTIC_DECISION", {"choices": _choices, "reason": "收工选择必须是 commit/keep/reverse/transfer"})
            choice = _choices[0]
        from . import scope as scope_mod

        binding = session_mod.load_binding(ctx.root, ctx.key())
        object_ref = (binding or {}).get("object") or {}
        if object_ref.get("kind") != "task":
            raise CliError("WF_BINDING_MISMATCH",
                           {"reason": "no task binding for stop preview",
                            "exits": ["先由人调用 start/`wf.py enable` 建立会话并绑定任务，或 `bind --task <id>`",
                                      "确认要预览的是哪个任务后重试"]})
        from . import tasks as tasks_mod

        task = tasks_mod.load_task(ctx.root, object_ref.get("id"))
        if task is None:
            raise CliError("WF_RECORD_INVALID", {"missing_task": object_ref.get("id")})
        classified = scope_mod.classify_candidates(ctx.root, task)
        facts = {
            "task": {"id": task.get("id"), "phase": task.get("phase"), "title": task.get("title")},
            "choice": choice,
            "buckets": classified.get("buckets"),
            "uncommitted": sorted(scope_mod.uncommitted_paths(ctx.root)),
            "note": "预览只读；本次未写入任何记录",
        }
        # P1-1（九轮）：不可逆确认投影——提交会触发哪类 K6 确认、缺哪条 record，
        # 在"先看后定"的决策位就要给（不要等 archive 拒绝时才暴露）。
        facts["irreversible"] = _irreversible_projection(ctx.root, task)
        # b-1（九轮，事实不阻断）：开工前已存在的交付路径——归属要人确认
        if classified.get("preexisting_in_scope"):
            facts["preexisting_in_scope"] = classified["preexisting_in_scope"]
        # §0.2 试点期抽样提示（2026-11-21 降档为建议，不阻断；无 picks 时附注）
        from . import sampling as sampling_mod

        if not sampling_mod.selection(task)["picks"]:
            facts["pilot_sampling_pending"] = True
        return ok(facts=facts, position=codes.position(scope="task", phase=task.get("phase"),
                                                       task_id=task.get("id")),
                  next_="按预览结果选定处置后写决定文件，去掉 --preview 重跑"
                        + ("；" + sampling_mod.PILOT_HINT
                           if facts.get("pilot_sampling_pending") else ""))
    if not path:
        raise CliError("WF_USAGE_INVALID", {"reason": "stop requires --decision <path>"})
    decisions = _load_decision(path)
    choices = [item.get("choice") for item in decisions]
    if not choices:
        # 空决定文件是业务输入错误，不能走到 IndexError/退出 70（第二十五轮复审外部 2）
        raise CliError("WF_SEMANTIC_DECISION", {"reason": "收工决定文件为空，需要一条 choice",
                                                "choices": [],
                                                "accepted": list(decisions_mod.domain("stop_choice"))})
    if not decisions_mod.accepts("stop_choice", choices[0]):
        raise CliError("WF_SEMANTIC_DECISION", {"choices": choices, "reason": "收工选择必须是 commit/keep/reverse/transfer"})
    from . import tasks as tasks_mod

    return tasks_mod.stop_work(ctx, decisions, choices[0])


def cmd_ready(ctx, args):
    """就绪视图（设计稿 §5.6 / §5.1）：无绑定新会话按创建时间给出最早就绪建议。

    只读：不写任何判定字段。每个活动/暂停任务给出 eligible（独立接续资格）、
    ready（能否直接开工）与 blockers；suggested 取 ready 中创建时间最早的一个。
    """
    from . import tasks as tasks_mod

    from . import runs as runs_mod

    entries = []
    run_of = {}
    unreadable_runs = []
    run_records = []
    for record, path in runs_mod.iter_runs(ctx.root):
        if not isinstance(record, dict):
            unreadable_runs.append(os.path.relpath(path, str(ctx.root)).replace(os.sep, "/"))
            continue
        run_records.append(record)
    for _path, task in tasks_mod.iter_tasks(ctx.root):
        if task.get("status") == "archived":
            continue
        if task.get("run_id"):
            run_of[task.get("id")] = task.get("run_id")
        blockers = []
        try:
            _eligible_task_bind(ctx, task)
        except CliError as exc:
            blockers.append(exc.code)
            # 实例轴上的细分事实：`WF_BINDING_MISMATCH` 同时覆盖在途实例、正常结束、
            # 无许可的异常结束，人看不出该找实例还是该走 repair（机制稿 §6.1）
            state = runs_mod.binding_state(ctx.root, task)
            if state["state"] == runs_mod.BINDING_IN_FLIGHT:
                blockers.append("run_in_flight")
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

    # 实例归组（机制稿 §6.1）：人要先看清「这些任务属于哪个实例、那个实例到哪一步」，
    # 才知道该绑实例还是绑普通任务。只做实例归组——**不按子仓库归组**：嵌套仓库是
    # charter T3 B2 的硬边界（触碰面、spec 与检查对象一律以本仓库工作树为界）。
    by_run = {}
    for task_id, run_id in run_of.items():
        by_run.setdefault(run_id, []).append(task_id)
    groups = []
    for record in run_records:
        run_id = record.get("id")
        groups.append({
            "run_id": run_id,
            "workflow_id": record.get("workflow_id"),
            "terminal": record.get("terminal"),
            "paused": record.get("paused"),
            "tasks": sorted(by_run.pop(run_id, [])),
        })
    for run_id in sorted(by_run):
        # 悬空的 run_id 不静默丢弃：它可能正是「记录被移动/删除」的现场
        groups.append({"run_id": run_id, "workflow_id": None, "terminal": None,
                       "paused": None, "tasks": sorted(by_run[run_id]),
                       "unknown": "run record missing or unreadable"})

    # 实例作为**可绑定候选**（`bind --run` 交付后）：人要先看到"这个实例现在能不能接"，
    # 而不只是"这个实例下有哪些任务"。资格与阻断项按 `_eligible_run_bind` 的同一判据。
    run_candidates = []
    for record in run_records:
        run_id = record.get("id")
        blockers_for_run = []
        try:
            _eligible_run_bind(ctx, run_id)
        except CliError as exc:
            blockers_for_run.append(exc.code)
        if record.get("paused"):
            blockers_for_run.append("paused")
        run_candidates.append({
            "id": run_id,
            "workflow_id": record.get("workflow_id"),
            "terminal": record.get("terminal"),
            "paused": record.get("paused"),
            "created_at": (record.get("creation_decision") or {}).get("at"),
            "steps_settled": sorted((record.get("step_results") or {}).keys()),
            "ready": not blockers_for_run,
            "blockers": blockers_for_run,
        })
    run_candidates.sort(key=lambda item: (str(item.get("created_at") or ""), str(item.get("id") or "")))
    suggested = next((item["id"] for item in entries if item.get("ready")), None)
    suggested_run = next((item["id"] for item in run_candidates if item.get("ready")), None)
    facts = {"tasks": entries, "suggested": suggested,
             "run_candidates": run_candidates, "suggested_run": suggested_run,
             "runs": groups}
    warnings = []
    if unreadable_runs:
        warnings.append({"area": "runs", "unreadable": unreadable_runs})
    return ok(
        facts=facts,
        position=codes.position(scope="session"),
        next_=("用 bind --task <id> 绑定建议任务，或用 bind --run <id> 接续在途实例"
               "（见 run_candidates.suggested_run）；或按 blockers 先解除阻断"),
        warnings=warnings,
    )


def cmd_spec(ctx, args):
    path = args.value("--file")
    if not path:
        raise CliError("WF_USAGE_INVALID", {"reason": "spec requires --file <RepoPath>"})
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


# `definition` 与 `run` 的子动作均由 runs.py 承接；不可用分支由对应 handler 抛 `WF_CAPABILITY_UNAVAILABLE`
SUBACTIONS = {
    "definition": ("prepare", "validate"),
    "run": ("create", "advance", "pause", "resume", "locate", "terminate", "finish"),
}


def _runs_command(prefix):
    """`definition <子动作>` 的分派：子动作取自位置参数，处理器固定在该模块里。"""

    def handler(ctx, args):
        from . import runs as runs_mod

        sub = (args.positional() or [None])[0]
        if sub not in SUBACTIONS[prefix]:
            raise CliError("WF_PATH_INVALID",
                           {"reason": f"{prefix} requires a subaction: "
                                      f"{'|'.join(SUBACTIONS[prefix])}", "got": sub})
        return getattr(runs_mod, sub)(ctx, args)

    # 委托目标自省（2026-11-23）：子动作 → 真实实现。与 `_task_command` 的 `__wf_target__`
    # 同一用途——帮助/注册表与"真实消费"的一致性断言必须能定位到真正读参数的函数，
    # 否则断言对委托型命令只是空跑（dogfood 五轮发现的盲区）。
    handler.__wf_target_map__ = {sub: f"runs:{sub}" for sub in SUBACTIONS[prefix]}
    return handler


def _task_command(name):
    def handler(ctx, args):
        from . import tasks as tasks_mod

        return getattr(tasks_mod, name)(ctx, args)

    handler.__wf_target__ = f"tasks:{name}"
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
            # `--launch-request` 可选：三类材料/只读范围/排除面由入口按当前对象生成；
            # 给了就作为覆盖/补充（例如人工缩小材料面）。
            # `--preview`（三轮三审 b8）：只读回显生成后的请求与外发授权状态，
            # 不落盘、不启动轮次——人签 export 前先看到将外发的路径清单。
            if args.flag("--preview"):
                try:
                    facts = review_mod.launch_preview(ctx, task, args.value("--launch-request"),
                                                      implementation_cli=args.value("--implementation-cli"))
                except review_mod.ReviewError as exc:
                    raise CliError(exc.code, exc.facts)
                return codes.result(
                    "WF_OK", object={"id": task.get("id"), "name": task.get("title")},
                    position_=codes.position(scope="task", phase=task.get("phase"), task_id=task.get("id")),
                    next_=("外发授权已入库：可直接 review-launch" if facts["export_authorization"]["recorded"]
                           else "先 authorize record choice=export（人核对 preview 的路径清单后签）再 review-launch"),
                    facts=facts,
                )
            try:
                return review_mod.launch(ctx, task, args.value("--launch-request"),
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
        draft = args.value("--main-review-draft")
        if draft:
            try:
                facts = review_mod.main_review_draft(ctx, task, int(round_no) if round_no else None, draft)
                return codes.result(
                    "WF_OK",
                    object={"id": task.get("id"), "name": task.get("title")},
                    position_=codes.position(scope="task", phase=task.get("phase"), task_id=task.get("id")),
                    next_="填五轴结论/依据、逐报告信赖度与逐 finding 复核后，用 --main-review <同一文件> 重跑",
                    facts=facts,
                )
            except review_mod.ReviewError as exc:
                raise CliError(exc.code, exc.facts)
        plan_draft = args.value("--plan-draft")
        if plan_draft:
            # 五轮审查 b5 尾项：处置数组只读骨架——当前轮未关闭 blocking 逐条占位，
            # decision=TODO 占位照抄会被 dispositions 校验拒（decision 只认 accepted/rejected/amended）
            from . import review as _review_mod

            _open = _review_mod.open_findings(ctx, task)["blocking"]
            skeleton = [{"finding_id": item.get("id"),
                         "decision": "TODO（accepted|rejected|amended——只有 accepted 关闭）",
                         "reason": "TODO（处置依据：已修复并重查通过 / 经复核认定误报 / 已重分类）",
                         "recheck_by": "TODO human:<来源>（不得等于提出者槽位）"}
                        for item in _open]
            if not skeleton:
                skeleton = [{"finding_id": "TODO（无未关闭 blocking 时本文件不需要）",
                             "decision": "TODO", "reason": "TODO", "recheck_by": "TODO"}]
            return codes.result(
                "WF_OK", object={"id": task.get("id"), "name": task.get("title")},
                position_=codes.position(scope="task", phase=task.get("phase"), task_id=task.get("id")),
                next_="逐条填完后存成 JSON 数组，用 --plan <文件> 随 review-decide 提交",
                facts={"draft": skeleton, "open_blocking": len(_open)},
            )
        acceptance_draft = args.value("--single-reviewer-acceptance-draft")
        if acceptance_draft:
            # 三轮三审 b9：单 reviewer 接受文件只读骨架（与其他 --draft 同型，只打印不落盘）
            _launches = [entry for entry in ((task.get("reviews") or {}).get("launches") or [])
                         if isinstance(entry, dict)]
            _round = int(round_no) if round_no else (max((int(e.get("round") or 0) for e in _launches),
                                                         default=0))
            skeleton = {"by": "TODO human:<来源>", "at": records.now_str(),
                        "quote": "TODO（人填写：接受只审一遍的原话）",
                        "source": "user-declared",
                        "residual_risk": "TODO（人填写：接受的残余风险具体是什么）",
                        "round": _round, "task": task.get("id")}
            return codes.result(
                "WF_OK", object={"id": task.get("id"), "name": task.get("title")},
                position_=codes.position(scope="task", phase=task.get("phase"), task_id=task.get("id")),
                next_="人填 TODO 后存成文件，用 --single-reviewer-acceptance <文件> 判定",
                facts={"draft": skeleton},
            )
        try:
            return review_mod.decide(ctx, task, int(round_no) if round_no else None,
                                     args.value("--plan"), args.value("--unavailable"),
                                     register_only=args.flag("--register-only"),
                                     gap_acceptance_path=args.value("--gap-acceptance"),
                                     main_review_path=args.value("--main-review"),
                                     single_reviewer_acceptance_path=args.value("--single-reviewer-acceptance"))
        except review_mod.ReviewError as exc:
            raise CliError(exc.code, exc.facts)

    return handler


def cmd_confirm_executor(ctx, args):
    raise CliError(
        "WF_CAPABILITY_UNAVAILABLE",
        {"reason": "confirm-executor is handled by the bootstrap layer (.wf/bin/wf.py)"},
        next_="直接运行 wf.py confirm-executor --scope system|global|project",
    )


# 帮助里的取值域由 `decisions.DOMAINS` 生成（唯一登记处）：dogfood 里 `approve-light`/
# `mechanical` 的残留就是帮助与登记域各写一份造成的。
PLAN_APPROVAL_CHOICES = "|".join(decisions_mod.DOMAINS["plan_approval"])
MECHANICAL_REVISION_CHOICES = "|".join(decisions_mod.DOMAINS["mechanical_revision"])

COMMAND_HELP = {
    "task-new": {
        "purpose": "建任务（ordinary/initialize/bootstrap）并取得写权与绑定",
        "args": {"--kind": "ordinary|initialize|bootstrap（必填）", "--title": "标题（必填）",
                 "--template": "<项目根>/.wf/templates/task（必填）"},
        "example": "wf.py task-new --kind ordinary --title \"补边界用例\" --template .wf/templates/task --json",
    },
    "task-approve": {
        "purpose": "记录人的规划批准（含复杂度与 TDD 的人工确认）",
        "args": {"--task": "任务 id（必填）", "--decision": "决定文件（必填，JSON 数组）",
                 "--draft": "只读生成批准决定草稿：先按正式入口同判据预检 PRD（模板/plan 块/占位/"
                            "touch_paths，不合格拒绝并给问题清单），通过后 object_digest 预填当前 PRD 摘要；"
                            "TODO 占位须人替换"},
        "inputs": {"decision[]": {"source": "人答复来源（必填）", "at": "时间（必填）",
                                  "subject": "人读的线索，**必须含任务 id**：摘要只绑内容，"
                                             "两份字节相同的 PRD 靠它区分任务（次级绑定，不是替代摘要）",
                                  "artifacts": "**必填**（0.0.1 起）：`{路径: 摘要}`，草稿按当时 "
                                               "prd/design/implement 预填。核当前值且必须覆盖当前产物集——"
                                               "产物被改、被删或**新增**都算没看过，一律拒；"
                                               "0.1.7 及更早的决定重导会被拒，按 `expected_artifacts` 补即可",
                                  "object_digest": "当前 PRD 的 sha256（**值必填**：缺或不等即 "
                                                   "WF_APPROVAL_MISSING 并回显 expected_prd_digest；"
                                                   "入口不代填——人对 PRD 的批准留痕不可替代；"
                                                   "`--draft` 预填）",
                                  "choice": f"批准：{PLAN_APPROVAL_CHOICES}；"
                                            f"机械修订：{MECHANICAL_REVISION_CHOICES}（必填）",
                                  "生成代次": "inputs.generation 可显式覆盖；缺省取本会话运行态记录的代次"
                                            "（取得写权时写入）。过期会报 WF_GENERATION_STALE 并给 current_generation",
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
                   "args": {"--task": "任务 id（必填）",
                            "--workspace-exclusion": "外来改动排除声明文件：数组元素 {choice: \"排除外来改动\", paths: [具体路径], by: \"human:<来源>\", at, quote, source: \"user-declared\"}（人确认不属于本任务；按记录时摘要绑定，内容一变即失效）"},
                   "example": "wf.py task-start --task <id> --json"},
    "task-check": {
        "purpose": "按批准验证实际执行并写 check 结果（复杂任务还需双轴内部审查）",
        "args": {"--task": "任务 id（必填）", "--review-notes": "双轴内部审查结论 JSON（复杂任务必填；放在当前任务目录内——用 `wf.py status` 回显的 directory（形如 `<id>-<slug>`），如 .wf/tasks/<id>-<slug>/notes.json；放错目录会被当成外来改动）",
                 "--review-notes-draft": "只读生成双轴审查结论骨架（打印目标路径与 TODO，不落盘、不要求写权）",
                 "--decision": "可选：决定文件（数组，每条仍须满足 Decision 六字段）。除人工验收决定外还承载重复调试两处落账——"
                               "声明 subject `debug-declaration:<verification_id>:count=<n>[:dedupe=<check_id>/<vid>,…][:evidence=<ref>,…]`、"
                               "裁定 subject `debug-ruling-<verification_id>-<multiple>`（choice=同一问题/不同问题，主会话按根因裁定，依据与证据入 reason；"
                               "未跨阈值倍数前无需裁定）",
                 "--workspace-exclusion": "外来改动排除声明文件：数组元素 {choice: \"排除外来改动\", paths: [具体路径], by: \"human:<来源>\", at, quote, source: \"user-declared\"}（人确认不属于本任务；按记录时摘要绑定，内容一变即失效）"},
        "inputs": {"--review-notes": {"standard": {"conclusion": "pass|fail|undecided", "basis": "依据"},
                                      "requirement": {"conclusion": "pass|fail|undecided", "basis": "依据"}}},
        "example": "wf.py task-check --task <id> --review-notes notes.json --json",
    },
    "task-knowledge": {"purpose": "记录知识处置（可判无更新）",
                       "args": {"--task": "任务 id（必填）", "--decision": "no-update|updated",
                                "--no-update": "简写：等价于 --decision no-update",
                                "--changes": "updated 时的知识变更清单 JSON 数组"
                                             "（字段是 action/path/reason/summary；与本框架 "
                                             "`spec-update --changes` 的 operation/new_paths 形状**不同**，"
                                             "两者不可互填）",
                                "--changes-draft": "只读生成 changes 骨架（打印目标路径与 TODO，不落盘）"},
                       "inputs": {"--changes[]": {"action": "add|update|merge|rename|delete",
                                                  "path": "spec 相对路径", "reason": "变更理由",
                                                  "summary": "≤80 字摘要"}},
                       "example": "wf.py task-knowledge --task <id> --decision updated --changes changes.json --json",
                       "changes_example": [{"action": "update", "path": ".wf/spec/guides/x.md",
                                            "reason": "补充本轮新契约", "summary": "新增骨架预填口径"}]},
    "stop": {"purpose": "收工：先 --preview 看逐路径归属，再按处置执行",
             "args": {"--decision": "决定文件（正式执行必填；--preview/--draft 可不带）",
                      "--preview": "只读预览（不写任何记录、不要求写权）",
                      "--draft": "只读生成收工决定草稿（commit 条目预填待提交路径）"},
             "inputs": {"decision[]": {"choice": "commit|keep|reverse|transfer",
                                       "subject": "路径或承接对象", "reason": "理由",
                                       "object_digest": "可选"}},
             "example": "wf.py stop --decision stop.json --preview --json",
             "example_file": [{"source": "human:chat", "at": "2026-11-21T10:00:00+08:00",
                               "subject": ["src/a.py", "tests/test_a.py"], "object_digest": "",
                               "choice": "commit", "reason": "授权提交以上交付路径"}]},
    "archive": {"note": "commit 的 subject 可写数组，或用逗号/分号/换行/空格分隔的多路径字符串",
"purpose": "正常归档（最终门禁 + 提交授权）",
                "args": {"--task": "任务 id（必填）", "--decision": "决定文件（必填）",
                         "--draft": "只读生成决定文件草稿（免 --decision，不要求写权与绑定；"
                                    "人确认后把草稿写成决定文件即授权）"},
                "inputs": {"decision[]": "至少一条 choice=finish；提交需 choice=commit 的授权条目"},
                "example": "wf.py archive --task <id> --decision finish.json --json",
                "example_file": [
                    {"source": "human:chat", "at": "2026-11-21T10:00:00+08:00",
                     "subject": "t-20261121-1 已了解结果与未核实项", "object_digest": "",
                     "choice": "finish", "reason": "结果符合预期，未核实项已在 next 声明"},
                    {"source": "human:chat", "at": "2026-11-21T10:00:00+08:00",
                     "subject": ["src/a.py", "tests/test_a.py"], "object_digest": "",
                     "choice": "commit", "reason": "授权提交以上交付路径"}],
                "draft_example": "wf.py archive --task <id> --draft --json"},
    "baseline-apply": {"purpose": "把已批准提案成组应用到基线/配置/spec",
                       "args": {"--task": "任务 id（必填）",
                                "--preview": "只读：按 --files 生成提案摘要供人批准，不落盘",
                                "--files": "逗号分隔的路径（推荐：由入口读工作树生成提案）",
                                "--decision": "人的批准决定文件（与 --files 一起用）",
                                "--proposal": "既有格式的提案 JSON（可选，兼容）"},
                       "inputs": {"--proposal": {"files": "[{path, before, content}]",
                                                 "approval": "{choice, subject} 人的批准引用"}},
                       "example": "wf.py baseline-apply --task <id> --proposal proposal.json --json"},
    "spec-update": {"purpose": "spec 增改删/合并/停用，并同步三段索引",
                    "args": {"--task": "任务 id（必填）",
                             "--changes": "变更数组（必填；--changes-draft 时除外）"
                                          "（字段是 operation/new_paths/old_paths/content；"
                                          "与 `task-knowledge --changes` 形状不同，不可互填）",
                             "--changes-draft": "只读生成 changes 骨架（打印目标路径与 TODO，不落盘）"},
                    "inputs": {"--changes[]": {"operation": "add|update|merge|rename|delete|disable",
                                               "new_paths": "新路径（数组或逗号/分号/空白分隔的字符串，单条可直写字符串）",
                                               "old_paths": "旧路径（同上：数组或分隔字符串）",
                                               "content": "add/update 时的完整正文（含 frontmatter）"}},
                    "example": "wf.py spec-update --task <id> --changes changes.json --json"},
    "review-launch": {"purpose": "发起一轮审查（默认要两份；实施 CLI 由 --implementation-cli 声明）",
                      "args": {"--task": "任务 id（必填）",
                               "--implementation-cli": "本次实施所用 CLI（必填，异种审查的判定输入）",
                               "--launch-request": "可选：覆盖/补充入口自动生成的请求",
                               "--preview": "只读预览：回显生成/合并后的请求与外发授权状态，"
                                            "不落盘、不启动轮次（人签 export 前核对路径清单）"},
                      "inputs": {"--launch-request": {
                          "export_decision": "可选：留痕标签；权威是已入库的外发确认（task + materials）",
                          "submitted_scope": "可选：入口默认生成 {diff:{paths}, requirement, test_results:{check}}；旧请求可省略本参数让入口重建",
                          "reviewers": "可选：要几份审查（默认 2）"}},
                      "example": "wf.py review-launch --task <id> --implementation-cli codex --json"},
    "review-context": {"purpose": "reviewer 侧唯一入口：占位 + 物化材料 + 给出报告路径",
                       "args": {"--task": "任务 id（必填）", "--round": "轮次（缺省＝当前轮）",
                                "--reset": "清掉本 agent 本轮的占位/报告",
                                "--as": "本次审查的 CLI（自动身份模式必填）"},
                       "example": "wf.py review-context --task <id> --round 1 --as pi --json"},
    "review-import": {"purpose": "导入本轮已完成的报告（按文件名发现，免路径）",
                      "args": {"--task": "任务 id（必填）",
                               "--round": "轮次（恢复较早一轮时必须给；缺省取最大发起轮，"
                                          "无报告时 facts.undecided_rounds 列出待处理轮次）",
                               "--slot": "可选（指定某个 agent）",
                               "--report": "可选（显式路径，兼容旧槽位制）",
                               "--as": "可选（显式声明报告署名）",
                               "--restore": "只在恢复**已存在的记录**时用（缺登记摘要的遗留记录重导；"
                                            "保留原登记的报告摘要与材料身份，不按当前材料冒充）"},
                      "example": "wf.py review-import --task <id> --json"},
    "project": {"purpose": "可重建投影（K8）：open-items / attribution / audit / skeleton；--check 断言等值",
                "args": {"--kind": "投影类型（必填）", "--task": "任务 id（必填）", "--check": "断言重建等值"},
                "example": "wf.py project --kind open-items --task 2026-xxxx --check --json"},
    "verify": {"purpose": "未核实项处置（S8/S5b）：resolve 收窄口径或记录人工核验",
               "args": {"resolve": "子命令", "--task": "任务 id", "--id": "验收项 id",
                        "--kind": "narrow|inspection", "--evidence": "证据",
                        "--by": "人工核验的署名（human:<来源>）",
                        "--reason": "收窄理由（narrow 必填）", "--impact": "影响面（narrow 必填）",
                        "--compensation": "补偿措施（narrow 必填）"},
               "example": "wf.py verify resolve --task 2026-xxxx --id a5 --kind narrow --evidence ... --json"},
    "authorize": {"purpose": "K6 不可逆动作的确认入口：record 落盘（脱敏入库）/ show 查看已确认（四类：delete/export/expand/repo_rules；提交授权唯一通道是 finish 决定的 commit_grants）",
                  "args": {"record|show": "子命令", "--task": "任务 id（必填）",
                           "--file": "决定文件（record 必填，每条含 choice∈四类 + quote）",
                           "--draft": "record：只读生成四类确认骨架（TODO 占位，只打印不落盘）"},
                  "example": "wf.py authorize record --task 2026-xxxx --file decisions.json --json"},
    "prefs": {"purpose": "判断偏好（只在本机）：ask_always 强制交人 / ai_decides 自己定",
              "args": {"set|show": "子命令", "--kind": "判断类（归属/关闭/沿用/扩面/标准变更/缺口/未核实/规模/框架改动）",
                       "--value": "ask_always|ai_decides"},
              "example": "wf.py prefs set --kind 标准变更 --value ask_always --json"},
    "sampling": {"purpose": "试点期判断抽样：pick 冻结事件集与种子并选样 / report 出按类统计 / "
                             "evaluate 写人的评估结果 / reviewed 登记人的复核声明（结束强化期）/ confirm 规模确认",
                  "args": {"pick|report|evaluate|reviewed|confirm": "子命令",
                           "--task": "任务 id（必填）",
                           "--freeze": "pick：首次选样前冻结事件集与种子（写任务记录）",
                           "--file": "evaluate：评估 JSON（必填）",
                           "--attestation": "evaluate：人确认凭证（可选）",
                           "--quote": "reviewed：人的声明原文（遮罩摘要入库）"},
                  "example": "wf.py sampling pick --task 2026-xxxx --freeze --json"},
    "judgments": {"purpose": "判断清单：add 追加一条（append-only）/ show 渲染收工预览",
                  "args": {"add|show": "子命令", "--task": "任务 id（必填）", "--file": "判断 JSON（add 必填）",
                           "--attestation": "add：豁免（waived_by=human:…）时的人确认文件",
                                  "--draft": "add：只读生成判断条目骨架（TODO 占位，只打印不落盘）"},
                  "example": "wf.py judgments show --task 2026-xxxx --json",
                  # v42 §4：判断指引写进 skill 与 help，不写进代码逻辑。
                  # 2026-11-12 人裁：**不单独成 skill**——十条散在"用得上它的那一步"的流程 skill 判据位上，
                  # 这里只给「哪条口径在哪」的指针；同一口径的完整论述只写一处，不跨文件复制。
                  "guidance": {
                      "where": "各流程 skill 的判据位点（不另设指引 skill）",
                      "topics": ["交付面 → `wf-continue` 实施期要自己判的几件事",
                                 "扩面（先确认再改）→ `wf-continue` 同上",
                                 "与人的限制冲突（停下报告）→ `wf-continue` 同上 / 各 skill「纪律」",
                                 "blocking 关闭：证据指回问题 → `wf-repair-loop` 0 节",
                                 "报告有效性：沿用必须点名 d: 位置 → `wf-review-action`",
                                 "影响面 / 规模 / 计划没覆盖的缺口 / 未核实项 → `wf-finish` 收工四项",
                                 "标准变更：改的是尺子还是判断 → `wf-spec-update`",
                                 "框架改动（vendor 去向确认，judgments add）→ `wf-continue`「vendor_dirty」段"],
                      "escalate": "判断不了就 write outcome=escalated + 一个具体问题；人回答后用新条目 supersedes 收口"}},
    "lint": {"purpose": "报告一次性全量预检（格式/轴/verdict 一致性/引用/回执），不是门禁",
             "args": {"report": "子命令（唯一支持值）", "--file": "报告路径", "--task": "任务 id（给定时可核批准集合与规则状态）"},
             "example": "wf.py lint report --file review/draft.md --task 2026-xxxx --json"},
    "review-status": {"purpose": "查看本轮审查到位状态（只读：已到 n/2、缺哪份、文件状态）",
                      "args": {"--task": "任务 id（必填）", "--round": "轮次（缺省取最新已发起轮）"},
                      "example": "wf.py review-status --task 2026-xxxx --json"},
    "review-decide": {"purpose": "判定本轮审查（人数/异种按报告文件名；实施 CLI 取 launch 时人声明的值）。"
                                 "报告带 `materials.identity`，结论只对它绑定的那批材料成立：与当前不符即拒",

                      "args": {"--task": "任务 id（必填）", "--round": "缺省＝当前轮",
                               "--main-review": "主会话五轴复核文件（产生 verdict 时必填；也可与 --register-only 登记 main findings）",
                               "--main-review-draft": "按本轮已导入报告生成主会话复核待填骨架后退出",
                               "--plan": "逐条 finding 处置", "--unavailable": "不可用声明（与 --plan 互斥）",
                               "--register-only": "只登记复核关闭或主会话 finding：不产生结论、不校验人数/异种"
                                                  "（需 --plan 或 --main-review；关闭的硬条件照旧）",
                               "--gap-acceptance": "人接受覆盖缺口的确认文件"
                                                   "（by/at/quote/source + round + axes）",
                               "--single-reviewer-acceptance": "单 reviewer 判定的留痕降级：人接受残余风险的"
                                                              "确认文件（by/at/quote/source + round + residual_risk）——"
                                                              "不默认；两位异种 reviewer 仍是复杂任务默认要求",
                               "--single-reviewer-acceptance-draft": "只读生成上述接受文件骨架（只打印不落盘）",

                               "--plan-draft": "只读生成处置数组骨架（当前未关闭 blocking 逐条占位，只打印不落盘）"},
                      "example": "wf.py review-decide --task <id> --main-review main-review.json "
                                 "--gap-acceptance gap.json --json"},
    # ---- 2026-11-21（五轮审查 P0-1）：help 覆盖补全至全命令面（48/48）----
    # 参数面以各 handler 实际消费为准；子命令以 dispatch 分支为准。
    "enable": {"purpose": "启用本会话：身份确认 + 激活登记 + 回显绑定对象与代次",
               "args": {"--identity": "可选，仅接受 host（显式确认以宿主标识为准）",
                        "--new-session": "可选：本执行边界显式换新会话身份（宿主无关）。"
                                          "前置＝旧绑定对象已终态且写权空闲；旧附件/绑定保留为历史"},
               "example": "wf.py enable --new-session --json"},
    "status": {"purpose": "只读总览：绑定对象、阶段、门禁/步骤状态、待决与下一步",
               "args": {"--short": "可选：只输出单行摘要"},
               "example": "wf.py status --json"},
    "gate": {"purpose": "按 due 时点只读核对 required 步骤（不写任何记录）",
             "args": {"--due": "必填：before_execute | before_check | before_archive | after_archive"},
             "example": "wf.py gate --due before_archive --json"},
    "spec": {"purpose": "读取 spec 规则正文（不依赖 MCP 的本地主路径）",
             "args": {"--file": "必填：spec 相对路径（如 .wf/spec/guides/x.md）"},
             "example": "wf.py spec --file .wf/spec/guides/x.md"},
    "bind": {"purpose": "把本会话绑定到既有对象（不新建）",
             "args": {"--task": "二选一：任务 id", "--run": "二选一：实例 id"},
             "example": "wf.py bind --task 2026-xxxx --json"},
    "dep": {"purpose": "任务依赖边维护（建边/删边校验）",
            "args": {"add|rm": "子命令（位置参数）", "--task": "必填：任务 id",
                     "--prereq": "必填：前置任务 id",
                     "--op": "等价于位置子命令（add|rm，兼容写法）"},
            "example": "wf.py dep add --task 2026-xxxx --prereq 2026-yyyy --json"},
    "inspect": {"purpose": "只读诊断：工作区候选分类、冲突与治理面核对明细",
                "example": "wf.py inspect --json"},
    "ready": {"purpose": "只读：每个活动/暂停任务的 eligible/ready/blockers 与建议（不写记录）",
              "example": "wf.py ready --json"},
    "help": {"purpose": "命令自述：purpose/args/inputs/example 与决定文件示例",
             "args": {"<command>": "可选：命令名；缺省列出全部命令"},
             "example": "wf.py help archive --json"},
    "version": {"purpose": "只读：框架版本与运行环境",
                "example": "wf.py version --json"},
    "confirm-executor": {"purpose": "人显式确认执行器（写本机确认记录，模型不代填）",
                         "args": {"--scope": "必填：system | global | project"},
                         "example": "wf.py confirm-executor --scope project"},
    "definition": {"purpose": "工作流实例定义：prepare 建准备代次 / validate 静态校验",
                   "args": {"prepare|validate": "子命令", "--id": "必填：工作流定义 id"},
                   "example": "wf.py definition validate --id <wf-id> --json"},
    "run": {"purpose": "实例生命周期：create / advance / pause / resume / locate / finish / terminate",
            "args": {"create": "子命令：建实例并首次绑定",
                     "advance|pause|resume|finish": "子命令（pause 必填理由）",
                     "locate": "子命令：只读回读",
                     "terminate": "子命令：批量处置",
                     "--run": "实例 id（子命令用）", "--creation": "create：创建输入 JSON",
                     "--decision": "advance/resume/finish：人判决定（可选）",
                     "--reason": "pause：暂停原因（必填）", "--plan": "terminate：处置计划 JSON",
                     "--preview": "terminate：只读预览（不落盘）"},
            "example": "wf.py run locate --run <run-id> --json"},
    "writer": {"purpose": "项目写入权：acquire 获取 / release 释放（锁内核验）",
               "args": {"acquire|release": "子命令"},
               "example": "wf.py writer acquire --json"},
    "writer-handover": {"purpose": "写权交接两段式：begin 出交按声明 / accept 接收方核验后授予",
                        "args": {"begin|accept": "子命令",
                                 "--to": "begin：接收会话标识（必填）",
                                 "--decision": "accept：交接确认决定（必填）"},
                        "example": "wf.py writer-handover accept --decision h.json --json"},
    "upgrade": {"purpose": "三方升级 / 只读导出本地偏离（经引导层转交 install.py --upgrade；本层不判定）",
               "args": {"--release": "发行检出根（其下直接有 install.py、wf-release.json 与 wf-release/）",
                        "--release-ref": "发行引用 refs/tags/wf-vX.Y.Z",
                        "--apply": "应用预览（交互终端输入预览指纹；同一进程完成；与导出互斥）",
                        "--export-deviations": "只读导出本地偏离补丁与清单（不取写权、不暂停任务、不应用升级）",
                        "--out": "导出目录（必须在项目树外；不存在则创建，已存在必须为空）",
                        "--keep": "升级冲突：保留本地（**项目相对路径**，与 preview 的 "
                                  "unresolved[].path 逐字一致，可重复；仅应用模式；仅可选资产，"
                                  "必需资产保留删除会被拒）",
                        "--restore": "升级冲突：恢复发行内容（**项目相对路径**，同上；仅应用模式）"},
               "example": "wf.py upgrade --release /path/to/wf-checkout --release-ref refs/tags/wf-v0.1.7 --apply",
               "example_export": "wf.py upgrade --release /path/to/wf-checkout --release-ref refs/tags/wf-v0.1.7 --export-deviations --out /tmp/wf-deviations --json"},
    "task-pause": {"purpose": "受控暂停任务（挂起点等实际答复）",
                   "args": {"--task": "必填：任务 id", "--reason": "可选：暂停原因"},
                   "example": "wf.py task-pause --task 2026-xxxx --reason '等人答复' --json"},
    "task-resume": {"purpose": "解除任务暂停（恢复推进）",
                    "args": {"--task": "必填：任务 id"},
                    "example": "wf.py task-resume --task 2026-xxxx --json"},
    "task-replan": {"purpose": "实质规划变更：回 Plan（只做状态迁移，不改写 PRD）",
                    "args": {"--task": "必填：任务 id", "--decision": "必填：choice=replan 的决定文件"
                                                            "（机械修订走 task-approve，不经本命令）",
                             "--draft": "只读生成 replan 决定草稿"},
                    "example": "wf.py task-replan --task 2026-xxxx --decision replan.json --json"},
    "task-rework": {"purpose": "返工：新建返工任务并挂起原任务（继承前置与上下文）",
                    "args": {"--task": "必填：原任务 id", "--decision": "必填：返工决定文件",
                             "--draft": "只读生成返工决定草稿"},
                    "example": "wf.py task-rework --task 2026-xxxx --decision rework.json --json"},
    "task-replace": {"purpose": "替换：废弃原任务并由新任务承接（支持 --preview）",
                     "args": {"--task": "必填：原任务 id", "--decision": "必填：替换决定文件",
                              "--preview": "可选：只读预览，不写记录"},
                     "example": "wf.py task-replace --task 2026-xxxx --decision r.json --preview --json"},
    "task-reassess": {"purpose": "挂起任务复评（首轮无返工能力时挂起集合为空直接通过）",
                      "args": {"--task": "必填：任务 id"},
                      "example": "wf.py task-reassess --task 2026-xxxx --json"},
    "task-attribute": {"purpose": "历史提交归属裁决（已提交改动归属本任务/他人）",
                       "args": {"--task": "必填：任务 id", "--commit": "必填：提交 sha"},
                       "example": "wf.py task-attribute --task 2026-xxxx --commit <sha> --json"},
    "task-curate": {"purpose": "策展：选用 spec 规则并记录目的（停用/释放走 spec-update 的 disable）",
                    "args": {"--task": "必填：任务 id", "--spec": "必填：spec 相对路径",
                             "--purpose": "必填：选用目的"},
                    "example": "wf.py task-curate --task 2026-xxxx --spec .wf/spec/guides/x.md "
                               "--purpose '本轮适用' --json"},
    "task-abandon": {"purpose": "异常归档（放弃）：逐项去向 + 停止决定",
                     "args": {"--task": "必填：任务 id", "--decision": "必填：停止决定",
                              "--disposition": "可选：逐项去向计划"},
                     "example": "wf.py task-abandon --task 2026-xxxx --decision stop.json "
                                "--disposition disp.json --json"},
    "task-retrospect": {"purpose": "复盘结论留痕（覆盖触发事实集合）",
                        "args": {"--task": "必填：任务 id",
                                 "--evidence": "必填：复盘证据文件（入口只读其 conclusion 字段并记入复盘）"},
                        "example": "wf.py task-retrospect --task 2026-xxxx --evidence r.json --json"},
    "review-accept-unknown": {"purpose": "审查环境不可用时的接受/撤销（人声明 + 码级留痕）",
                              "args": {"--task": "必填：任务 id", "--file": "accept：不可用声明（必填）",
                                       "--batch": "可选：批量接受", "--revoke": "可选：撤销已接受",
                                       "--round": "可选：目标轮次", "--slot": "可选：目标槽位",
                                       "--digest": "revoke：声明的原文摘要"},
                              "example": "wf.py review-accept-unknown --task 2026-xxxx --file u.json --json"},
}


def cmd_project(ctx, args):
    """`project --kind open-items|attribution|audit|skeleton --task [--check]`（K8 投影，`--check` 断言等值）。"""
    from . import projection as projection_mod, tasks as tasks_mod

    kind = args.value("--kind")
    if kind not in ("open-items", "attribution", "audit", "skeleton"):
        raise CliError("WF_USAGE_INVALID", {"reason": "unknown projection kind", "kind": kind,
                                          "known": ["open-items", "attribution", "audit", "skeleton"]})
    task_id = args.value("--task")
    if not task_id:
        raise CliError("WF_USAGE_INVALID", {"reason": "project requires --task <id>"})
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
        raise CliError("WF_USAGE_INVALID", {"reason": "verify requires resolve", "known": ["resolve"]})
    task_id = args.value("--task")
    acceptance_id = args.value("--id")
    if not task_id or not acceptance_id:
        raise CliError("WF_USAGE_INVALID", {"reason": "verify resolve requires --task <id> --id <acceptance-id>"})
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
    守卫（delete/expand/repo_rules/export）只认这些文件，不认"模型说的已获授权"；
    K6 第①类（提交/推送）不经本入口——提交授权唯一通道是 finish 决定的
    `commit_grants`（choice=commit 的授权条目在 finish/stop 归档守卫消费）。
    """
    from . import authorize as authorize_mod, tasks as tasks_mod

    sub = (args.positional() or [None])[0]
    task_id = args.value("--task")
    if not task_id:
        raise CliError("WF_USAGE_INVALID", {"reason": "authorize requires --task <id>"})
    task = tasks_mod.load_task(ctx.root, task_id)
    if task is None:
        raise CliError("WF_TARGET_MISSING", {"reason": "task not found", "task": task_id})
    directory = tasks_mod.task_dir(ctx.root, task_id)
    if sub == "show":
        # record_log 消费点（十三→十五轮 P2-1/P2-2）：show 是机制稿登记的审计视图——
        # 折叠计数必须在此可见（否则"计数可见"的声明边界不成立）；export 的当前生效范围
        # 一并投影，审计不必打开 JSON 原件。键名按形状命名：records 为对象（digest+log+计数）。
        def _projection(action):
            stored = authorize_mod.require(directory, action) or {}
            entry = {"original_digest": stored.get("original_digest"),
                     "record_log": stored.get("record_log") or []}
            if stored.get("record_log_truncated"):
                entry["record_log_truncated"] = stored["record_log_truncated"]
            if stored.get("materials") is not None:
                entry["materials"] = stored["materials"]
                entry["scope_digest"] = stored.get("scope_digest")
            return entry

        found = {action: _projection(action) for action in authorize_mod.ACTIONS
                 if authorize_mod.require(directory, action) is not None}
        return codes.result("WF_OK", object={"id": task_id, "name": task.get("title")},
                            position_=codes.position(scope="task", phase=task.get("phase"), task_id=task_id),
                            next_="缺哪一类就用 authorize record 补哪一类",
                            facts={"recorded": {name: digest for name, digest in found.items() if digest},
                                   "actions": dict(authorize_mod.ACTIONS)})
    if sub != "record":
        raise CliError("WF_USAGE_INVALID", {"reason": "authorize requires record|show",
                                          "known": ["record", "show"]})
    if args.flag("--draft"):
        # 三轮三审 b9：人签确认文件的只读骨架（与 task-approve --draft 同型）——
        # 只打印不落盘；TODO 占位照抄会被入口预检拒（quote/by 缺失即拒）。
        draft = []
        for action, action_zh in authorize_mod.ACTIONS.items():
            entry = {"choice": action,
                     "task": task_id,
                     "paths": ["TODO（人填写：本确认覆盖的具体路径/glob）"],
                     "quote": "TODO（人填写：谁在什么范围确认了什么）",
                     "by": "TODO human:<来源>",
                     "at": records.now_str(),
                     "source": "user-declared",
                     "reason": f"TODO（人填写：为什么需要{action_zh}确认；不需要的条目删除）"}
            if action == "export":
                entry["materials"] = ["diff", "requirement", "test_results"]
            draft.append(entry)
        return codes.result("WF_OK", object={"id": task_id, "name": task.get("title")},
                            position_=codes.position(scope="task", phase=task.get("phase"), task_id=task_id),
                            next_="人按需保留条目、填 TODO 后存成文件，再 authorize record --file 落档",
                            facts={"draft": draft})
    file_value = args.value("--file")
    if not file_value:
        raise CliError("WF_USAGE_INVALID", {"reason": "authorize record requires --file <决定.json>"})
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
            if action == "export":
                # 外发授权必须绑定"本次范围"：任务 + 材料类集合。任务缺省取本次记录所在任务，
                # 材料类必须显式——否则旧授权会被复用给新增材料。
                entry = dict(entry)
                entry.setdefault("task", task_id)
                _scope_problems = authorize_mod.export_decision_problems(entry)
                if _scope_problems:
                    raise CliError("WF_SEMANTIC_DECISION",
                                   {"reason": "外发确认必须写明任务与材料类集合",
                                    "action": action, "problems": _scope_problems,
                                    "known_materials": list(authorize_mod.EXPORT_MATERIALS),
                                    "exits": ["在决定文件里补 task 与 materials"
                                              "（例如 [\"diff\",\"requirement\",\"test_results\"]）后重跑",
                                              "由人重写该决定文件（AI 不得代写）"]})
            info = authorize_mod.record_authorization(
                directory, action, entry,
                raw_copy_dir=join(ctx.root, ".wf/.runtime/decisions"), root=ctx.root)
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
            raise CliError("WF_USAGE_INVALID", {"reason": "sampling confirm requires --task <id>"})
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
            raise CliError("WF_USAGE_INVALID", {"reason": "sampling reviewed requires --task <id>"})
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
        raise CliError("WF_USAGE_INVALID", {"reason": "sampling requires pick|report|evaluate|reviewed|confirm",
                                          "known": ["pick", "report", "evaluate", "reviewed", "confirm"]})
    task_id = args.value("--task")
    if not task_id:
        raise CliError("WF_USAGE_INVALID", {"reason": "sampling pick requires --task <id>"})
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
        raise CliError("WF_USAGE_INVALID", {"reason": "prefs requires set|show", "known": ["set", "show"]})
    kind = args.value("--kind")
    value = args.value("--value")
    if not kind or not value:
        raise CliError("WF_USAGE_INVALID", {"reason": "prefs set requires --kind <类> --value <值>"})
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
        raise CliError("WF_USAGE_INVALID", {"reason": "judgments requires --task <id>"})
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
        raise CliError("WF_USAGE_INVALID", {"reason": "judgments requires add|show", "known": ["add", "show"]})
    if args.flag("--draft"):
        # 五轮审查 b5 尾项：判断条目只读骨架（kind 列全合法类，TODO 占位照抄会被校验拒）
        draft = {"kind": "TODO（人填：" + "、".join(judgments_mod.KINDS) + "）",
                 "decision": "TODO（判断内容/归属去向）",
                 "basis": "TODO（依据：留下可核实的理由，不规定结论）",
                 "outcome": "applied",
                 "by": "human",
                 "at": records.now_str(),
                 "note": "TODO 与非法 kind 在 validate 处被拒；escalated 才必须写 escalated_question"}
        return codes.result("WF_OK", object={"id": task_id, "name": task.get("title")},
                            position_=codes.position(scope="task", phase=task.get("phase"), task_id=task_id),
                            next_="填完 TODO 存成 JSON 文件，再 `judgments add --task <id> --file <文件>` 入库",
                            facts={"draft": draft, "known_kinds": list(judgments_mod.KINDS)})
    path_value = args.value("--file")
    if not path_value:
        raise CliError("WF_USAGE_INVALID", {"reason": "judgments add requires --file <json>"})
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
        raise CliError("WF_USAGE_INVALID", {"reason": "lint requires `report`", "known": ["report"]})
    path = args.value("--file")
    if not path:
        raise CliError("WF_USAGE_INVALID", {"reason": "lint report requires --file <path>"})
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
        raise CliError("WF_USAGE_INVALID", {"reason": "review-accept-unknown requires --task <id>"})
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
        raise CliError("WF_USAGE_INVALID", {"reason": "review-status requires --task <id>"})
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
    # A6（三轮二审）：实施宿主与最近 launch 的实施 CLI 是否一致是可稳定计算的客观事实——
    # 换宿主后未重新 launch 时提前可见（F18 残余），不留给 AI 临场发现。
    latest_launch_cli = None
    for entry in (task.get("reviews") or {}).get("launches") or []:
        if isinstance(entry, dict) and int(entry.get("round") or 0) == facts["round"]:
            latest_launch_cli = review_mod.review_cli(entry.get("implementation_cli"))
    facts["implementation_cli_of_round"] = latest_launch_cli
    # B1：status 只报材料与资格，不承诺判定资格（结论只能由 review-decide 产生）
    coverage = facts.get("coverage") or {}
    uncovered = list(coverage.get("uncovered") or [])
    accepted = set(coverage.get("accepted") or [])
    result_record = (task.get("reviews") or {}).get("result") or {}
    if facts.get("ready_to_import"):
        next_ = (f"报告已写完待导入（{', '.join(facts['ready_to_import'])}）："
                 "先 review-import；其余槽位可继续写，不必等齐再导入")
    elif not facts["material_ready"]:
        # 材料身份失配与"报告还没交"是两回事：前者等不来新报告（同轮摘要锁），
        # 必须给恢复原材料或另开一轮的出口，否则恢复会话会白等一轮。
        # 基线口径与 decide/check_next_hint 同一实现（review.round_materials_basis）
        _round_imported = [item for item in (task.get("reviews") or {}).get("imported") or []
                           if isinstance(item, dict) and int(item.get("round") or 0) == facts["round"]]
        _basis = review_mod.round_materials_basis(
            _round_imported, review_mod.round_materials_identity(ctx, task, facts["round"]))
        material_stale = [str(item.get("slot")) for item in _basis["live_mismatch"]]
        restored_only = [str(item.get("slot")) for item in _basis["restored"]]
        mixed = _basis["mixed"]
        if mixed:
            next_ = (f"本轮既有还原记录（{', '.join(restored_only)}）也有对不上当前材料的正常条目"
                     f"（{', '.join(material_stale)}）：把后者也按 `--restore` 重导，"
                     "或按新材料重写并开新一轮；直接判定会撞混合基线")
        elif material_stale:
            next_ = (f"材料身份已变（{', '.join(material_stale)}）：同轮不能重导——"
                     "有备份就把原字节放回材料目录并重跑 review-context；"
                     "没有备份则按新材料重写报告并开新一轮")
        elif restored_only and not facts.get("ready_to_import"):
            # 还原记录的身份来自记录本身：可直接判定，不必等也不必开新轮
            next_ = (f"本轮报告按记录还原（{', '.join(restored_only)}），可直接 review-decide；"
                     "要恢复可核身份再放回原字节并重跑 review-context")
        else:
            next_ = (f"材料未齐（已到 {facts['arrived']}/{facts['required']}）："
                     "等 reviewer 产出后 review-import")
    elif facts["eligibility"]["problems"]:
        next_ = ("材料已齐，但判定资格不足："
                 + "；".join(item["reason"] for item in facts["eligibility"]["problems"]))
    elif result_record.get("round") == facts["round"]:
        if result_record.get("verdict") == "fail":
            next_ = ("本轮已 fail：先核实是否误报/漏处置；误报可在本轮用 --plan + --main-review "
                     "同轮重判，已实质修复则重跑 Check 后发新轮")
        else:
            next_ = "本轮已产生判定；如需改结论请开新一轮（review-launch），不覆盖已判轮次"
    elif not facts.get("main_review_ready"):
        next_ = ("材料已齐、资格检查通过：先生成并填写主会话复核"
                 "（review-decide --main-review-draft <file>），再带 --main-review 判定；"
                 "未覆盖轴由你先补证，补不了再交人")
    elif uncovered and not set(uncovered) <= accepted:
        missing = sorted(set(uncovered) - accepted)
        next_ = (f"材料与主会话复核已齐，但本轮仍有未覆盖轴（{', '.join(missing)}）："
                 "先判断能否同轮补证；仍补不了再请人接受缺口后用 --gap-acceptance 重判")
    else:
        next_ = "材料与主会话复核已齐：下一步 review-decide（结论以判定为准）"
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
        raise CliError("WF_USAGE_INVALID", {"reason": "unknown command for help", "command": name,
                                           "known": sorted(COMMAND_HELP)})
    facts = dict(entry)
    facts["command"] = name
    facts["envelope"] = ("自动模式（默认）不手写信封：直接运行 `wf.py <子命令>`，身份由执行边界派生、"
                         "写权代次由会话运行态携带。仅显式信封模式（拿不到执行边界时）才从 stdin 或 "
                         "--envelope <file> 提供请求信封（provider=host + identity.host_id + session_id）")
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
    "dep": _task_command("cmd_dep"),
    # `task-rework` 已实现（返工建 R、挂起 T、继承前置）。机制稿 §6.2 与
    # `workflows/instance-flow.md` 把 `control.task.rework` 声明为 [required] 步骤；机制稿是
    # 本框架权威，v42 §4 的删除要求属审查稿意见，不再作为待裁冲突。保留命令；要删除须按
    # 设计稿 §0 的维护协议同批改机制稿、部署声明与 handler 自检。
    "task-rework": _task_command("cmd_task_rework"),
    "task-replace": _task_command("cmd_task_replace"),
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
    "definition": _runs_command("definition"),
    "run": _runs_command("run"),
    "upgrade": _transfer_stub(),
}


ACTIVATION_REQUIRED = frozenset({
    "dep",
    "definition",
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



# ---- 命令用法注册表（2026-11-21 五轮审查 P0-2/P0-3）----
# 唯一口径：flags 来自各 handler 实际消费（args.value/flag 静态提取），subs 来自 dispatch 分支。
# dispatch() 据此拒绝未知参数与多余/未知位置参数（WF_USAGE_INVALID）——入口对"输入不成立"不再沉默。
GLOBAL_FLAGS = ("--json", "--envelope", "--envelope-last", "--session")

COMMAND_FLAGS = {
    "archive": {"--task", "--decision", "--draft"},
    "authorize": {"--task", "--file", "--draft"},
    "baseline-apply": {"--task", "--files", "--decision", "--proposal", "--preview"},
    "bind": {"--task", "--run"},
    "confirm-executor": {"--scope"},
    "definition": {"--id"},
    "dep": {"--task", "--op", "--prereq"},
    "enable": {"--identity", "--new-session"},
    "gate": {"--due"},
    "inspect": set(),
    "judgments": {"--task", "--file", "--attestation", "--draft"},
    "lint": {"--file", "--task"},
    "prefs": {"--kind", "--value"},
    "project": {"--kind", "--task", "--check"},
    "ready": set(),
    "review-accept-unknown": {"--task", "--file", "--batch", "--revoke", "--round", "--slot", "--digest"},
    "review-context": {"--task", "--round", "--reset", "--as"},
    "review-decide": {"--task", "--round", "--plan", "--unavailable", "--gap-acceptance",
                      "--main-review", "--main-review-draft", "--register-only",
                      "--single-reviewer-acceptance", "--single-reviewer-acceptance-draft",
                      "--plan-draft"},
    "review-import": {"--task", "--round", "--slot", "--report", "--as", "--restore"},
    "review-launch": {"--task", "--launch-request", "--implementation-cli", "--preview"},
    "review-status": {"--task", "--round"},
    "run": {"--run", "--creation", "--decision", "--reason", "--plan", "--preview"},
    "sampling": {"--task", "--freeze", "--file", "--attestation", "--quote"},
    "spec": {"--file"},
    "spec-update": {"--task", "--changes", "--changes-draft"},
    "status": {"--short"},
    "stop": {"--decision", "--preview", "--draft"},
    "task-abandon": {"--task", "--decision", "--disposition"},
    "task-approve": {"--task", "--decision", "--draft"},
    "task-attribute": {"--task", "--commit"},
    "task-check": {"--task", "--decision", "--review-notes", "--review-notes-draft", "--workspace-exclusion"},
    "task-curate": {"--task", "--spec", "--purpose"},
    "task-knowledge": {"--task", "--decision", "--no-update", "--changes", "--changes-draft"},
    "task-new": {"--kind", "--template", "--title"},
    "task-pause": {"--task", "--reason"},
    "task-reassess": {"--task"},
    "task-replace": {"--task", "--decision", "--preview"},
    "task-replan": {"--task", "--decision", "--draft"},
    "task-resume": {"--task"},
    "task-retrospect": {"--task", "--evidence"},
    "task-rework": {"--task", "--decision", "--draft"},
    "task-start": {"--task", "--workspace-exclusion"},
    # W4-1/W4-2：upgrade 经引导层转交、不经本层用法校验——条目为 help 一致性保留
    "upgrade": {"--apply", "--release", "--release-ref", "--export-deviations",
                "--out", "--keep", "--restore"},
    "verify": {"--task", "--id", "--kind", "--reason", "--impact", "--compensation",
               "--evidence", "--by"},
    "help": set(),
    "version": set(),
    "writer": set(),
    "writer-handover": {"--to", "--decision"},
}

# 子命令级参数集（九轮审查 b-2）：run 各子命令只认自己的参数——
# 共用并集会放过"finish --preview"这类对当前子命令无效的参数（被静默忽略成真实动作）。
COMMAND_SUB_FLAGS = {
    "run": {
        "create": {"--creation"},
        "advance": {"--run", "--decision"},
        "pause": {"--run", "--reason"},
        "resume": {"--run", "--decision"},
        "locate": {"--run"},
        "finish": {"--run", "--decision"},
        "terminate": {"--run", "--plan", "--preview"},
    },
}

# 布尔旗标注册表（十一轮 a P1-1 重构）：**按命令**登记（--check 在 project 是布尔、
# 在 task-curate 取值——全局名单无法表达）；未列出的该命令 flag 一律要求紧跟值。
# 来源：各 handler 的 args.flag(...) 静态提取；upgrade 是能力桩不读 args，按 help 示例登记。
GLOBAL_BOOL_FLAGS = frozenset({"--json", "--envelope-last"})
COMMAND_BOOL_FLAGS = {
    "project": {"--check"},
    "authorize": {"--draft"},
    "enable": {"--new-session"},
    "judgments": {"--draft"},
    "review-accept-unknown": {"--revoke"},
    "review-context": {"--reset"},
    "review-decide": {"--register-only"},
    "review-launch": {"--preview"},
    "review-import": {"--restore"},
    "sampling": {"--freeze"},
    "status": {"--short"},
    "stop": {"--preview", "--draft"},
    "archive": {"--draft"},
    "task-approve": {"--draft"},
    "task-replan": {"--draft"},
    "task-rework": {"--draft"},
    "task-knowledge": {"--no-update", "--changes-draft"},
    "spec-update": {"--changes-draft"},
    "task-check": {"--review-notes-draft"},
    "task-replace": {"--preview"},
    "baseline-apply": {"--preview"},
    "run": {"--preview"},
    # W4-1：upgrade 经引导层转交、不经本层用法校验——条目为 help 一致性保留
    "upgrade": {"--apply", "--export-deviations"},
}

COMMAND_SUBS = {
    "definition": set(SUBACTIONS["definition"]),
    "run": set(SUBACTIONS["run"]),
    "writer": {"acquire", "release"},
    "writer-handover": {"begin", "accept"},
    "sampling": {"pick", "report", "evaluate", "reviewed", "confirm"},
    "judgments": {"add", "show"},
    "prefs": {"set", "show"},
    "authorize": {"record", "show"},
    "lint": {"report"},
    "verify": {"resolve"},
    "dep": {"add", "rm"},
}


def validate_usage(command, rest):
    """dispatch 前的用法校验（唯一实现）：未知 flag / 多余或未知位置参数一律 WF_USAGE_INVALID。

    值消费启发：flag 后紧跟的非 flag token 视为该 flag 的值——与所有现存调用一致
    （子命令都是第一个位置参数，布尔 flag 不带值）。
    """
    subs = COMMAND_SUBS.get(command)
    sub_flags_map = COMMAND_SUB_FLAGS.get(command)
    # 子命令级收窄前置（九轮 b-2）：首位置参数是已知子命令时，参数面收窄到该子命令集合——
    # 否则"finish --preview"会先按并集放行、被 handler 静默忽略成真实动作。
    first_positional = next((tok for tok in rest if not tok.startswith("--")), None)
    if sub_flags_map and first_positional in sub_flags_map:
        allowed = GLOBAL_FLAGS + tuple(sub_flags_map[first_positional])
    else:
        allowed = GLOBAL_FLAGS + tuple(COMMAND_FLAGS.get(command, ()))
    positionals = []
    index = 0
    while index < len(rest):
        token = rest[index]
        if token.startswith("--"):
            # 值内联形态（Args.value 支持 --flag=value）：flag 名取 = 前缀（九轮审查 b-2）
            flag_name = token.split("=", 1)[0]
            if flag_name not in allowed:
                import difflib

                near = difflib.get_close_matches(flag_name, allowed, n=1, cutoff=0.6)
                hint = f"；最接近的合法参数是 {near[0]}" if near else ""
                raise CliError("WF_USAGE_INVALID", {
                    "reason": f"unknown flag {flag_name} for `{command}`{hint}",
                    "known_flags": sorted(allowed),
                    "exits": ["按 wf help <命令> 修正参数拼写后重试",
                              "不改触碰面、不绕过参数校验"]})
            is_bool = (flag_name in GLOBAL_BOOL_FLAGS
                       or flag_name in COMMAND_BOOL_FLAGS.get(command, ()))
            if "=" in token:
                # 十一轮 b-1：布尔旗标不接受赋值形态——Args.flag() 只认裸旗标，
                # `--preview=true` 会绕过只读分支变成真实操作。
                if is_bool:
                    raise CliError("WF_USAGE_INVALID",
                                   {"reason": f"boolean flag {flag_name} takes no value",
                                    "known_flags": sorted(allowed),
                                    "exits": [f"去掉 =…，写裸 {flag_name}"]})
                index += 1
                continue
            if is_bool:
                index += 1
                continue
            index += 1
            if index >= len(rest):
                raise CliError("WF_USAGE_INVALID",
                               {"reason": f"flag {flag_name} requires a value (nothing follows)",
                                "known_flags": sorted(allowed),
                                "exits": ["补上该参数的值后重试"]})
            nxt = rest[index]
            if nxt.startswith("--"):
                nxt_name = nxt.split("=", 1)[0]
                if nxt_name in allowed:
                    raise CliError("WF_USAGE_INVALID",
                                   {"reason": f"flag {flag_name} requires a value, got flag {nxt_name}",
                                    "known_flags": sorted(allowed),
                                    "exits": [f"给 {flag_name} 补上值（它不吞下一个参数）"]})
            index += 1     # flag 的值
            continue
        positionals.append(token)
        index += 1
    if positionals:
        if subs is not None:
            if positionals[0] not in subs:
                raise CliError("WF_USAGE_INVALID", {
                    "reason": f"`{command}` requires subcommand: {'|'.join(sorted(subs))}",
                    "got": positionals[0], "known": sorted(subs),
                    "exits": ["补合法子命令后重试"]})
            if len(positionals) > 1:
                raise CliError("WF_USAGE_INVALID", {
                    "reason": f"`{command}` takes at most one subcommand", "got": positionals,
                    "exits": ["去掉多余位置参数（路径等一律用 flag 传）"]})
        elif command == "help":
            if len(positionals) > 1:
                raise CliError("WF_USAGE_INVALID", {"reason": "help takes at most one command",
                                                    "got": positionals})
        else:
            raise CliError("WF_USAGE_INVALID", {
                "reason": f"`{command}` takes no positional argument", "got": positionals,
                "exits": ["路径与取值一律用 flag 传；子命令见 wf help <命令>"]})


def dispatch(ctx, argv):
    if not argv:
        raise CliError("WF_USAGE_INVALID", {"reason": "missing subcommand", "commands": sorted(COMMANDS)})
    command = argv[0]
    ctx.command = command
    handler = COMMANDS.get(command)
    if handler is None:
        import difflib

        near = difflib.get_close_matches(command, sorted(COMMANDS), n=1, cutoff=0.6)
        raise CliError(
            "WF_USAGE_INVALID",
            {"reason": f"unknown subcommand: {command}" + (f"；最接近的命令是 {near[0]}" if near else ""),
             "commands": sorted(COMMANDS),
             "exits": ["wf.py help（无参）列出全部命令"]},
        )
    validate_usage(command, list(argv[1:]))
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
        # carries_id（load_task 的目录名/id 错配）给结构化出口；其余 RecordInvalid
        # 原因（duplicate/unreadable 等）不扩权，保持纯 reason（2026-11-21）。
        carries_id = getattr(exc, "carries_id", None)
        facts = {"reason": str(exc)}
        if carries_id:
            facts["actual_id"] = carries_id
            facts["exits"] = [f"改用记录 id {carries_id} 重试（传入的可能是目录名）"]
        payload = codes.result("WF_RECORD_INVALID", facts=facts)
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
