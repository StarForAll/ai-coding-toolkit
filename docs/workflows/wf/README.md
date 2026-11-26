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
| 目标版本 | `0.0.16`（只有人主动要求时才改；本轮内容见 [round-history](analysis/round-history.md)）。**0.0.16**：系统级 `wf` 命令由最新正式 release 的稳定 `install.py` 附件启动、再取同一 release 的 wheel（`uv tool` / `pipx`，无版本参数），目标项目用 `wf install`（按命令自身版本）与 `wf upgrade`（取登记源默认分支最新发行），系统命令自身用 `wf self-upgrade` 升级、用 `wf self-uninstall`（预览 + `--apply`）卸载；用户面不再接受 `--release`/`--release-ref`/`--source`；`wf uninstall`/`wf repair` 转交已安装独立入口，运行期命令由 `wf` 定位并转交 `.wf/bin/wf.py`。 |

`dev-manifest.json` 只登记资产清单、版本与必需标记，**不含手填字节哈希**；
`scripts/build-wf-release.py` 与 `scripts/wf-dev-deploy.py` 按源文件字节现算 digest、模板标记与
`rules_digest`，两者共用 `scripts/wf_release_common.py` 的同一份算法（同名函数），首轮锚点因此可复现。

## 2. 工具与运行环境

- `scripts/build-wf-release.py --version 0.x.y`：校验源树完整性 → 生成发行根与清单 → 打印哈希清单。
  `--verify` 重建到临时目录并与现有发行树逐字节比较；`--verify-token-parity` 用固定 `--nonce`
  比对 `repair.py` / `uninstall.py` / `install.py` 三份自含实现的令牌四步输出。
- `scripts/release-wf.py`：一次性完成版本递增、发行校验、本地 tag、wheel 构建、tag push、release 附件上传，
  并在成功发布后把 Forgejo 上超出最新 3 个的**历史 release 与其 tag 一并删除**（先删 release，再删 tag）。
- `scripts/prune-wf-releases.py [--keep 3] [--protect wf-vX.Y.Z] [--dry-run]`：清理超出保留数的
  Forgejo 历史 release（连同 wheel 与 `install.py` 附件）。tag 与 release 是 Forgejo 上两类对象，
  只清 tag 会留下 `/releases` 里的历史版本页；`release-wf.py` 每次成功发布后都调用它，失败时也可单独重跑。
- `scripts/install-wf.py`：本机从 checkout 安装系统级 `wf` 命令（**首次安装入口**）：读取/提示
  `WF_FORGEJO_BASE`、`FORGEJO_TOKEN`，调用 `docs/workflows/wf-cli/install.py` 取最新正式 release 的
  wheel 附件安装，不指定版本。
- `scripts/build-wf-cli-wheel.py`：按发行清单版本构建系统命令 wheel（`wf_cli-<version>-py3-none-any.whl`），
  作为 Forgejo release 附件；不进入项目发行清单。`scripts/attach-wf-cli-asset.py` 用环境变量 token
  把它附加到对应 release；同名同大小视为已附加，同名不同大小拒绝覆盖。
- `docs/workflows/wf-cli/`：系统级 `wf` 命令的发行包（`pyproject.toml` + 仅标准库模块 + 无版本 bootstrap），
  **不投放目标项目**；版本动态读取 `docs/workflows/wf-release/wf-release.json`，因此命令与
  它解析的发行集同版。它从登记源取得按版本 worktree，并调用该发行根 `install.py`。
  系统命令的安装与自升级只使用 release 附件，不在安装命令里指定版本。
