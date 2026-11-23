# wf 模块源树（authoring）

本目录是 wf 独立框架的**作者侧模块源**，不是可运行应用、不随安装投放。
它由三部分组成：`payload/`（投放目标项目的运行时内容）、`skills/`（13 个宿主 skill 副本）、
`dev-manifest.json`（首轮开发态部署与打包共用的资产登记）。

判据来源（冻结）：[charter](../wf-framework-charter.md)、[设计稿](../wf-framework-design.md)、
[机制稿](../wf-framework-mechanism.md)、[实现方案](../wf-framework-implementation.md)。
本目录只承载实现产物；状态值、原因码、记录字段、哈希域与门禁顺序一律以机制稿为准。

## 1. 打包输入

| 项 | 值 |
|---|---|
| 源树 | `docs/workflows/wf/` |
| 发行根 | `docs/workflows/wf-release/`（生成物，**不手改**） |
| 清单 | `<发行根>/wf-release.json` |
| 目标版本 | `0.1.6`（dogfood 四轮修正：升级闭环实测缺陷收口——发行清单副本同步、已接受偏离自检、本地缺失人裁/必需资产禁止保留删除、缺 writer/journal/gitignore 冲突/落点边界/paused+suspended；`--export-deviations` 只读回源（全部本地偏离、pending/accepted、基线 N、项目树外）；`wf.py upgrade` 参数完整转交与未知参数拒绝；task-check/spec-update/task-knowledge 只读骨架；§1.1 指引与 skill 登记对齐。本轮重建后由人创建 `wf-v0.1.6`）。**0.1.5 → 0.1.6 可用 upgrade 升级**：`python3 <目标>/.wf/bin/wf.py upgrade --release <发行检出根> --release-ref refs/tags/wf-v0.1.6 [--apply]`（或直接 `<检出根>/install.py --upgrade --target <项目> --release-ref … --source <检出根>`）；交互终端预览令牌确认，模型不代跑。升级前置：全部活动任务暂停或未开工、保留 WIP 已处置、写权空闲（入口逐项给出三步出口）。已装 0.1.4 及更早版本仍需卸载重装（跨多版升级不在本通道） |

`dev-manifest.json` 只登记资产清单、版本与必需标记，**不含手填字节哈希**；
`scripts/build-wf-release.py` 与 `scripts/wf-dev-deploy.py` 按源文件字节现算 digest、模板标记与
`rules_digest`，两者共用 `scripts/wf_release_common.py` 的同一份算法（同名函数），首轮锚点因此可复现。

## 2. 工具与运行环境

- `scripts/build-wf-release.py --version 0.x.y`：校验源树完整性 → 生成发行根与清单 → 打印哈希清单。
  `--verify` 重建到临时目录并与现有发行树逐字节比较；`--verify-token-parity` 用固定 `--nonce`
  比对 `repair.py` / `uninstall.py` / `install.py` 三份自含实现的令牌四步输出。
- `scripts/wf-dev-deploy.py --target <abs> --platform <平台> [--platform <另一个平台>] [--confirm]`：首轮开发态部署（预览 →
  首装契约 → 投放 → 自检 → 释放为空闲）。`--platform` 可重复、至少一项，解析出的**目标项目内**技能目录写入
  `installation.json.roots`（相对路径），平台名写入 `installation.platforms`——**平台清单即身份事实**；R93（commit `20e3ae8`）
  已删除 `--host-id`、`--verify-capability` 与 `installation.json.session_profile`，不要按旧口径描述它们。
  目标已安装时的处理：**同发行引用只允许追加平台**（`install.py` 亦然），资产与项目数据不动；不同发行引用属升级，
  走 `wf.py upgrade --release <检出根> --release-ref refs/tags/wf-vX.Y.Z --apply`（已交付，
  经引导层转交 install.py --upgrade），开发态工具不按新装覆盖。
- 两个工具：仅标准库、在作者机运行、**不进入发行清单**。发行根里的 `install.py` 才是安装入口，
  它按 `target_class=release_only` 计入 `rules_digest`。

