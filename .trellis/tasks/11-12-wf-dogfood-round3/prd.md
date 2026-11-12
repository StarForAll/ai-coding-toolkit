# wf 第二轮 dogfood 缺陷修正（材料/代次/契约一致性）

## Goal

把 traffic_monitor dogfood 后两份分析报告中被源码核实为真的**确定性缺陷**在 wf 模块内修掉，
并让实现、指引与发行树重新自洽。用户价值：下一次 dogfood 的审查材料可信、写命令不再靠模型
手工带代次、`next`/帮助/骨架不再把模型引到错路。

## Background

- 输入证据：4 份 dogfood 会话导出（`/tmp/traffic_monitor_1..4.md`）、ZCode 日志（仅协议遥测，
  无 reviewer 正文）、两份既有分析（`/tmp/wf-find-a.md`、`/tmp/wf-find-b.md`）、两份第 1 轮复核输出
  （agent a / agent b，见用户消息）。
- 本轮对上述结论逐条重核源码；**采信以代码证据为准**，不采信未复现的推断。
- 范围由用户在 2026-11-12 明确：只要范围 A（确定性缺陷），B（脱敏/外发授权收紧）与
  C（未提交越界改动归属通道）本轮不做，必须登记为后续项。

## 已核实事实（含证据锚点）

- **F1 材料漏未跟踪文件内容**：`review._material_diff()` 仅调用 `git diff [HEAD] -- path`
  （`docs/workflows/wf/payload/lib/wflib/review.py:1112-1149`），未跟踪文件两种调用都输出 0 字节；
  异常被 `except Exception: owned = []` 吞掉，最终写成 `# 无工作树差异`（同文件 `:1186`）。
- **F2 交付集合三处各拼**：`check.object_paths()` 只取 e 桶（`check.py:28-45`）；材料取 e∪f
  （`review.py:1120`）；`check.run_check_scope()` 把已批准扩面的 f 并进 e 只用于展示
  （`check.py:767-779`）。扩面路径因此可能进材料却不进 Check 内容指纹。
- **F3 自动模式代次断裂**：`Context.inputs()` 只读显式信封（`cli.py:388-391`），
  `require_held()` 强制要求 `inputs.generation`（`cli.py:493-498`）；而 `wf-start`
  第 5 步与 `wf-finish` 都宣称“自动模式下不需要手写信封”（`skills/wf-start/SKILL.md:28`、
  `skills/wf-finish/SKILL.md:55`）。自动身份已含 `provider=wf`，`participant_cli` 因此要求
  `--as`（`review.py:84-102`），而 `wf-review` 技能仍称“输入只有任务 id 与轮次”。
- **F4 Check pass 路由不分复杂度**：`task-check` 的成功回显固定为“人了解结果后调用 finish”
  （`tasks.py:2645`），复杂任务实际要先 `review-launch`。
- **F5 报告骨架过薄**：`review.context()` 只写两行占位（`review.py:1213-1214`），
  协议块、字段集与 lint 提示都缺席；`wf-review` 技能仍让 reviewer 写已不在
  `REPORT_FIELDS` 的 `scope-exceptions`（`skills/wf-review/SKILL.md:36,45`）。
- **F6 帮助与取值域漂移**：`task-approve` 帮助写 `approve|approve-light|approve-complex|mechanical`
  （`cli.py:2072`），登记域只有 `approve/批准` 与 `机械修订`
  （`decisions.py:22-30`）。
- **F7 文档/发行漂移**：
  - `AGENTS.md:25` 仍写 wf 源树“path is empty”，与现有完整源树矛盾；
  - `docs/workflows/wf/README.md:4,78,86` 称 11 个 skill，实际 13 个；
  - 设计稿 §301 把“会话绑定、项目写入权记录”列入“登记进 Git”，与
    `scripts/wf_release_common.py:20-26` 的 gitignore 清单（含 `/.wf/session-bindings/`、
    `/.wf/writer.json`）冲突；机制稿 §10.1 的运行态表只列 `.wf/.runtime/` 与 `.wf-lock`，
    三处对“忽略集合”没有单一枚举；
  - `payload/install.py:397` 的托管段回退值只有两条，与清单五条不同源。

## Requirements

- **R1 交付集合单一实现**：新增 `scope.delivery_set()` 作为唯一来源（e ∪ 已批准扩面的 f ∪
  策展输入 ∪ `.wf/baseline.md`/`.wf/project-config.json`，排除 vendor），`check.object_paths`
  与审查材料都消费它；未获批准的 f 仍由 Check 阻断。
  验收：已批准扩面的新路径出现在 `check.anchor.object_paths` 与内容指纹输入中；
  未批准时 Check 依旧 `WF_SCOPE_VIOLATION`。
