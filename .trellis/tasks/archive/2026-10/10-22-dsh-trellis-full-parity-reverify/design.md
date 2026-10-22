# Design: dsh-trellis 0.1.3 Codex parity 全量复核与缺口验证

## 环境基线（已实测确认）

| 组件 | 版本 / 状态 | 证据 |
|---|---|---|
| dsh 宿主 | 0.2.1-rc.2（全局 npm） | `dsh --version` |
| Trellis CLI | 0.7.0-beta.4（全局） | `trellis --version` |
| Trellis 源码 | ~/projects/other/Trellis @ be9e19b2 (0.7.0-beta.4, feat/v0.7-beta) | git log |
| dsh-trellis（web profile） | **0.1.3**，git 依赖（forgejo ai-coding-toolkit#path:dsh-plugins/dsh-trellis） | web/node_modules/dsh-trellis/package.json |
| headless profile | dsh-base + dsh-headless，**无插件** → 天然对照组 | headless/package.json |
| 本仓库 Codex 部署 | .codex/ + .agents/skills/ + .dsh/skills/（trellis-agent-{implement,check,research} 等） | ls 实测 |
| 本仓库 config.yaml | 含 `dsh:` 配置段（dispatch_mode 契约） | grep 实测 |

## 证据等级（沿用前任务并收紧）

1. **真实 dsh 会话**（最强）：headless profile 跑真实 LLM 会话，从
   `~/.dsh/sessions/` 的 session.v4.jsonl.zstd 事件日志取证（消息、工具调用、
   push 注入、deny 事件逐条可复核）。
2. **真实插件代码 + 真实项目**（中）：node 直载已安装插件的处理器，对 /tmp 临时
   项目实际执行（/trellis-status、/trellis-doctor、dispatch_mode 引导写入等）。
3. **源码比对**（中）：插件 src 与 Trellis 源码（init 产物模板、active_task.py、
   workflow 模板）及本仓库 .codex/ 部署契约逐点比对。
4. **插件自带测试**（补充，不作通过依据）。

## 验证矩阵

### 测试项目（/tmp/dsh-parity-reverify/，全新目录，不复用旧目录避免状态污染）
- `proj-basic`：git init + `trellis init --dsh`（主力验证场）
- `proj-nogit`：trellis init --dsh 但无 .git（projectRootMarkers / dispatch_mode 引导）
- `proj-plain`：无 Trellis（零干扰对照）

### 测试 profile
- `trellis-headless`（新建）：dsh-base + dsh-headless + dsh-trellis（与 web 同 git 快照安装）
- `headless`（现有）：无插件对照组（基准 B）

### 用例分组

**G1 = R1 修复回归（真实会话）**
- G1.1 inline 模式下 `subagent(description="trellis-agent-implement (round 1)", prompt=无角色名)`
  → 预期守卫 deny；事件日志取证 deny reason。
- G1.2 任务 in_progress 后同方式派发 → 预期子代理首步收到 subagent-context push
  （角色契约 + curated context）；检查 push 文本：`was prepared by dsh-trellis` 恰好一次、
  含"不要再次加载 skill"权威说明。
- G1.3 `description="研究 trellis-agent-implement 插件的 README"`（话题型）→ 预期
  generic：无 push、无 deny。
- G1.4 临时移除项目内某个 `.dsh/skills/trellis-agent-*/SKILL.md` 后派发 → 预期 push
  退化为路径提示且无"已推送"矛盾表述；验证后恢复。

**G2 = R2 主链路复核（C1–C10 重跑）**
逐条复跑 10-21 任务的 C1–C10 用例（面包屑状态映射/去重/no-trellis 跳过、
DSH_TRELLIS_CONTEXT_ID 隔离、trellis_wait、子代理 push、/trellis 命令面、
dispatch_mode 引导、spec 注入 deny-once/ticket/持久化/compaction、bootstrap 一次性、
非 Trellis 项目、init 双向一致），证据以真实会话事件日志为主。
每条同时与 Codex 侧比对：本仓库 .codex/hooks + .codex/agents/*.toml +
Trellis 源码 codex 平台实现 → 三档结论（对齐 / 有意差异已声明 / 未声明差异）。

**G3 = R3 补足评估**
- 用无插件 `headless` profile 在 proj-basic 跑同流程，列出缺失清单；
  对照插件版逐项确认补足；残余不足（事件形状限制、频率差异等）单列并评估可改进性。

**G4 = R4 缺漏扫描（新角度）**
- G4.1 多会话并发：两个 dsh 会话同项目 → session 指针与 spec-inject 分片隔离。
- G4.2 异常路径：task.json 损坏（task_error 面包屑）；config.yaml 损坏/只读时
  dispatch_mode 引导与 spec 注入的 fail-closed；.trellis 会话中途被删。
- G4.3 长会话：compaction 后 bootstrap/spec 重注入；`--session-id` resume 的
  projection 行为（README 声称可能重复注入一次——实测验证声明属实性）。
- G4.4 research 角色链路：派发 trellis-agent-research → push 为项目结构上下文
  （.trellis/spec 树 + packages + 搜索提示）；无任务派发 research 允许且有 notice。
- G4.5 冲突检测与版本监控：headless 下不可安全模拟的部分标注"未实测"+原因；
  可由代码审查+单元测试佐证的部分给出该等级证据。
- G4.6 与 workflow.md 派发协议一致性：Active task 前奏、trellis_wait / 
  run_in_background:false 二选一在当前 dsh rc.2 的实际可行性。
- G4.7 Trellis 0.7.0-beta.4 契约：task.py current --json 退出码、
  active_task.py 对 DSH_TRELLIS_CONTEXT_ID 的解析优先级（源码比对 + 实测）。

## 取证与产出

- 每个真实会话记录：profile、项目、session id、事件日志路径。
- 产出 `verification-report.md`（任务目录）：G1–G4 逐项结论表 + 证据等级 + 取证位置；
  Codex 对照表（三档）；三段式补足结论；问题清单（定性/影响/方案/推荐项）。
- **修复闸门**：报告交付后停止，等待用户逐条确认；确认后修复作为本任务 Phase 2
  的后续迭代（不新建任务）。

## 风险与边界

- 真实 LLM 会话依赖 deepseek API 可用性；若不可用降级为真实代码执行 + 源码比对并
  在报告标注证据缺口。
- 不向 dsh 会话传入任何凭据；临时项目不含敏感内容。
- 不修改 web profile 的任何配置；新建 profile 验证后保留（供复核）或清理由用户决定。
- web UI 专属功能（设置页、通知路由）在 headless 环境无法真实验证，按"代码审查 +
  单元测试 + README 声明比对"处理并明确标注。
