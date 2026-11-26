"""wflib.session 的锚点与唯一裁决单测（R1）。

覆盖 identity-redesign.md §2.3d 的三值证据与 `adjudicate()` 的每个 verdict 分支，
以及 R0 实测确认的边界（tmux 只有 L1、容器无锚、leader 先死无锚）。

所有用例只用**注入的 FakeProbe**，不依赖运行环境的真实进程表；
`TestRealProc` 一组例外：它只断言"同一进程内连续两次调用结果一致"这类可移植性质。
"""
import os
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LIB = REPO / "docs" / "workflows" / "wf" / "payload" / "lib"
sys.path.insert(0, str(LIB))

from wflib import session as S  # noqa: E402

BOOT = "boot-A"


class FakeProbe(S.Probe):
    """stat_of: pid → dict/None/OSError；exe_of: pid → 名字。"""

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
        info = self.table.get(int(pid))
        return (info or {}).get("exe")

    def name_of(self, pid):
        return self.exe_of(pid)


def proc(pid, start="100", ppid=1, state="S", exe="node"):
    return {"pid": int(pid), "comm": exe, "state": state, "ppid": ppid,
            "session": int(pid), "tty_nr": 0, "start": str(start), "exe": exe}


def l1(sid=4711, sid_start="100", boot=BOOT):
    return {"kind": "sid", "boot": boot, "sid": int(sid), "sid_start": str(sid_start)}


def root(pid=5538, start="100", boot=BOOT, exe="node"):
    return {"kind": "pid", "boot": boot, "pid": int(pid), "start": str(start), "exe": exe}


def sess(key, attached_l1=None, roots=()):
    return {"session_key": key, "attached_l1": attached_l1, "roots": list(roots)}


class TestKeys(unittest.TestCase):
    def test_sid_key_is_stable_and_boot_sensitive(self):
        a = dict(l1())
        b = dict(l1())
        self.assertEqual(S.anchor_key(a), S.anchor_key(b))
        c = dict(l1(boot="boot-B"))
        self.assertNotEqual(S.anchor_key(a), S.anchor_key(c))

    def test_pid_key_changes_with_start(self):
        self.assertNotEqual(S.anchor_key(root(start="1")), S.anchor_key(root(start="2")))

    def test_key_ignores_extra_fields(self):
        a = dict(root())
        b = dict(root(), extra="ignored")
        self.assertEqual(S.anchor_key(a), S.anchor_key(b))


class TestL1State(unittest.TestCase):
    def test_null_is_gone(self):
        self.assertEqual(S.state_of_l1(None, BOOT, FakeProbe()), S.GONE)

    def test_boot_mismatch_is_gone(self):
        self.assertEqual(S.state_of_l1(l1(boot="boot-old"), BOOT, FakeProbe()), S.GONE)

    def test_enoent_is_gone(self):
        self.assertEqual(S.state_of_l1(l1(), BOOT, FakeProbe({})), S.GONE)

    def test_starttime_mismatch_is_gone(self):
        probe = FakeProbe({4711: proc(4711, start="999")})
        self.assertEqual(S.state_of_l1(l1(), BOOT, probe), S.GONE)

    def test_zombie_is_gone(self):
        probe = FakeProbe({4711: proc(4711, state="Z")})
        self.assertEqual(S.state_of_l1(l1(), BOOT, probe), S.GONE)

    def test_unreadable_is_unverified(self):
        probe = FakeProbe({4711: proc(4711)}, unreadable={4711})
        self.assertEqual(S.state_of_l1(l1(), BOOT, probe), S.UNVERIFIED)

    def test_match(self):
        probe = FakeProbe({4711: proc(4711)})
        self.assertEqual(S.state_of_l1(l1(), BOOT, probe), S.MATCH)

    def test_corrupt_record_is_unverified(self):
        self.assertEqual(S.state_of_l1({"sid": "4711"}, BOOT, FakeProbe()), S.UNVERIFIED)


