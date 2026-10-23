# 技术设计：已安装 dsh-trellis 对等性与补足独立复验

## 1. 验证对象与基线

| 项 | 值 | 取证方式 |
| --- | --- | --- |
| 验证对象 | 已安装 `~/.dsh/profiles/web/node_modules/dsh-trellis` = 0.1.6 | S1/S2/S3 |
| 源码参照 | `dsh-plugins/dsh-trellis` = 0.1.7；`lib/` 与安装副本仅 `client.js` 的 `PLUGIN_VERSION` 不同 | S3 |
| DSH 宿主 | `dsh` 0.2.1-rc.2（真实 CLI，`dsh --profile <p> headless`） | S1 |
| Trellis | CLI + 只读上游 `~/projects/other/Trellis` 均 0.7.0-beta.4 | S1/S3 |
| Codex 对照 | codex-cli 0.163.0（真实 `codex exec` + 隔离 `CODEX_HOME` 尝试 hook） | S1/S2 |
| 临时项目 | `/tmp/dsh-trellis-reverify-1023/proj` 及派生变体 | S1 |

**安装态判定原则**：S1 一律在隔离 `DSH_HOME` 的测试 profile 中运行，该 profile 的 `node_modules/dsh-trellis` 必须**直接复制自真实 web 安装副本**，运行前用 `diff -rq` 证明两者一致；源码 0.1.7 只用于差异说明，不参与 S1。若 0.1.7 相对 0.1.6 只有文档/版本 stamp 差异，报告中明确"被测运行时 = 0.1.6 = 0.1.7 逻辑"。

## 2. 证据分级

- **S1**：真实 DSH 会话（真实 LLM + 真实工具调用）或真实 Codex 会话/hook 执行。
- **S2**：直载已安装副本模块执行（命令处理器、doctor、路由、spec 决策、hook payload 直调、compaction 处理）。
- **S3**：源码/模板/脚本/hook 契约比对（安装副本 ↔ 源码 ↔ 上游 Trellis ↔ Codex hook ↔ DSH 宿主 API）。
- **S4**：单测（`node --test "test/*.test.js"`，源码基线 350/346/0/4；如可行对安装副本跑同套测试）。
- 规则：行为结论必须有 S1 或 S2；S3/S4 只支撑契约/逻辑存在。每个结论在报告中标注等级与证据路径。

## 3. 隔离与安全设计

- 证据根：`/tmp/dsh-trellis-reverify-1023/`，包含 `home/`（隔离 DSH_HOME）、`evidence/`、`proj/` 及派生项目、`harness/`。
- profile：
  - `trellis-headless`：`@deepseek-ai/dsh-base` + `@deepseek-ai/dsh-headless` + 已安装 `dsh-trellis` 0.1.6（复制自 web 副本）。
  - `bare-headless`：只含 base + headless，用于补足度对照。
  - 如需验证冲突检测，增加 `dup-headless`（再挂一个改名副本，制造同 profile 双挂载）。
- 凭据：`DEEPSEEK_API_KEY` 由 harness 从 `~/.dsh/.credentials.yaml` 的 `refs` 读取后仅经环境变量传给子进程；不打印、不写日志、不出现在命令行参数。复制 `.anonymous-user-id` 避免匿名身份漂移。
- Codex：`CODEX_HOME=/tmp/.../codex-home`（从 `~/.codex` 复制配置与认证文件，不读取内容），仅在隔离 home 中做 trust/hooks 试验，不触碰真实 `~/.codex`。
- 仓库零改动：所有写操作限于 `/tmp` 与隔离 home；每阶段结束 `git status --porcelain` 复核仅剩用户既有两个未跟踪文件。

## 4. 对照矩阵（三臂）

| 维度 | Codex + Trellis | DSH 裸用（class-2 pull） | DSH + 已安装插件 | 判定标签 |
| --- | --- | --- | --- | --- |
| 会话启动 bootstrap | UserPromptSubmit 每轮附 bootstrap | 仅模型主动读 skill | 插件每会话一次 bootstrap | 对等/增强/不及 |
| 每轮工作流状态 | UserPromptSubmit 面包屑 | 无自动注入 | `agent/pre-step` 面包屑 + 去重 | |
| 任务状态语义 | 六状态 + stale 标签 | 依赖模型自查 | 六状态 + stale 专用正文 | |
| spec 路径注入 | PreToolUse deny-once | 无（模型可违反 spec） | pre-execute deny-once + ticket | |
| 子代理上下文 | SubagentStart push | child-pull | 首步 push + 角色契约 | |
| 角色识别/守卫 | 无守卫（silent return） | 无 | 声明式识别 + fail-closed 守卫 | |
| 命令面 | 无项目级 `/trellis` 命令 | 技能面 | `/trellis-status/finish/doctor` | |
| 会话身份 | Codex session id | `.dsh` 原生 session | `DSH_TRELLIS_CONTEXT_ID` | |
| 模式配置 | `codex.dispatch_mode` | 无 | `dsh.dispatch_mode` 只读 | |
| 安装/升级 | hooks + agents | `trellis init --dsh` | 插件安装 + `trellis update` | |
| 运维面 | 无 | 无 | settings/doctor/版本监控/冲突横幅 | |

