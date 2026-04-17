# brainstorm: 修复新项目开发工作流归属与水印方案

## Goal

在不破坏当前 `docs/workflows/新项目开发工作流` 的 Trellis 核心工作流模型前提下，分析并设计一套可落地的“作者归属声明 / 水印 / 防冒名顶替”方案。方案需要兼容当前工作流的多 CLI 原生适配边界（Claude Code / Codex / OpenCode），并在涉及 Trellis 联动时，先通过 `/tmp` 临时项目上的真实 `trellis init` 产物验证判断基础。

## What I already know

* 用户当前只要求分析与修改方案，不要求立即修改仓库文件
* 分析范围限定在 `docs/workflows/新项目开发工作流/`
* 涉及 Trellis 联动时，需要先在 `/tmp` 新建临时项目并执行 `trellis init`
* 修改方向必须优先遵守 Trellis 框架核心，再按 Claude Code / Codex / OpenCode 官方原生格式适配
* 用户特别要求深入分析 `out/` 目录下 6 个文件内容，并据此判断“个人开发项目如何防冒名顶替 / 如何永久保存水印”
* 当前 workflow 已存在多 CLI 适配文档、安装器、升级兼容脚本、命令补丁和 shell 辅助脚本

## Assumptions (temporary)

* `out/` 目录中的 6 个文件承载了外部项目交付控制、归属声明、授权/移交相关的示例或候选方案
* 需求中的“防冒名顶替”不能被理解为绝对技术防伪，更可能是“提高伪造成本 + 保留可审计证据链 + 在交付物中保留稳定署名/归属元数据”
* 若要做到“永久保存水印”，需要区分文档/代码/仓库/部署产物/运行时 UI 这些不同载体，单一手段不足以覆盖全部场景
* 当前 workflow 可能尚未把作者归属、交付签名、授权切换、元数据校验做成统一机制

## Open Questions

* 用户期望保护的“项目归属”主要覆盖哪些交付载体：源码、文档、网页 UI、构建产物、部署实例、合同/授权材料，还是全部？
* 用户对“水印”的接受边界是什么：显式署名、隐式元数据、不可见指纹、法律/合同证据链，还是多层叠加？

## Requirements (evolving)

* 分析 `docs/workflows/新项目开发工作流/` 中与安装、CLI 适配、交付控制、元数据闭环相关的工作流资产
* 分析 `out/1.md` 至 `out/6.md`（含 `out/4.pdf`）的内容及其对归属/水印设计的启发
* 在 `/tmp` 中创建临时 Trellis 项目并执行 `trellis init`，确认 Trellis 基线产物、命令入口和当前 workflow 的真实叠加点
* 给出符合现实约束、可审计、可实施、与多 CLI 原生适配兼容的修改方案
* 修改方案必须补上“源码中的水印操作”，不能只停留在外部证据链
* 源码水印方案需显式覆盖：
  * 零宽字符水印
  * 偶然代码中不起眼位置的代码标识 / 分片标记
* 在真正动手修改前，先向用户说明修正思路并获得确认

## Acceptance Criteria (evolving)

* [ ] 明确当前 workflow 中与作者归属/水印/交付控制相关的现状与缺口
* [ ] 明确 Trellis 基线与当前 workflow 自定义层的边界
* [ ] 明确 Claude Code / Codex / OpenCode 下可原生承载的归属/水印机制
* [ ] 给出至少一套推荐方案，并说明为什么它在现实中有效、哪些风险无法绝对消除
* [ ] 若仍有关键偏好缺失，只提出最小阻塞问题，不提前改动仓库

## Definition of Done (team quality bar)

* 方案包含证据链、约束、风险和取舍
* 结论基于仓库现状与临时 Trellis 项目验证，不依赖猜测
* 未经用户确认，不执行仓库修改

## Out of Scope (explicit)

* 本轮不直接修改 `docs/workflows/新项目开发工作流/`
* 本轮不承诺实现“绝对不可伪造”的归属保护
* 本轮不处理与当前工作流无关的其他项目目录

