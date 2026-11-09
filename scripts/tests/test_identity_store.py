"""identity_store 的单测：路由所有权、roots 维护顺序、租约投影（K2）、身份冲突（K1）。

关键断言（对应 identity-redesign.md）：
- L1 单主 / L2 多主（§2.2a）
- roots 维护顺序 snapshot→判定→维护，且 **阻断时不得 upsert**（§3.4）
- C2 分级：未登记调用者 + 存活兄弟根 ⇒ 阻断（§2.3d 分级表）
- 多源冲突只报事实、不猜（K1）
- 租约状态 = live/superseded/gone/unknown 的派生判据（K2）
"""
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import identity_store as store  # noqa: E402
from wflib import session as S  # noqa: E402

BOOT = "boot-A"


class FakeProbe(S.Probe):
    def __init__(self, table=None, boot=BOOT, unreadable=()):
        super().__init__(boot)
        self.table = dict(table or {})
        self.unreadable = set(unreadable)

    def stat_of(self, pid):
        pid = int(pid)
        if pid in self.unreadable:
            raise OSError("EACCES")
        return self.table.get(pid)

    def exe_of(self, pid):
        return ((self.table.get(int(pid)) or {})).get("exe")

    def name_of(self, pid):
        return self.exe_of(pid)


def proc(pid, start="100", ppid=1, state="S", exe="node"):
    return {"pid": int(pid), "comm": exe, "state": state, "ppid": ppid,
            "session": int(pid), "tty_nr": 0, "start": str(start), "exe": exe}


def root(pid=5538, start="100", boot=BOOT, exe="node"):
    return {"kind": "pid", "boot": boot, "pid": int(pid), "start": str(start), "exe": exe}


def attachment(session_key="K", roots=(), l1=None, **extra):
    payload = {"session_key": session_key, "roots": list(roots), "attached_l1": l1,
               "activation": {"enabled": True}, "activation_stale": False}
    payload.update(extra)
    return payload


class TestRoutes(unittest.TestCase):
    def test_l1_single_owner(self):
        routes = {}
        store.register(routes, "k1", "A", "session", BOOT, "t0")
        with self.assertRaises(store.StoreError):
            store.register(routes, "k1", "B", "session", BOOT, "t1")
        # 同一会话重复登记是幂等的
        store.register(routes, "k1", "A", "session", BOOT, "t2")
        self.assertEqual(store.owners_of(routes, "k1"), ["A"])

    def test_l2_appends_without_overwriting(self):
        routes = {}
        store.register(routes, "k2", "A", "proc", BOOT, "t0")
        store.register(routes, "k2", "B", "proc", BOOT, "t1")
        self.assertEqual(store.owners_of(routes, "k2"), ["A", "B"])

    def test_round_trip_preserves_shape(self):
        routes = {}
        store.register(routes, "k1", "A", "session", BOOT, "t0")
        store.register(routes, "k2", "A", "proc", BOOT, "t0")
        self.assertEqual(routes["k1"]["owners"], ["A"])
        self.assertEqual(routes["k2"]["owners"], ["A"])
        self.assertNotIn("roots", routes["k1"])  # 状态不在路由里

    def test_replace_owner_keeps_others(self):
        routes = {"k1": {"owners": ["A"]}, "k2": {"owners": ["A", "B"]}, "k3": {"owners": ["B"]}}
        store.replace_owner(routes, "A", "N")
        self.assertEqual(routes["k1"]["owners"], ["N"])
        self.assertEqual(routes["k2"]["owners"], ["N", "B"])
        self.assertEqual(routes["k3"]["owners"], ["B"])


class TestMaintainRoots(unittest.TestCase):
    def test_first_call_registers_root(self):
        att = attachment()
        out = store.maintain_roots(att, root(), "P1", FakeProbe({}))
        self.assertEqual(out["action"], "normal")
        self.assertEqual(len(att["roots"]), 1)

    def test_c2_blocks_and_does_not_upsert(self):
        probe = FakeProbe({5538: proc(5538), 6000: proc(6000)})
        att = attachment(roots=[root(pid=5538)])
        newcomer = root(pid=6000)
        out = store.maintain_roots(att, newcomer, "P1", probe)
        self.assertEqual(out["action"], "block")
        self.assertEqual(out["reason"], store.CONCURRENT_CALLER)
        # 关键：被拒的调用不得把自己登记进 roots
        self.assertEqual([r["pid"] for r in att["roots"]], [5538])

    def test_evidence_unknown_blocks_and_does_not_upsert(self):
        probe = FakeProbe({}, unreadable={5538})
        att = attachment(roots=[root(pid=5538)])
        out = store.maintain_roots(att, root(pid=9999), "P1", probe)
        self.assertEqual(out["action"], "block")
        self.assertEqual(out["reason"], store.EVIDENCE_UNKNOWN)
        self.assertEqual([r["pid"] for r in att["roots"]], [5538])

    def test_all_dead_sets_stale_then_registers(self):
        probe = FakeProbe({})
        att = attachment(roots=[root(pid=5538)], activation_stale=False)
        out = store.maintain_roots(att, root(pid=9999), "P1", probe)
        self.assertEqual(out["action"], "stale")
        self.assertTrue(att["activation_stale"])
        self.assertEqual([r["pid"] for r in att["roots"]], [9999])  # 死根被剪掉

    def test_known_root_with_dead_sibling_is_normal(self):
        probe = FakeProbe({6000: proc(6000)})
        att = attachment(roots=[root(pid=5538), root(pid=6000)])
        out = store.maintain_roots(att, root(pid=6000), "P1", probe)
        self.assertEqual(out["action"], "normal")
        self.assertEqual([r["pid"] for r in att["roots"]], [6000])

    def test_registered_multi_root_discloses(self):
        probe = FakeProbe({5538: proc(5538), 6000: proc(6000)})
        att = attachment(roots=[root(pid=5538), root(pid=6000)])
        out = store.maintain_roots(att, root(pid=6000), "P1", probe)
        self.assertEqual(out["action"], "disclose")
        self.assertEqual(len(out["facts"]["concurrent_callers"]), 1)