标签定义：**达到同等效果**、**DSH 增强**、**DSH 不及**、**双方共同缺陷**、**宿主限制**、**上游只读观察**。

## 5. 场景设计（S1 为主）

### 5.1 主链路（必须 S1）

- **S01 bootstrap + no_task**：新会话首轮注入 bootstrap 与 no_task 面包屑；后续普通轮不重复。
- **S02 状态链**：`task.py create` → planning 面包屑；`task.py start --allow-empty-context` → in_progress；`task.py finish` → completed；状态未变不重复注入。
- **S03 spec deny-once**：写 `src/app.js` 首次被 deny，reason 含 spec 正文与 sha；读 spec 后重试成功；窗口内再写不 deny；spec 内容变更后重新 FULL deny。
- **S04 子代理 push + 子代理 spec**：真实派发 `trellis-agent-implement`（`Active task:` 前奏），子代理首步收到角色契约 + curated context；子代理写文件同样被 spec deny 并按 spec 重试。
- **S05 守卫**：no_task 下派发 implement/check 被 fail-closed 拒绝；inline 模式声明式派发被拒并给出两条出路；research 无任务放行并收到位置提醒。
- **S06 角色识别回归**：话题型 description、路径提及不触发；首行前缀、`Role:` 行、严格 description 前缀正确触发。
- **S07 spec 变体**：子目录 cwd、`tools: [Read]`（不阻断、post-execute 补正文）、大写工具名规范化、`refresh_window_seconds`/`max_spec_chars` 边界、损坏分片安全回退。
- **S08 skip 与零干扰**：`no-trellis` 独立词整轮跳过（含工具后续 step）；非 Trellis 目录零注入；无 git 的 Trellis 项目正常注入。
- **S09 模式**：默认 inline banner；fresh 项目首会话后 `git status` 干净（不写 tracked config）；显式 auto 后状态名无 `-inline`、派发链路通。
- **S10 身份**：会话内 `DSH_TRELLIS_CONTEXT_ID`、`task.py current` 指针、命令子进程身份一致；子代理转发身份优先。
- **S11 resume/跨进程**：`--session-id` 恢复后 projection 去重、spec 分片持久化、bootstrap 是否重复（记录实际行为与 README 声明是否一致）。
- **S12 并发**：两个会话同项目并行写不同文件，spec 分片互不串扰。
- **S13 compaction**：尽可能触发真实 compaction（长上下文/宿主入口）；若不可行，S2 直载 `compaction/end` 处理器验证内存+磁盘重置，S4 单测补偿，并明确限制。
- **S14 升级**：`trellis update --skip-all` 后插件主链路仍工作；managed-file 漂移检查。
- **S15 工作流变体与自定义状态**：`--workflow tdd`（或任务级 workflow）下块选择正确；自定义 `[workflow-state:...]` 状态可渲染。

### 5.2 裸用对照（S1 抽样）

- **B01** no_task 会话：无 bootstrap/面包屑。
- **B02** 写文件：spec 被静默违反（无 deny）。
- **B03** 派发 implement：无 push/守卫，子代理自行 pull 或空跑。
- **B04** 命令面/身份：无 `/trellis-*`、无托管身份。

### 5.3 Codex 对照（S1 优先，S2 补偿）

- **C01** 隔离 `CODEX_HOME` + 项目 trust + hooks 配置，尝试 `codex exec` 真实触发 UserPromptSubmit/PreToolUse/SubagentStart；成功则与插件逐项对照。
- **C02** 若 hook 仍无法触发：用真实 hook payload 直调三脚本（S2），并记录"exec 内自动触发未覆盖"的限制与已尝试配置。

### 5.4 命令/运维/模块（S2 + S4）

