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
| 目标版本 | `0.0.2`（版本号已从 0.1.x 回退：wf 仍未达到正式可用，后续一律在此号上迭代；**只有人主动要求时才改版本号**）。本轮内容（dogfood 六~八轮 + 复核轮）：在途审查轮不再被旧结论挤掉——`check_next_hint` 按「轮次＋锚点」判在途，旧 fail/pass 留作历史，不再误导重新 `review-launch`；审查材料 `status.json` 汇总后一次写出，日志问题并入后不再丢 `redacted`/`redaction` 脱敏说明；wf-review 材料指引与实现对齐（`logs[]` 只含通过证据身份核对的日志，不符/缺失改在 `status.json.problems`）；升级帮助示例只引用已打 tag 的发行版本并加机械护栏测试；会话轮换出口修正（暂停不解除在途绑定，移除"暂停后重试"无效出口）；重复调试裁定（debug-ruling）归还主会话授权内——机制保留计数、证据、留痕与归档门禁，诊断语义不再逐倍数人签（机制稿 §1.3/§8.1/§11.2 同步；finish 草稿投影已裁「不同问题」倍数，复核面闭合）；wf-review-action 外发确认口径与 wf-continue 对齐（同任务同材料类持续有效）；**七轮**：轮次材料一经物化即固定（manifest，同轮重入只校验不重写），pass 判定要求全部轮次已知 blocking 已关闭，`check_next_hint` 判据统一走 `latest_decision`，`task-approve --draft` 前移 PRD 结构预检，`review-context` 续写补授权事实；**八轮**：判定侧消费材料身份（drift 拒、采纳记弱身份、不重写 manifest）、Check 下一跳在有 blocking 时不再指向 finish、PRD 摘要单读数（草稿/正式批准/机械修订/replan 同源，**0.1.7 上手写或照旧报错抄的 `object_digest` 需按新草稿重出**）、会话轮换与 `enable` 共用终态判据（记录缺失按 unknown 拒绝并给 status/repair 出口）、`judgments` 的 `kind` 增 `框架改动` 并修 help 指针。**0.1.x → 0.0.2 升级通道（前提：人确认版本号并创建 `wf-v0.0.2` tag；`wf-v0.0.1` 是上一快照，不再作为升级目标）**：发行引用只认真实 tag，未建 tag 时该命令在 `REF_RE`/`rev-parse` 层面即不可执行；`python3 <目标>/.wf/bin/wf.py upgrade --release <发行检出根> --release-ref refs/tags/wf-v0.0.2 [--apply]`（或直接 `<检出根>/install.py --upgrade --target <项目> --release-ref … --source <检出根>`）；交互终端预览令牌确认，模型不代跑。升级前置：全部活动任务暂停或未开工、保留 WIP 已处置、写权空闲（入口逐项给出三步出口）。**存量分级载体**：`confirmed_source != decision` 的复杂任务在归档会被 `WF_SEMANTIC_DECISION` 拒（0.1.7 起同一门禁，非本版新增）；出口是未开工时用 `task-approve --draft` 重新批准、已开工时回 Plan 重新分级后再批准。已装 0.1.4 及更早版本仍需卸载重装（跨多版升级不在本通道）。**第四轮独立复审（2026-11-25）**：`task-approve --draft` 输出 `complexity_proposal`（四项条件与提议）与生效 `tdd`，并把两值写进 approve 条目的 `plan` 骨架；正式批准在决定与 inputs 都未给 complexity 时把 `confirmed_source` 记 `proposed` 并给出可见提示（不再冒充 `inputs`）；`review-status` 按「对象终态 / 外部审查是否必需」投影 `entry_gate`，已归档对象不再被劝去 `review-launch`，`review-launch` 对归档对象报终态事实（此前误报「规划批准已失效」）；pass 结果的 `exit` 置 null（与机制稿 §11.1「exit 是失败/待决出口」一致）；草稿在项目配置/请求 TDD 取值非法时只报事实、不阻断骨架；轻量任务不再被给"临时加审查轮"的出口（与 wf-review 同口径）；`.wf/spec/` 顶层`index.md` 与两份 checklist 不再被当作规则加载（出厂模板不再自带 3 条 frontmatter 问题）；`review-context` 首次物化后按真实状态回显 `materials_check`；**0.0.2**：复杂分级没有人的批准决定承载时，`task-approve` 直接以 `WF_SEMANTIC_DECISION` 拒绝（出口：`--draft` 骨架已预填 `plan.complexity`，或手写决定补该键；请求 inputs 只作提议）；TDD 未写入决定仍按项目默认/发行缺省并给出「未由人确认」提示。 |

`dev-manifest.json` 只登记资产清单、版本与必需标记，**不含手填字节哈希**；
`scripts/build-wf-release.py` 与 `scripts/wf-dev-deploy.py` 按源文件字节现算 digest、模板标记与
`rules_digest`，两者共用 `scripts/wf_release_common.py` 的同一份算法（同名函数），首轮锚点因此可复现。

## 2. 工具与运行环境

