# 核验台账（主会话逐条对照源码/实测会话，不采信任何报告结论）

证据来源：
1. 四份 dogfood 实测会话 `/tmp/traffic_monitor_1..4.md`（对应 `~/.codex/sessions/2026/11/08/rollout-*.jsonl`）
2. `/tmp/wf-find-a.md`（人工介入时间线 + 增量发现 1–15）
3. `/tmp/wf-find-b.md`（F09–F23 逐项状态）
4. 参考（非本轮报告、部分已陈旧）：`/tmp/wf-find-c.md`、`/tmp/wf-find-d.md`
5. 源码：`docs/workflows/wf/payload/**`（0.1.6 源码树）、`docs/workflows/wf-framework-*.md`
6. `git tag -l`、`scripts/build-wf-release.py`、`scripts/tests/wf_runtime/**`

## A. a/b 点名项逐条判定

| 编号 | 判定 | 决定性事实（可复核） |
|---|---|---|
| a-1 多根下 keep/restore 丢根身份 | **成立（P1）** | `install.py:1349-1357` N 侧键为 `(base, rel)`，skill_root 会展开成安装记录 `roots` 里**每个**根；`1358-1359` 却把 `--keep/--restore` 收成 `rel` 集合，`1373-1379 / 1402-1411 / 1427-1434 / 1469-1472` 全按 `rel in keep_rels` 匹配 → 同名副本无法分别处置。`1740-1764` 预览 `selected_paths/risks`、`1583-1591` 导出清单、`1895-1900` 安装记录 decisions 也都只写 `relative`。`cli.py:2989` 帮助写"相对项目根"，与匹配用的资产相对路径不一致。多根条件真实存在：`install.py:710-742` 只有 `claudecode` 是 `reads_shared=False`（`.claude/skills`），其余全部落 `.agents/skills`；claudecode + 任一共享平台即两根本同 rel。 |
| a-2 task-retrospect 帮助与必填冲突 | **成立（P2）** | 帮助 `cli.py:3031-3034`：`--evidence` 标"可选"、`--decision` 标"必填"；handler `tasks.py::cmd_task_retrospect`：`if not task_id or not evidence_path: WF_USAGE_INVALID`，`--decision` 缺失可继续。**额外发现（同类）**：帮助登记的 `--commit` 在该 handler 中从未读取（幽灵旗标）。 |
| b-P0 发行 tag 义务未履行 | **成立（流程缺口，P0 级后果）** | `git tag -l` 仅 `wf-v0.1.0`；`scripts/build-wf-release.py:77-84` 只"已存在则拒绝重建"，从不校验 tag 是否应存在或与树一致；`install.py:24 REF_RE` + `rev-parse` 使无 tag 即无法安装/升级；`README.md:18` 却记载 0.1.5→0.1.6 可用 upgrade 升级。⇒ 文档承诺的升级路径在字段上不可执行；0.1.5 自举实跑只能依赖临时/事后清理的引用。 |
| b-P1 升级不覆盖 hooks.json | **成立（P1）** | `merge_hooks_json` 只在 `install.py:1066`（add_platforms）与 `2217`（首装）调用；`run_upgrade` 的 apply 段（`1876-1971`）只写资产字节与清单、跑 `self_check`；`self_check`（`584-640`）对 `host_hook` 只核脚本文件 digest，不核 `.codex/hooks.json` 条目。⇒ 一旦某版改 hook 落点/命令串，已升级项目带着失效条目运行（退化方向 = M1 身份错配），且自检报绿。 |
| b-P2 #1 dsh/zcode 身份 unknown | **部分成立、表述不准确** | 实现稿 `wf-framework-implementation.md:516` 已声明"DSH 维持显式信封通道…不为 DSH 新增 hook/映射机制；zcode/pi 维持 unknown"。部署表 `install.py:715` 对 dsh 写 `env:DSH_SESSION_ID`（`source=user-declared`），但**全仓无消费者**（`grep DSH_SESSION_ID` 仅表内与注释；宿主映射唯一写者是 codex hook）。⇒ 摩擦真实（无适配层宿主运行期等同不可区分），但"uknown"对 dsh 不准确——准确说法是"声明值只在适配层/显式信封可见，运行期不可区分"。 |
| b-P2 #2 审批决定代笔 | **成立但属已声明边界** | `wf-framework-design.md:38`（强度如实声明）+ `:68`（不代人作答）已把"模型伪造人判不可辨"写成声明边界；`--draft` 骨架（`cli.py:2746/2795/2806/3002/3006`）已消除"靠报错试错"。不新增伪造防护（§1.5 明确不建立证据链）。 |
| b-P2 #3 review-context 需已发起轮 | **驳回（设计正确）** | 材料面与"允许自主读取"由 launch 声明并绑定本轮锚点（`design §6.5`）；launch 前的材料外发没有人的本次范围授权，预取会绕开 `authorize record export`。入口维持现状。 |
| b-P3 `--changes` 同名异构 | **成立（低危）** | `cli.py:2780-2790`（task-knowledge：`action/path/reason/summary`）vs `2827-2834`（spec-update：`operation/new_paths/old_paths/content`）；双侧 `--changes-draft` 已存在。本轮只加双向提示，不改 schema（b 自评"登记即可"；改名会动已发行帮助面）。 |

