# brainstorm: trellis升级机制/tmp验证

## Goal

在`/tmp`中构造可重复的测试项目，基于`docs/workflows/新项目开发工作流/`当前定义的安装/升级兼容机制，验证升级后工作流是否还能正确执行，是否存在遗留漂移、假阳性“已安装/已兼容”状态、以及回滚/重装后的残留问题；在真正执行修复前，仅输出问题清单、复现步骤、影响判断和建议修复方案，等待用户确认后再改代码。

## What I already know

* 用户要求先测试，再修复；修复前必须再次确认。
* 升级兼容入口写在`docs/workflows/新项目开发工作流/命令映射.md`，核心脚本是`commands/upgrade-compat.py`。
* 当前机制的实际部署对象是：
  * `.claude/commands/trellis/start.md`
  * `.claude/commands/trellis/{feasibility,design,plan,test-first,self-review,check,delivery}.md`
  * `.trellis/scripts/workflow/{feasibility-check.py,design-export.py,plan-validate.py,self-review-check.py}`
  * `.trellis/workflow-installed.json`
* `install-workflow.py`会备份原始`start.md`并注入 Phase Router。
* `upgrade-compat.py`会比较`.trellis/.version`和`.trellis/workflow-installed.json`里的`trellis_version`，并在版本变化时做检测/合并/强制覆盖。
* `uninstall-workflow.py`会删除已部署命令、删除`.trellis/scripts/workflow/`、恢复备份的`start.md`并清理安装记录。

## Assumptions (temporary)

* 这次要验证的重点不是“文档描述是否合理”，而是“脚本在真实目录状态变化下是否会误判、漏判或留下残留漂移”。
* `/tmp`测试应尽量覆盖 install → simulate upgrade drift → check/merge/force → uninstall/reinstall 的完整生命周期。
* 兼容机制目前主要围绕 Claude 目录实现；如果文档宣称的跨 CLI 能力与脚本行为不一致，这本身可能也是一种漂移。

## Open Questions

* 无。

## Requirements (evolving)

* 基于`/tmp`构造独立测试环境，不污染当前仓库。
* 覆盖至少以下场景：
  * 首次安装
  * 已安装后版本未变
  * 已安装后版本变化但无冲突
  * `start.md`丢失 Phase Router
  * 某些命令/脚本缺失
  * 安装记录损坏或缺失
  * 卸载后重装
  * 安装/升级后与`/trellis:start` Phase Router 相关的最低烟测
* 明确区分三类问题：
  * 执行错误
  * 状态误判
  * 升级遗留漂移
* 在未获确认前，不修改正式实现文件。
* 本轮范围限定为`/tmp`黑盒测试与证据采集，不对当前仓库做漂移检查。

## Acceptance Criteria (evolving)

* [ ] 已识别升级机制涉及的入口脚本、状态文件和目标部署物。
* [ ] 已形成`/tmp`测试矩阵，覆盖安装、升级、回滚、残留漂移检查。
* [ ] 已输出每个问题的复现步骤、实际结果、期望结果和影响面。
* [ ] 在用户确认前，没有修改正式修复代码。
* [ ] 已至少覆盖一次安装后与`start`门禁/Phase Router有关的烟测。

## Definition of Done

* 问题发现阶段：测试已执行，结果有证据，问题按严重度归类。
* 若进入修复阶段：修复后重新执行关键验证链路，并明确说明 pass / fail / not run。

## Out of Scope (explicit)

* 未经确认直接修复正式实现。
* 与本工作流升级机制无关的 Trellis 大范围重构。
* 无法在本地/tmp环境复现的第三方 CLI 内部缺陷。

## Technical Notes

* 任务目录：`.trellis/tasks/03-29-trellis-upgrade-mechanism-tmp-test/`
* 已定位关键文档：`docs/workflows/新项目开发工作流/命令映射.md`
* 已定位关键脚本：
  * `docs/workflows/新项目开发工作流/commands/install-workflow.py`
  * `docs/workflows/新项目开发工作流/commands/upgrade-compat.py`
  * `docs/workflows/新项目开发工作流/commands/uninstall-workflow.py`