- `scripts/build-wf-release.py --version 0.x.y`：校验源树完整性 → 生成发行根与清单 → 打印哈希清单。
  `--verify` 重建到临时目录并与现有发行树逐字节比较；`--verify-token-parity` 用固定 `--nonce`
  比对 `repair.py` / `uninstall.py` / `install.py` 三份自含实现的令牌四步输出。
- `scripts/wf-dev-deploy.py --target <abs> [--confirm]`：首轮开发态部署（预览 →
  首装契约 → 投放 → 自检 → 释放为空闲）。**安装面向全部支持平台**（`PLATFORMS` 是唯一来源，
  2026-11-23 人裁：不再有 `--platform`），解析出的**目标项目内**技能目录写入
  `installation.json.roots`（相对路径），平台名写入 `installation.platforms`——**平台清单即身份事实**；R93（commit `20e3ae8`）
  已删除 `--host-id`、`--verify-capability` 与 `installation.json.session_profile`，不要按旧口径描述它们。
  目标已安装时的处理（`install.py` 与开发态工具同形）：**重跑 = 补齐/核对**——缺的落点与
  hook 条目只补不改（取写权、产回执）、内容被本地改过则拒绝并指向升级、全一致则只读核对；
  **没有"追加平台"这一步**（安装已面向全部平台）。跨版本走
  `wf.py upgrade --release <检出根> --release-ref refs/tags/wf-vX.Y.Z --apply`（已交付，
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

**版本号只由人推进**：本仓库不按提交或轮次自动加版本（2026-11-24 人裁，wf 仍是 0.0.2 未达可用）。
需要发新号时由人明确要求并同批改「目标版本」、`--version`、tag；自动化脚本只校验三者一致，不替你挑号。
tag 只在人确认提交后创建，打包脚本不建 tag、不推送。

**义务的机械核对（2026-11-23 起，dogfood 五轮 b-P0）**：上面这条"三者同批"过去只写在本文里——
实况是仓库长期只有 `wf-v0.1.0` 一个 tag，而本文却记载过 0.1.5→0.1.6 可用 upgrade 升级；安装器
只认真实存在的 tag，于是**文档承诺的升级通道在字段上不可执行**。现在同一条义务有可执行核对：

```bash
python3 scripts/verify-wf-release.py --version 0.x.y --ref refs/tags/wf-v0.x.y   # 六项只读核对
```

核对项：tag 存在且解析到提交；源码树重建 == 工作树发行树；tag 提交内的发行树与工作树逐字节相同
（含"只在工作树多出来的发行文件"）；清单 `version`；本文「目标版本」行；重算 `rules_digest`。
tracked pre-push 钩子对 `refs/tags/wf-v*` 的推送自动跑同一脚本，不通过即拒绝推送该 tag
（普通分支推送与"先提交后打 tag"的顺序不受影响）。脚本只报事实与出口，不创建、不修改、不删除 tag。
**"忘记打 tag"也有提醒**：推送的提交若改动发行树、且发行树清单声明的版本没有对应 `wf-v*` tag，
pre-push 打印 WARN（只提示、不阻断——先推分支再打 tag 是合法顺序）。

**现有发行 tag 的事实（勿据旧文推测）**：已发行 tag 以 `git tag --list 'wf-v*'` 实况为准；
`0.1.1`–`0.1.6` 是未打 tag 的开发版本，**既不是升级来源、也不能作为升级目标**——升级引用只认
真实 tag。

## 4. 产物校验

- 同一源树应**字节复现**发行根：`python3 scripts/build-wf-release.py --verify`。
- 令牌实现不得漂移：`--verify-token-parity`。
- 清单 `compatibility.rules_digest` 由 `H("wf-rules-v1", …)` 计算，安装器会重算并与声明值比对；
  不一致按 `WF_RELEASE_CONFLICT` 拒绝投放。

## 5. 首发与升级步骤（人执行）

1. 同步版本（`dev-manifest.json` 与本文）；
2. `python3 scripts/build-wf-release.py --version 0.x.y`，复核差异与哈希清单；
3. 人按授权暂存精确路径并提交；
4. 人创建 `refs/tags/wf-v0.x.y`，随后跑 `python3 scripts/verify-wf-release.py --version 0.x.y
   --ref refs/tags/wf-v0.x.y`：不通过则该 tag **不是**有效发行（pre-push 也会拒绝推送它）；
5. 安装：`python3 <发行根>/install.py --target <abs> --release-ref refs/tags/wf-v0.x.y --source <已检出发行目录> [--confirm]`（无平台参数：一次装齐全部支持平台）；
6. 升级：`python3 <目标>/.wf/bin/wf.py upgrade --release <发行检出根> --release-ref refs/tags/wf-vX.Y.Z [--apply | --export-deviations --out <dir>]`——预览含全部路径动作、偏离清单与宿主 `hooks.json` 动作，`--apply` 在交互终端输入预览指纹确认；冲突逐路径用 `--keep <项目相对路径>` / `--restore <项目相对路径>` 选择（路径与预览 `unresolved[].path` 逐字一致，同名技能副本因根不同而各自可处置）；`--keep` 仅对可选资产有效，必需资产保留删除会在写入前 `WF_SEMANTIC_DECISION`。
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