## B. b 报告已陈旧（不得据其修）

| 条目 | 事实 |
|---|---|
| F13 "未跟踪新文件内容不进 diff" | **不成立**：`review.py:2723-2791 materialize_delivery` 对 `??` 用 `git diff --no-index /dev/null <path>`，且以任务基线提交为 base（中途提交也可取差异）。 |
| F18 后半 `workflow_snapshot_digest` 恒 None | **不成立**：`check.py:106` 有实现，`:194` 进锚点。 |
| F09/F11/F12 部分缺口 | 需按当前源码复核后再判（本轮不据此立项）。 |

## C. c/d 报告（上一轮已收口，仅作背景）

- d-F03「generation 需手拼」不成立：`cli.py:27-37 resolve_generation` 缺省回退 session-runtime 记录。
- c 的 `AGENTS.md:25` 陈旧表述、README skills「11 个」均已不存在（现 13 个且 AGENTS.md 已更新）。
- d-F20「工作区无关改动无排除通道」不成立：`scope.py:439-580` 已实现 `workspace_exclusions` + `--workspace-exclusion`。
- d-F22「archive 无 --preview」不成立：`archive --draft` 已交付。

## D. 主会话自行发现（同类、未被 a/b 点名）

1. **委托型命令的一致性断言实际为空**：`scripts/tests/wf_runtime/test_help_domains.py::RegistryCompletenessTest` 用闭包 `cell_contents` 取源码，而 `_task_command` 的闭包只含字符串 `name`（`cli.py:2585-2591`）→ `srcs` 为空 → `if not flags: continue`，20 余个 tasks 命令根本没被覆盖。`test_every_documented_flag_is_in_registry` 只核注册表面，不核"该命令是否真的消费"。
2. **`task-knowledge --evidence` 是幽灵旗标**：`tasks.py::cmd_task_knowledge` 从不读该参数，`task["knowledge"]["evidence"]` 恒 `[]`；帮助却写"updated：知识变更的证据"。
3. **§1.1 陈旧句**：`wf-framework-design.md:58`「固定流转程序化」清单仍写"三方升级匹配（本轮随 §7.2 upgrade 交付；未交付期间该条为登记缺口…）"，而 upgrade 已于 0.1.5 交付。
4. **§1.1 人签封闭清单不完整**：`:44` 的封闭清单未列"机械修订的等价性签认"，而实现（`task-approve` choice=机械修订）与 W1-a2 裁决都要求人签。
5. **§1.1 措辞偏窄**：`:44`"机制侧只提供它需要的事实（`facts`/`next`）"未覆盖 `exits` 令牌表与 `--draft` 骨架，读者易把两者读成越层。
6. **部署表声明冒充能力**：`install.py:707-742` 的 `session_identity` 注释未说明"未交付适配层的宿主运行期等同 unknown"（见 A 表 b-P2#1）。

## E. 归入本轮 / 不归入本轮的判定依据

- 归入：能在既有入口内由明确输入稳定计算或稳定核对（路径身份、必填声明、hooks.json 条目、tag↔树↔清单），且已有观察到的失败实例。
- 不归入（交人裁）：同轮报告修订（11-21 已裁"维护导入后不可覆盖"）、审批代笔的防伪强化（§1.5 声明边界）。