- `scripts/wf-dev-deploy.py --target <abs> [--confirm]`：首轮开发态部署（预览 →
  首装契约 → 投放 → 自检 → 释放为空闲）。**安装面向全部支持平台**（`PLATFORMS` 是唯一来源，
  2026-11-23 人裁：不再有 `--platform`），解析出的**目标项目内**技能目录写入
  `installation.json.roots`（相对路径），平台名写入 `installation.platforms`——**平台清单即身份事实**；R93（commit `20e3ae8`）
  已删除 `--host-id`、`--verify-capability` 与 `installation.json.session_profile`，不要按旧口径描述它们。
  目标已安装时的处理（`install.py` 与开发态工具同形）：**重跑 = 补齐/核对**——缺的落点与
  hook 条目只补不改（取写权、产回执）、内容被本地改过则拒绝并指向升级、全一致则只读核对；
  **没有"追加平台"这一步**（安装已面向全部平台）。跨版本在目标项目运行系统级
  `wf upgrade`（预览）→ `wf upgrade --apply`；系统命令解析最新发行后把该发行根
  `install.py --upgrade` 拉起。开发态工具不按新装覆盖。
- 作者机工具（build/dev-deploy/wheel/attach）：仅标准库、在作者机运行、**不进入项目发行清单**。用户入口是系统级 `wf` 命令；
  发行根里的 `install.py` 是它拉起、在目标项目实际应用的入口，按
  `target_class=release_only` 计入 `rules_digest`。

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

**版本推进由人发起**：本仓库不按提交或轮次自动加版本（当前 0.0.16 仍属预正式发行）。
`scripts/release-wf.py` 是发布入口：默认 patch +1，`--minor`/`--major` 由人选择递增级别；
它更新「目标版本」与发行树、提交、建 tag、推送并发布。`scripts/build-wf-release.py` 只重建/校验，
不建 tag、不推送；不要把它的 `--version` 当成自动版本决策。

**义务的机械核对（2026-11-23 起，dogfood 五轮 b-P0）**：上面这条"三者同批"过去只写在本文里——
实况是仓库长期只有 `wf-v0.1.0` 一个 tag，而本文却记载过 0.1.5→0.1.6 可用 upgrade 升级；安装器
只认真实存在的 tag，于是**文档承诺的升级通道在字段上不可执行**。现在同一条义务有可执行核对：

```bash
python3 scripts/verify-wf-release.py --version 0.x.y --ref refs/tags/wf-v0.x.y   # 七项只读核对
```

核对项：tag 存在且解析到提交；源码树重建 == 工作树发行树；tag 提交内的发行树与工作树逐字节相同；tag 提交内 `docs/workflows/wf-cli/` 存在且版本动态解析到同一清单、入口为 `wf = wf_cli.main:entry`
（含"只在工作树多出来的发行文件"）；清单 `version`；本文「目标版本」行；重算 `rules_digest`。
`scripts/release-wf.py` 在本地创建 tag 前运行同一脚本；普通 pre-push 钩子不再处理 wf tag
（普通分支推送与"先提交后打 tag"的顺序不受影响）。`verify-wf-release.py` 只报事实与出口，不创建、不修改、不删除 tag；它不检查 Forgejo release 附件，第 5 步负责把系统命令 wheel 附加到 release。
**"忘记打 tag"不再由 git hook 拦**：普通推送不处理 wf tag；发布入口是
`python3 scripts/release-wf.py`（先提交工作区，再一次性递增版本/打 tag/推送/上传）。
如果只改发行树未发布，`verify-wf-release.py` 会报告 tag 不存在。

**现有发行 tag 的事实（勿据旧文推测）**：已发行 tag 以 `git tag --list 'wf-v*'` 实况为准；
`0.1.1`–`0.1.6` 是未打 tag 的开发版本，**既不是升级来源、也不能作为升级目标**——升级引用只认
真实 tag。

## 4. 产物校验

- 同一源树应**字节复现**发行根：`python3 scripts/build-wf-release.py --verify`。
- 令牌实现不得漂移：`--verify-token-parity`。
- 清单 `compatibility.rules_digest` 由 `H("wf-rules-v1", …)` 计算，安装器会重算并与声明值比对；
  不一致按 `WF_RELEASE_CONFLICT` 拒绝投放。

## 5. 首发与升级步骤（人执行）

