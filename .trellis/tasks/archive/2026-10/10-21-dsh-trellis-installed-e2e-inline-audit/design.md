# Design — 验证架构与用例矩阵

## 1. 证据模型

| 等级 | 含义 | 允许用途 |
| --- | --- | --- |
| E1 | 本轮真实执行：真实 DSH 进程 / 真实 hook 进程 / 真实文件读取 / 真实 HTTP 响应 | 唯一可支撑结论 |
| E2 | 静态推断（读源码得到的执行路径） | 标注后作为待验证假设 |
| E3 | 插件 README、validation 文档、单测结果 | 仅作基线参考与用例设计输入 |

所有 E3 声明都必须找到对应 E1 复现，否则写成「无法验证」。

## 2. 验证环境（一次搭建，全场景复用）

```
/tmp/trellis-verify-<ts>/            # R2 唯一临时项目
  .trellis/ .dsh/ .codex/ .agents/   # trellis init --dsh --codex -y -u xzc
  src/                               # spec 注入与工具调用目标
/tmp/dsh-verify-home-<ts>/           # R3 独立 DSH_HOME
  profiles/trellis-verify/           # headless 模板副本 + dsh-trellis 软链 + insert 条目
/tmp/dsh-verify-<ts>/mock-llm/       # mock LLM：记录 messages/tools，按脚本返回 tool_calls
```

关键技术选择：

- **DSH 侧**用 `dsh --profile trellis-verify --json "..."`（headless 应用，进程级隔离），
  `--json` 事件流 + mock 请求日志提供模型视角取证；`--session-id` 用于同会话多轮状态切换。
- **Codex 侧**用 `python3 -X utf8 .codex/hooks/<hook>.py` 喂真实形态 payload，得到逐字基线；
  真实 `codex exec` 仅作行为补充（项目 hook 需一次性 `/hooks` 审批，未审批时如实记录限制）。
- **插件加载**只读软链到本仓库源码，保证“安装态 = 源码态”，不复制、不打补丁。
- 每个场景独立会话，避免 digest 去重与 bootstrap 一次性语义互相污染。

## 3. 能力矩阵（R6）

| ID | 能力面 | 方法 | 通过判据 | 对照基线 |
| --- | --- | --- | --- | --- |
| A1 | 插件装载 | `--dump-config` + `/json` 事件里工具列表 | 条目存在、无加载错误、`trellis_wait` 在 tools | `web` profile dump |
| A2 | 命令注册 | 事件/日志中命令面 | `/trellis-status`、`/trellis-finish`、`/trellis-doctor` 可达 | Codex skills 入口 |
| B1 | bootstrap 注入 | 新会话首轮 no_task | 出现独立 `<trellis-bootstrap>` 消息，恰好一次 | Codex UserPromptSubmit 输出 |
| B2 | bootstrap 去重 | 同会话第二轮 | 不重复注入 | Codex 每轮重复（有意差异） |
| B3 | 子代理静默 | 派发子代理 | 子代理请求无 bootstrap | Codex SubagentStart 只推送角色上下文 |
| C1 | 状态面包屑 | 逐状态切换：no_task/stale/task_error/planning/in_progress/completed/自定义/blocked | 正文与 Codex hook 字节一致或有明确差异 | `.codex/hooks/inject-workflow-state.py` |
| C2 | 去重与重投 | 重复同状态 + compaction | 无变化不重复；压缩后重投 | 设计契约 |
| C3 | 项目 skip_keyword | config.yaml 设自定义词 | 命中词时 0 注入 | Codex hook 同配置 |
| C4 | workflow 变体选择 | task.workflow → `.developer` → `default_workflow` → 全局 | 与 `workflow_selection` 优先级一致 | 真实 `.trellis/workflows/*.md` |
| D1 | spec deny-once | edit/write 命中 `paths` | deny 一次，文案与 hook 逐字一致，文件未落盘 | `inject-spec-context.py` |
| D2 | spec retry 放行 | 重试同调用 | 放行并落盘 | 同上 |
| D3 | spec ticket 投递 | 只读工具（read） | 下一次请求出现 `<spec-context>` | 同上 |
| D4 | spec 配置解析 | `enabled/max_*/tools/refresh_window` 变体 | 行为随配置变化且与 hook 数值一致 | hook 同输入 |
| D5 | spec 状态持久化 | `.trellis/.runtime/spec-inject/` | 分片生成、损坏时可恢复 | 设计契约 |
| E1 | 子代理上下文推送 | `subagent` 派发 `trellis-agent-implement` | 首步注入角色契约正文 + prd/清单，仅一次 | `inject-subagent-context.py` |
| E2 | 通用子代理静默 | 非 trellis 角色 | 不注入，不编造状态 | hook silent return |
| E3 | 派发守卫 | 缺失/不可读任务时派发 | fail-closed 拒绝且子代理未启动 | Codex 无此守卫（增强项） |
| F1 | `trellis_wait` 语义 | 后台子代理 + 事件汇合 | 成功/失败/中止映射正确，无 sleep/轮询 | DSH 原生 settlement |
| G1 | 会话身份 | bash 打印 `DSH_TRELLIS_CONTEXT_ID`；`task.py current` | `dsh_<session>` 且指针可解析 | Trellis 会话指针契约 |
| H1 | doctor | `/trellis-doctor` | 输出项目根/版本/状态/spec 配置/inline 模式 | README 声明 |
| H2 | 冲突检测 | profile 内再加含 trellis 的条目 | 报冲突或 unavailable，不伪造“无冲突” | 设计契约 |
| H3 | 版本监控路由 | 真实 HTTP 请求（无网络时记录限制） | 路由存在、只访问白名单 | README 声明 |
| J1 | 非 Trellis 项目 | 无 `.trellis` 目录 | 0 注入、命令提示未初始化 | 设计契约 |