- **R2 材料物化单一实现**：新增材料生成函数，按 git 状态逐路径产出片段——
  未跟踪文件用 `git diff --no-index`（含内容）、已跟踪用 `diff HEAD`、删除给删除 hunk、
  二进制给显式标记；任何取片段失败进 `materials/status.json.problems`，不再写成“无差异”。
  验收：(a) 未跟踪新文件内容出现在 `diff.patch`；(b) 生成失败时 `problems` 非空且
  `diff.patch` 不含“无工作树差异”伪结论；(c) 真正无可交付路径时 `empty=true` 且文案不暗示“已审查”。
- **R3 代次由会话运行态携带**：写权持久化时把 `generation` 同步进该会话运行态侧车
  （`.wf/.runtime/sessions/<key>.json`，与游标字段合并写入）；`require_held()` 优先显式
  `inputs.generation`，缺失时取本会话侧车值并核对，绝不读取 writer 当前代次。
  验收：(a) 自动模式下取得写权后，不传 generation 的写命令成功；(b) 侧车代次与 writer 不符
  仍报 `WF_GENERATION_STALE`；(c) 显式值优先且不被侧车覆盖。
- **R4 契约回显与骨架一致**：`task-check` pass 的 `next_` 按 `plan.complexity` 分流
  （complex → 先 review-launch）；`review-context` 落盘**完整报告骨架**（状态行、协议标记、
  预填 `task-id`/`round`/`check-anchor`、五轴与 findings 空位、lint 提示）；`wf-review` 技能
  与实现对齐（去掉 `scope-exceptions` 漂移、写明自动模式 `--as`、提交前跑 `wf lint report`）。
- **R5 帮助取值域单一来源**：`task-approve` 的 `choice` 帮助由 `decisions.DOMAINS` 生成；
  新增断言防止帮助与登记域再次漂移。
- **R6 文档与发行对齐**：修 `AGENTS.md`、`wf/README.md`（11→13）；把 gitignore 忽略集合
  定为清单单一枚举并同步设计稿 §301、机制稿 §10.1 表、实现稿目录注释；`install.py`
  托管段回退改为“缺 `gitignore_managed.lines` 即明确拒绝”，不再维护第二份常量。
- **R7 发行与验证闭环**：`dev-manifest.json` 与本轮改动同步（如新增资产），重建
  `docs/workflows/wf-release/`，跑第 8 节最小证据集。

## Acceptance Criteria

1. `python3 -m unittest discover -s scripts/tests` 与 `... -s scripts/tests/wf_runtime` 全绿，
   且新增用例能区分 R1/R2/R3/R5 的缺陷（人为回退实现时变红）。
2. `bash scripts/tests/wf_runtime/full/run_all.sh` 通过，或失败的套件给出失败命令、关键错误与归因。
3. `python3 scripts/build-wf-release.py --verify` 与 `--verify-token-parity` 通过。
4. `python3 scripts/validate-wf-design.py`、`python3 scripts/check-doc-refs.py`、
   `./scripts/validate-skills.sh` 通过。
5. 交付前复核 `git diff`，确认未改动任务范围外的文件，且未提交用户工作区里的其他改动。

## Out of Scope（登记，不实现）

- **B 安全收紧**：`authorize.redact()` 仍是黑名单（`authorize.py:45-70`）；`review.launch()`
  只核 export 授权“存在”（`review.py:984-996`）。属语义变更，需与协议文件、机制稿同批改。
- **C 未提交越界改动的归属/隔离通道**：机制稿 §33 的 f 档声明“含未提交”，但
  `scope.classify_candidates()` 的 `owned` 只由提交归属与批准 glob 得出（`scope.py:440,471-478`），
  `task-attribute` 只接受 `--commit`（`tasks.py:2748-2774`）；c 桶因此无出口
  （`check.py:786-787`）。需要新增路径归属语义与设计稿/机制稿登记，单独一轮。
- `workflow_snapshot_digest` 恒 `None`（`check.py:135`）、`read_agent_status` 只读前 400 字符
  （`review.py:118-125`）、`review-launch` 请求仍需手写 JSON：本轮只做已被 R4 覆盖的部分。
- 不修改 `~/projects/personal/traffic_monitor` 目标项目；不代跑人的终端确认。

## Key Decisions

- 交付集合与材料生成都收进 `scope` / `review` 的单一函数，调用点只消费（纪律 #4），
  不给三处各补一段 diff 逻辑。
- 代次用“会话运行态侧车”而**不**抄 writer 当前值：侧车记录的是调用者自己取得写权时拿到的代次，
  侧车陈旧仍会被拦，显式信封保持优先。
- 文档冲突以“发行清单的 `gitignore_managed` 为单一枚举”收口，不按某一处旧文改实现。
- B/C 两项不做，但保留证据锚点与验收方向，避免下轮重新推导。

## Open Questions

（无；B/C 已由用户明确排除并登记为后续项。）
