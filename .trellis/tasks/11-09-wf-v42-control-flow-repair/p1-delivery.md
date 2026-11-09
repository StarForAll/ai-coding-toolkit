# P1 交付记录（K1/K2 身份与租约 + §2 授权边界）

前置：身份口径已由人裁定（见 [decision-identity.md](./decision-identity.md)），上位文档同批修订（见 [revision-identity.md](./revision-identity.md)）。本文件记录 P1 的代码与验证。

## 1. 改动清单（文件 → 动机 → 编号）

| 文件 | 动机 | 编号 |
|---|---|---|
| `payload/lib/wflib/identity_store.py` | 删 `S0–S4` / `five_state` / `can_override_evidence_unknown` / `rotate` / `mark_superseded` / `valid_sessions` / `migration_candidates`（v42 §4 必删；均已无调用点），新增租约**投影** `LIVE/SUPERSEDED/GONE/UNKNOWN`、`boundary_alive`、`lease_state`、`conflicting_owners` | K2、K1、§7.1 |
| `payload/lib/wflib/cli.py` | `enable` 增 `--identity host` 钉住、身份事实（`source`/`host_identity_absent`/`clear_indistinguishable`/`anchor_conflict`）、冲突不猜（`WF_IDENTITY_UNRESOLVED` + 两条出口）；`status` 增 `lease.state` | K1、K2、S9 |
| `payload/protocol/thresholds.json` | 增 `identity_path`（枚举 P1/P2/P3，缺省 P1） | 机制稿 §8.1 |
| `payload/lib/wflib/protocol.py` / `config.py` | 支持 `enum` 类型与非法值阻断（`WF_RECORD_INVALID`） | 纪律 #4 |
| `scripts/wf-protocol-docs.py` | 解析「枚举 …，缺省 X」行并比对取值集合 | 不变量⑤ |
| `scripts/tests/test_identity_store.py` | 删除测五态的用例（被测对象已删），补租约投影与身份冲突用例 | K1/K2 |
| `scripts/tests/wf_identity/test_identity_lease.py` | 新增 P1 用例（`/clear`、冲突钉住、接管 bump、§2 边界） | K1/K2/§2 |
| `wf-framework-design.md` / `.index.md` / `wf-framework-mechanism.md` / `wf-framework-implementation.md` | 身份取用次序与 `identity_path` 登记（详见 revision-identity.md） | 裁定 |

## 2. 关键判据（实现层）

- **租约是投影，不落盘**：`lease_state` 由 `writer.json` + 附件 + 锚点存活派生，判据顺序固定（记录可解释 → 谁持有 → 边界是否存活）。失效由 `generation` 比较表达，因此不需要第二套状态机（v42 §4 删 `five_state/rotate/mark_superseded` 的覆盖者就是这里）。空口无凭的"顺序两任务/接管"从此可机械复算。
- **冲突不猜**：锚点指向别的会话时，`enable` 直接 `WF_IDENTITY_UNRESOLVED`，两条出口（`--identity host` 钉住 / 换新会话）；钉住写进 **runtime 附件**（`identity_pin`），不进 committed——它是会话级事实，S10 不允许把运行态写进库。
- **看不见 `/clear` 必须说出来**：只有进程锚时 `facts.identity.clear_indistinguishable = true`，并在 `warnings` 里显式列出"该宿主无法区分 `/clear`"，不静默复用旧绑定。
- **§2 授权边界**：确认令牌（`preview_token` / `WF_PREVIEW_STALE`）只允许出现在维护入口；语义层（`cli`/`tasks`/`gates`）一旦出现即判红。

## 3. 验证记录

| 命令 | 结果 |
|---|---|
| `python3 -m unittest discover -s scripts/tests -t . -q` | **通过** `Ran 98 tests … OK`（基线 81 → 88（P0）→ 97 → 98） |
| `python3 -m unittest scripts.tests.wf_identity.test_identity_lease -q` | **通过** `9 tests OK` |
| `python3 -m unittest scripts.tests.test_identity_store -q` | **通过** `19 tests OK`（含替换后的租约/冲突用例） |
| `python3 scripts/wf-protocol-docs.py --check` | **通过** 35 码 / **16 配置键** / 11 条转移 |
| `python3 scripts/validate-wf-design.py` | **通过** 定义命中 100% / 消费点命中 100% / 输入摘要 4/4 |
| `python3 scripts/check-doc-refs.py` | **通过** `0 problem(s)` |
| `python3 scripts/build-wf-release.py --verify` | **通过** `byte reproduction (0.1.0, 63 assets)` |