## 4. inline 专项（R7）

| ID | 检查 | 判据 |
| --- | --- | --- |
| I1 | 是否实现 | 源码路径 + 真实会话 `planning-inline` 注入 |
| I2 | 状态覆盖 | `planning` / `in_progress` 生效；`completed`/`stale`/`task_error`/自定义状态的预期行为 |
| I3 | 块缺失回退 | workflow 变体无 `-inline` 块时是否回退基础块且不产生半截横幅 |
| I4 | 配置解析 | `inline`/`auto`/缺省/非法值/带注释/引号；大小写与空白 |
| I5 | 横幅内容 | 与 `*-inline` 块是否冲突/重复；是否覆盖 DSH 特有机制（技能面、commit、finish-work） |
| I6 | 作用域 | 子代理是否收到 inline 横幅；是否影响子代理派发协议 |
| I7 | 去重 | 同状态多轮是否重复注入；切换 auto↔inline 是否重新注入 |
| I8 | 与派发守卫关系 | inline 下仍可派发 `trellis-agent-*` 是否与“主会话自己做”冲突（是否应有技术门禁） |
| I9 | 与 Trellis 契约 | Trellis 把 `*-inline` 标注为 Codex-only；DSH 复用是否产生语义/路由冲突（Phase Index 的 `[codex-inline]` vs `[DeepSeek Harness]` 路由段） |
| I10 | 与 Codex 对照 | Codex `codex.dispatch_mode: inline` 实际选中块与 DSH `dsh.dispatch_mode: inline` 的正文差异 |
| I11 | 无 workflow 变体/无 config | 缺 config.yaml、缺 dsh 段时默认 `auto` |
| I12 | 注入体积 | inline 正文 + 横幅字节数是否在预算内、是否被截断 |

## 5. 交付物

```
findings/
  environment.md      # 环境搭建与可复现命令
  bootstrap.md        # B*
  state.md            # C*（含逐状态字节对照表）
  spec-injection.md   # D*
  subagent.md         # E* + F1
  session-identity.md # G1
  commands-doctor.md  # H* + J1
  inline-mode.md      # I1–I12
report.md             # 结论、问题清单（P0-P3）、修复方案、无法验证项
```

## 6. 风险与回滚

- 独立 `DSH_HOME` + 软链安装：删除 `/tmp/dsh-verify-*` 即完全回滚，用户 profile 不受影响。
- 真实 LLM 不参与验证（mock 只证明“模型收到什么”），避免额度与不确定性；真实 Codex 仅做一次
  行为补充，失败即记录为限制。
- 不修改 `dsh-plugins/`；若验证中临时需要故障注入，只改 `/tmp` 项目内的 `.trellis/` 文件。