1. 确认 `dev-manifest.json` 仍是开发态占位符（`0.0.0-dev`），工作区已提交；
2. 可先跑 `python3 scripts/build-wf-release.py --version 0.x.y --verify` 复核现有发行树；
3. 保持工作区干净（一次性发布脚本拒绝脏工作区，不自动收编无关改动）。
4. 运行 `python3 scripts/release-wf.py [--minor|--major]`：默认 patch `x.x.y -> x.x.(y+1)`，
   `--minor` 为 `x.(x+1).0`，`--major` 为 `(x+1).0.0`；当前清单版本尚无本地 tag 时默认发布该版本。
   脚本更新 README/发行树并提交，先把项目分支推送到**所有已配置 git remote**，再创建并校验
   本地 tag、构建 wheel、push tag 到 Forgejo，最后创建 release 并上传 wheel 与 `install.py`。
   项目分支走所有远端；tag/release 只走 Forgejo。发布成功后 Forgejo 只保留最新 3 个
   `wf-v*` **tag 与对应 release**：先删历史 release（含 wheel 与 `install.py` 附件），再删旧远端 tag；
   本地旧 tag 默认保留，加 `--prune-local-tags` 才删。
   `--prune-tags` 是对正常发布流程的补充开关，不是独立清理命令；远端清理在每次成功发布后都会执行。
5. Forgejo Actions 在本实例不可用（`.forgejo/workflows/` 已移除），发布只有 `release-wf.py` 这一条路径；
   需要手动补发时仍可用
   `python3 scripts/build-wf-cli-wheel.py` 与
   `python3 scripts/attach-wf-cli-asset.py --create-release --tag wf-v0.x.y --wheel tmp/wf-cli-dist/wf_cli-0.x.y-py3-none-any.whl`；
   历史 release 可单独清理：`python3 scripts/prune-wf-releases.py --keep 3 --protect wf-v0.x.y`。
6. 安装系统命令（**不指定版本**）：在本地 checkout 运行 `python3 scripts/install-wf.py`。
   它读取/提示 `WF_FORGEJO_BASE`、`FORGEJO_TOKEN`，调用本地 `docs/workflows/wf-cli/install.py` 取
   最新正式 release 的 wheel 附件安装；公开仓库 token 可空，私有仓库需 token（token 只经环境变量或
   终端输入，不进 argv、不落盘）。没有 checkout 的机器改用登记源上的同一 bootstrap：
   `curl -fsSL "${WF_FORGEJO_BASE}/xzc/ai-coding-toolkit/raw/branch/main/docs/workflows/wf-cli/install.py" | python3 -`
   （私有仓库需带 `Authorization` 头的 urllib 版本，见 [wf-cli README](../wf-cli/README.md)）。
   若 Web/API 地址/端口不同，用 `WF_FORGEJO_BASE` 指定真实基址；若 HTTP/API 不可达而只有 SSH 可用，
   改用 `bash scripts/install-wf-ssh.sh`（按 tag 日期取最新，无版本参数）；随后 `wf version` 核对；
7. 目标项目安装：在该项目根运行 `wf install`（预览）→ `wf install --confirm`（无平台参数：一次装齐全部支持平台）。`--python` 选定运行 wf 的解释器（绝对路径、>=3.11）：给定时写入本机用户级配置并按 global 确认，缺省用系统 `python3` 并按 system 确认；系统没有 `python3` 且未给该参数则拒绝安装。确认提示与写入在安装命令的终端里完成（人输入 yes），不需要再单独跑 `confirm-executor`。**不再给 `--release-ref`/`--source`，也不把本仓库路径当发行源**；命令按自身版本解析登记源 tag；
8. 项目升级：在目标项目根运行 `wf upgrade`（预览）→ `wf upgrade --apply`。它取登记源默认分支**按 tag 创建时间最新**的发行，不支持指定版本；预览含全部路径动作、偏离清单与宿主 `hooks.json` 动作，`--apply` 在交互终端输入预览指纹确认；冲突逐路径用 `--keep <项目相对路径>` / `--restore <项目相对路径>` 选择（路径与预览 `unresolved[].path` 逐字一致，同名技能副本因根不同而各自可处置）；`--keep` 仅对可选资产有效，必需资产保留删除会在写入前 `WF_SEMANTIC_DECISION`。
   `wf upgrade --export-deviations --out <dir>` 是**只读回源**：导出全部本地偏离（含未接受项，清单标 `status=pending`；已接受项标 `accepted`）的补丁与 `manifest.json`，不取写权、不暂停任务、不应用升级；同版也允许导出。与 `--apply` 互斥。