## 3.5 真实部署验证（2026-11-09，已按要求清理）

**部署**：`bash scripts/tests/wf_runtime/full/wf_fixture.sh /tmp/wf-fixtures/p1check`（开发态部署到仓库外临时夹具，`--platform dsh`）。
**驱动**：临时脚本（验证后删除）按真实 CLI + 请求信封跑 14 项断言。

结果 **14/14 通过**：

| 断言 | 观测 |
|---|---|
| 部署含新资产类 | 夹具 `.wf/protocol/` 5 个文件齐全；`.wf/install/installation.json` 62 项资产 |
| `enable` 宿主身份 | `WF_OK`，`identity.source=host`、`host_identity_absent=false`、`anchor_candidates=2` |
| S1 建任务并持租约 | `task-new A` → `WF_OK`，`status.lease.state=live` |
| 顺序两任务的互斥 | S2（另一宿主会话）抢写权 → `WF_WRITER_BUSY` |
| 正常释放前置 | `task-pause A` → `writer release` 均 `WF_OK`（未暂停时 release 被拒，符合设计稿 §4.4） |
| 接管 bump generation | S2 `task-new B` → `WF_OK`，generation **4 → 5** |
| 旧租约失效 | S1 旧写入 → `WF_WRITER_BUSY`；S2 旧请求代次 → `WF_GENERATION_STALE` |
| 租约投影 | S1 `status.lease.state=superseded`；S2 `status.lease.state=live` |

**部署验证发现并修复的缺陷**（真机才暴露）：

- `lease_state` 把"附件缺失"当作"证据不足 → unknown"，但**显式（宿主身份）模式不写附件**（附件是自动模式的载体），导致真实持有时租约被判 `unknown`。
- 修复：判据改为「记录可解释 → holder 是否他者 → 有附件才核边界存活 → holder 是本会话即 live → 有绑定但附件缺失且非本会话才 unknown」，并补两条用例（`test_live_without_attachment_when_holder_is_me`、`test_unknown_when_bound_but_held_by_other_and_no_attachment`）。
- 该缺陷只在部署后暴露：单测默认给附件、CLI 也拿不到"显式模式无附件"这条事实。

**清理**：夹具目录、临时驱动、`/tmp/deploy.log` 已删除；`~/.wf/interpreters.json` 与部署前快照逐字节一致（`68a9e265…70f6`），无残留。

## 4. P1 五条用例的覆盖状态

| 用例 | 状态 | 覆盖点 |
|---|---|---|
| 顺序两任务 | **覆盖（真机）** | 部署夹具内 S1 建 A 并暂停释放 → S2 接管建 B；`generation` 4→5；互斥与释放前置均按设计稿 |
| `/clear` 后新任务 | **覆盖（身份层）** | 不同宿主 `session_id` ⇒ 不同 `session_key`；只有进程锚时显式声明看不见 `/clear` |
| 冲突钉住 | **覆盖** | `conflicting_owners` 两种形态（锚点指向我 / 指向他人）+ 钉住写入 runtime + 附件缺失时阻断 |
| 旧租约接管 | **覆盖（真机 + 单测）** | 真机：S1 旧写入 `WF_WRITER_BUSY`、S2 旧代次 `WF_GENERATION_STALE`、S1 租约 `superseded`；单测：代次递增与 `require_supported` 拒绝 |
| 批准范围内修改免确认 | **覆盖（边界）** | 语义层不得出现 `preview_token`/`WF_PREVIEW_STALE` |

## 5. 已知未完成 / 待下一轮

1. ~~顺序两任务的端到端用例~~ → 已由 §3.5 的真实部署验证覆盖（临时驱动，未入库）。
2. **`/clear` 的端到端验证**：需要真实宿主在不同 `/clear` 后给出不同 `session_id` 的观察证据；当前只验证了身份派生层。
3. **`enable --identity` 只接受 `host`**：`anchor`（以锚点会话为准）等价于接管另一会话，涉及 K2 的两段交接，未在本轮实现；`--identity anchor` 明确拒绝（`WF_PATH_INVALID` + known=["host"]），不静默接受。
4. 实现稿的身份传输契约（信封有无 `session` 对象）已按新次序补了消费者清单，但"宿主优先"的传输描述随 P1 剩余项一起收尾。