运行环境：Python ≥ 3.11；Linux 本机普通文件系统；目标侧其余要求见清单 `compatibility`。

## 3. 版本同步义务

源树 `dev-manifest.json` 的 `version`、清单 `wf-release.json` 的 `version`、发行 tag
`refs/tags/wf-v<X.Y.Z>` 三者必须同批修改。清单 `version` 与 tag 不一致时安装器按
`WF_RELEASE_CONFLICT` 拒绝。

**唯一例外（开发态占位符）**：`dev-manifest.json` 的 `version` 取占位值 `0.0.0-dev`
（`DEV_VERSION_PLACEHOLDER`）时，打包脚本不要求它与 `--version` 相同——版本源唯一在
`--version` 参数，占位符只表示"这是开发态源树、尚未声明发行号"。占位符以外的任何值都必须
与 `--version` 一致，否则 `scripts/build-wf-release.py` 直接 `SystemExit`（`_assert_version_consistency`）。

打包入口另有两项机械守卫：`--version` 必须与本文「目标版本」一致（README 漂移即拒绝）；
`refs/tags/wf-v<version>` 已存在时拒绝重建同版（防止同一个版本号对应两份不同内容）。
tag 只在人确认提交后创建，打包脚本不建 tag、不推送。

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
5. 安装：`python3 <发行根>/install.py --target <abs> --release-ref refs/tags/wf-v0.x.y --source <已检出发行目录> --platform <平台> [--confirm]`；
6. 升级：`python3 <目标>/.wf/bin/wf.py upgrade --release <发行检出根> --release-ref refs/tags/wf-vX.Y.Z [--apply | --export-deviations --out <dir>]`——预览含全部路径动作与偏离清单，`--apply` 在交互终端输入预览指纹确认；冲突逐路径用 `--keep <路径>` / `--restore <路径>` 选择；`--keep` 仅对可选资产有效，必需资产保留删除会在写入前 `WF_SEMANTIC_DECISION`。
   `--export-deviations --out <dir>` 是**只读回源**：导出全部本地偏离（含未接受项，清单标 `status=pending`；已接受项标 `accepted`）的补丁与 `manifest.json`，不取写权、不暂停任务、不应用升级；同版也允许导出。与 `--apply` 互斥。直接入口 `install.py` 同样适用这些组合校验。

打包脚本不提交、不建 tag、不推送；安装器只在本地已检出的发行目录解析人给的引用。

## 6. 目录速览

```
payload/bin/{wf.py, repair.py, uninstall.py}   # 引导层与两个自含独立入口
payload/install.py                             # 发行根安装入口（不投放）
payload/lib/wflib/*.py                         # 运行时包（32 个 .py 文件，含 `__init__.py`；仅标准库）
payload/workflows/*.md                         # 6 份流程文档（每个 required 步骤带 enforcement 行）
payload/templates/**                           # 配置/spec/任务/基线/用户定义模板
skills/<13 个>/SKILL.md                        # 宿主 skill 副本
dev-manifest.json                              # 资产登记（打包与开发态部署的输入）
```

目标项目侧的落点、升级/卸载覆盖与项目数据分区见实现方案 §1.1–§1.3。

## 7. 原语与审查副本的来源登记

`skills/` 下 13 个副本中，6 个是改编件（`wf-grilling`、`wf-tdd`、`wf-diagnosing-bugs`、`wf-code-review`、`wf-review`、`wf-review-action`），
其余 7 个（`wf-start`、`wf-continue`、`wf-finish`、`wf-bootstrap`、`wf-spec-update`、`wf-repair-loop`、`wf-review-accept-unknown`）为本项目原创。
每个改编件在自己 `SKILL.md` 末尾带「来源与差异」段，登记来源、许可、基线、差异与最近正反例（设计稿 §7.4）。

- 审查两副本（`wf-review`/`wf-review-action`）的适配源是本仓库全局 `skills/multi-cli-review*`，属一次性适配源；适配成果只由本目录的副本承载。
- 来源仓库为内部私有源；上游改动不自动流入，吸收与否由人裁决（设计稿 §7.5）。目标项目不跟上游。