class TestLeaseState(unittest.TestCase):
    """K2：租约状态是**投影**（live/superseded/gone/unknown），失效由 generation 表达。

    防的失败：dogfood 里"绑定终身"，同一事实在附件标记（`superseded_by`）与 writer 代次
    各存一份、互相打架；v42 §4 删掉五态/轮换后，状态只由 writer 记录 + 锚点存活派生。
    """

    def _writer(self, state="held", generation=2, holder=None):
        return {"schema_version": 1, "state": state, "generation": generation, "holder": holder}

    def test_live_when_holder_is_me_and_boundary_alive(self):
        probe = FakeProbe({5538: proc(5538)})
        att = attachment("K", roots=[root(pid=5538)])
        writer = self._writer(holder={"kind": "session", "id": "K", "generation": 2})
        self.assertEqual(store.lease_state(writer, "K", att, probe=probe), store.LIVE)

    def test_superseded_when_another_session_holds(self):
        probe = FakeProbe({5538: proc(5538)})
        att = attachment("K", roots=[root(pid=5538)])
        writer = self._writer(generation=3, holder={"kind": "session", "id": "N", "generation": 3})
        self.assertEqual(store.lease_state(writer, "K", att, probe=probe), store.SUPERSEDED)

    def test_gone_when_boundary_dead(self):
        probe = FakeProbe({})
        att = attachment("K", roots=[root(pid=5538)],
                         l1={"sid": 5538, "sid_start": "100", "boot": BOOT})
        writer = self._writer(holder={"kind": "session", "id": "K", "generation": 2})
        self.assertEqual(store.lease_state(writer, "K", att, probe=probe), store.GONE)

    def test_unknown_when_writer_record_unreadable(self):
        self.assertEqual(store.lease_state({"state": "held"}, "K"), store.UNKNOWN)

    def test_live_without_attachment_when_holder_is_me(self):
        """显式（宿主）模式下不写附件：持有者是本会话即 live，不因缺附件被判 unknown。"""
        writer = self._writer(holder={"kind": "session", "id": "K", "generation": 2})
        self.assertEqual(store.lease_state(writer, "K", None, binding={"object": "t"}), store.LIVE)

    def test_unknown_when_bound_but_held_by_other_and_no_attachment(self):
        writer = self._writer(generation=3, holder={"kind": "session", "id": "N", "generation": 3})
        self.assertEqual(store.lease_state(writer, "K", None, binding={"object": "t"}), store.SUPERSEDED)
        writer_idle = self._writer(state="idle", generation=3, holder=None)
        self.assertEqual(store.lease_state(writer_idle, "K", None, binding={"object": "t"}), store.UNKNOWN)


class TestIdentityConflict(unittest.TestCase):
    """K1：宿主标识与进程锚不一致时不得猜（多源冲突交人钉住）。"""

    def test_no_conflict_when_anchor_points_at_me(self):
        routes = {"k1": {"owners": ["K"]}}
        self.assertEqual(store.conflicting_owners(routes, ["k1"], "K"), [])

    def test_conflict_lists_other_owner(self):
        routes = {"k1": {"owners": ["OLD"]}, "k2": {"owners": ["OLD", "K"]}}
        self.assertEqual(store.conflicting_owners(routes, ["k1", "k2"], "K"), ["OLD"])

    def test_unregistered_anchor_is_not_a_conflict(self):
        self.assertEqual(store.conflicting_owners({}, ["k9"], "K"), [])


class TestAttachmentIdentity(unittest.TestCase):
    def test_verify_round_trip(self):
        issued = {"issued_id": "u-1"}
        key = S.records.sha256_hex(S.records.canonical_bytes({"provider": "wf", "identity": issued}))
        att = store.new_attachment(issued, "wf", key, root(), {"enabled": True}, "t0")
        self.assertTrue(store.verify_attachment_identity(att))
        att["identity"] = {"issued_id": "u-2"}
        self.assertFalse(store.verify_attachment_identity(att))


if __name__ == "__main__":
    unittest.main(verbosity=2)