## Technical Notes

* 任务目录：`.trellis/tasks/04-17-workflow-watermark-hardening/`
* 初步定位到的关键文件：
  * `docs/workflows/新项目开发工作流/commands/install-workflow.py`
  * `docs/workflows/新项目开发工作流/commands/workflow_assets.py`
  * `docs/workflows/新项目开发工作流/命令映射.md`
  * `docs/workflows/新项目开发工作流/CLI原生适配边界矩阵.md`
  * `docs/workflows/新项目开发工作流/commands/claude/README.md`
  * `docs/workflows/新项目开发工作流/commands/opencode/README.md`
  * `docs/workflows/新项目开发工作流/commands/codex/README.md`
* 已确认本机可用 `trellis` 命令：`/ops/softwares/nodeNpm/nodejs/bin/trellis`

## Repo Inspection Findings

### Workflow current-state findings

* `docs/workflows/新项目开发工作流/工作流总纲.md` 已明确要求：维护 workflow 源内容时，Trellis 升级兼容判断必须以 `/tmp` 临时项目执行 `trellis init` 后的纯净产物为基线，而不是拿当前仓库已混入补丁的 `.trellis/`、`.claude/`、`.opencode/`、`.codex/` 当初始 Trellis
* `docs/workflows/新项目开发工作流/CLI原生适配边界矩阵.md` 明确了三类资产分工：安装器管理、手动维护、运行前置/仅校验；`AGENTS.md` 在三种 CLI 中都被视为“项目长期规则”，但当前 workflow 没有把作者归属或签名校验纳入这一层的明确契约
* `docs/workflows/新项目开发工作流/commands/install-workflow.py` 当前负责分发阶段命令、共享脚本，以及对部分 Trellis 基线命令做补丁增强；并不负责创建长期的归属证明资产，如 `NOTICE`、签名公钥、归属报告模板、SBOM / provenance 文件
* `docs/workflows/新项目开发工作流/commands/shell/delivery-control-validate.py` 当前只校验双轨交付控制字段、交付任务拆分、交付物目录和 `transfer-checklist` 基本内容；未校验作者署名、版权声明、源码包校验和、签名、公钥指纹、时间戳、归属验证报告
* `docs/workflows/新项目开发工作流/commands/delivery.md` 当前交付阶段关注“控制权移交是否合规”，但没有建立“交付物如何证明这是开发者原始作品”的验证门禁

### Existing reusable assets

* `trellis-library/checklists/universal-domains/project-governance/transfer-checklist.md` 已要求记录源码仓库/归档身份和 commit/checksum，但未延伸到签名、公钥、时间戳、NOTICE、归属验证证据
* `trellis-library/templates/universal-domains/project-governance/external-project-delivery-tasks/source-code-transfer.md` 已要求归档 transfer record with hash and timestamp，说明 workflow 已具备“哈希 + 时间”的语义基础，可进一步扩展为更完整的归属证据链
* `trellis-library/templates/universal-domains/project-governance/external-project-delivery-tasks/trial-run-delivery.md` 已出现“Apply trial branding (watermarks, 'Trial Version' labels) if applicable”，说明“水印/标识”并非完全陌生概念，但目前仅用于试运行品牌提示，不等于归属确权机制

### Gaps identified

* 当前 workflow 有“交付控制”，但没有“归属控制 / author provenance”概念
* 当前 workflow 有“transfer-checklist”，但没有“ownership-evidence checklist”或“provenance manifest”
* 当前 workflow 有 `record-session` 元数据闭环，但没有“对外可验证的作者证据闭环”
* 当前三 CLI 适配文档强调官方原生格式与 Trellis 核心优先，但没有针对归属/签名/水印的 CLI 分工说明

## /tmp Trellis Baseline Findings