* 关键状态判断依赖：
  * `.trellis/.version`
  * `.trellis/workflow-installed.json`
  * `start.md`内是否包含`## Phase Router \`[AI]\``
* `start-patch-phase-router.md`还引入了“首次嵌入后的初始化门禁”，因此黑盒验证不能只检查文件存在性，还要验证安装后的最低执行口径是否合理。
* 初步风险点：
  * 文档写“版本不一致 + 无冲突 → 自动重新部署”，但`--check`模式目前只报错退出，不会自动部署。
  * `upgrade-compat.py`的冲突检测只覆盖`start.md`和 7 个命令，不检查 4 个辅助脚本是否缺失或陈旧，可能漏报漂移。
  * 当前脚本只操作`.claude/commands/trellis`，与“跨 CLI”叙述之间可能存在边界不一致，需要验证是否属于预期。
  * `uninstall-workflow.py`依据安装记录删除命令；若记录缺失/损坏，可能出现残留或清理不全，需要单独验证。

## Research Notes

### What similar tools do

* 安装型工作流通常把“已安装状态”拆成显式元数据和目标文件完整性两层校验，避免仅凭版本号判断成功。
* 升级兼容脚本通常需要同时验证命令、脚本、补丁注入点、备份完整性与卸载可逆性。

### Constraints from our repo/project

* 需要遵守“修复前先确认”的边界，因此先做问题清单与证据采集。
* 本仓库已有历史兼容性验证任务，说明这块逻辑已有过升级后漂移案例，不能只做 happy path。

### Feasible approaches here

**Approach A: `/tmp`黑盒生命周期测试** (Recommended)

* How it works:
  * 在`/tmp`构造最小 Trellis 项目骨架，直接调用 install/upgrade/uninstall 脚本并人工制造漂移。
* Pros:
  * 最贴近真实使用方式，能测出状态误判和残留问题。
* Cons:
  * 需要自己搭建足够像真的目录结构。

**Approach B: 只做脚本静态审查 + 局部命令执行**

* How it works:
  * 以源码分析为主，只运行少量命令验证。
* Pros:
  * 速度快，侵入小。
* Cons:
  * 容易漏掉生命周期残留问题。

**Approach C: `/tmp`黑盒测试 + 当前仓库一次只读对照**

* How it works:
  * 在`/tmp`做主测试，同时对当前仓库安装状态做只读比对，不修复。
* Pros:
  * 能同时发现机制缺陷和本仓库可能已存在的残留漂移。
* Cons:
  * 范围更大，输出也会更多。

## Decision (ADR-lite)

**Context**: 用户要求优先验证升级兼容机制是否存在执行问题与遗留漂移，并明确要求修复前先确认。  
**Decision**: 采用`/tmp`黑盒生命周期测试，仅在隔离环境中执行安装/升级/卸载/漂移注入/烟测，不检查当前仓库实时状态，也不提前修复正式实现。  
**Consequences**: 这能最大限度避免污染当前仓库，并先拿到可复现证据；代价是本轮不会自动发现当前仓库自身可能存在的残留漂移。

## Technical Approach

在`/tmp`创建最小 Trellis 项目骨架，准备：

* `.claude/commands/trellis/start.md`原始文件
* `.trellis/.version`
* 目标部署目录`.trellis/scripts/workflow/`

然后按以下顺序执行黑盒测试：

1. install happy path
2. install 后重复 check
3. 修改`.trellis/.version`，触发 upgrade check
4. 制造单点漂移：
   * 删除 Phase Router
   * 删除某个命令
   * 删除某个 helper script
   * 破坏`workflow-installed.json`
5. 分别执行`--check / --merge / --force`
6. 执行 uninstall → reinstall
7. 对安装后的`start.md`和门禁前提做最低烟测

输出每个场景的：

* 环境前置
* 执行命令
* 观察结果
* 预期结果
* 是否构成 bug / 漂移 / 文档口径问题

## Implementation Plan (small PRs)

* 阶段 1: 搭建`/tmp`测试夹具并跑 install/upgrade/uninstall 主链路
* 阶段 2: 注入破坏场景，验证是否存在漏检和残留漂移
* 阶段 3: 汇总问题清单、风险分级与修复建议；等待用户确认后再进入修复
