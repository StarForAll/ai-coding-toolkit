# 执行计划：dsh-trellis 对等性验证

## A. 已完成（本轮验证，未改代码）

| 步骤 | 内容 | 产物 |
| --- | --- | --- |
| A1 | 读取插件源码/已安装包、DSH 源码契约、Trellis 0.7.0-beta.4 DSH 模板与 Codex hook | 本文件 §B、报告 §2 |
| A2 | 建临时项目 `/tmp/dsh-trellis-parity-verify/proj`（`trellis init --codex --dsh`），另建 `plain`、`proj-fresh`、`proj-nogit` | 证据目录 |
| A3 | 跑 DSH 真实会话：no_task、planning、in_progress、spec deny/ticket/refresh、子代理 push、inline/auto 守卫、`trellis_wait`、子目录、skip、task_error、stale、非 Trellis | `/tmp/dsh-trellis-parity-verify/evidence/*.jsonl` |
| A4 | 跑 Codex 真实会话与真实 hook：UserPromptSubmit、PreToolUse deny-once、SubagentStart（父有/无任务）、task 生命周期、身份对照 | `evidence/codex-*`、rollout |
| A5 | 直载已安装插件模块执行 `/trellis-status`、`/trellis-finish`、`/trellis-doctor` | `evidence/s2-register.mjs` 输出 |
| A6 | 单测回归 | `evidence/unit-tests.log`（364/360/0/4） |
| A7 | `trellis update`、config 自动写入、安装版本对照 | `evidence/` 与报告 |
| A8 | 汇总问题清单与执行方案 | `research/verification-report.md` |

## B. 对照矩阵（执行记录）

见 `research/verification-report.md` §4；证据位置在各小节。

## C. 待用户确认后的修复计划（本轮不执行）

按严重级别排序；每项先给出方案选择，确认后才动代码。

### C1 角色误判（push/guard 假阳性，P2）

- 现象：普通子代理 prompt 只要提到 `trellis-agent-*` / `trellis-*` 就被当作角色派发；无任务时会拒绝。
- 影响：错误注入实现/检查角色契约；合法 generic 委派被拒。
- 候选：
  1. prompt 角色识别只接受“首行/专用标记”或 `Role:` 行；忽略路径限定（`.dsh/skills/...`）与普通叙述；更新 workflow/skills 的派发模板。
  2. 仅用 descriptor label（严格前缀）判定；prompt 不再参与；需要 Trellis 模板把角色名放进 description。
  3. 维持现状，只补 README 风险说明（不推荐）。
- 验证：新增单测（generic prompt mentions role / path mention / bare skill name）；真实会话复测 guard 与 push。

### C2 子目录相对路径 spec 漏注入（P2，双方共同）

- 现象：session cwd 为子目录、工具传 cwd 相对路径时，spec 匹配把路径按项目根解析，漏 deny；Codex hook 同样。
- 候选：
  1. DSH 插件：在 `spec-policy` 中用 `resolveWorkingDirectory` 解析相对路径；同时尝试 root 相对路径，取并集匹配（宁可多注入）。
  2. 仅修上游 Trellis hook（`normalize_repo_relative` 接受 cwd），两侧一致。
  3. 不改，文档声明“请使用绝对路径或仓库相对路径”（不推荐）。
- 验证：子目录会话 + `d.js`；根会话 + `src/d.js`；Codex hook 同 payload。

### C3 默认 inline + 自动改 config（P2，产品决策）

- 现象：首次会话自动把 `dsh.dispatch_mode: inline` 写入被跟踪的 `.trellis/config.yaml`；与 Codex 默认 auto 不同；`trellis update` 会把它标为“用户修改”；`trellis update -f` 会覆盖该段，下一次会话又写回；`.dsh` 被 `task.py` 无条件视为 sub-agent-capable，inline 下仍需 curated jsonl 或 `--allow-empty-context`；DSH 没有 inline 的 phase 变体，phase detail 仍教派发。
- 候选（详见 `research/remaining-issues-analysis.md` §A/D）：
  1. 默认 auto + 不写 tracked config（最接近 Codex；phase/gate 语义一致；auto 下需 jsonl）。
  2. 默认 inline + 不写 tracked config，并补 DSH-inline 的 phase 契约（需要上游 workflow 变体或 banner 显式覆盖）。
  3. 保留 inline，但只在用户确认后写（设置页/首次提示）。
