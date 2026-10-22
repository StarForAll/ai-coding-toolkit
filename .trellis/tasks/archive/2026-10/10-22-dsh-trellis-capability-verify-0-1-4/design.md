# Design — dsh-trellis 全量能力复核

## 1. 验证架构

```
/tmp/dsh-cap-verify/
├── proj/                 # 同一临时项目：git init + trellis init --codex --dsh
│   ├── .trellis/         # workflow/spec/tasks（Codex 与 DSH 共用）
│   ├── .codex/           # Codex 产物（hooks.json/agents/config）
│   ├── .agents/skills/   # 共享技能
│   └── .dsh/skills/      # DSH 入口/角色技能
├── home/                 # 隔离 DSH_HOME（不触碰 ~/.dsh）
├── codex-home/           # 隔离 CODEX_HOME（避免污染用户配置）
├── sessions/             # 复制/解压的会话取证
└── evidence/             # 命令输出、diff、解析结果
```

- **DSH 侧**：`DSH_HOME=/tmp/dsh-cap-verify/home` 新建 profile（headless bundles +
  本地 `dsh-plugins/dsh-trellis` 以 `link:` 挂载），真实 LLM 走既有 provider 配置，
  凭据只经环境变量。会话日志在 `$DSH_HOME/sessions/<encoded-cwd>/<session>/session.v4.jsonl.zstd`。
- **Codex 侧**：`CODEX_HOME` 隔离副本（复制用户 config 的 provider 段，但引用环境变量，
  不写明文），项目标记 trusted，启用 user-level `features.hooks`；`codex exec --json`
  跑真实回合，rollout 在 `$CODEX_HOME/sessions/`。若 hooks 需 `/hooks` 一次性审批而无法在
  exec 模式生效，则在临时项目直接以 Codex 事件 payload 调 hook 脚本（S2）并明确标注限制。
- **plain DSH 对照**：同一 profile 去掉插件（或第二个无插件 profile），同项目同提示，
  确认零注入/零补足。

## 2. 证据等级

| 等级 | 含义 | 用途 |
|---|---|---|
| S1 | 真实 LLM 会话（Codex rollout / DSH jsonl 逐事件） | 主证据 |
| S2 | 真实代码执行（node 直载插件 lib、真实 CLI、真实 hook 脚本 + 真实 payload） | 主证据 |
| S3 | 源码比对（插件 lib ↔ Trellis 源码 ↔ 宿主源码） | 补充/解释 |
| S4 | 单元测试（`node --test`） | 回归证据 |

## 3. 对照矩阵（R1/R2）

每条链路四列：Codex 实际接线、DSH 插件实现、plain DSH 行为、结论档位。

1. workflow-state 注入（时机、去重、跳过词、状态映射）
2. no-task bootstrap（内容、频率、compaction）
3. spec 注入（触发工具、deny-once、重试、持久化、read ticket、重置）
4. 子代理上下文（角色识别、任务来源、内容、静默边界、守卫）
5. 任务与会话身份（active task 解析、DSH_TRELLIS_CONTEXT_ID、多会话隔离）
6. 命令/工具面（`/trellis-status`、`/trellis-finish`、`trellis_wait`、agent 定义能力）
7. 项目引导（`dsh.dispatch_mode` 写入、并发写、显式值）
8. finish 流程（commit → archive → journal）
9. 非 Trellis 项目零干扰

## 4. 新角度（R4）

- 并发：两个项目 × 两个会话交叉触碰 spec 文件，检查分片键与任务指针。
- 异常：损坏 `task.json` / `config.yaml`、删除 `.trellis`、只读 `.trellis`。
- 长会话：compaction 后 bootstrap/spec 重注入；`--session-id` resume。
- 升级：`trellis update` 前后产物 hash；插件 `upstream` 监控对 0.7.0-beta.4 的版本判定。
- 增强：doctor 全项、冲突告警、版本监控、设置页字段与真实行为一致性。

## 5. 判定规则

- **对齐**：两边真实行为在用户可感知层面等价（措辞可不同）。
- **有意差异**：README / DSH.md / Trellis 源码注释显式声明，且有宿主机制依据。
- **未声明差异**：行为差异无文档依据，或文档与实测相反 → 记为问题候选。
- **问题**分级：P1 阻断主链路 / P2 体验或一致性问题 / P3 文档或边界缺陷。

## 6. 风险与回退

- Codex hooks 在非 TUI 下可能需审批：记录为“真实会话受限”，改用真实 payload 直调 + 明确标注。
- 真实 LLM 会话不稳定：关键链路用多轮/重试，失败不掩盖，报告写明。
- 隔离 profile 的 bash/subprocess 偶发失败（历史现象）：用 S2 补证，不据此判缺陷。
- 全程不动仓库既有改动（`M .trellis/spec/platforms/dsh-workflow-behavior.md` 等保留）。