class TestRootState(unittest.TestCase):
    def test_pid_alive_dead_unverified(self):
        probe = FakeProbe({5538: proc(5538)}, unreadable={9999})
        self.assertEqual(S.state_of_root(root(), BOOT, probe), S.ALIVE)
        self.assertEqual(S.state_of_root(root(pid=1234), BOOT, probe), S.DEAD)
        self.assertEqual(S.state_of_root(root(pid=9999), BOOT, probe), S.UNVERIFIED)

    def test_pid_reuse_and_zombie_are_dead(self):
        probe = FakeProbe({5538: proc(5538, start="777"), 6000: proc(6000, state="Z")})
        self.assertEqual(S.state_of_root(root(start="100"), BOOT, probe), S.DEAD)
        self.assertEqual(S.state_of_root(root(pid=6000), BOOT, probe), S.DEAD)

    def test_boot_mismatch_is_dead(self):
        self.assertEqual(S.state_of_root(root(boot="boot-old"), BOOT, FakeProbe()), S.DEAD)

    def test_sid_root_is_judged_by_process_facts(self):
        """六轮复核 b.8：sid 型根必须查真实进程事实，不再"结构合法即 alive"。

        同一 boot 内会话已死亡时若仍判 ALIVE，写权/并发判定会永久卡住。
        """
        good = {"kind": "sid", "boot": BOOT, "sid": 4711, "sid_start": "100"}
        probe = FakeProbe({4711: proc(4711, start="100")})
        self.assertEqual(S.state_of_root(good, BOOT, probe), S.ALIVE)
        # sid_start 不符 = 进程被复用 = dead
        stale = {"kind": "sid", "boot": BOOT, "sid": 4711, "sid_start": "999"}
        self.assertEqual(S.state_of_root(stale, BOOT, probe), S.DEAD)
        # 进程已不存在 = dead
        self.assertEqual(S.state_of_root(good, BOOT, FakeProbe({})), S.DEAD)
        # 读不到 = unverified（不折成 alive）
        self.assertEqual(S.state_of_root(good, BOOT, FakeProbe({4711: proc(4711)}, unreadable={4711})),
                         S.UNVERIFIED)
        # 缺 sid_start 的损坏记录 = unverified
        self.assertEqual(S.state_of_root({"kind": "sid", "boot": BOOT, "sid": 1}, BOOT, probe),
                         S.UNVERIFIED)


class TestOtherRoots(unittest.TestCase):
    def test_excludes_current_root(self):
        state = sess("k", roots=[root(pid=1), root(pid=2)])
        self.assertEqual([r["pid"] for r in S.other_roots(state, root(pid=1))], [2])

    def test_sid_identity_uses_three_tuple(self):
        state = sess("k", roots=[{"kind": "sid", "boot": BOOT, "sid": 5, "sid_start": "1"}])
        same = {"kind": "sid", "boot": BOOT, "sid": 5, "sid_start": "1"}
        other = {"kind": "sid", "boot": BOOT, "sid": 5, "sid_start": "2"}
        self.assertEqual(S.other_roots(state, same), [])
        self.assertEqual(len(S.other_roots(state, other)), 1)


