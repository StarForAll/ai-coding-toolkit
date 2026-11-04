# wf 模块源树（authoring）

本目录是 wf 独立框架的**作者侧模块源**，不是可运行应用、不随安装投放。
它由三部分组成：`payload/`（投放目标项目的运行时内容）、`skills/`（11 个宿主 skill 副本）、
`dev-manifest.json`（首轮开发态部署与打包共用的资产登记）。

判据来源（冻结）：[charter](../wf-framework-charter.md)、[设计稿](../wf-framework-design.md)、
[机制稿](../wf-framework-mechanism.md)、[实现方案](../wf-framework-implementation.md)。
本目录只承载实现产物；状态值、原因码、记录字段、哈希域与门禁顺序一律以机制稿为准。

## 1. 打包输入

| 项 | 值 |
|---|---|
| 源树 | `docs/workflows/新项目开发工作流/` |
| 发行根 | `docs/workflows/wf-release/`（生成物，**不手改**） |
| 清单 | `<发行根>/wf-release.json` |
| 目标版本 | 首发候选 `0.1.0`；正式发布前保持 `0.x.y` |

`dev-manifest.json` 只登记资产清单、版本与必需标记，**不含手填字节哈希**；
`scripts/build-wf-release.py` 与 `scripts/wf-dev-deploy.py` 按源文件字节现算 digest、模板标记与
`rules_digest`，两者共用 `scripts/wf_release_common.py` 的同一份算法（同名函数），首轮锚点因此可复现。

## 2. 工具与运行环境

- `scripts/build-wf-release.py --version 0.x.y`：校验源树完整性 → 生成发行根与清单 → 打印哈希清单。
  `--verify` 重建到临时目录并与现有发行树逐字节比较；`--verify-token-parity` 用固定 `--nonce`
  比对 `repair.py` / `uninstall.py` 两份自含实现的令牌四步输出。
- `scripts/wf-dev-deploy.py --target <abs> --skill-root <abs> [--confirm]`：首轮开发态部署（预览 →
  首装契约 → 投放 → 自检 → 释放为空闲）。`--host-id` / `--verify-capability` 是人确认宿主身份的
  承载；目标已安装时只允许更新 `installation.json` 的 `session_profile`，不覆盖资产与项目数据。
- 两个工具：仅标准库、在作者机运行、**不进入发行清单**。发行根里的 `install.py` 才是安装入口，
  它按 `target_class=release_only` 计入 `rules_digest`。

运行环境：Python ≥ 3.11；Linux 本机普通文件系统；目标侧其余要求见清单 `compatibility`。

## 3. 版本同步义务

源树 `dev-manifest.json` 的 `version`、清单 `wf-release.json` 的 `version`、发行 tag
`refs/tags/wf-v<X.Y.Z>` 三者必须同批修改。清单 `version` 与 tag 不一致时安装器按
`WF_RELEASE_CONFLICT` 拒绝。

## 4. 产物校验

- 同一源树应**字节复现**发行根：`python3 scripts/build-wf-release.py --verify`。
- 令牌实现不得漂移：`--verify-token-parity`。
- 清单 `compatibility.rules_digest` 由 `H("wf-rules-v1", …)` 计算，安装器会重算并与声明值比对；
  不一致按 `WF_RELEASE_CONFLICT` 拒绝投放。

## 5. 首发与升级步骤（人执行）

1. 同步版本（`dev-manifest.json` 与本文）；
2. `python3 scripts/build-wf-release.py --version 0.x.y`，复核差异与哈希清单；
3. 人按授权暂存精确路径并提交；
4. 人创建 `refs/tags/wf-v0.x.y`；
5. 安装：`python3 <发行根>/install.py --target <abs> --release-ref refs/tags/wf-v0.x.y --source <已检出发行目录> --skill-root <abs> [--confirm]`；
6. 升级：`python3 <目标>/.wf/bin/wf.py upgrade --apply --release-ref … --source …`（第三轮交付；
   当前返回 `WF_CAPABILITY_UNAVAILABLE`）。

打包脚本不提交、不建 tag、不推送；安装器只在本地已检出的发行目录解析人给的引用。

## 6. 目录速览

```
payload/bin/{wf.py, repair.py, uninstall.py}   # 引导层与两个自含独立入口
payload/install.py                             # 发行根安装入口（不投放）
payload/lib/wflib/*.py                         # 运行时包（23 个模块，仅标准库）
payload/workflows/*.md                         # 6 份流程文档（每个 required 步骤带 enforcement 行）
payload/templates/**                           # 配置/spec/任务/基线/用户定义模板
skills/<11 个>/SKILL.md                        # 宿主 skill 副本
dev-manifest.json                              # 资产登记（打包与开发态部署的输入）
```

目标项目侧的落点、升级/卸载覆盖与项目数据分区见实现方案 §1.1–§1.3。

## 6. 原语与审查副本的来源登记

`skills/` 下 11 个副本中，6 个是改编件（`wf-grilling`、`wf-tdd`、`wf-diagnosing-bugs`、`wf-code-review`、`wf-review`、`wf-review-action`），
其余（`wf-start`、`wf-continue`、`wf-finish`、`wf-bootstrap`、`wf-spec-update`）为本项目原创。
每个改编件在自己 `SKILL.md` 末尾带「来源与差异」段，登记来源、许可、基线、差异与最近正反例（设计稿 §7.4）。

- 审查两副本（`wf-review`/`wf-review-action`）的适配源是本仓库全局 `skills/multi-cli-review*`，属一次性适配源；适配成果只由本目录的副本承载。
- 来源仓库为内部私有源；上游改动不自动流入，吸收与否由人裁决（设计稿 §7.5）。目标项目不跟上游。
