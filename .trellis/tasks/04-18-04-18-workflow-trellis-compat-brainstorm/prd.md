# brainstorm: 提升新项目工作流 Trellis 兼容性

## Goal

分析 `docs/workflows/新项目开发工作流` 在最新 Trellis 初始化项目中的实际嵌入兼容性，站在真实开发实践视角识别使用问题、兼容风险和数据漂移风险，并在用户确认后再执行限定于 `docs/workflows/新项目开发工作流` 目录范围内的修复。

## What I already know

* 用户要求先在 `/tmp` 创建空白项目，执行 `trellis init`，再嵌入当前项目的 `docs/workflows/新项目开发工作流`。
* 本轮目标是剖析、兼容性分析和修复方案确认；未获得明确同意前不执行具体兼容性修复。
* 修复范围必须限定在 `docs/workflows/新项目开发工作流` 目录内。
* 修复时必须避免数据漂移，尤其是版本号、命令映射、安装器、测试、文档和生成物之间的漂移。
* 项目规范要求 Trellis 官方基线来自 `/tmp` 空白项目执行 `trellis init` 后的纯净产物，不能用当前仓库已经定制过的 `.trellis/` 或 CLI 目录充当基线。

## Assumptions (temporary)

* “最新版本 Trellis”以当前机器可执行的 `trellis init` 产物作为实际兼容基线；外部公开版本信息仅作为辅助证据。
* 本轮不会处理目标项目业务代码，也不会修改当前仓库根目录下除任务 PRD 外的文件。

## Open Questions

* 待兼容性分析完成后，用户需要从候选修复方案中确认一个实施方向。

## Requirements (evolving)

* 在 `/tmp` 创建干净目标项目并完成 `trellis init`。
* 将当前仓库的 `docs/workflows/新项目开发工作流` 嵌入该目标项目。
* 从实际开发流程、安装结果、托管边界、版本记录、命令可用性和数据漂移风险分析兼容问题。
* 给出可执行的修复方案，但在用户确认前不实施。

## Acceptance Criteria (evolving)

* [ ] 有一份基于实际 `/tmp` 初始化和安装结果的兼容性分析。
* [ ] 明确列出已验证通过、失败、未验证或存在证据缺口的部分。
* [ ] 给出 2-3 个具体修复方案及取舍。
* [ ] 在实施前获得用户明确确认。

## Definition of Done (team quality bar)

* Tests added/updated where implementation changes behavior.
* Validation commands run and reported truthfully.
* Docs/notes updated if behavior changes.
* Data drift across workflow version, installer, docs, tests, and generated references is checked.

## Out of Scope (explicit)

* 未经用户确认，不修改 `docs/workflows/新项目开发工作流`。
* 不修改当前仓库的 `.trellis/`、`.claude/`、`.opencode/`、`.codex/` 作为兼容性修复目标。
* 不处理任意目标项目业务代码。
* 不执行 `git commit`。

## Technical Notes

* `ace.search_context` 已定位到 `install-workflow.py`、`upgrade-compat.py`、`workflow_assets.py`、安装器测试和目标项目兼容升级指导。
* 外部检索初步显示 Mindfold Trellis CLI 最新公开版本可能为 `0.4.0`，但需要结合本地 `trellis --version` 和 `/tmp` 实际产物确认。
* 本地 `trellis --version` 返回 `0.4.0`；公开 npm 源 `@mindfoldhq/trellis` 也显示 latest 为 `0.4.0`。
* 已创建真实 `/tmp` 目标项目 `/tmp/trellis-compat-yVHdBF`，执行 `git init -b main`、配置 `origin` 两个 push URL，并运行 `trellis init --claude --opencode --codex -u xzc -y`。
* 已在 `/tmp/trellis-compat-yVHdBF` 上安装当前 workflow，安装器返回 0，部署 Claude/OpenCode/Codex 三类适配层。
* 安装后 `upgrade-compat.py --check --project-root /tmp/trellis-compat-yVHdBF` 返回 0，总冲突为 0。
* 已构建三态 fixture：
  * A: `/tmp/trellis-compat-a-bMnwPp`，纯净 Trellis 0.4.0 init
  * B: `/tmp/trellis-compat-b-HqrNxA`，A 上安装当前 workflow
  * C: `/tmp/trellis-compat-yVHdBF`，真实安装目标项目
* `analyze-upgrade.py --baseline-root A --expected-root B --target-root C --cli claude,opencode,codex` 返回 0，报告 54 个 `keep`，无 `add/replace/merge/delete`。
* 实际开发路径检查：
  * `.trellis/scripts/get_context.py` 可正常输出会话上下文。
  * `.trellis/scripts/task.py list` 可正常输出任务列表。
  * `feasibility-check.py --help`、`workflow-state.py --help`、`record-session-helper.py --help` 可正常输出帮助。
  * `plan-validate.py --help` 返回 1 并报 `task_plan.md 不存在`，不是纯帮助行为。