class TestAdjudicate(unittest.TestCase):
    def test_empty_candidates_is_new(self):
        self.assertEqual(S.adjudicate([], root(), "P1", FakeProbe())["verdict"], S.NEW)

    def test_single_gone_no_other_roots_use(self):
        probe = FakeProbe({})
        out = S.adjudicate([sess("k", l1(), [root()])], root(), "P1", probe)
        self.assertEqual(out["verdict"], S.USE)
        self.assertEqual(out["session_key"], "k")

    def test_unknown_root_blocks_use(self):
        probe = FakeProbe({}, unreadable={5538})
        out = S.adjudicate([sess("k", l1(), [root()])], root(pid=1111), "P1", probe)
        self.assertEqual(out["verdict"], S.BLOCK_EVIDENCE)

    def test_alive_other_root_blocks(self):
        probe = FakeProbe({5538: proc(5538), 6000: proc(6000)})
        state = sess("k", l1(), [root(pid=5538), root(pid=6000)])
        out = S.adjudicate([state], root(pid=9000), "P1", probe)
        self.assertEqual(out["verdict"], S.BLOCK_OTHER_ROOT)

    def test_two_gone_candidates_are_ambiguous(self):
        probe = FakeProbe({})
        states = [sess("k1", l1(sid=1), [root()]), sess("k2", l1(sid=2), [root()])]
        self.assertEqual(S.adjudicate(states, root(), "P1", probe)["verdict"], S.BLOCK_AMBIGUOUS)

    def test_l1_match_blocks_without_unknown(self):
        probe = FakeProbe({4711: proc(4711)})
        out = S.adjudicate([sess("k", l1(), [root()])], root(), "P1", probe)
        self.assertEqual(out["verdict"], S.BLOCK_OTHER_BOUNDARY)

    def test_l1_unverified_reports_evidence_unknown(self):
        probe = FakeProbe({4711: proc(4711)}, unreadable={4711})
        out = S.adjudicate([sess("k", l1(), [root()])], root(), "P1", probe)
        self.assertEqual(out["verdict"], S.BLOCK_EVIDENCE)

    def test_partial_gone_blocks_as_other_boundary(self):
        # sid=1 的 leader 不存在（gone）、sid=2 的 leader 存在（match）⇒ |C|>|G|
        probe = FakeProbe({2: proc(2, start="100")})
        states = [
            sess("k1", {"kind": "sid", "boot": BOOT, "sid": 1, "sid_start": "100"}, [root()]),
            sess("k2", {"kind": "sid", "boot": BOOT, "sid": 2, "sid_start": "100"}, [root()]),
        ]
        out = S.adjudicate(states, root(), "P1", probe)
        self.assertEqual(out["verdict"], S.BLOCK_OTHER_BOUNDARY)

    def test_p2_treats_l1_as_non_boundary(self):
        probe = FakeProbe({4711: proc(4711)})
        out = S.adjudicate([sess("k", l1(), [root()])], root(), "P2", probe)
        self.assertEqual(out["verdict"], S.USE)
        self.assertEqual(out["facts"]["anchor_degraded"], "l1-drift")

    def test_p2_ignores_l1_unverified_but_not_root_unverified(self):
        l1_unknown = FakeProbe({4711: proc(4711)}, unreadable={4711})
        self.assertEqual(S.adjudicate([sess("k", l1(), [root()])], root(), "P2", l1_unknown)["verdict"], S.USE)
        root_unknown = FakeProbe({4711: proc(4711)}, unreadable={5538})
        self.assertEqual(
            S.adjudicate([sess("k", l1(), [root()])], root(pid=1111), "P2", root_unknown)["verdict"],
            S.BLOCK_EVIDENCE)

    def test_invalid_path_rejected(self):
        with self.assertRaises(ValueError):
            S.adjudicate([], root(), "P9", FakeProbe())


class TestRealProc(unittest.TestCase):
    """只断言可移植性质（同一进程内稳定），不绑定具体 sid/pid。"""

    def test_candidates_stable_within_process(self):
        first = [S.anchor_key(a) for a in S.candidates()]
        second = [S.anchor_key(a) for a in S.candidates()]
        self.assertEqual(first, second)
        self.assertTrue(first, "当前环境应至少有一个锚点")

    def test_l1_matches_getsid(self):
        anchor = S.l1_anchor()
        self.assertIsNotNone(anchor)
        self.assertEqual(anchor["sid"], os.getsid(0))

    def test_missing_pid_is_none_not_error(self):
        """ENOENT 必须映射成 None（dead/gone），不能与读取失败混同（§2.3d 三值）。"""
        self.assertIsNone(S.Probe().stat_of(999999999))
        self.assertEqual(S.state_of_root(root(pid=999999999), BOOT, S.Probe()), S.DEAD)

    def test_l2_is_not_self(self):
        anchor = S.l2_anchor()
        if anchor is not None:
            self.assertNotEqual(anchor["pid"], os.getpid())
            self.assertNotIn(anchor["exe"], S.SHELLS_OR_UTILS)


if __name__ == "__main__":
    unittest.main(verbosity=2)