* 在 `/tmp/trellis-baseline-20260417` 执行 `git init`、切换本地分支为 `main` 后，运行 `trellis init --claude --opencode --codex -y -u xzc` 成功生成纯净基线
* 纯净基线中存在：
  * `AGENTS.md`
  * `.claude/commands/trellis/*.md`
  * `.opencode/commands/trellis/*.md`
  * `.agents/skills/*/SKILL.md`
  * `.codex/config.toml`
  * `.codex/hooks.json`
  * `.claude/settings.json`
  * `.trellis/scripts/*.py`
* 纯净基线里的 `AGENTS.md` 只包含 Trellis 启动指引，不承载版权、归属、签名或水印规则
* 纯净基线里的 `record-session` / `add_session.py` 只解决工作日志与 `.trellis/` 元数据闭环，不解决对外交付的作者归属证明
* `trellis --help` 输出显示本机 CLI 提示存在 `0.4.0-beta.9 -> 0.4.0-beta.10` 更新；但新初始化项目中的 `.trellis/.version` 为 `0.4.0-beta.10`。这意味着当前 workflow 若要依赖“最新 Trellis 版本”判定，需要区分 CLI 本体版本提示与新初始化产物版本
* 对临时项目执行 `install-workflow.py --dry-run` 时，安装器首先卡在 `origin` 至少 2 个 push URL 的前置校验，说明当前 workflow 的嵌入模型默认把“多远端可审计发布”当作正式安装前提；这与“作者归属证据链”方向是相容的

## Out Folder Findings

* `out/1.md`、`out/2.md`、`out/3.md`、`out/4.pdf`、`out/5.md`、`out/6.md` 都围绕同一主题：个人开发项目的防冒名顶替、版权保护、水印、签名、时间戳、证据链
* 六份材料高度重合，反复出现的共同结论是：
  * 无法“绝对防止”冒名，只能提高伪造/洗稿成本并建立强证据链
  * 单一水印不可靠，必须组合“版权/许可证 + Git/发布签名 + 哈希/时间戳存证 + 交付验证记录”
  * 源码级隐形水印和高级二进制水印存在，但对个人开发 workflow 来说，直接落地成本高、跨技术栈通用性弱、难以做成工作流默认强制项
  * 更现实的主线是：显式署名、签名、校验和、时间戳、交付时的归属报告和验证步骤
* `out/4.pdf` 标题为“源码隐形水印确权方案 - Google 文档”，创建时间为 `2026-04-17 07:59:09 CST`，内容同样强调多层证据链：GPG/SSH 签名、RFC 3161 时间戳、源码深层水印、司法证据链
* `out/6.md` 的表达最贴近工程现实：先分威胁场景，再选组合；推荐优先级是版权声明 / README 身份说明 / Git 提交与标签签名 / 发布物签名 / 哈希与时间戳 / 再按需增加轻量源码指纹与 SBOM / provenance

## Preliminary Solution Direction

* 推荐不要把“复杂源码深层水印 / 动态二进制水印”做成当前 workflow 的默认主方案
* 推荐把“作者归属保护”拆成四层可验证资产：
  * 法律与声明层：版权声明、许可证、`NOTICE` 或等效作者声明
  * 仓库与发布层：Git tag / commit 签名、公钥指纹、发布物 checksum
  * 存证层：时间戳 / 归档记录 / 外部证据索引
  * workflow 交付层：归属验证清单、交付报告、CLI 适配说明、交付阶段门禁
* 若后续要修改当前 workflow，更像是新增“归属证据链”规范与验证点，而不是承诺用某种神奇水印永久锁死代码归属
* 用户已明确要求把“源码中的水印操作”补入 workflow，因此后续推荐方案需要把源码水印拆成明确的设计决策、实施 task、交付校验和验证报告
* 用户进一步要求把“零宽字符水印”和“不起眼处的代码标识”纳入正式方案，因此默认分层需要从“可见 + 静态分片 + 零水印记录”扩展为“可见 + 零宽字符 + 不起眼静态分片 + 零水印记录”
