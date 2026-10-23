# 技术设计：已安装 dsh-trellis 0.1.6 全面验证

## 1. 验证对象与环境

| 项 | 值 | 取证方式 |
| --- | --- | --- |
| 验证对象 | 已安装 `~/.dsh/profiles/web/node_modules/dsh-trellis` 0.1.6 | S1/S2/S3 |
| 源码参照 | `dsh-plugins/dsh-trellis` 0.1.6（已确认 lib/ 与安装副本逐字节一致，本轮开头复查） | S3 |
| DSH 宿主 | `dsh` 0.2.1-rc.2（真实 CLI） | S1 |
| Trellis | CLI 0.7.0-beta.4 + 只读上游 `~/projects/other/Trellis`（0.7.0-beta.4） | S1/S3 |
| Codex 对照 | codex-cli 0.163.0（真实 exec + hook） | S1 |
| 临时项目 | `/tmp/dsh-trellis-016-verify/proj`（`trellis init --codex --dsh`）及派生变体 | S1 |

## 2. 证据分级（结论必须标注）

- **S1**：真实 DSH 会话（真实 LLM + 真实工具调用）或真实 Codex 会话/hook 执行。
- **S2**：直载**已安装副本**模块执行（命令注册、doctor、路由、决策函数）。
- **S3**：源码/模板/脚本/hook 契约比对（安装副本 ↔ 源码 ↔ 上游 Trellis ↔ Codex hook）。
- **S4**：已安装副本（或源码）单测。
- 规则：S3/S4 只能支撑"契约存在/逻辑正确"，行为结论必须有 S1 或 S2；报告逐条标注。

## 3. 隔离策略（不污染真实环境）

- 新证据根：`/tmp/dsh-trellis-016-verify/`（不复用旧目录，避免旧状态串扰）。
- 真实会话用隔离 `DSH_HOME=/tmp/dsh-trellis-016-verify/home` + 独立测试 profile（`trellis-headless` 同款做法）：从本仓库源码安装 0.1.6，安装后**先 diff 证明与真实 web 安装副本逐字节一致**，再开始 S1——保证"测的就是已安装的代码"；差异如实记录。
- 真实 web profile 的 UI 面（settings 页/版本监控 banner）：仅当存在不暴露凭据的本地路径时做 S1；否则按 PRD Non-Goals 记录为验证限制，用 S2（路由直载）+ S4（client 单测）覆盖逻辑层。
- Codex 对照：同一临时项目内用 `codex exec` + 该项目 `.codex/hooks.json` 的真实 hook 路径执行。

## 4. 验证维度矩阵