9. 系统命令升级/卸载（与项目操作分开）：`wf self-upgrade` 解析最新系统发行（优先取 release wheel 附件）并替换已安装命令；资产基址与安装同源（`WF_FORGEJO_BASE` → 本机安装记录 `~/.wf/system-command.json` → 登记实例缺省基址），附件取不到时按发行 tag 从 git 安装并明确报告降级（写明地址与原因），不报成资产安装；`wf self-uninstall` 预览 → `--apply` 移除系统命令本身；`wf upgrade` / `wf uninstall` 只作用于项目内资产。

打包脚本不提交、不建 tag、不推送；系统 wf 命令只从登记源解析发行 tag，不把本机 checkout 当发行源。

**定位口径（`--project` 可选）**：7–9 步的命令都可省略 `--project`——在项目内运行时缺省用当前目录
（`wf upgrade`/`wf uninstall`/`wf repair`/`wf version` 从当前目录向上找 `.wf/`，`wf install` 直接用当前目录），
只在项目外才需要 `wf --project <绝对路径> <命令>`。项目内的 `.wf/bin/wf.py` 同样接受可选 `--project`：
先按脚本自身安装位置确认 `.wf/bin` 布局，确认不了（重取/复制出来的入口）再取当前目录；`.wf/bin/repair.py`
与 `.wf/bin/uninstall.py` 取 `--project` → 引导层转交的 `WF_PROJECT_ROOT` → 当前目录。所有缺省都要过同一
`.wf/` 布局（与安装记录）核对，所以在项目根直接运行单文件即可，坏运行时下不必再凑 `--project`。

## 6. 目录速览

```
payload/bin/{wf.py, repair.py, uninstall.py}   # 引导层与两个自含独立入口
payload/install.py                             # 发行根安装/升级入口（不投放；自定位发行根/tag）
payload/lib/wflib/*.py                         # 运行时包（32 个 .py 文件，含 `__init__.py`；仅标准库）
payload/workflows/*.md                         # 6 份流程文档（每个 required 步骤带 enforcement 行）
payload/templates/**                           # 配置/spec/任务/基线/用户定义模板
skills/<13 个>/SKILL.md                        # 宿主 skill 副本
dev-manifest.json                              # 资产登记（打包与开发态部署的输入）

../wf-cli/                                     # 系统级 wf 命令发行包（不投放项目）
```

目标项目侧的落点、升级/卸载覆盖与项目数据分区见实现方案 §1.1–§1.3。

## 7. 原语与审查副本的来源登记

`skills/` 下 13 个副本中，6 个是改编件（`wf-grilling`、`wf-tdd`、`wf-diagnosing-bugs`、`wf-code-review`、`wf-review`、`wf-review-action`），
其余 7 个（`wf-start`、`wf-continue`、`wf-finish`、`wf-bootstrap`、`wf-spec-update`、`wf-repair-loop`、`wf-review-accept-unknown`）为本项目原创。
每个改编件在自己 `SKILL.md` 末尾带「来源与差异」段，登记来源、许可、基线、差异与最近正反例（设计稿 §7.4）。

- 审查两副本（`wf-review`/`wf-review-action`）的适配源是本仓库全局 `skills/multi-cli-review*`，属一次性适配源；适配成果只由本目录的副本承载。
- 来源仓库为内部私有源；上游改动不自动流入，吸收与否由人裁决（设计稿 §7.5）。目标项目不跟上游。