- **M01** `/trellis-status`、`/trellis-finish`、`/trellis-doctor` 注册、输出、拒参数、非 Trellis 目录提示。
- **M02** 设置页/版本监控/冲突检测：直载 client/host 决策函数与路由；duplicate 挂载下 doctor/冲突路由输出。
- **M03** 单测回归；兼容矩阵测试（`scripts/test-compat.mjs` 如可离线运行）。

### 5.5 宿主/上游契约（S3）

- **H01** DSH 0.2.1-rc.2：插件使用的 `agent/pre-step`、`tools/pre-execute|post-execute`、`compaction/end`、`subagent/end`、`commands`、`settings.section`、`webServer`、`loader` API 仍存在且语义未变；peerDependencies 满足。
- **H02** 插件是否遗漏宿主新能力（如新的 session/compaction/subagent 事件）导致可补未补。
- **H03** Trellis 0.7.0-beta.4：`get_context.py --platform dsh`、`task.py current --json`、`workflow.md` 状态块、`trellis update`、`.dsh/` 模板契约与插件读取逻辑一致；已知 O2（`run_in_background` 过期指引）按只读政策仅记录。
- **H04** 安装/升级形态：git path 安装、client bundle 构建/加载、版本号一致性、headless profile 无插件的现实覆盖。

## 6. 问题分类与编号

- `P#`：插件缺陷（可修，进执行方案）。
- `X#`：双方共同缺陷（Codex 也有；插件侧修复需声明不对称）。
- `H#`：DSH 宿主限制（记录边界；插件层可缓解则给候选）。
- `O#`：上游 Trellis 只读观察（不进问题清单/修复项）。
- 每项含严重级别 P0–P3、复现步骤、证据路径、影响面、候选修复方案（含推荐与取舍）。
- 反吹毛求疵：纯措辞/排版/非契约文档差异不立项；只保留影响行为、诊断、可维护性或用户判断的项。

## 7. 判定"补足"的基准

1. **Codex 接线面**（C01/C02）：同等 / DSH 增强 / DSH 不及。
2. **Trellis 原生 DSH 契约**（H03）：插件不得破坏 pull；push 是否补上 pull 缺失的自动注入。
3. **DSH 裸用差距**（B01–B04）：逐项覆盖判定（已补足/部分/未补足/宿主限制）。
4. **"尽可能弥补"**：对宿主限制导致的不可补项，判断插件是否已给出等价路径或文档指引（如 headless 命令限制的 shell 等价命令）。

## 8. 风险与限制（预先声明）

- 真实 LLM 会话非确定：关键断言以 `--json` 事件流、tool deny/result、`.trellis/.runtime` 文件为依据，模型自述只作线索；每维度至少 1 次成功观测，关键项 2 次。
- compaction 可能无法在 headless 下自然触发；不得为触发而伪造，改用 S2/S4 并标注。
- Web GUI 需本地鉴权；若无法在不暴露凭据的前提下进入，降级 S2+S4 并记录限制。
- Codex hook 自动触发受 trust/审批约束；隔离 `CODEX_HOME` 试验若仍失败，记录已尝试项与 S2 补偿。
- 上游只读政策不变；版本/安装相关结论以本机实际版本为准并写日期。
- 单任务约束：本任务内完成验证与问题清单；修复待用户逐项确认后在同一任务内进行（不另开任务）。

## 9. 修复闸门与回滚

- 验证阶段（本设计覆盖的全部实验）零仓库修改；仅 `/tmp` 与隔离 home 可写。
- 用户确认问题清单与执行方案后，才允许进入修复；每项修复独立、可 revert；提交/推送另行请示。

## 10. 交付物布局

```text
.trellis/tasks/10-23-dsh-trellis-installed-parity-reverify/
├── prd.md
├── design.md
├── implement.md
└── research/
    ├── verification-report.md      # 主报告（矩阵/分级/问题清单）
    └── evidence-index.md           # 场景 → 证据路径 → 断言 → 等级
```

## 11. 与上一轮归档任务的关系

- `10-23-dsh-trellis-016-installed-verify` 的结论仅作为**待复核假设**；本轮不复制其证据，重新运行。
- 新增/加强：真实 compaction、隔离 Codex hook 触发、duplicate 冲突、工作流变体/自定义状态、`trellis update` 兼容、settings/version 路由、安装态 0.1.6↔0.1.7 边界、无 git/嵌套项目。
- 前轮已充分覆盖且本轮环境未变的场景做抽样复测，不追求重复次数。