- 验证：fresh 项目首次会话 `git status`；`trellis update --dry-run`/`-f`；`.dsh` 单独存在时的 `task.py start` 闸门；`get_context.py --platform dsh` 的 inline/auto 文本；inline/auto 两种模式的 breadcrumb、guard、task start。

### O1（忽略，非问题）Codex-in-DSH 身份优先级 —— 上游只读观察

- 结论：Trellis 官方 `resolve_context_key` 的优先级问题；官方源码只读、无修改权限。
- 处理：**不修复、不进入待办、不提议上游补丁**；仅在验证报告中作为边界观察记录。
- 若需要规避：操作层面避免从 DSH 托管 shell 启动 Codex 执行 Trellis 任务（边界说明）。

### O2（忽略，非问题）上游 Trellis DSH 文档/模板过期 —— 上游只读观察

- 结论：官方 `workflow.md`/`DSH.md` 的过期文案与 `run_in_background` 指引；官方源码只读、无修改权限。
- 处理：**不修复、不进入待办、不向上游提议补丁**；插件 0.1.6 的 banner/README 只做本地缓解，不改变上游文件。
- 验证：已记录 `get_context.py --platform dsh` 与真实 subagent 传参结果，作为边界证据。

### C6 trellis-headless 安装版本漂移（P3）

- 现象：web profile 0.1.5，trellis-headless 0.1.4；后者 stale 文案仍是 0.1.4 旧行为。
- 修复：更新 `trellis-headless` profile 到 0.1.5（重装或 link 已安装副本），重启后复测 stale。
- 验证：stale 会话输出专用正文 + bootstrap。

### C7 文档/契约补充（P3）

- `DSH.md` 表格补 spec 注入、subagent push、dispatch guard、身份细节。
- 插件 README 注明 prompt 角色识别的误判边界（或按 C1 修复后更新）。
- 说明 `dsh.dispatch_mode` 只被插件读取，Trellis 脚本仍读 `codex.dispatch_mode`；inline 下 `task.py start` 需 `--allow-empty-context`（banner 已提示）。

## D. 回归与验收

- 单测：`node --test "test/*.test.js"`（当前基线 364/360/0/4）。
- 真实会话：至少覆盖 no_task/planning/in_progress/stale/task_error/skip/非 Trellis、spec deny/ticket/refresh、子代理 push + wait、inline/auto 守卫。
- Codex 对照：UserPromptSubmit、PreToolUse、SubagentStart（父有/无任务）。
- 升级：临时项目 `trellis update --skip-all` 后插件仍工作；config 冲突可解释。
- 回滚点：每个修复独立可 revert；不触碰用户未提交改动。

## E. 闸门

- 本轮不执行 C1–C7；等待用户逐项选择方案（或整体确认）。
- 用户确认后才创建实现计划变更、跑单测与真实复测；提交另行请示。

## F. 用户确认（2026-10-23）

- 模式：B（默认 inline + 不写 tracked config + 补 inline 契约）。
- 范围：C1、C2、C3、C6、C7。
- 配置写入：不写任何 tracked config。
- 上游 `~/projects/other/Trellis`：只读参考，无修改权限；U1/U2 按政策忽略，仅作为边界观察。
- 角色识别：专用 Role/首行标记 + description 严格；子目录 spec：cwd + root 并集。

## G. 实施结果（2026-10-23，未提交）

- 已按用户确认执行 C1/C2/C3/C6/C7；U1/U2 按“上游只读”政策忽略（不作为问题/待办）。
- 版本 `0.1.5 → 0.1.6`，client bundle 重建；`trellis-headless` profile 已安装 0.1.6。
- 单测 350 / 346 pass / 0 fail / 4 skip；真实会话复测见
  `research/verification-report.md` §9。
- Web profile 仍为 0.1.5，需用户确认后更新并重启 DSH。
- 未提交、未推送；等待提交授权。