| # | 维度 | 方法 | 等级 |
| --- | --- | --- | --- |
| V1 | 安装态：web 0.1.6、lib 一致性、headless profile 无插件的影响与定性 | diff + profile 清点 | S3 |
| V2 | 面包屑全状态：no_task/planning/in_progress/stale/task_error/completed、未变不重复、skip 关键词 turn 级、非 Trellis 零注入 | 真实会话逐状态 + `--json` 事件流 | S1 |
| V3 | bootstrap：每会话一次、压缩后重注入、子代理不注入、与面包屑解耦 | 真实会话 + resume/compaction 触发 | S1 |
| V4 | 会话身份：DSH_TRELLIS_CONTEXT_ID、task.py current 解析、子代理转发身份、命令子进程身份 | 真实会话 + .trellis/.runtime/sessions 指针取证 | S1 |
| V5 | 子代理 push：角色契约 + curated context、`Active task:` 首行优先、父指针回退、双缺失静默；C1 回归（generic/路径提及/话题型 description 不误判；首行前缀/Role: 行/派发语/description 严格前缀正确命中） | 真实子代理会话（implement/check/research/generic 各类 dispatch） | S1 |
| V6 | dispatch guard：无任务 implement/check fail-closed、research 输出位置提醒 | 真实会话 | S1 |
| V7 | trellis_wait：continuable 后台派发 → 独立工作 → wait 汇合；completed/failed/aborted/unknown fail-closed | 真实会话（含一次故意失败子代理） | S1 |
| V8 | spec 注入：deny-once → ticket → refresh 窗口；持久化分片；损坏回退；compaction 重置；tools 大小写；read 不阻断；C2 回归（子目录 cwd 相对路径并集匹配） | 真实会话 edit/write/read + 分片文件取证 + S2 决策函数 | S1+S2 |
| V9 | 模式：默认 inline 只读、不写 tracked config（C3 回归，fresh 项目 `git status` 取证）；显式 auto 派发链路；banner 契约；task.py start 闸门与 `--allow-empty-context` | 真实会话 + fresh 项目 diff | S1 |
| V10 | 命令面：/trellis-status、/trellis-finish（零输入、拒参数/图片、非 Trellis 项目提示）；旧版 Trellis 回退用 S2 模拟 | 真实会话调用 + S2 | S1+S2 |
| V11 | settings/doctor/版本监控/冲突检测：路由与决策逻辑 | S2 直载已安装模块 + S4 | S2+S4 |
| V12 | 升级/安装形态：`trellis update --skip-all` 后插件功能仍在；C6 回归（版本一致性；headless profile 缺插件的定性） | 临时项目升级 + 复测面包屑 | S1 |
| V13 | Codex 对照基线：UserPromptSubmit bootstrap/状态、PreToolUse deny-once、SubagentStart push（父有/无任务）、stale 行为 | 真实 `codex exec` + hook 日志 | S1 |
| V14 | Trellis 原生 DSH 支持（class-2 pull）不被插件破坏：`.agents/skills`、`.dsh/skills`、`.dsh/DSH.md`、`get_context.py --platform dsh`、task.py 闸门；push 与 child-pull 叠加一致 | 临时项目资产清点 + 真实会话验证 pull 仍可用 | S1+S3 |
| V15 | 多会话并发：两个并发会话各自 spec 分片互不串扰；`--session-id` resume 后 projection 去重 | 真实会话并发 + 分片文件 | S1 |
| V16 | 补足评估：DSH 裸用 Trellis（无插件）能做什么/缺什么 → 插件逐项补足判定 | 裸 profile 真实会话抽样 + 机制比对 | S1+S3 |

## 5. 问题分类与编号

- `P#`：插件缺陷（可修，候选方案进执行方案）。
- `X#`：双方共同缺陷（Codex 也有；修插件侧需声明不对称性）。
- `H#`：DSH 宿主限制（记录边界，除非插件层有可行缓解）。
- `O#`：上游 Trellis 只读观察（不进问题清单/修复项，只记边界）。
- 每项含：严重级别 P0–P3、复现步骤、证据路径、影响面、候选修复方案（含推荐）。

## 6. 判定"补足"的基准（R5）

以三项并列基准判定，不以 Codex 为唯一标准：
1. **Codex 接线面**（V13 实测）：达到同等效果 / DSH 增强 / DSH 不及。
2. **Trellis 原生 DSH 契约**（V14）：插件不得破坏原生 pull；push 层是否补上 pull 层缺失的"自动注入"。
3. **DSH 裸用差距**（V16）：无插件时的实际缺口清单 → 插件逐项覆盖判定。

## 7. 修复闸门与回滚

- 本任务验证阶段零仓库修改：`git status` 除既有两个未跟踪文件外不得新增/变化。
- `/tmp/dsh-trellis-016-verify/` 与隔离 DSH_HOME 内的任何写操作不受限。
- 用户确认问题清单与执行方案后，修复工作在本任务内继续（不另开任务），逐项独立可 revert；提交另行请示。

## 8. 风险与限制（预先声明）

- web UI 若无法在凭据安全前提下进入，UI 面降级为 S2+S4 并如实标注。
- 真实 LLM 会话存在非确定性：每维度至少 2 次关键路径复现或 1 次成功 + 事件流证据；结论写明观测次数。
- 上游 Trellis 与本机 CLI 若有 patch 差异，以本机 0.7.0-beta.4 行为为准并记录。
