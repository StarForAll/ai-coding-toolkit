# Findings — 验证环境（E1）

## 版本与安装链

| 项 | 值 | 取证 |
| --- | --- | --- |
| DSH | `0.2.1-rc.2` | `dsh --version` |
| dsh-trellis（已安装） | `0.3.9`，`~/.dsh/profiles/web/package.json` → `link:/home/xzc/projects/personal/ai-coding-toolkit/dsh-plugins/dsh-trellis` | `node -e "require('…/web/node_modules/dsh-trellis/package.json').version"`；`dsh --profile web --dump-config`（第 1303 行 `id: dsh-trellis`） |
| Trellis CLI | `0.7.0-beta.4` | `trellis --version` |
| Codex CLI | `0.163.0` | `codex --version` |
| Node / Python | v24.20.0 / 3.14.7 | `node --version`、`python3 --version` |

## 隔离环境（不触碰用户 profile）

```
/tmp/trellis-verify-20261021-1547/      # trellis init --dsh --codex -y -u xzc 生成的临时项目
/tmp/dsh-verify-home-20261021-1547/     # 独立 DSH_HOME
  profiles/trellis-verify/              # headless 模板副本
    node_modules/dsh-trellis -> 本仓库插件源码（软链，安装态=源码态）
    cordis.patch.yml                    # insert dsh-trellis；mock provider
/tmp/dsh-verify-harness/mock-llm.mjs    # 本地 OpenAI-compatible mock，记录模型完整 messages/tools
/tmp/dsh-verify-20261021-1547/{state-seq,spec,subagent,variant,guard2}/
                                        # 每个场景的 plan.json / requests.jsonl / events.jsonl / stderr.log
```

- 运行入口：`DSH_HOME=/tmp/dsh-verify-home-20261021-1547 dsh --profile trellis-verify --json "<prompt>"`。
- 会话续接：`--session-id <id>`；状态切换实验复用同一会话（`session-aaa548aa-…`）。
- Codex 基线：`python3 -X utf8 .codex/hooks/inject-workflow-state.py` / `inject-spec-context.py`，
  输入真实形态 payload（`cwd`/`session_id`/`prompt`/`hook_event_name`/`tool_name`/`tool_input`）。
  运行时剥离 `DSH_*` 环境变量，避免 dsh-trellis 注入的会话身份覆盖 Codex 会话键。
- 本地 mock 只证明“模型实际收到什么”，不证明模型遵循程度；真实 `codex exec` 只用于确认真实 hook 是否生效。

## 真实 Codex 运行（补充）

`codex exec --skip-git-repo-check "Reply with exactly OK and nothing else."` 在临时项目内真实执行成功，
`~/.codex/sessions/.../rollout-2026-10-21T15-55-12-01a15d75-….jsonl` 中 **没有任何
`workflow-state` / `codex-mode` / `trellis-bootstrap` 内容**：新项目的 Codex hooks 尚未通过
`/hooks` 一次性审批（用户级 `features.hooks = true` 已开），所以真实 Codex 会话看不到注入。
本报告的 Codex 基线因此采用“真实 hook 进程 + 真实 payload”的逐字输出，而非整机 Codex 会话。
