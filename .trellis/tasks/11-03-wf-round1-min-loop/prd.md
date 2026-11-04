# PRD：wf 框架首轮最小闭环实现

## 目标

按已冻结契约从零建立 wf 独立框架的 **authoring 源树** 与 **首轮可运行闭环**：一个真实普通任务能从 `wf-start` 走到 `archive`，且第二/三轮能力对应的命令存在但按 `tier=blocked / WF_CAPABILITY_UNAVAILABLE` 声明未交付。

## 契约（唯一判据源，逐字为准）

- `docs/workflows/wf-framework-charter.md`（129 行）
- `docs/workflows/wf-framework-design.md`（720 行）
- `docs/workflows/wf-framework-mechanism.md`（1141 行）
- `docs/workflows/wf-framework-implementation.md`（738 行，正文绑定 `sha256 051aade5…`）

实现方案只给「文件在哪、函数叫什么、命令怎么拼」；状态值、原因码、记录字段、哈希公式、门禁顺序一律取机制稿，不自造判定、不新增开关或入口（charter T2/T3）。四份上位文件本轮**不改**；发现冲突只出「需人裁决」。

## 范围（首轮 = 机制稿 §12.1 的全部跨轮基础项）

1. authoring 源树 `docs/workflows/新项目开发工作流/`（`payload/` + `skills/` + `dev-manifest.json` + 源树 `README.md` 发行说明）。
2. `payload/bin/{wf.py, repair.py, uninstall.py}`（后两者自含、不导入 `wflib`）、`payload/install.py`、`payload/lib/wflib/*.py`（23 个模块，实现稿 §1.2 A2）、`payload/workflows/*.md`（6 份，每份 `[required]` 步骤带 enforcement 行）、`payload/templates/**`、11 个 skill。
3. `scripts/build-wf-release.py`（确定性打包 + `rules_digest` + `--verify-token-parity`）、`scripts/wf-dev-deploy.py`（开发态部署）。
4. 目标项目侧：`.wf/` 全树、项目根 `.wf-lock`、`.gitignore` 托管段（段内 `/.wf-lock`；卸载后段外裸行容忍）。
5. 第二/三轮命令存在、行为 `blocked`、`facts` 记轮次。
6. 首轮不出现挂起任务：复评与 `task-reassess` 按空集合处理，**不得**返回 `WF_CAPABILITY_UNAVAILABLE`。

## 非目标

- 不改 charter/设计稿/索引/来源说明/机制稿/实现稿正文（除任务要求最后按实跑结果更新实现稿 §7.1 的「未运行」）。
- 不做提交、tag、推送、归档、`finish`，除非人明确授权。
- 不引入第三方依赖、MCP、hook 或常驻服务。

## 验收

| 项 | 判据 |
|---|---|
| 机检 | `scripts/validate-wf-design.py` 全绿 + 「输入摘要 4/4」；`check-doc-refs.py` 0 problem；`unittest` 19 tests OK（全程保持） |
| P2 出口 | 真实普通任务完整闭环：`task-new → task-approve → task-start → task-check（五步）→ task-knowledge → 人调用 finish → archive` |
| P4 出口 | F0 从零安装可跑：`install.py` 从打包发行树装到空项目，`wf.py status` 可达 |
| P5 | F0/F1/F2 与 V1–V5 有实际结果；未运行必须写「未运行 + 原因分类」；三夹具专属场景不互相替代；记录版本与环境 |

## 约束

- 脚本仅 Python 标准库，最低 3.11；`wflib` 只 import 标准库与自身模块。
- 键值/凭据不进代码、日志、提交。
- 任务目录、`.wf/` 布局、CLI 形态取实现稿 §1、§2；字段/码表取机制稿 §1、§11。
