# 宿主事实登记（会话标识 / 新会话命令）

来源：**用户实测口述**（2026-11-09）。按 S12 口径 A，这类"哪个宿主从哪取会话标识"的事实只登记在
**安装期部署表**（`payload/install.py` 的 `PLATFORMS[*].session_identity`），不进语义层。

| 宿主 | 会话标识来源 | `/clear`（或等价的新会话命令） | 证据等级 |
|---|---|---|---|
| `codex` | `host-hook:SessionStart` | **有 `/clear`，且之后会话标识真实变化（已实测）** | 用户实测 |
| `dsh` | `env:DSH_SESSION_ID`（托管 shell 内可见） | **无 `/clear` 命令** | 用户实测 |
| `cursor` / `geminicli` / `copilot` / `claudecode` | 未核实 | 未核实 | `unknown` —— 适配层不得猜，走 `WF_SEMANTIC_DECISION` |

## 由此确定的两条结论

1. **`/clear` 的可判别性由宿主决定**，不是框架能力：codex 给了变化的标识 ⇒ `/clear` → 新 `session_key` → 旧租约 `superseded`（K2 的接管路径自然成立）；dsh 没有 `/clear`，同一终端要换会话只能开新终端。
2. **警告措辞不绑定具体命令**：`enable` 在"只有进程锚"时输出 `new_session_indistinguishable`，说明"框架无法区分同一进程内的新会话（宿主自带的新会话命令、或同终端新开聊天）"，并提示开新终端——不再写死 `/clear`。

## 部署表校验（`scripts/tests/wf_identity/test_deployment_table.py`）

- 每个平台必须有 `session_identity`，`source ∈ {official-docs, user-declared, unknown}`；
- `source=unknown` 时 `value` 必须为 `null`（未核实不许猜）；
- 部署表只有一份：`scripts/wf-dev-deploy.py` 从 `install.py` 取表，源码里不得再出现 `PLATFORMS = {`；
- 身份语义层（`session.py` / `identity_store.py` / `protocol.py`）不得出现宿主名。