* 发现的兼容性/实践问题：
  * 安装完成提示的下一步编号出现 `2` 和 `2.1`，对用户执行路径不够清晰。
  * Trellis 0.4.0 目标项目没有 `.trellis/spec/index.md`，但 workflow 文档 `命令映射.md` 仍把它列为“项目规范索引”；真实索引位于 `.trellis/spec/<layer>/index.md` 或嵌套目录。
  * `workflow-installed.json` 不记录 `AGENTS.md` NL 路由块、`todo.txt`、`.trellis/library-lock.yaml` 导入结果，当前文档将它们列为人工必检项；这是可接受边界，但安装后自检不覆盖这些资产的漂移。
  * `plan-validate.py` 缺少标准 `--help` 早返回，不符合脚本可探索性预期。
  * 当前安装器单测主要使用手工 fixture 的 `2.0.0/2.1.0` 版本，没有覆盖真实 `trellis init 0.4.0` smoke fixture；这会让未来 Trellis 基线变化更难提前发现。
* 已按用户要求补充“直接审阅临时项目”的人工兼容性判断，不只依赖脚本：
  * Claude/OpenCode 的 `.claude/.opencode/commands/trellis/start.md` 已注入 Phase Router；但 Codex 的 `.agents/skills/start/SKILL.md` 仍是 Trellis 原生 start skill，不包含强门禁 Phase Router。AGENTS.md 虽有自然语言路由，但如果用户显式触发 `start` skill，仍可能落回原生 Task Workflow 语义，绕开“先 feasibility / workflow-state / 不自动跨阶段”的新 workflow 规则。
  * 安装后的阶段命令和 skills 中仍残留大量源仓库维护语境引用，例如 `docs/workflows/新项目开发工作流/commands/shell/workflow-state.py`、`../阶段状态机与强门禁协议.md`、`../需求变更管理执行卡.md`、`见 codex/README.md` / `opencode/README.md`。这些文件在目标项目中不存在，用户在临时项目里点击链接或复制某些源仓库命令会失败或迷路。
  * `feasibility.md` 的流程顺序存在实践矛盾：Step 1.5 要求用 `<任务目录>` 生成 `risk-analysis-guide.md` 和 `assessment.md`，但 Step 4 才创建正式 `TASK_DIR`；同时又规定 Step 1.5 未完成前不得进入 Step 4。这会让首次新项目评估缺少明确的评估目录落点。
  * Codex 路由表在 `AGENTS.md` 中写“显式触发 `start` skill”，但实际 `start` skill 未被 workflow 覆盖；这是路由文案与真实 skill 行为不一致。
  * 阶段命令中的相对 Markdown 链接在 Claude/OpenCode 命令目录或 Codex skill 目录下不具备可解析的目标文件，说明安装器当前只同步阶段命令本体和 helper scripts，未同步 workflow 参考文档或替换为目标项目可用路径。

## Research Notes

### What similar/related tooling evidence says

* `@mindfoldhq/trellis` npm 页面显示 latest version 为 `0.4.0`。
* 本地 `trellis init --help` 支持 `--claude`、`--opencode`、`--codex`、`-u/--user`、`-y/--yes` 等参数，和本次 fixture 构建方式一致。

### Constraints from this repository

* 工作流源资产兼容修复必须限定在 `docs/workflows/新项目开发工作流`。
* 必须避免版本、命令映射、安装器、测试和文档之间的数据漂移。
* 修改后需至少运行 `test_workflow_installers.py` 和 workflow installer/upgrade/analyze 相关 smoke 验证。

### Feasible approaches here

**Approach A: 目标项目可执行性修复 + smoke 测试补强（推荐）**

* How it works: 在保留当前托管边界的前提下，修复目标项目内直接使用会踩坑的问题：
  * 覆盖或补丁化 Codex `.agents/skills/start/SKILL.md`，使其承载同等 Phase Router / 强门禁语义，或把 AGENTS.md 中 `start skill` 推荐改为不会触发原生 start 的自然语言状态恢复入口。
  * 清理安装后命令/skills 中的源仓库维护路径，把 `docs/workflows/.../commands/shell/*.py` 示例统一替换为 `.trellis/scripts/workflow/*.py`，并将不可用 Markdown 链接改成“安装后说明文本”或同步必要参考文档。
  * 修正 `feasibility` 首次评估目录顺序，明确 Step 0 先创建/选择 assessment task 或临时评估目录，再写 `assessment.md`。
  * 修复 `plan-validate.py --help`、安装完成编号、`.trellis/spec/index.md` 文档残留。
  * 补充安装后直接审阅/grep 型测试，覆盖目标项目中不存在的源仓库路径残留、Codex start 语义和真实 Trellis 0.4.0 fixture。
* Pros: 直接解决“脚本通过但目标项目不好用”的问题，兼容性收益最大。
* Cons: 触及 Codex start 入口与阶段命令文案，需做跨文件同步和回归测试。

**Approach B: 扩大自动漂移检测边界**

* How it works: 在 Approach A 基础上，在 `upgrade-compat.py` 或 `analyze-upgrade.py` 中把 `AGENTS.md` NL 路由、`todo.txt`、`.trellis/library-lock.yaml`、目标项目可解析链接/路径残留也纳入自动检查。
* Pros: 更强自动化，减少人工必检项遗漏。
* Cons: 边界更复杂，`todo.txt` 和 library-lock 容易与目标项目本地变更冲突，误报风险更高。

**Approach C: 只更新文档，不改脚本**

* How it works: 保留现有脚本行为，仅把实际 Trellis 0.4.0 兼容结论、人工必检边界、Codex start 入口限制、源仓库路径残留和 feasibility 首次目录顺序写清楚。
* Pros: 最低风险。
* Cons: 目标项目仍会保留实际使用踩坑点，未来兼容回归仍主要靠人工发现。
