---
doc: wf 独立框架实现方案
scope: 目标项目的文件布局、脚本接口、命令形态、发行物构成与单页使用速查
audience: 框架实现者、安装者与日常使用者
status: 按已覆盖轴定稿（以未参与修订的独立 CLI 复审为准，共 12 轮、逐轮定向）：早期 10 轮覆盖功能与协议面；第十一轮针对本次结构性改动（task-new 合并为 writer 父动作、Finish→Check 迁移）判「不成立」并给 D1–D4，修复后第十二轮按同一注入矩阵复验判「成立 / A1 的修复可接受」；同一轮把 `repair --dispose` 的锁忙出口文案与一处死分支修掉。**未覆盖轴**：真实断电/fsync 掉电、并发竞争、`repair` 接管路径、dogfood 真实使用观察。（D1 的“压缩后绑定仍可读”已于 2026-11-05 第三次真实压缩后复核成立，见 validation.md §85。）因此「定稿」仅指已覆盖轴；未覆盖轴见本文 §2.3.11 与 validation.md §65–§83。
baseline: 机制稿首版（2026-11-02 人工审查通过）与设计稿/charter 定稿
normative: 本文件只定义文件布局、脚本接口、命令形态与发行物构成；记录 schema、判定编码、状态机与算法由机制稿定义，本文件不复制
---

# wf 独立框架实现方案

**目录**：§0 效力与遵循声明 · §1 资产与模块拆分 · §2 CLI 与子命令面 · §3 命令引导与执行器解析 · §4 发行物组装 · §5 审查适配 · §6 首轮最小闭环实现清单 · §7 验证与验收映射 · §8 单页使用速查 · §9 未落地项与已裁定事项

## 0. 效力、遵循声明与阅读方式

**遵循声明**：本文件遵循 [wf 框架基调与边界](./wf-framework-charter.md)（charter）及 [wf 框架设计](./wf-framework-design.md)（设计稿），并把 [wf 独立框架机制设计](./wf-framework-mechanism.md)（机制稿）的编码落成可投放的文件结构与命令面。charter 定义要不要做、边界与停止条件；设计稿定义行为与验收；机制稿定义记录 schema、判定编码、状态机与算法；本文件只定义布局、接口、命令形态与发行物构成。冲突按 charter T1 与设计稿 §1.5 交人裁决，本文件不自行改变上位规则，也不以「实现更方便」放宽任何门禁。

**分工与优先级（唯一定义）**：本文件与机制稿冲突时以机制稿为准，修正本文件；与设计稿或 charter 冲突时按 charter T1 出「需人裁决」，不改上位、不改机制稿。本文件不重复定义任何判定：凡出现状态值、原因码、记录字段、哈希公式、门禁顺序，一律引用机制稿对应章节；删除引用后仍需保留的只剩「文件在哪、函数叫什么、命令怎么拼」。违反这一分工的段落按缺陷处理。

**输入基线与不改动声明**：机制稿 §0.1 以四份文件（设计稿、charter、定义索引、来源说明）的 SHA-256 作为输入基线，机检报告「输入摘要 4/4」。本文件不在基线内，且本阶段不修改这四份文件、不在其上新增指针（唯一的入站指针落在机制稿 §12.4，机制稿不在摘要基线内，见本文 §9.2 第 2 项）。本文件的内容若被日后判定与机制稿冲突，只改本文件并重跑机检，不改上游摘要。

**引用约定**：`本文 §x.y` 指本文件章节；`机制稿 §x.y`、`设计稿 §x.y` 分别指两份上游文档；`charter Tn` 指 charter 条目。机制稿的「操作名」（`task.check`、`writer.acquire` 等）只作机制标识，不等于公开子命令（机制稿 §0）。`scripts/check-doc-refs.py` 对本文件使用严格模式（2026-11-02 人裁）：每个 `§x.y` 必须带所有者前缀（`本文 `、`机制稿 `、`设计稿 `；脚本另登记 `依赖说明 `、`原 ` 两条旧文档专用前缀），缺前缀即报错——**即使本文件存在同号章节**；`本文 §x.y` 另核本文件章节真实存在；连续列举可只写一次前缀（`机制稿 §1.3、§8.1` 与 `机制稿 §6.2–§6.4` 整组继承），前缀与 `§` 之间出现其他语义文字则不予继承。该脚本只核引用形状与可解析性，不核语义归属，也不核 markdown 链接目标；不在 `validate-wf-design.py` 的七项检查内，二者互不替代。

**验证纪律**：本文第 7 章列出的验证顺序、第 5 章的审查链路与第 1 章的投放自检，写作时为待运行断言。2026-11-03 首轮实现已实跑并记录（任务记录 `validation.md`，含版本、环境与未运行项的原因分类）；实际结果只在该记录与本文 §7.3 表述，不以文本引用推出未跑项的可用性。

**四层对象（后文一律按此命名）**：

| 层 | 位置 | 说明 |
|---|---|---|
| authoring 源树 | 本仓库 `docs/workflows/wf/` | 模块源，不是可运行应用；作者侧编辑与打包输入 |
| 打包发行树 | 发行提交根 | 由源树生成，含 `wf-release.json`；安装器的唯一输入 |
| 目标项目 | 被安装项目的工作树 | `.wf/` 资产与数据、宿主 skill 根、`.gitignore` 托管段 |
| 本机用户层 | `~/.wf/` | 单机用户配置与解释器确认集合；不进项目 Git、不随发行投放 |

## 1. 资产与模块拆分

### 1.1 目标项目目录总览

```
<目标项目根>/
├── .wf-lock                       # 最小互斥锁对象（运行态，只创建不删除；机制稿 §4.1）
├── .gitignore                     # 含 wf 托管段（本文 §4.5）
└── .wf/
    ├── bin/{wf.py, repair.py, uninstall.py}      # 发行资产：引导 + 两个独立恢复入口
    ├── lib/wflib/*.py                            # 发行资产：运行时包（仅标准库）
    ├── workflows/*.md                            # 发行资产：框架流程文档
    ├── templates/**                              # 发行资产：配置/spec/任务/基线模板
    ├── install/{installation.json, release-manifest.json, recovery.md}  # 本机投放事实（默认卸载保留）
    ├── tasks/                                    # 项目数据：任务记录与内容
    │   ├── <task-id>-<slug>/{task.json, prd.md, design.md, implement.md, review/review-round-<N>/<slot>.md}
    │   └── archive/<YYYY-MM>/<task-id>-<slug>/...
    ├── preparations/<preparation-id>.json        # 项目数据：准备记录
    ├── user-workflows/<workflow-id>.md           # 项目数据：用户工作流定义
    ├── workflow-runs/<run-id>.json               # 项目数据：实例记录
    ├── workflow-runs/<run-id>/definition.md      # 项目数据：固定快照
    ├── workflow-runs/<run-id>/artifacts/<step-id>/ # 项目数据：步骤专属产物根（step_artifact 落点）
    ├── session-bindings/<session-key>.json       # 项目数据：会话绑定
    ├── writer.json                               # 项目数据：写入权记录（含维护回执）
    ├── project-config.json                       # 项目数据：项目配置
    ├── baseline.md                               # 项目数据：项目基线（含治理面机读块）
    ├── spec/{index.md, pre-dev-checklist.md, quality-checklist.md, rules/*.md}
    ├── out-of-scope/<concept>.md                 # 项目数据：项目内知识拒绝
    └── .runtime/                                 # 运行态（gitignore，可重建）
        ├── sessions/<session-key>.json
        └── spec-reads/<session-key>.json
```

`<task-id>` 为机制稿 §1.1 的 `Id`（`YYYY-<uuid32>`），目录名以完整 id 起首后接名称 slug；`archive/{YYYY-MM}` 的月份取 `archived_at` 的 UTC 月（机制稿 §1.1、§5.2）。活动根与归档根的相对位置由本文固定为 `tasks/` 与 `tasks/archive/`；机制稿 §5.2 只要求「任务目录名以完整 id 起首」与归档分层，其余布局为实现方案职责。

### 1.2 资产落点表（资产类型 → 具体路径 → 所有者 → 升级/卸载覆盖）

目标是机制稿 §10.1 的落实：该表只到类型，本节点到文件名。

| # | 资产 | 具体路径（目标项目内，除注明） | 所有者/写者 | 升级（机制稿 §10.4 三方） | 默认卸载 |
|---|---|---|---|---|---|
| A1 | 常规引导脚本 | `.wf/bin/wf.py`（单文件，纯引导段） | 发行资产 | 覆盖（`L=O` 则更新为 `N`；偏离走冲突预览） | 移除 |
| A2 | 运行时包 | `.wf/lib/wflib/{module_main,__init__,cli,records,paths,fingerprint,scope,actions,lock,writer,session,tasks,gates,check,curation,spec,runs,review,maintenance,assets,config,templates,codes}.py` | 发行资产 | 逐文件覆盖 | 移除 |
| A3 | 独立恢复入口 | `.wf/bin/repair.py`（单文件、仅标准库、**不导入** `wflib`） | 发行资产 | 覆盖 | 移除 |
| A4 | 独立卸载入口 | `.wf/bin/uninstall.py`（单文件、仅标准库、**不导入** `wflib`） | 发行资产 | 覆盖 | 移除（自身在退出末尾处理） |
| A5 | 框架流程文档 | `.wf/workflows/{task-flow,session-flow,review-flow,knowledge-flow,instance-flow,maintenance-flow}.md` | 发行资产 | 覆盖；本地修改作为偏离保护 | 移除 |
| A6 | 项目配置模板 | `.wf/templates/project-config.skeleton.json` | 发行资产 | 覆盖；已生成的 `.wf/project-config.json` 属项目数据，不替换 | 移除模板 |
| A7 | spec 模板 | `.wf/templates/spec/{index.md,pre-dev-checklist.md,quality-checklist.md,rule.md}` | 发行资产 | 覆盖 | 移除结构；已生成的 `.wf/spec/**` 属项目数据，保留 |
| A8 | 任务模板 | `.wf/templates/task/{prd.md,design.md,implement.md,task-record.json}` | 发行资产 | 覆盖 | 移除结构 |
| A9 | 基线模板 | `.wf/templates/baseline.md` | 发行资产 | 覆盖 | 移除结构；`.wf/baseline.md` 保留 |
| A10 | 用户定义模板 | `.wf/templates/user-workflow.md` | 发行资产 | 覆盖 | 移除结构 |
| A11 | 入口 skill | `<skill 根>/wf-start/`、`wf-continue/`、`wf-finish/`、`wf-bootstrap/`、`wf-spec-update/`（各 `SKILL.md`） | 发行资产 | 覆盖；偏离按裁决 | 移除 |
| A12 | 审查成对副本 | `<skill 根>/wf-review/`、`wf-review-action/` | 发行资产 | 覆盖；纳入三方升级 | 移除 |
| A13 | 原语副本 | `<skill 根>/wf-grilling/`、`wf-tdd/`、`wf-diagnosing-bugs/`、`wf-code-review/` | 发行资产 | 覆盖 | 移除 |
| A14 | `.gitignore` 托管段 | `<目标项目根>/.gitignore` 内由 `# wf-managed-v1` 与 `# wf-managed-end` 界定的连续段 | 发行资产约定（段外属用户） | 按标记串定位整段比对；段内容与登记不符按偏离 | 移除整段，保留 `/.wf-lock` 裸行 |
| A15 | 最小互斥锁对象 | `<目标项目根>/.wf-lock` | 运行态 | 不参与 O/L/N | **不删除**（预览报告存在，人手清理） |
| A16 | 安装记录、运行期清单副本与恢复说明 | `.wf/install/installation.json`、`.wf/install/release-manifest.json`、`.wf/install/recovery.md` | 入口写；本机投放事实 | 更新为本次投放结果 | 保留（`purge` 单独确认） |

`<平台技能目录>` 由安装时人声明平台后确定（设计稿 §1.2 的「人声明 CLI 与可读根」）：平台能读共享层就用 `.agents/skills/`，否则用该平台自有目录（如 `claudecode` → `.claude/skills/`）；技能副本一律落在**目标项目内**。不同根的同名副本共享同一逻辑来源与版本，不发展平台差异门禁（机制稿 §10.1）。

**命名选择（本文追加）**：框架自有副本一律带 `wf-` 前缀。理由是投放根可能已有用户的同名 skill，`grilling`、`tdd` 等通用名被框架副本占用属静默接管；前缀使安装预览的同名核对退化为「框架自身重装」判断，同时不改变设计稿 §7.4 借用的原语内容。`wf-review` / `wf-review-action` 与来源版 `skills/multi-cli-review*` 不同名，清理来源版时不会误删自有副本（设计稿 §7.4）。

### 1.3 项目数据落点表

| 数据 | 路径 | 写者（机制稿 §5.3） | 升级 | 默认卸载 | `--purge` |
|---|---|---|---|---|---|
| 任务记录与内容 | `.wf/tasks/<task-id>-<slug>/` | 入口写判定字段；AI 起草 PRD/design/implement | 不替换 | 保留 | 删除 |
| 归档任务 | `.wf/tasks/archive/<YYYY-MM>/` | 归档入口 | 不替换 | 保留 | 删除 |
| 准备记录 | `.wf/preparations/<preparation-id>.json` | 准备入口 | 不替换 | 保留 | 删除 |
| 用户定义 | `.wf/user-workflows/<workflow-id>.md` | 已绑定/准备会话按授权 | 不替换 | 保留 | 删除 |
| 实例、快照与步骤产物 | `.wf/workflow-runs/<run-id>.json`、`<run-id>/definition.md`、`<run-id>/artifacts/<step-id>/` | 实例入口；步骤产物由对应任务在其批准范围内写 | 不替换；格式不兼容保留原文并阻断相关实例 | 保留 | 删除 |
| 会话绑定 | `.wf/session-bindings/<session-key>.json` | `session.bind` / 交接入口 | 不替换 | 保留 | 删除 |
| 写入权记录 | `.wf/writer.json` | 写权/维护入口（公共字段与维护回执分离，机制稿 §4.5） | 不替换，只有专门维护入口更新 | 保留 | 删除（最后一步） |
| 项目配置 | `.wf/project-config.json` | 初始化/bootstrap 或 `baseline.apply` | **不覆盖** | 保留 | 删除 |
| 项目基线 | `.wf/baseline.md` | 同上，成组应用 | 不覆盖 | 保留 | 删除 |
| spec 实体与索引 | `.wf/spec/**` | `spec.update` 入口 | 不覆盖 | 保留 | 删除 |
| 知识拒绝项 | `.wf/out-of-scope/<concept>.md` | 知识处置入口 | 保留 | 保留 | 删除 |

> `templates/task/task-record.json` 随清单投放但**无代码消费**：它是记录形状的参考文档（`task.json` 由 `new_task_record` 生成），第二轮才决定是否用于形状校验。

> 上表是**落点布局**，不等于已启用：`.wf/out-of-scope/` 首轮零引用（见本文 §2.3.11 的 P2-1 条目，明确延至第三轮）。读表时请以本文 §2.3.11 的轮次状态为准。


### 1.4 运行态与本机用户层

| 对象 | 位置 | 谁写 | 说明 |
|---|---|---|---|
| 会话定位缓存 | `.wf/.runtime/sessions/<session-key>.json` | 入口（可丢弃） | 只能由持久绑定与实例游标重建（机制稿 §1.4） |
| 读取留痕侧车 | `.wf/.runtime/spec-reads/<session-key>.json` | 当前会话入口，按会话隔离 | 无写权会话可写本会话侧车，不写判定字段（设计稿 §4.4）；`complete=false` 表示未完整装载 |
| 锁对象 | `<项目根>/.wf-lock` | 锁原语 | 只创建不删除；内容固定 `wf-lock-v1\n`（机制稿 §4.1）。首次以**排他创建**（`O_CREAT\|O_EXCL`）新建并写标记；已存在时只有「普通文件、真实落点属于项目根、内容完整等于标记」三条同时满足才复用；空文件或部分标记一律 `WF_CAPABILITY_UNAVAILABLE` 交人核实，普通入口不认领、不覆写 |
| 用户层全局配置 | `~/.wf/config.json` | 人（或人显式执行的确认动作） | `{schema_version: 1, python_executable?: 绝对路径}`；缺失=未设置（机制稿 §8.2） |
| 解释器确认集合 | `~/.wf/interpreters.json` | 只由 `confirm-executor` 子命令写 | 独立于 `config.json`；按完整元组集合保存，多条并存互不覆盖（机制稿 §8.2） |
| 审查暂存目录 | `<临时根>/wf-review/<project_id>/<task-id>/round-<N>/<slot>/` | reviewer 进程 | 项目树外；隔离键为任务/轮次/槽位（本文 §5.2）；槽位 id 与 `--reviewer-id` 是同一标识；卸载清单不覆盖，只列残留位置 |

临时根取 `tempfile.gettempdir()`，不读环境变量拼接；用 `project_id` 而非项目路径分目录，避免把本机路径带进 reviewer 可见范围。

### 1.5 authoring 源树与打包发行树

**源树**（作者侧维护，不被安装）：

```
docs/workflows/wf/
├── payload/
│   ├── bin/{wf.py, repair.py, uninstall.py}
│   ├── install.py                    # 发行根安装入口（不投放，见本文 §1.5）
│   ├── lib/wflib/*.py
│   ├── workflows/{task-flow,session-flow,review-flow,knowledge-flow,instance-flow,maintenance-flow}.md
│   └── templates/{project-config.skeleton.json, baseline.md, user-workflow.md, spec/*, task/*}
├── skills/{wf-start,wf-continue,wf-finish,wf-bootstrap,wf-spec-update,wf-review,wf-review-action,
│           wf-grilling,wf-tdd,wf-diagnosing-bugs,wf-code-review}/SKILL.md
└── dev-manifest.json        # 首轮开发态部署用：登记资产清单/版本/标记，字节哈希由部署工具现算（本文 §4.6）
```

**打包发行树**（发行提交根的形态，安装器唯一输入）：

```
<发行提交根>/
├── wf-release.json          # 清单（机制稿 §10.2 定位）
├── install.py               # 安装入口（发行根单文件，不投放）
└── wf-release/
    ├── bin/{wf.py, repair.py, uninstall.py}
    ├── lib/wflib/*.py
    ├── workflows/*.md
    ├── templates/**
    └── skills/<11 个 skill>/SKILL.md
```

打包树是**生成产物**：由 `scripts/build-wf-release.py` 从源树确定性复制并按源文件字节计算哈希，人不手改；提交与 tag 由人执行（框架不做分支或提交自动化，charter T3 B1）。把生成树放在 `wf-release/` 而非仓库根，是为了避免与仓库根既有的 `skills/`（来源资产层）混淆；清单的 `source_path` 相对发行根写 `wf-release/...`，仍在发行根内（机制稿 §10.2 的越界校验按此解析）。

`scripts/build-wf-release.py` 与 `scripts/wf-dev-deploy.py` 是 authoring 开发工具，**不进入发行清单**（设计稿 §8.1 第 0 项把 authoring 脚本排除在目标发行集外）。

**发行根安装入口**：正式安装由发行根的单文件 `install.py`（仅标准库、自包含）承接，因为安装发生时目标项目还没有 `.wf/bin/`。它不投放目标项目、不属于 `.wf/` 资产，因此不参与三方升级，也不出现在卸载清单里；但它是**发行资产**，按 `target_class=release_only` 登记进清单 `assets` 并计入 `rules_digest`（本文 §4.2）。每次安装/重装都从所选发行重取，安装结果记入 `.wf/install/installation.json`（`release_ref`、`source_commit`、`version`、`manifest_digest`、`platforms`、`roots`、`assets`、`decisions`；R93 起不再有 `session_profile`）。机制稿 §10.1 的落点表只登记 `.wf/` 内脚本，本条补的是该类资产的发行侧落点；它的资产类型判定与是否纳入发行清单见本文 §9.2 第 5 项。

**发行说明（源树 `README.md`，authoring 文档，不投放）必须包含**：打包输入（源树路径与目标版本）、工具与运行环境（`scripts/build-wf-release.py`、`scripts/wf-dev-deploy.py`，仅标准库、在作者机运行、**不进发行清单**）、版本同步义务（源树 `dev-manifest.json`、清单 `version` 与 tag 三者同批改）、产物校验（同一源树应字节复现 `wf-release/` 与清单哈希）、首发与升级步骤（人提交、人建 tag；安装器只接受该 tag）。2026-11-02 人裁：这两个工具不随发行分发；若日后要求随发行分发，须先给清单新增一个「随发行但不投放」的 `target_class` 并同批修订机制稿 §10.2。

## 2. CLI 与子命令面

### 2.1 两层入口

| 层 | 文件 | 职责 | 依赖 |
|---|---|---|---|
| 引导层 | `.wf/bin/wf.py` | 定位目标项目根、分派 `repair`/`uninstall`、只读解析执行器并移交 | 仅标准库；**不导入** `wflib` |
| 语义层 | `.wf/lib/wflib/cli.py`（由 `wflib/module_main.py` 拉起） | 解析请求信封、分派子命令、调用固定处理器、输出结果结构 | 仅标准库；不联网、不调用 MCP |

引导层固定顺序（对齐设计稿 §1.1 命令启动与机制稿 §8.2）：

1. 由 `Path(__file__).resolve()` 上溯确定项目根，核对 `.wf/bin/wf.py` 与 `.wf/` 布局；布局或目标无法确认即阻断（`WF_CAPABILITY_UNAVAILABLE`，facts 记缺失项）。源码/重取恢复入口必须由人用 `--project <绝对路径>` 显式给目标，不把源码目录或 cwd 当目标。
2. `argv[1] ∈ {repair, uninstall}` → 直接 `os.execv(sys.executable, [sys.executable, <同目录>/repair.py|uninstall.py, *rest])`，不读项目配置、不导入运行时（坏配置仍可达，机制稿 §10.5）。
3. `argv[1] == confirm-executor` → 由引导层自身在当前解释器内执行：只写 `~/.wf/interpreters.json`、只读项目配置、不写项目数据、不进项目锁，完成后退出。该分支必须在第 4 步之前，否则「未确认即停」会让确认动作本身不可达（机制稿 §8.2 要求该子命令由引导解释器拉起）。该子命令只接受**人在终端**执行：非 TTY 一律返回 `WF_SEMANTIC_DECISION` 且不写记录；写入前把完整元组打印到终端并要求输入确认词，已有相同元组时直接报告「已确认」不再提示（设计稿 §1.1，实测见任务记录 `validation.md` §21）。
4. 只读 `.wf/project-config.json` 取 `python_executable`，缺失则读 `~/.wf/config.json` 同名键，再回落到 `python3`；按机制稿 §8.2 取候选存在/可执行/路径身份/`size`/`mtime_ns` 并与 `~/.wf/interpreters.json` 元组匹配。未匹配即输出 `WF_EXECUTOR_UNCONFIRMED` 并停（不在引导解释器继续判定，出口是第 3 步的 `confirm-executor`）。
5. `os.execve(executor, [executor, <lib>/module_main.py, *rest], env)`，env 只追加 `PYTHONPATH=<lib>`、`WF_PROJECT_ROOT=<根>`、`WF_BOOTSTRAP=1`。这三个变量是进程间移交标记，**不作为身份、配置或授权来源**（身份只经请求信封，机制稿 §1.4）。

### 2.2 请求信封与自动身份模式（两种模式互斥）

**两种模式（2026-11-08 交付，`identity-redesign.md` v3.31）**：

| 请求形态 | 模式 | 身份/启用/实例来源 |
|---|---|---|
| 信封**含 `session` 对象** | **显式 legacy 模式** | 全按旧规则：身份取 `provider/identity`；`instance_id`、`activation` 从请求读；`host_id ∈ platforms` 照旧校验 |
| 信封**无 `session` 对象**（或空 stdin） | **自动模式** | 身份由锚点派生（`/proc` 会话 leader + 进程链，见 `payload/lib/wflib/session.py`）；`instance_id`/`activation`/启用降级从 `attachments/<session_key>.json` 读；不做 `host_id` 校验 |

- **模式由"有没有 `session` 对象"唯一决定**，不做字段级拼接、不回退；
- 自动模式下 `inputs.generation` **仍然必填**（代次是业务并发参数，不是身份）；
- 自动模式的写业务命令会按机制稿的 roots 维护规则改写 `attachments` 的 `roots`，并可能返回
  `WF_IDENTITY_UNRESOLVED(concurrent_unregistered_caller|evidence_unknown)` 或 `WF_NOT_ENABLED(activation_stale)`；
- 首次 `enable` 在自动模式下**建立执行会话**：签发 `issued_id`、写附件、登记 `anchors.json`（L1 单主、L2 追加）。

会话类子命令从标准输入读一个 JSON 对象：`session` 对象照机制稿 §1.4 的请求协议（provider/identity/instance_id/activation，不新增键）；顶层 `inputs` 是本文定义的参数容器，只承载命令行参数的规范化值，不携带身份或授权。

```json
{
  "session": {
    "provider": "host",
    "identity": {"host_id": "<人安装时确认的宿主标识>", "session_id": "<宿主提供的稳定会话标识>"},
    "instance_id": null,
    "activation": null
  },
  "inputs": {}
}
```

- `provider: "wf"` 时 `identity` 为 `{"issued_id": "<入口签发的 UUID4>"}`。
- 不接受命令行或环境变量覆盖身份；非交互场景可用 `--envelope <path>` 从文件读同一 schema 的信封，内容校验与 stdin 相同。`--envelope` 只承载信封，领域请求文件另有名称（见下文的 `--decision`/`--plan`/`--creation`/`--launch-request` 等），两者不共用同一选项名。
- 信封缺失、`session` 结构非法、provider 未知或身份字段缺失 → `WF_IDENTITY_UNRESOLVED`，facts 列出未核实的字段与出口；入口不猜环境变量、不退回项目全局指针。
- **`inputs` 的两个保留键**（缺省即不携带，其余键由各命令声明）：`generation` 为调用方上次看到的写权代次，只用于比对、不授予权限；`retry_of_action` 为重试时显式引用的旧 `action.id`。
- **代次的携带与核验**（按**子动作**分类，不按命令族；每个写权期只有一个来源）：
  - **允许省略（建立代次或根本不写项目判定字段）**：
    - 建立新代次：`writer acquire`、`bind`（在其写权获取动作内成组写入首次绑定）、`writer-handover accept`、`task-new` 内的首次 acquire、**`definition prepare`**（取得 preparation scope）、**`run create`**（取得实例写权并完成首次绑定）、维护类 `upgrade`/`repair`/`uninstall`。入口在这些动作结束时回显新代次。
    - 不写项目判定字段：不带信封的纯只读命令（`status`/`gate`/`inspect`/`version`）、只读断言子动作（`definition validate`、`run locate`）、只做启用检查的 `enable` 与只写本会话侧车的 `spec --file`。
  - **必须携带**：其余会写项目判定字段、且**不建立新代次**的子动作——`task-approve`/`task-start`/`task-replan`/`task-pause`/`task-resume`/`task-curate`/`task-check`/`task-knowledge`/`task-retrospect`/`task-attribute`/`task-rework`/`task-replace`/`task-abandon`/`task-reassess`、`dep`、`stop`、`archive`、`review-launch`/`review-import`/`review-decide`、`baseline-apply`、`spec-update`、`run advance`/`run pause`/`run terminate`。**未携带与不匹配同判** `WF_GENERATION_STALE`：facts 区分「未携带 generation」与「generation 不符」，出口都是重新读取当前代次后重试，不自行递增、不按当前 writer 补用新代次。
  - **不同写权期不共享代次**：准备写权（`definition prepare`）与实例写权（`run create`）是两个独立代次，创建实例前先完成准备释放与工作区处置，再在 acquire 中建立首次绑定（机制稿 §4.2 末段）；不得把准备代次用于创建，也不得在准备未释放时取得实例写权。
  - 由此，同一会话释放后重新 acquire 得到新代次时，旧调用材料里的旧代次会被判不符而拒绝，不会被套进新的授权期。
- **重试语义**：结果中回显本次 `action_id`；携带 `retry_of_action` → 入口按该动作已保存的意图走重入四态（机制稿 §5.2），不携带 → 按当前 `revision` 建新 `action`（机制稿 §5.1 的幂等派生，不重放业务副作用）。
- **信封必需**：凡会写会话侧车或判定字段的命令——`spec --file`（写本会话读取侧车）、`enable`、`bind`、`writer`、`writer-handover`、`stop`、`task-*`、`review-*`、`dep`（写前置集合）、`archive`、`baseline-apply`、`spec-update`、`definition`、`run`。缺信封时按机制稿 §2.1 处理：只读诊断可继续，但不写侧车、不给完整读取回执、不推进状态。
- **信封可选（纯只读）**：`status`、`gate`、`inspect`、`version`——均不写会话侧车与判定字段（机制稿 §11.3 的只读断言「无论调用会话是否持权都如此」）；缺信封时 `position.scope` 为 null（机制稿 §11.1 的 position 只有 scope/phase/step_id/task_id/action_id/action_state，无 session 键）。
- **引导层、独立脚本与维护入口**：`confirm-executor`、`repair`、`uninstall`、`upgrade --apply` 不读信封——三者靠人直调与终端确认，维护不以会话绑定授权（机制稿 §2.1）；`upgrade` 的预览/令牌见本文 §4.3 与机制稿 §10.3。

### 2.3 子命令清单

「机制操作」列取机制稿 §11.3 的固定名称；「状态机」列取机制稿 §2.2、机制稿 §5.1 的动作；「路径判定」列取机制稿 §3 的判定点。轮次列见本文 §6。

| 子命令 | 关键参数 | 机制操作（机制稿 §11.3） | 状态机动作（机制稿 §2.2、机制稿 §5.1） | 路径判定（机制稿 §3） | 轮次 |
|---|---|---|---|---|---|
| `help` | `[<命令>]` | 无（只读注册表） | 自报输入结构/最小示例/出口 | 实现稿本节（2026-11-07 增补，消"读源码猜字段"） | 1 |
| `status` | `[--json]` | `gate.evaluate`（只读） | 只读断言，不迁移 | 机制稿 §3.1 边界核对 | 1 |
| `gate` | `--due before_execute\|before_check\|before_archive` | `gate.evaluate`（只读） | 只读断言 | 机制稿 §3.2（指纹）、机制稿 §3.5（范围） | 1 |
| `spec` | `--file <RepoPath>`（信封必需） | 只读查询 + 本会话读取侧车 | 无（不写判定字段） | 机制稿 §3.1 | 1 |
| `inspect` | `[--json]` | 只读巡检（机制稿 §8.5） | 无 | 全库只读视图 | 1 |
| `enable` | 信封 | 只读启用核对（Trellis 互斥、身份能力与 activation；不属固定操作集合，见机制稿 §2.1） | 无迁移 | 机制稿 §3.1 | 1 |
| `ready` | `[--json]` | 只读就绪视图（机制稿 §6.1 候选枚举） | 无（不写判定字段） | 设计稿 §5.6 / 机制稿 §6.1 | 1 |
| `bind` | `--task <id>` \| `--run <id>`（**2026-11-12 交付**：新会话接续在途实例） | `session.bind`（在写权获取动作内成组写入；机制稿 §4.2「首次绑定按本文 §5 成组写入」） | 空闲态下新会话对**既有就绪对象**的首次绑定；实例绑定只确认「接哪个在途实例」，游标正确性由写入口核（`tasks.bind_task_for_write`）；**不承担首次创建**（见 `task-new` / `run create`），**不承担交接接收**（见 `writer-handover accept`） | 机制稿 §3.1、机制稿 §6.1、机制稿 §4.4 工作区分类 | 1（实例分支属第二轮，2026-11-12 交付） |
| `writer` | `acquire` \| `release` | `writer.acquire` / `writer.release` | 写权获取/释放 | 机制稿 §4.4 | 1 |
| `writer-handover` | `begin --to <session-key>` \| `accept` | `writer.handover.begin` / `writer.handover.accept` | 两段交接：`begin` 由旧写者发起（失效旧代次、写接收者与待恢复）；**`accept` 由接收方一次性完成绑定核验与代次授予**，接收方不再单独调 `bind` | 机制稿 §4.3、§4.4 | 1 |
| `stop` | `--decision <path> [--preview]`（`--preview` 只读预览逐路径归属，不写任何记录；2026-11-07 增补）（数组：收工选择一条 commit/keep/reverse/transfer + 提交/反向修正授权若干条；subject 列覆盖路径或承接对象）（信封） | `session.stop` + `task.pause` | 日常收工（设计稿 §4.4） | 机制稿 §4.3（同对象 WIP）、机制稿 §4.4 | 1 |
| `task-new` | `--kind ordinary\|initialize\|bootstrap --title <t> --template <path>`（信封） | `writer.acquire` + `session.bind` + `task.create`（**单一父 action**，主记录 writer） | 创建规划 + 首次绑定 | 机制稿 §3.1、机制稿 §5.2 目录防撞 | 1 |
| `task-approve` | `--task <id> --decision <path>` | `task.transition` | 批准规划（含复杂度/TDD/plan-q 答复） | 机制稿 §2.3 提取、机制稿 §3.4 条件① | 1 |
| `task-start` | `--task <id>` | `task.transition` | 首次开工 / 再入 Execute（写 `entry_snapshot`） | 机制稿 §3.1、§3.3 | 1 |
| `task-replan` | `--task <id> --decision <文件>` | `task.transition` | 实质规划变更（回 Plan；原批准/检查留历史但当前无效，`status` 不回未开工） | — | 1 |
| `task-pause` / `task-resume` | `--task <id> [--reason]` | `task.pause` / `task.transition` | 暂停 / 恢复 | 机制稿 §4.4 | 1 |
| `task-curate` | `--task <id> --spec <path> --purpose <text>` | `task.curate` | 策展写入 | 机制稿 §3.1 | 1 |
| `task-check` | `--task <id> [--decision <path>] [--review-notes <path>]` | `task.check` | Check（固定五步，机制稿 §3.2）；并写 `task.work-satisfied` 的 completed 回执 | 机制稿 §3.5 范围核对 | 1 |
| `task-knowledge` | `--task <id> --decision no-update\|updated`（`updated` 的具体操作由 `changes` 按机制稿 §8.4 的 `{operation, …}` 记录） | `task.knowledge-dispose` | 知识处置留痕 | 机制稿 §3.1 | 1 |
| `task-retrospect` | `--task <id> --evidence <path> [--decision <path>]` | `task.retrospect` | 复盘记录（人要求或触发后执行） | — | 1 |
| `task-attribute` | `--task <id> --commit <oid>` | `task.attribute` | 归属裁决 | 机制稿 §3.3 | 1 |
| `dep` | `add\|rm --task <id> --prereq <id>` | `dependency.change` | 建边/删边 | 机制稿 §6.1 图校验 | 2（2026-11-12 已交付） |
| `task-rework` / `task-replace` | `--task <id> --decision <path>` | `task.rework` / `task.replace` | 返工/替换 | 机制稿 §6.2、§6.3 | 2（2026-11-12 已交付） |
| `task-abandon` | `--task <id> --decision <path> [--disposition <path>]`（承载与记录映射见本节「结构化人工输入」） | `task.abandon` | 单任务放弃（异常归档） | 机制稿 §6.4 | 1 |
| `task-reassess` | `--task <id>` | `task.reassess` | 挂起复评 | 机制稿 §6.2 | 2（2026-11-12 已交付） |
| `review-launch` | `--task <id> --launch-request <path>`（结构化声明，骨架见本节末） | `review.launch` | 审查发起；round/attempt/anchor/temp_paths 由入口生成并回显 | 机制稿 §3.5 前置 | 1 |
| `review-context` | `--task <id> [--round <n>] [--reset]`（reviewer 侧唯一入口；身份取本会话宿主，占位即闸门） | 无（只写暂存目录与材料） | 取材料/锚点/报告路径并占位 | 机制稿 §9.2（2026-11-07 修订） | 1 |
| `review-import` | `--task <id> [--round <n>] [--slot <agent>] [--report <绝对路径>]`（后三项可省：按文件名发现） | `review.import` | 导入与锚点核对（机制稿 §9.2） | 机制稿 §3.2 锚点 | 1 |
| `review-decide` | `--task <id> [--round <n>] [--plan <path>] [--unavailable <path>]`（轮次缺省＝当前轮）（`--plan` 为逐条 finding 处置，元素 `{finding, decision_ref, reason}`；`--unavailable` 为人声明的审查环境不足及证据） | `review.decide` | 审查判定（**由入口按机制稿 §9.2 的事实推导**，不是人选）与逐条处置 | — | 1 |
| `archive` | `--task <id> --decision <path>`（人调用 finish 的证据 + 提交授权 `commit_grants`） | `task.archive` | 正常归档（由 `wf-finish` 调用） | 机制稿 §3.5、机制稿 §9.3 门禁 | 1 |
| `baseline-apply` | `--task <id> --proposal <path>` | `baseline.apply` | 基线/配置成组应用 | 机制稿 §3.4 | 1 |
| `spec-update` | `--task <id> --changes <path>` | `spec.update` | 知识变更成组应用 | 机制稿 §3.1、§8.4 | 1 |
| `definition` | `prepare --id <workflow-id>`（建立准备代次） \| `validate --id <workflow-id>`（只读校验） | `definition.prepare` / `definition.validate` | 准备定义 / 静态校验 | 机制稿 §3.1、§7.2 | 2（2026-11-12 已交付） |
| `run` | `create --creation <path>`（建立实例代次并首次绑定） \| `advance --run <id> [--decision <path>]` \| `pause --run <id> --reason <text>` \| `resume --run <id> [--decision <path>]`（解除**实例**暂停；`--decision` 可选） \| `locate --run <id>`（只读） \| `finish --run <id> [--decision <path>]`（正常结束；有覆盖实例记录的 `commit` 授权才提交，否则停在 `persist_pending`） \| `terminate --run <id> --plan <path>`（批量处置计划，元素 `{object, decision_ref, reason}`；`decision_ref` 为内联 `Decision`，其 `choice` 声明处置：`放弃`/`abandon` 或 `保留`/`keep`——**这两个取值由本文定义**） | `run.advance` / `run.terminate`（`create` 由 writer 主记录承载首次创建与首次绑定、`pause`/`resume` 是该动作的受控字段写入、`locate` 是只读断言） | 实例创建、推进、暂停/恢复与终态 | 机制稿 §2.2（实例暂停/恢复）、机制稿 §7.3、机制稿 §7.4 | 2（2026-11-12 **已交付**：`create`/`locate`/`advance`/`pause`/`resume`/`terminate`/`finish` 全部可用） |
| `upgrade` | `--apply`（预览 + 令牌） | `asset.apply` | 维护（机制稿 §10.3） | 全路径 | 3 |
| `repair` | 转交 `repair.py`（预览 + 令牌）；第二形态 `--dispose <plan>` 做维护组处置回写（见本文 §4.6） | `repair.apply` | 受控修复（机制稿 §5.4） | 机制稿 §5.4 | 1（写权/绑定/锚点最小恢复）、3（全部资产修复） |
| `uninstall` | 转交 `uninstall.py`（`--purge` 单独确认） | `uninstall.apply` | 退出（机制稿 §10.5） | 机制稿 §10.5 | 1（开发态退出）、3（purge 与发行清单） |
| `confirm-executor` | `--scope system\|global\|project` | 引导层例外（机制稿 §8.2） | 无（只写 `~/.wf/interpreters.json`） | — | 1 |
| `version` | `[--json]` | 只读 | 无 | — | 1 |

**阶段回退的承载与再入路径（实质规划变更）**：机制稿 §2.2 的「实质规划变更」行只给目标状态（进入 `phase=plan`、原批准/检查留历史但当前无效、`status` 不回未开工）与失败出口（人澄清并重批），调用形态由本文补：`task-replan --task <id> --decision <文件>`（决定须 `choice=replan`），机制操作 `task.transition`，与其他迁移共用同一套迁移入口（`wflib/tasks.py::cmd_task_replan` 等 `cmd_task_*` 处理器，动作记 `task.transition`，见本文 §6.3）。它的边界是**只做这一行迁移**——不改写 PRD、不写 `touch_paths`、不产生新批准、不改既有 `entry_snapshot` 的内容；原批准/检查的留史与失效按机制稿 §1.3 的 `check_history` 与机制稿 §2.2 该行定义，本文不在命令面复述状态机。回 Plan 之后仍是既有两步：`task-approve`（批准规划，源态含 `in_progress/plan`）→ `task-start`（再入 Execute：重新提取 PRD 并与当前有效批准核对后替换 `entry_snapshot`，按机制稿 §2.3），不设第三个迁移入口，也不允许在 Execute/Check/Finish 直接改 `task.phase`。速查中「回 Plan 补可证包含条目」「回 Plan 扩范围重批」的出口即这条命令加上述两步（本文 §8.2）。

**结构化人工输入（约定）**

人的决定只有两种承载方式，其余一律不塞进命令行：

- **封闭枚举（可留在命令行）**：取值由机制稿固定、不超过三个值的「选一个」开关——`task-knowledge --decision no-update|updated`——这两个值由**本文**定义，语义取设计稿 §6.3（「本次无更新」与「新增/更新/合并/改名/删除后的结论」），机制稿 §1.3 只登记 `knowledge` 的三个字段、未登记值域，因此扩展值域须先回机制稿登记；`run pause` 等带说明文本的子动作不在此列（它们有 `--reason`）。审查结论**不是**封闭枚举：pass/fail 由入口按机制稿 §9.2 的事实推导，只有「环境不可用」需要人声明（`--unavailable <path>`）。
- **JSON 文件（承载具体内容）**：
  - `--decision <path>`：单条 `Decision` 或其数组，结构照机制稿 §1.1；`subject` 写该决定覆盖的对象与具体路径，`choice` 取机制稿已登记的取值。用于 `task-approve`（批准）、`task-abandon`（**停止决定一条** + 提交/反向修正授权若干条；`subject` 列覆盖路径或承接对象，与 `stop` 同一约定）、`stop`（**收工选择一条** + 提交/反向修正授权若干条）、`archive`（finish 调用证据 + `commit_grants`）、`run advance`（人判答复）。
  - `--plan <path>`：**对象级**批量处置计划，元素为 `{object|finding, decision_ref, reason}`；只用于实例批量终止（`run terminate`，元素是任务）与审查逐条处置（`review-decide`，元素是具名 finding）。它不表达「同一组路径各用不同处理」——收工是单一选择（机制稿 §4.3 的 `decision` 只有 commit/keep/reverse/transfer 四值，wip 记录的 `paths` 只存逐路径状态、不含 per-path choice），混合去向要先改机制稿该节的 wip schema，属机制侧变更。

  - `--disposition <path>`：单任务放弃（`task-abandon`）的**逐项去向**，元素为 `{object, decision_ref, reason}`——`object` 记被处置路径或具名承接对象，`decision_ref` 指向该去向的 `Decision`，`reason` 记风险与未落实依据。入口把它落到机制稿 §1.3 `disposition` 的 `changes`/`targets`/`pending`（`disposition.decision` 与 `commit_grants` 仍由 `--decision` 提供）；是否构成待决、什么算已落实一律取机制稿 §6.4，本文不另立判据。放弃要求**逐项**去向（机制稿 §6.4「每项给保留现状/反向修正/具名承接的实际去向」），与收工的单一选择（机制稿 §4.3）是两个不同的决定，因此不复用 `--plan` 的用途与边界。

其余领域文件沿用各自名称（`--launch-request`、`--creation`、`--proposal`、`--changes`、`--review-notes`、`--evidence`、`--disposition`）；文件只承载人的决定，不承载身份（身份只走信封）。

**证据与裁定的输入通道（Check / 复盘）**

Check 的固定五步里有四类事实脚本无法自造，各自的入口如下（都不新增判定，只是把既有人判与材料落到机制稿已有的字段）：

| 事实 | 输入 | 落点 |
|---|---|---|
| `argv` 验证结果 | 入口按批准声明执行并自行取证；无输入参数 | `check.commands` |
| `manual` 验证与 `verification_ids` 为空的验收 | `--decision <path>`：每条 Decision 的 `subject` 记 `verification_id` 或 `acceptance_id` 与当前 `plan.version`；**不要求文件预含 `check.anchor`**——本次 `check_anchor` 要到 Check 内部才算得出，由入口在写入 `acceptance_results` 时把该 Decision 核绑到本次锚点并在记录里补记 | `check.commands`（manual）/ `check.acceptance_results` |
| 内部双轴审查 | `--review-notes <path>`：标准轴与需求轴各一段结论与依据；它是材料，不是人的决定。两轴 `conclusion` 必须均为 `pass`，任一 `fail` 或 `undecided` 都不判 pass（机制稿 §3.5） | `check.internal_review` |
| Execute 期重复调试声明与 `debug-ruling` 裁定 | `task-check --decision <path>`（人或主会话声明 + 「同一问题/不同问题」裁定） | `execution.debug_declarations` / `execution.human_decisions` |
| 复盘触发与可选复盘 | `task-retrospect --evidence <path>`（触发事实与证据引用）+ `--decision <path>`（裁定；无触发时人主动复盘记 `required=false`） | `task.retrospective` |

`task.work-satisfied` 的首次 completed 回执由 `task-check` 在写入前核验并在同一 action 内写（**承载动作由本文指定**：机制稿只要求「由执行入口在后置成立时记录」，未钉死是哪个状态动作；与 `task.retrospect` 承担 `task.retrospective-done` 同构）。`gate` 是只读断言，不补写回执。

**参数骨架（审查发起与实例）**

- `review-launch --launch-request <path>` 的文件内容是机制稿 §9.1 的 `launches` 声明中**由人给出**的那部分；`round`（= `last_round+1`）/`attempt`/`anchor`/`temp_paths` 由入口生成并回显，命令不接受人传轮次：

```json
{
  "implementation_clis": ["claude", "codex"],
  "slots": [{"slot": "r1", "reviewer_cli": "codex"}, {"slot": "r2", "reviewer_cli": "dsh"}],
  "submitted_scope": {"diff": "<path>", "requirements": ["<path>"], "test_results": ["<path>"]},
  "readable_scope": {"code": ["<glob>"], "spec": ["<path>"], "prd": ["<path>"]},
  "exclusions": ["<path 或 glob>"],
  "export_decision": "<Decision 引用>"
}
```

  `slots` 至少一项：两项且每个 `reviewer_cli` 与 `implementation_clis` 全项不同、彼此也不同时满足复杂任务的完成条件；只有一项时**同一命令照常放行**（人声明环境不足，见本文 §5.3），入口只在 `task.reviews.launches` 记 `degraded: single-provider`；判定由 `review-decide` 按机制稿 §9.2 处理（单 reviewer 属「人数不合格」→ **拒绝输入、不产生 verdict**），degraded 事实随 `launches` 条目保留，**不写入 result 字段**（该字段写者与取值见机制稿 §9.2）。**槽位 id 即 `--reviewer-id`**：同一字符串用于暂存目录层名、报告文件名与导入槽位，不设第二套标识。
- `run create --creation <path>` 给定义 id 与内容哈希、输入值/引用、步骤适用性与顺序展开规则的人确认引用；入口据此固定快照、创建实例并完成首次绑定（writer 主记录）。`run terminate --plan <path>` 给逐任务放弃/保留的批量处置（元素为任务，不是路径）。

**`task.retrospect` 的登记说明**：2026-11-02 人裁「复盘作为独立机制操作」，机制稿 §11.3 的状态动作集合与机制稿 §5.1 的主记录归属已同批登记 `task.retrospect`（`control.task.retrospect` 随之按该节公式派生），门禁侧仍由机制稿 §11.2 的 `task.retrospective-done` 核验。本文只给命令与落点：处理器 `wflib/tasks.py::cmd_task_retrospect`，写入 `task.retrospective`，并在同一 action 内写 `task.retrospective-done` 的 completed 回执（机制稿 §11.2 的回执写者句；人裁 ①：该操作即该步骤的执行入口）。该操作不新增判定，只把一个已有记录字段提升为可独立期次化的动作。

**没有公开子命令的机制操作**：`verification.resolve` 作为只读断言由内部调用（`task-start`/`task-check`/`archive`/`run` 内部步骤）暴露；`asset.compare` 同属只读断言，消费面是发行侧三方比较（安装/升级/卸载/自检，落点见本文 §6.2 D31、本文 §7.2 G16），两者都不单设命令；`run` 的子动作按机制稿 §5.1、§7.2、§7.4 由 writer 主记录与 `run.advance` 承载（实例首次创建与暂停都不是独立操作名），第二轮随实例能力一起交付。**操作名不自动新增公开命令**：本表之外的任何操作名不因为存在于机制稿就成为命令；新增命令必须同时满足「映射到已登记机制操作或已定义只读查询」与「在本文与用户文档同批登记」。

### 2.3.1 归档动作的提交顺序（与设计稿 §4.2 一致）

`archive` 的顺序固定为：**业务/spec/基线/配置变更按精确路径提交 → 核对最终门禁（机制稿 §9.3 第 1–7 项）→ 写终态并移动任务目录 → 归档记录单独成组提交 → 提交后只读核对**。

- 依据：设计稿 §4.2 要求「业务变更……与任务记录归属明确后提交，**随后**核对最终门禁，归档记录最后单独成组」；机制稿 §5.3 的固定步骤表约束的是归档动作自身（终态/移动/记录组），两者分工不同、不构成冲突。
- 门禁失败时的中间态是可恢复的：业务组已提交、任务仍在 `finish`、动作停在未完成态；重入 `archive` 会续做（提交按路径幂等、`persist_pending` 由可达提交派生），不重复归档、不重复提交。失败事实与恢复出口见任务记录 `validation.md` 的 V2 与 CP3 的提交语义条目（见任务记录对应小节）。
- 记录组提交失败后的重入：任务已写终态并移入归档、但记录组未进提交时，若记录里已有 `finish_decision`（归档已由人授权），同入口续做记录组提交并重算持久化结果；**续做前必须核当前写权与代次（`require_held`），历史授权不能替代当前写权**；无授权或写权不满足时停在待持久化并给出出口。
- 放弃（`task-abandon`）：未提交改动必须「已授权提交」或「由人实际处置」——有 `commit` 授权的路径先实际提交，其余须已不在工作树差异中；仍有残留则 `WF_WORKSPACE_UNRESOLVED`，不写异常终态、不移动目录（机制稿 §6.4）。移入归档后**还要提交记录组并核对持久化**（`git ls-files` + 该目录无未提交差异）；未提交成功则报 `WF_PERSISTENCE_FAILED` 并停在待持久化，不报告退出全部完成。
- **按已落盘步骤恢复**：不使用 `status` 单值代表全部完成。归档与放弃共用同一套判定：①记录是否位于 `.wf/tasks/archive/<YYYY-MM>/<id>-*`（未移动则持写权先完成移动，幂等）；②记录是否已进入提交（未提交则持写权补提交）；③终态与 `persisted` 事实一致。三步都在**同一个 `.wf-lock` 互斥内**完成，续做写入（移动/暂存/提交）与正常路径同权限；`archive_persisted` 同样核对记录位置。
- 不按机制稿 §5.3 字面把提交整体后移：那会让门禁失败也先提交业务，与设计稿 §4.2 相反；若日后要求改序，按 charter T1 出需人裁决并同批改机制稿。

### 2.3.2 成组写入与接续（`baseline-apply` / `spec-update`）

- **先整批校验、后写入**：路径合法性与前缀、内容非空、重命名源/目标、删除/停用前的依赖解除目标与「活动依赖是否已解除」都在写入前一次判定；任一不过即返回原因码（`WF_PATH_INVALID`/`WF_SEMANTIC_DECISION`/`WF_TARGET_COLLISION`）且**零写入**。语义校验放在建立动作之前，因此「校验失败」不会留下未完成动作。
- **写入失败可续做**：逐条写入仍用单文件原子替换；写入抛错映射为 `WF_PERSISTENCE_FAILED`（facts 带已完成路径与失败路径），动作停在未完成态。
- **接续语义**：同一入口再次调用时，若存在同类未完成动作且输入摘要（路径 + 内容摘要）一致 → 复用该动作续做，幂等、不重复写入、不另建动作；输入不一致 → `WF_ACTION_INCOMPLETE`，不覆盖原动作，出口是用原提案重入或先核对未完成动作。续做时按**已落盘事实**识别已完成步骤（改名源已不在但目标在、删除目标已不在），其余前置不放松。
- **写入边界**：`baseline-apply` 要求在 `execute`/`check`/`finish` 阶段且当前规划有有效批准，目标只允许基线文件、项目配置与 `spec` 骨架且必须被批准 `touch_paths` 匹配；`spec-update` 要求在 `execute`/`check`、规划有效批准、且未暂停/挂起，目标必须落在 `.wf/spec/**`，**且必须被批准的 `touch_paths` 匹配**——按设计稿 §4.2，触碰面覆盖业务、文档、spec、基线与配置，固定职责豁免只包括任务自身规划/控制记录/审查报告/运行态，以及改名同步与依赖解除这类窄写入。
- **真实落点与嵌套仓库**（唯一判据 `paths.boundary_violation`，读、spec 写、基线写三处共用）：①目标/读取对象的 `realpath` 必须仍在项目根内；②嵌套仓库边界按**字面路径与真实路径两遍**核对——先查字面祖先（宽 glob 的字面语义仍要生效），再查 `realpath` 后逐段祖先是否含 `.git`（目录或 gitfile），这样「项目内的符号链接把目标带进嵌套仓库」也会被拦住（设计稿 §6.1「符号链接先解析目标」）。`cmd_spec` 命中即 `WF_PATH_INVALID`、不返回正文、不写完整读取侧车；`spec-update` 的改名旧端/新端、删除目标与新增目标，以及 `baseline-apply` 的整批目标，命中即 `WF_PATH_INVALID` 且零写入；新增写入入口必须调用同一函数，不另写判据。两者都核真实落点（`realpath` 仍在项目根内），控制记录（`.wf/writer.json`、`.wf/tasks/**`、`.wf/session-bindings/**`、`.wf/install/**`、`.wf-lock`）一律拒绝（`WF_SCOPE_UNRESOLVED`/`WF_PATH_INVALID`）。
- **整批冲突**：同一变更集内源路径唯一、目标路径唯一，且一条变更的目标不得是另一条变更的源；冲突即 `WF_TARGET_COLLISION` 且零写入。改名/删除前另查**真正引用这些路径的活动任务**是否有未完成动作：有则 `WF_ACTION_INCOMPLETE` 且发生在任何写入之前；未被引用的任务即使有未完成动作也不阻断，本次任务自身的在途动作不算冲突。
- **改名与归档引用**：改名只同步**活动**任务的策展路径/哈希，已归档记录按历史路径解释、不改写；关联活动任务若存在未完成动作，先恢复再同步（`WF_ACTION_INCOMPLETE`），不并行叠写。
- 依据：机制稿 §3.4、§5.2 的动作四态，以及机制稿 §3.1 与 §3.4 的成组应用；本节只补「校验—写入—接续—边界」的先后次序，不新增操作名或状态值。

### 2.3.3 Check 的必需验证与知识兜底

- **必需验证全部执行**：`required=true` 与被验收引用的验证都在 Check 中实际执行并写 `check.commands`，`consume_at=finish` 只把「就绪与版本重核」延后到归档前，不豁免本次执行（机制稿 §3.5 第 245 行）。
- **配置取值统一入口**：所有消费者只经 `config.value_of(config, problems, key)` 取值——键缺失且配置可用时取发行缺省（**不阻断**）；键存在但非法、或配置整体不可读时返回 `(None, problem)`，调用方**必须**用它阻断依赖该键的判断（设计稿 §3），不能只接入函数名而丢弃 problem。
- **问题分两级**：`load_project_config` 的 problems 是 `{level, key, message}`；`structure`（不受支持的 `schema_version`、配置整体不可读）约束所有相关键，`field`（某键非法）只影响该键，**无关键的字段错误不得扩散**。当前消费者：周期核实（`spec_verify_days`）、调试阈值（`debug_repeat_threshold`，非法走 `WF_CAPABILITY_UNAVAILABLE` 并阻断归档门禁的调试分支）、spec 输出预算（`spec_output_codepoints`）、TDD 默认（`tdd_default`，非法走 `WF_SEMANTIC_DECISION` 并提示可显式传 `inputs.tdd`，不再 `bool()` 静默取反）、身份兜底证据策略（`identity_path`，枚举 P1/P2/P3，非法走 `WF_RECORD_INVALID`，不静默取 P1）。新增配置消费者必须走同一入口，不另写 `isinstance` 兜底——兜底不等于阻断。
- **核实周期**：周期不可用时仍按缺省值算出到期/未核实候选，但 `period_problems` 让它照常阻断；`period_days` 与 `period_problems` 都写入 `check.spec_review` 供事后核对。其余键的问题只阻断依赖它的判断，不整体阻断项目。
- **知识兜底**：Check 的判定集合为「本次命中 ∪ 本任务策展」——命中但未进策展清单、`verified_at` 为 `extracted`/空、或核实日期距今超过项目配置的周期（缺省 90 天）且无人判覆盖 → `WF_SPEC_INCOMPLETE`（设计稿 §6.2、§6.4）。已读正文不替代策展与处置；人判覆盖的证据记入检查记录。
- **规则集合进入锚点**：`check.spec_versions` 取「策展 ∪ 本次交付路径实际命中的 spec」，与机制稿 §3.5 的定义一致；因此 Check 之后由其他提交新增（或改写）的命中规则会改变 `check_anchor`，旧 Check 按 `WF_CHECK_STALE` 失效，需重检。
- **结束前重算范围**：写结果前重跑一次完整范围核对（分类 a–f、外部变更、治理面声明）并与开始时比对，任一变化 → `WF_CHECK_STALE`，不判 pass（机制稿 §3.5）。
- **规则版本参与门禁**：`task.check-passed` 比较 `check.anchor.rule_version` 与当前规则版本，不同即 `WF_CHECK_STALE`（facts 并列两版本），由人按发行兼容声明决定重跑或声明兼容；规则类回执（check/tdd/review/changes-persisted）因版本失配不匹配时，`evaluate` 不得归为 `satisfied`。
- **TDD 证据结构**：`tdd_evidence` 须含 `assertion`/`red_command_ref`/`red_reason`/`green_command_ref`/`properties` 五段非空；**绿引用须对应本次 `check.commands` 中实际通过的命令，红引用须对应历史检查（`check_history` 或即将被替换的当前检查）中实际失败的命令**，两者不得是同一条；结构不符与门禁同判（机制稿 §3.5）。历史红运行与当前最终结果分开保存，不用两条成功命令代替。
- **人判绑定**：manual 验证与空 `verification_ids` 的验收接受 `Decision` 时，`subject` 必须按整词包含目标 id（不做子串匹配），且决定须绑定当前规划（显式 `plan_version` 或当前批准对象摘要）；失配保持未决，不写锚点。

### 2.3.4 写权与保留 WIP 的共享判据

- **锁内重核**：`writer release`、`writer-handover begin` 只把锁外 `require_held` 当快速失败；取到锁后**重新执行同一套完整核验**（状态、持有者 id、scope、以及调用携带的 generation），不匹配即 `WF_WRITER_BUSY`/`WF_GENERATION_STALE`，不写记录。只比较会话 id 不够：同一会话释放后重新取得的**新代次**也不能被旧调用释放（机制稿 §4.2）。
- **保留 WIP 共同消费**：判据取自 `stop` 写入的 `handoff.wip`（`paths` 为指纹条目，按 `path` 取值）与 `disposition.pending` 的并集，并用**实际状态**判定——保留路径若已不在工作树差异中即视为已处置，不再阻断（防止「已提交却被旧记录长期挡住」）。
- **授予写权的统一前置**：`writer acquire`、`bind`、`task-new` 三个入口在各自互斥内调用同一函数 `assert_no_foreign_wip(ctx, exclude_id)`；`writer acquire` 与 `bind` 都排除目标对象（同一对象重新取得写权、新会话接续原对象都不算「外来 WIP」），`task-new` 无可排除对象。任一不过即 `WF_WORKSPACE_UNRESOLVED`。`bind` 的响应交回 `inherited_wip`（登记路径或未登记脏改动 + 原始 WIP 记录），供新会话核验后接续。
- **未登记的脏改动同样计入**：判据除 `handoff.wip` 与 `disposition.pending` 外，还取该任务可见的未提交交付路径（范围分类 e 桶 ∩ 工作树差异），facts 以 `registered` 标出来源；释放写权不因本任务的未处置改动而阻断（改动仍归属该任务），拦截点统一放在授予侧。
- **显式归属优先于 glob 重叠**：先由各任务 `handoff.wip.paths` 建立「路径 → 任务」归属表；计算某任务的未登记脏改动时排除已被其他任务显式记录的路径。两个任务批准 glob 都覆盖同一文件时，不再各算一份；没有显式归属且确实分不清时仍列出并交人裁决，脚本不擅自认领。
- **解除结论写回**：`stop` 按选择写 `handoff.wip.resolved`——`commit`/`reverse`/`transfer` 记录选择与证据（提交头/承接对象），只有 `keep` 留空；`task-resume` 在保留路径已干净时补写「恢复前已处置」的依据。解除不新增命令，写在既有字段里。
- **恢复前的指纹核对**：`task-resume` 不只判路径是否存在——逐条比较 `handoff.wip.paths` 保存的 `{path, exists, kind, executable, digest}` 与当前指纹，任一不同即 `WF_WORKSPACE_UNRESOLVED`（facts 给 `changed` 的保存值与当前值），要求按实际内容重新核对归属与范围；全部一致才清暂停。
- **已持久化的删除**：记录即删除（保存指纹 `exists: false`）时，当前仍不存在且已不在差异中视为「合法删除、已处置」，放行并写回 `handoff.wip.resolved`（`evidence.deleted` 列路径）；只有「记录为存在、现在既无差异也不存在」才按去向不明拒绝。
- 该判据只消费既有字段（`disposition.pending`），不新增状态值或独立 WIP 账本。

### 2.3.5 复杂产物与 spec 结构复验

- **批准决定的消费**：`task-approve` 从决定集中筛出 `choice ∈ {approve, 批准}` 的那一条作为批准；没有即 `WF_SEMANTIC_DECISION`（facts 列实际 choice 与可接受值）。该决定的 `object_digest` 若存在必须等于当前 PRD 摘要（`subject` 含任务 id 时兜底），不符即 `WF_APPROVAL_MISSING`。开工门禁 `task.plan-approved` 复核 `plan.approval.choice` 仍在可接受集合内——拒绝或无关决定不得因「记录存在」放行。
- **复杂产物门禁**（分级先按本文 §8.5「复杂度」的四项汇总定稿，再执行本节检查）：复杂度为 `complex` 时，`design.md` 与 `implement.md` 必须在批准前存在、**非空**且不含未填占位（`{{WF_REQUIRED:…}}` 与 `__WF_REQUIRED__`）；`task-start` 在既有 PRD 占位校验后复核同一集合。空文件记 `empty`、去掉标题行与空行后无内容记 `empty body`——只有标题不算填完。任一不合即 `WF_TEMPLATE_INCOMPLETE`（facts 逐份列产物与 reason：`missing`/`empty`/`empty body`/`unfilled placeholders` 并带具体 `fields`）。文件摘要参与版本哈希，不替代「齐全且已填」；轻量任务仍是 PRD-only，不受影响。
- **标记字段名**：`{{WF_REQUIRED:<field>}}` 的 field 允许 `[A-Za-z0-9_-]`（机制稿 §10.2「非空 ASCII 字段名」）——发行模板自身使用的 `data-flow`、`non-goals`、`verification-commands`、`example-good`、`example-bad` 必须被识别，否则成品校验与 `template_markers` 双向登记都会漏。
- **spec 结构复验**：改写 frontmatter 必须保留起止分隔符；`disable` 写盘后重新解析并核对 `status=disabled` 且无 problems，不成立即 `WF_RECORD_INVALID`——报成功之前先证明文件仍可路由。

### 2.3.6 人判字段、调查任务与证据核验

- **调查任务成果**：`touch_paths` 为空的纯调查任务，`task.work-satisfied` 要求可观察成果——复盘、策展所依据的 spec、或已通过 Check；**人判记录不算**（`plan-q` 批复就会写它），全无则 `WF_CHECK_FAILED`（机制稿 §11.2）。
- **`knowledge` 只由 `task-knowledge` 写**：`spec-update` 只留动作证据，不替人写 `knowledge`，也不新增未登记字段（机制稿 §0.2、§5.3），`task.knowledge-disposed` 保留「人处置」语义。
- **debug 声明证据**：声明必须带 `evidence_refs` 且逐条可定位（任务内文件、check id、`check:`/`handoff:` 具名引用）；`dedupe_refs` 的 `check_id` 必须存在。缺失分别 `WF_SEMANTIC_DECISION` / `WF_HISTORY_UNRESOLVED`（机制稿 §1.3、§11.2）。
- **Trellis 档位**：「当前宿主配置存在」是线索，默认 `WF_SEMANTIC_DECISION`；只有输入声明 `trellis_loaded`（本会话确实加载）才 `WF_FLOW_CONFLICT`（机制稿 §2.1「线索 ≠ 激活」）。
- **未交付能力的出口**：run 绑定遇 `gate` 抛 `WF_CAPABILITY_UNAVAILABLE`（tier=round 2），不落内部错误码。
- **降级条目与哈希域**：`{"downgrade": true, …}` 在 `compute_plan_version` 之后追加，重算（含机械修订）一律剔除，与机制稿 §1.1 的哈希域一致。降级齐全性（`reason`+`evidence`）在 `final_gate` 核，轻量任务归档同样受检；`task.review-passed` 仍按机制稿 §11.2 只对复杂任务适用。
- **归档后写入**：`task-knowledge` / `task-curate` / `task-retrospect` 遇 `status=archived` 一律 `WF_BINDING_MISMATCH`，只有人确认的 `repair` 可修记录（设计稿 §5.1）。

### 2.3.7 秘密边界与副本来源

- **秘密边界**：检查命令的摘要与 `argv` 都过 `check.redact_secrets()`，日志文件与 `evidence` facts 写的都是脱敏结果（机制稿 §3.5）。形态覆盖 `key=value`/`token:`/`Bearer`、`sk-`、`gh*_`、`AKIA`；**形态优先，已知非凭据键（tokenizer/max_tokens 等）豁免**——认不出就原样保留（整段丢会毁掉排障价值）。
- **身份来源**：由安装记录的 `platforms` 清单声明，安装/追加平台用 `--platform`（可重复）。R93（commit `20e3ae8`）已删除 `--provider`、`--verified-version`、`--capability-evidence` 与 `session_profile`：不再要求人逐次举证宿主能力，改为「平台清单即身份事实 + 真实异常由各自路径 fail-loud」（机制稿 §1.4）。因此**不得**再按「声明式 verified / 未核实能力」口径描述本框架；能力未被观察时如实报告该事实，但不据此阻断只在已声明平台上运行。
- **副本来源**：六个改编副本（grilling/tdd/diagnosing-bugs/code-review/review/review-action）各自 `SKILL.md` 末尾有「来源与差异」段，登记来源、许可、基线、差异与最近正反例（设计稿 §7.4）；模块 README §6 列明改编件与原创件，并注明审查两副本的适配源是一次性的、上游不自动流入（设计稿 §7.5）。

### 2.3.8 公共写入口的统一核验

日常入口在既有检查前先过同一组核验，不在 `start` 时只核一次：

- **会话实例标识与能力状态**（机制稿 §1.4）：绑定里缺 `instance_id` → `WF_RECORD_INVALID`；请求未携带 → `WF_IDENTITY_UNRESOLVED`（待核对携带标识）；两侧不同 → `WF_BINDING_MISMATCH`（转本文 §5.4 出口）。R93 起不再有 `session_profile.capability` 核对（平台清单即身份事实）。实现上 `cli._require_instance_match()` 是唯一实现，**绑定入口与写权入口（`writer acquire`/`release`）都调用它**；适配层从 `status` 的 `binding.instance_id` 取值随每次请求携带；`writer-handover begin/accept` 同样调用同一实现，不在个别入口另写检查。
- **写者结构**（机制稿 §1.2）：`writer.require_supported()` 是所有读者的前置——`schema_version` 必须为 1、`state ∈ {idle, held, recovering}`、idle 不得留 holder、held 必须有 holder，且 **holder 代次必须等于顶层代次**。未知字段照旧保留，但未知 schema 或所有权事实矛盾阻断依赖它的读写。
- **对象终态**（设计稿 §5.1、§5.4）：`status=archived` 或已有 `terminal` 的对象不再接受 `task-pause`/`task-resume`/`task-knowledge`/`task-curate`/`task-retrospect` 等日常写入；未完成的归档动作走专用恢复分支。
- **义务来源**（机制稿 §11.2）：`gates.declared_step_specs()` 从**已校验发行清单**读「有哪些义务」。声明先完整校验：非对象、缺 `id`、未注册处理器、重复 `id`、缺 `mode`/`due` 一律 `WF_ASSET_DECISION`；随后任务步骤若声明 `scope != "task"`、或 `condition`/`mode`/`due` 与处理器不一致，同样判矛盾——**不能靠改 scope 把门禁移出义务集合**。`TASK_STEP_SPECS`/`HANDLERS` 只保留「谁来算、按什么顺序算」。
- **记录定位**（设计稿 §5.4）：`locate_task_dirs()` 收集活动区与归档区的全部匹配，重复即拒并列出双方；`load_task()` 再核记录内 id 与请求一致，不静默取其中一个副本。

### 2.3.9 基线提案、续做与状态约束

- **可写状态**（机制稿 §3.4）：`baseline-apply` 要求任务执行中且**未暂停/未挂起/未归档**——`archived`/`terminal` → `WF_BINDING_MISMATCH`，`paused`/`suspended` → `WF_SEMANTIC_DECISION`。持写权不等于可写状态。
- **批准必须绑定本次提案**：`choice ∈ {approve, 批准}`（`reject` 或无关决定一律 `WF_SEMANTIC_DECISION`）；`object_digest` 必须等于 `plain_digest({"files": files})`，拿旧提案的批准用不了（`WF_APPROVAL_MISSING`）。
- **前像必填且有约束**：每条 `files` 项必须带 `before`；`null` 表示此前不存在，dict 必须含 `digest` 或显式 `{"exists": false}`——`{}` 等于没有约束，直接 `WF_SEMANTIC_DECISION`。
- **续做三分类（整批前置）**：先识别未完成的 `baseline.apply` 动作与提案同一性，再把**全部**条目分类为 已到目标内容（`skipped`）／仍等于登记前像（待写）／都不是（冲突）；**存在任何冲突即整体拒绝**（`WF_WORKSPACE_UNRESOLVED`，facts 列 `conflicts`），一件都不写——前像判定绝不放进写入循环，否则会留下半应用状态。
- **核验顺序**：先核提案结构与范围（既有路径/嵌套仓库/触碰面判定），再核批准绑定与前像。

### 2.3.10 审查判定的输入核验、预览令牌与独立入口锁

- **判定输入六核**（机制稿 §9.2）：`review-decide` 逐份核 ①`check-anchor` 等于**当前**锚点（导入后重跑 Check 也失效）②`findings` 无 `blocker/blocking/critical/high` ③`source-cli` 等于该槽位声明的 `reviewer_cli` ④`read-scope`/`excluded-scope` 非空 ⑤`scope-exceptions` 为空 ⑥`axes` 每轴 `conclusion=pass`，且 `material-gaps`/`missing-materials` 为空。命中即 `WF_REVIEW_INVALID`——「判定输入不成立」与「意见为否 → fail」分开。
- **判否与输入不合法分开**（机制稿 §9.2、§11.2）：锚点、`source-cli`、材料声明、导入摘要冲突属**输入不成立** → `WF_REVIEW_INVALID` 且不写结论；阻塞发现、轴 `conclusion≠pass`、`scope-exceptions`、材料缺口、报告 `verdict≠pass` 属**有效审查判否** → 记 `verdict=fail` 并写 `attempts[].outcome=fail`，使「首轮失败→次轮通过」仍能重建 `review_fail` 触发强制复盘。
- **外部审查固定五轴**（机制稿 §9.2、skill `wf-review`）：报告 `axes` 必须齐 `range / acceptance / contract / regression / testability`，缺一或出现五轴之外的键即 `WF_REVIEW_INVALID`；每轴结论只取 `pass|fail|uncovered`，非 `pass` 记 `fail`。Check 期内部自审用 `standard/requirement` 两轴，两者不得混用。
- **导入与门禁引用**（机制稿 §9.2）：同轮同槽位**同摘要**幂等重入、**不同摘要**报冲突（`WF_REVIEW_INVALID`，不覆盖也不留旧结论）；`task.review-passed` 除核 `verdict=pass` 与 `check_id` 绑定，还核 `result.imported[]` 每份报告的 `report_digest` 仍等于当前 `reviews.imported` 的同轮同槽位摘要——报告被换掉，旧 pass 立即失效。
- **预览令牌与锁内重核**（机制稿 §10.3）：令牌是**随机 128 位 nonce**，只在本次进程/本次预览有效；`--nonce` 仅为测试注入点。确认之后**在同一把锁内重算预览并比摘要**才是漂移防护：普通 `repair` 重算 `build_preview`、`repair --dispose` 重算 `dispose_preview`（计划文件被换即失效）、`uninstall` 重核选中集合 + 写者状态 + 逐路径预览指纹 + `.gitignore` 全文。任一不符即 `WF_PREVIEW_STALE`，不动任何文件。
- **卸载锁内重核**（机制稿 §10.3）：两种比较必须分开——**删/留**用发行摘要（本地偏离按设计保留），**确认期间是否变化**用**预览时指纹**（逐路径在预览阶段记录）；`.gitignore` 另比当前全文与预览读入是否一致。任一「变过」即 `WF_PREVIEW_STALE`，一个文件都不删；既有偏离不会因此被误判。
- **巡检治理面**（设计稿 §6.2、机制稿 §8.4）：回收候选只看「**最近连续 N 个正常归档任务**的完整策展清单是否引用」+「无活动任务引用」——不是「引用次数达 N」；异常归档与未开工任务不作观察样本，样本不足或旧记录缺清单报 unknown 而不当零。周期触发按正常归档的 `(archived_at, id)` 累计，达 `inspection_every_tasks` 整数倍即触发，异常归档不计也不重置。
- **卸载入口的资产边界**（设计稿 §7.2、§7.3）：`uninstall.py` 先核 `installation.manifest_digest` 存在且等于清单实际摘要（缺失、空值、不符都阻断）；再对每个登记资产核「安全相对路径（拒绝对路径、`..`/`.`/空段、反斜杠、盘符）→ `realpath` 仍在项目根 / skill 根内 → 类别属白名单」。`release_only` 是发行侧资产、目标项目无落点，显式跳过；其余未知类别拒绝。任一条目不合规即汇总全部问题、**整批拒绝**——前置在任何读取与删除之前，令牌只授权预览范围、不能扩大资产边界。
- **独立入口锁与运行时同契约**：`repair.py`/`uninstall.py` 只在 `O_CREAT|O_EXCL` 成功时写 `wf-lock-v1` 标记；已存在的锁文件标记为空或不认识一律拒绝，不认领「初始化未完成」的对象。

### 2.3.10.1 平台表与身份判定

支持的 agent 由 `--platform` 声明，装完还可以再跑一次追加（同发行引用）。**平台清单就是本项目的身份事实**：不再有 `--host-id`、`--verify-capability`、`--capability-evidence`，安装记录里也不再有 `session_profile`。

| 平台 | 自有目录 | 是否读共享层 | 落地 |
|---|---|---|---|
| `dsh` / `codex` | — | 是 | `.agents/skills/` |
| `cursor` | `.cursor/skills` | 是 | `.agents/skills/` |
| `geminicli` | `.gemini/skills` | 是 | `.agents/skills/` |
| `copilot` | `.github/skills` | 是 | `.agents/skills/` |
| `claudecode` | `.claude/skills` | 否 | `.claude/skills/` |

依据：[Cursor 技能目录](https://cursor.com/docs/skills)、[Gemini CLI 发现层级](https://geminicli.com/docs/cli/using-agent-skills)、[VS Code Copilot 技能位置](https://learn.microsoft.com/en-us/visualstudio/ide/copilot-agent-skills)、[Claude Code skills](https://code.claude.com/docs/en/skills)。

**运行期判据**（`session.check_platforms`）：信封 `identity.host_id` 必须出现在 `installation.platforms` 里；未出现 → `WF_IDENTITY_UNRESOLVED`（`reason=host not installed for this project`，facts 带 `installed_platforms` 与 `next: install --platform <名字>`）。只读诊断（`status`/`inspect`/`gate`/`definition`）不受此限。

**为什么把能力证据去掉**：机制稿 §1.4 的判据原文是"证据是否**适用**当前宿主"，而实现此前做成了"宿主是否**等于**安装时那一个"，等于把项目判给了单个 agent。修订后：能力是宿主属性、由平台表静态声明；真实异常（实例丢失、绑定不符、代次过期、检查锚点失效）由各自路径即时报错，属于 **fail-loud 而非事前让人举证**。

**多 agent 的覆盖保护与身份无关**（全部建立在会话身份与代次之上）：

| 机制 | 作用 |
|---|---|
| `.wf-lock` + 持有者存活探测 | 所有写入串行化 |
| `writer.holder.id == session_key` 且 `scope=对象` | 别的会话进入即 `WF_WRITER_BUSY` |
| `generation` 三处一致 + 请求携带 | 旧代次写入被 `WF_GENERATION_STALE` 拒绝（防丢更新） |
| 绑定按 `session_key` 分文件、`bind` 要求写权空闲 | 同一时刻只有一个会话推进同一对象 |
| 检查锚点 / 审批摘要 / 外部变更门禁 | 内容被别人改过就失效 |

### 2.3.11 已知边界与实现说明

「不存在的命令不得在文档与 skill 中宣称」同样适用于函数名与能力条目。本节登记**已实现但有边界**的项与**明确的实现纪律**；确属未实现的项会显式标注「未实现」，不混写。

- **锁的存活探测**（已实现，含边界）（设计稿 §4.4 的三要素）：`lock.py` 在固定标记行之后追加 `holder pid=<pid> start=<进程启动时刻>`；`verify_holder(root)` 只读判定该进程是否仍在且启动时刻一致（pid 复用会被识破），不获取锁、不改文件。获取时刷新持锁者事实、释放时清除，避免陈旧 pid 被当成存活。**运行时与 `repair`/`uninstall` 都在锁内消费该判定**：登记的持有者仍存活即 `WF_WRITER_BUSY`，不因人在预览里点了确认就清空写权；人确认是补充出口而非替代。`repair`/`uninstall` 的锁与运行时同契约（见本文 §2.3.10）。
- **`task-new` 的主记录与意图归属**（第七至十一轮；人裁 A 已落地并修完 4 条复审缺陷）：首次创建是 writer 上的单一 `task.create` 父动作——意图与写权同一次写入；`targets` 一次固定 writer/task/binding/runtime **以及 instance/template/title/task-kind**（不可变目标，重入只按这些值重建，不从当前请求取）；四个步骤由 `_run_creation_steps()` **逐步推进**，每步先核真实后置、缺什么补什么，再置 done；`_finish_writer_action` 结案前**重核每步真实后置**，手工标 done 不能代替产物；实例不符由 `_require_instance_match` 与意图内固定值双重拒绝。旧版本留在 `task.action` 的 `task.create` 遗留形态给 `WF_RECORD_INVALID` + repair 出口，不再输出无法执行的恢复指引。`bind`（绑定既有对象）仍用独立 `session.bind` 动作，因为那不是首次创建。
- **外部变更的阻断**（P1-1 / D-01，已接线）：`scope.external_changes` 的结果进 `check.scope_facts`，**触及本任务批准触碰面的未归属提交**在 Check 时必须有「已核对无影响」的人判（按提交 OID 精确匹配，或用 subject 含 `external-changes` 的整体声明）才放行，否则 `WF_SEMANTIC_DECISION` 并给四条出口（逐条核对、用 `task-attribute` 裁决归属、回 Plan、重检）。未触及触碰面的外部提交只记事实、不阻断。登记时的顾虑——夹具/人手提交无 trailer 会被一律判死——用「人判承载」解决，而不是放弃判定。
- **Finish 期的规范变更通路**（P1-2 / N52-02，已交付受控迁移）：`spec-update` 与 `baseline-apply` 都允许 `execute/check/finish`；在 finish 期应用后，`_reenter_check_from_finish()` 作为**父动作内部的一步**把 phase 置回 `check`，旧检查结果保留并追加 `invalidated={at, by, action_id, reason}`，门禁侧见到该失效事实即 `WF_CHECK_STALE`；不伪造新的 Check 成功回执。
- **`.wf/out-of-scope/` 知识拒绝项（2026-11-12 已交付，人裁 A 由第三轮提前到第二轮）**：机制稿 §8.4 定 schema，四项启用前置同批打勾——
  ① **写入者**：`spec-update --changes` 的 `add`（首建）与 `update`（重提追加）经 `spec.out_of_scope_problems()` 校验：frontmatter 三字段（`concept`/`reason`/`reconsider_when`）非空、文件名与 `concept` 一致、`## 既往请求` 段存在；`update` 还要求**既往内容逐行不变**（只增不改）且追加行形如 `- <YYYY-MM-DD> ｜ <摘要> ｜ <裁决引用>`。全部在整批校验段完成，任一不过即 `WF_SEMANTIC_DECISION` 且**零写入**。
  ② **重提追加**：同 concept 已存在时 `add` 被拒（出口：按重提追加处理），不新建文件、不改写既往行。
  ③ **路径放行**：`.wf/out-of-scope/` 进 `paths.WRITE_TARGET_PREFIXES` 与 `protocol/project_data.json`（两处都是唯一声明处，不散在各调用点）。
  ④ **消费者**：`inspect` 的治理面新增 `out_of_scope_duplicates`（同 concept 多文件报重复、不可解析单列 `unverified`），并把它从 `governance_omitted` 移除。
  用例：`scripts/tests/wf_runtime/test_out_of_scope.py`（10 例，覆盖 PRD 的五项验收：建文件 / 重提追加 / 空 `reason` 拒 / concept 与文件名不符拒 / 多文件被巡检报重复，另加「改写既往内容被拒」「未知不当零」「声明清空」）。**仍未做**：知识处置入口（`task-knowledge`）在 facts 里引用拒绝项原文——当前只有巡检面可见；语义去留仍由人判。
- **`scope.classify_candidates` 的归属判定（2026-11-05 第二次复审修正；2026-11-12 **d 档已交付**）**：候选集 = 未提交路径 ∪ 本任务归属路径；`owned = 归属标记/裁决 ∪ 命中批准触碰面`，`in_scope = 命中批准触碰面`。首轮可达结果为 e（owned∧in_scope）、f（owned∧¬in_scope → `WF_SCOPE_VIOLATION`）、c（未归属且未提交 → `WF_WORKSPACE_UNRESOLVED`）；**首轮 d 档恒空**——未归属的候选必然未提交，已经落 c。已提交的外部提交不进候选集，由外部变更核对要求人作「已核对无影响」判断（本节 P1-1）。
  **第二轮补上的 d 档（归属语义存疑，2026-11-12 交付）**：判据只此一处——路径命中批准触碰面、却被**另一个未归档任务**的 `handoff.wip.paths` 显式登记为未处置 WIP，即归 `d`（`WF_SCOPE_UNRESOLVED`，facts 同时给 `ambiguous_ownership` 与 `cross_task_claims`）。实现在 `classify_candidates` 内调用既有 `scope.cross_task_conflicts(root, task, touch_paths)`（批准触碰面只推导一次，注入点不会被第二处掩盖），`check.run_check` 不再重复计算争抢。用例：`scripts/tests/wf_runtime/test_scope_d_bucket.py`（含 e 档正对照）+ `repro/f7-3-scope-single-source.py` 双模。**仍未覆盖**：非 wf 编辑者留下的、无 WIP 登记的「已提交但归属不可解析」路径——它们不进候选集，仍由外部变更核对承载，不据本条宣称已覆盖。
- **巡检的知识治理两类（P1-3 剩余；2026-11-12 已交付）**：机制稿 §8.5 要求『需人工比对』清单（witnessed/potential 模式对）与 `author` 复核顺序（`author=ai` 优先、`extracted` 前置）。实现在 `tasks._manual_compare` / `_author_order`：
  - `manual_compare`：按 `spec.all_specs` 的合法 `paths` 与**本次巡检的仓库路径集**（`git ls-files --cached --others --exclude-standard`，不含 `.git/`）比对；有当前见证 → `witnessed`（列见证路径与对应模式），无见证但任一模组合按 `paths.provably_disjoint` 不能证明不相交 → `potential`（列未排除的组合与依据）；全部组合可证不相交的两份规则不进候选。**不判语义矛盾**——只给人对照正文的事实（机制稿 §8.5 末段）。
  - `author_order`：只给顺序与依据（`extracted` 前置、`author=ai` 优先、再按路径稳定排序），不判「该不该复核」。
  - 未知不当零：无合法 `paths`、规格不可解析、仓库扫描不可用 → 进 `unverified` 且不据此给候选结论。
  - `governance_omitted` 同批**清空**（空列表本身是断言「没有隐瞒的类别」）；`governance` 现有七类。用例：`scripts/tests/wf_runtime/test_inspect_governance.py`（6 例）与 `repro/inspect-declares-omitted.py`（双模，注入=把已交付类别继续声明为未输出）。
- **`assets.branch_source_check` 的消费点**（P2-5a，登记未实现）：函数已实现但**首轮无调用方**，第三轮 `upgrade` 才消费；文档若声称它在运行期生效即为不实。
- **追加平台 = 重复安装语义（2026-11-05 第二轮复审后定稿）**：`install.py::add_platforms` 与 `wf-dev-deploy.py` 同名分支行为一致——①**锁内**重读安装记录与写权记录、重建计划并复算冲突（锁外读取可能已被并发追加改变）；②写权记录按运行期同一判据校验（schema/状态组合/holder/代次），不只看 `state == idle`；③新根技能副本登记进 `installation.assets`，否则它们会落未归属路径（c 桶）挡住开工；④目标已存在且内容不同 → 整批 `WF_ASSET_DECISION`、零写入（不覆盖本地偏离）；⑤安装记录等元数据变更计入回执 `changes`，路径一律**项目相对**；⑥授予与释放各递增一次代次；⑦无任何变化时幂等返回，不取写权、不产生空回执。
- **安装期的分支来源核对（2026-11-05 已交付）**：设计稿 §7.1／机制稿 §10.4 要求投放前核对「当前分支缺失、其他本地分支存在」的同名路径。`install.py` 自含 `branch_source_findings()`（与 `wflib/assets.py::branch_source_check` 同语义；安装时尚无 `.wf/lib`，故不导入运行时）：预览列出路径与分支并返回 `needs_decision`（`WF_ASSET_DECISION`，exit 2），不写任何文件；人在该分支执行、或重跑同一命令加 `--confirm` 表示在本分支按新安装继续，后者写入 `installation.decisions`（`kind=branch-source`）。只读核对，不保存 branch 字段、不切换分支；未取得的远端引用不假装已扫描。
- **单 reviewer 的「参考性执行」（2026-11-05 人裁 B）**：设计稿 §6.5 允许「只能凑一个时执行单 reviewer 并标 `degraded: single-provider`」，其口径已在同批修订中明确为「**发起与报告导入照常留档供参考，但不产生判定结论**」：`review-launch` 记 `degraded` 与槽位；`review-import` 照常导入报告；`review-decide` 以 `WF_REVIEW_INVALID` 拒绝，facts 带出已导入报告与两个出口（补第二家 CLI / `--unavailable` 不可用处置）。因此不存在「degraded 结论」，也不得把单 reviewer 的报告当作审查 pass；要归档必须满足两个彼此不同、且均异于实施 CLI 的 reviewer。

- **跨任务碰撞预检**：没有集中的 `preflight_collisions`，各入口就地判定（`task-new`/`archive`/`task-abandon`/`spec` 的 `WF_TARGET_COLLISION`）；新增入口需自行调用同一判定，不得另写。
- **`dep` 的建删边（2026-11-12 交付）**：`tasks.cmd_dep` 只做四件事——两端存在性（`WF_TARGET_MISSING`）、自环与环（`_prerequisite_graph` + `_find_cycle` 的 DFS 三色）、活动区约束（建边要求前置未归档，删边只改未归档持有侧、目标可在归档区由 repair 处置死引用）、写回 `prerequisites`。动作是 `dependency.change`，**targets 覆盖两端任务**（D08「第二轮加入全部依赖/实例目标」），因此跨任务目标碰撞走既有 `WF_TARGET_COLLISION` 判定而不是新写一份。幂等：重复 `add`/`rm` 返回 `WF_OK` 且注明「幂等」，不重复写入、不产生新动作。用例：`repro/dep-edges.py`（双模：注入把自环守卫与环检测**两层都**退回 → 自环被接受）、`test_dep_edges.py`（环/菱形/只收活动记录）。
- **日界时钟**：核实周期按 `records.utc_now().date()` 计日（UTC），用例与实现须同源；用本地 `date.today()` 会跨日误判。
- **「补结构」不等于「补词表」**：规范未登记取值域时（如 `released.decision.choice`），实现只核结构、不自造白名单；规范登记了的观察类别（压缩/重入/新会话/传递）必须真被消费，安装器转写声明的 `declared-verification` 不得支撑 `capability.status=verified`。
- **续做三态覆盖全部写入类操作**：add/modify/delete/disable/rename 都要「符合前像→执行、已是本动作后像→跳过（并补齐索引等后置）、都不符→冲突并保留现场」；disable 的后像识别靠 frontmatter `status=disabled` 而非摘要比对，rename 的后像识别要同时核目标内容。
- **跨记录写入先落意图**：`task-new` 与 `bind` 都先写动作意图（`task.create`/`session.bind`）再做写权、绑定、运行态等跨记录写入，并各自有 `_resume_*` 续做入口；恢复入口与普通入口共用身份核验，不是特权通道。
- **巡检治理面的未知纪律**（已实现）：`inspect` 的 `spec_usage` 在**任一**未知存在时不输出候选、`inspection.due` 在配置非法时为 `null`——未知来源包括样本不足、**归档记录事实不完整**（`status≠archived`、`terminal` 非 normal/abnormal、`archived_at` 缺失或不可解析）、**归档样本或活动任务**缺 `curation`、条目非对象/不可解析、`spec_reclaim_tasks`/`inspection_every_tasks` 非法、以及样本或活动任务引用过的 spec 路径已不存在（改名/合并无法可靠映射）——活动任务一侧同样适用「读不出不等于没依赖」，依赖优先保护。任一未知即 `statistic_complete=false`，且 `inspection.due` 也为 `null`——记录不完整时正常归档计数不可信，触发时机同样不能给结论。

- **`stop` 的 transfer 用 `Decision.target_task` 指定承接对象（2026-11-05 第七轮复审后续查证并修正）**：subject 只列待承接路径；承接须通过三项核对——任务存在且不是本任务、未归档/终止、已批准且批准触碰面覆盖全部待承接路径，任一不满足即 `WF_SEMANTIC_DECISION` 并给三个出口。修复前把 subject 首项当 id，id 会与路径混在同一清单里被逐项指纹化，承接核验实际不可达。
- **`writer-handover begin` 的 `--to` 是接收者的 session-key（2026-11-05 第六轮复审）：不是裸会话名；`accept` 按 `handover.receiver_session_key` 与当前会话 key 比对，传裸名会得到 `WF_BINDING_MISMATCH`。人给接收会话名时，入口侧应先按本机身份派生 key 再调用（E2E 用例见 r71 第 4 组）。
- **启动校验覆盖七步，另两步显式不在启动面（2026-11-06 扩交付；原「四步子集」条目关闭）**：`startup_check` 现按机制稿 §5.2 的固定顺序输出 **①绑定与写者、⑤记录可解释性、③执行候选唯一性（新）、⑦对象与依赖、⑧写者标记锚点（新）、⑨框架资产可用性（新）、⑩工作区边界**；③ 在多候选时按记录集不变量报 `WF_RECORD_INVALID`（不是写权占用），活动记录不可读时按「未知优先」报 `WF_HISTORY_UNRESOLVED`；⑧ 在持有/恢复态核 `.wf-lock` 的 `wf-lock-v1` 标记行，缺失或未知报 `WF_HISTORY_UNRESOLVED`；⑨ 缺任一必需资产报 `WF_CAPABILITY_UNAVAILABLE` 并点名。**仍不在启动面的两项**（`STARTUP_OUT_OF_SCOPE` 常量在代码里列明）：④维护写者与预览范围的对应（只有维护入口有预览上下文）、⑥未结束实例的快照/游标/任务归属（实例属第二轮）。因此对外只能说「status 覆盖七步、两项显式不在启动面」，不得再说「startup 四步 ok＝完整启动校验」。用例：`repro/startup-checks-anchor-assets.py`。
- **D18 降级阶梯与 D21 集合负例：标签与事实漂移，2026-11-06 人裁落地（第十轮复审登记，裁定见 `pending-decisions.md` §6）**：机制稿 §12.1 与本文 §6.2 曾把 D18 标为「跨轮基础项」，但代码只有单文件读取路径（`load_one_with_budget` 恒 `complete=true`），设计稿 §6.2 的「缩小策展→退索引→短提醒→汇总、截断标记」无运行点；D21 的执行器集合语义负例（多 clone 不覆盖、目录移动不失效、venv 重建沿用、purge 后须重确认）在夹具 §4 列为「首轮遗留」、`validation` §93 登记未运行。**处置**：D18 已由人裁登记为延期（见 §4）——多文件预算降级链该轮交付·第三轮，首轮只保单文件不截断；D21 已按裁定补齐 repro 负例（`d21-executor-set-*.py`），`repair` 重建标识留第三轮；在此之前不得把「跨轮」读作「已交付」。
- **`task-replan` 已要求 Decision（2026-11-06 交付；原第七/十轮登记条目关闭）**：`cmd_task_replan` 只核绑定与写权，持写权者可静默把任务打回 Plan、使原批准失效；同族的 `task-abandon`/`stop`/`archive` 都强制 `--decision`。命令面现要求 `--decision` 且必须是 `choice=replan` 的决定：subject 需含任务 id 或 `object_digest` 等于当前规划版本；生效时旧批准移入 `plan.approval_history` 并清空 `approval/approved_version`（旧批准不再可用），决定写入 `execution.human_decisions` 与动作 `decision_refs`。
- **低优先观察（第十轮）**：`paths.touch_path_errors` 对嵌套仓库只查字面祖先（未做 realpath 双遍，风险低）；`review.py::decide` 的 `--unavailable` 未核该轮确实发起过 launch；`project_key_approved` 用子串匹配作证据（强度弱）；原语类 skill 复制的入口纪律块对不调 CLI 的原语无行为意义（保留以统一口径）；`project-config.skeleton.json` 第 2 行缩进不一致（效果无关）。
- **`lock.verify_holder` 无运行时消费：本节首条「锁的存活探测」的「运行时」半边不成立（2026-11-06 查证并**归因完成**：属**文档错**，不是实现缺陷）**：`payload/` 全树对 `verify_holder` 只有 **1 处**引用——`lib/wflib/lock.py:215` 的定义本身，**零调用点**；`repair.py` 用的是自含的 `_live_holder`（`repair.py:109`），`uninstall.py` 同样自含，二者都不导入运行时。因此本节开头那句「运行时与 `repair`/`uninstall` 都在锁内消费该判定」只有后半成立：运行期的互斥来自 flock 本身与标记行校验，**运行期既不读持锁者事实行，也不会因持有者仍存活而返 `WF_WRITER_BUSY`**。单元测试（`scripts/tests/wf_runtime/test_lock.py`、`r75`、`r76`）只覆盖函数本身，不构成运行期消费的证据。处置：按机制稿 §12.4 先判「实现缺陷」或「文档错」，归入 688「历史锚点或旧写者事实待核对」批处理；归因依据：设计稿 §8.2「互斥与锁生命周期」的应拒绝列明写「**PID 消失即当空闲**」为禁止行为，并给出「持锁标记 / 存活探测 / 人确认恢复」三条出口；设计稿 §4.4 对「未知旧写者是否仍活动」要求的动作是**阻断相关写入**并交人按设计稿 §5.5 恢复，而不是自动接管。运行期不读持锁者事实行、一律阻断（fail-closed），与上述要求一致；`repair`/`uninstall` 各自自含 `_live_holder`，才承担「判定死活」的职责。因此本节原文对「运行时也在消费该判定」的表述是**失实**，已按本条更正；`verify_holder` 目前是**无调用方的死代码**，清理或改由 repair 复用属维护项（见本节末「运行时死代码」条），不影响首轮行为。另注：若日后要让运行期区分死活持有者，须先改设计稿（现文禁止以 PID 消失放行），不能由实现自决。

- **锁文件「持锁者事实行」的措辞债（2026-11-05 第十三轮复审 P3）**：机制稿 §4.1 的字面是「已存在文件只在完整内容等于 `wf-lock-v1\n……` 时复用」，而实现每次获取都在自己持锁后刷新标记之后的持锁者行（供存活探测）。行为正确、方向安全，但按「契约以机制稿为唯一来源」的纪律，这属**需回机制稿同批登记**的措辞债（补一句「标记行不可变；标记后的持锁者事实行由当前持锁者刷新」）。在机制稿补入前，本文以此条为准，不视为实现可自决的细节。
- **`spec-update` 的 update 首跑核前像（2026-11-06 登记，**2026-11-12 已交付**）**：`baseline-apply` 强制每条 `before` 并在续做时三分支消费前像，而 `spec-update` 的 `before_digests` 原先只在续做判定里被消费——批准与写入之间 spec 文件被改过会被静默覆盖。现在 `validate_changes` 的**整批校验段**对**首跑**也逐条核前像（登记过 `before_digests` 的条目；删除/停用取 `old_paths`，其余取 `new_paths`），不符即 `WF_SEMANTIC_DECISION` 并**零写入**，出口是「按当前内容重新取前像并重新批准」或「先处置批准后的改动」。用例：`scripts/tests/wf_runtime/test_spec_first_run_before.py`（含「停用该判定即回到静默覆盖」的注入）。
- **发行身份已绑定 tag 提交内容（2026-11-06 交付，关闭 第二十六轮复审外部 1）**：`install.py::verify_assets` 在解析出提交后**按该提交的树取字节核摘要**（`git show <commit>:<path>`），「同版异内容」从此相对**提交**成立；工作树是否干净只作 `source_dirty` 事实，`--strict-source` 仍可要求子树干净（作者链路保持可用）。用例：`repro/release-identity-commit.py`（篡改工作树资产并把清单改成与工作树一致 → 必须 `WF_RELEASE_CONFLICT`；注入=退回工作树核摘要 → 判红）。仍未做：清单本身的签名/来源证明（设计稿 §1.5 声明不防伪），以及按提交取字节的**性能**优化（当前逐资产 `git show`）。
- **复杂度与 TDD 的人工载体已交付（2026-11-07 关闭 外部 2）**：批准决定可带 `plan` 块——`complexity`/`tdd`/`downgrade` 由**人写的决定文件**给出，请求里的同名输入降为「提议」；任务记录保存 `plan.confirmed_source`（`decision`/`inputs`）、`plan.human_inputs` 与 `plan.unconfirmed_keys`。**可扩展**：`tasks.HUMAN_PLAN_KEYS` 是注册表，新增人判项只需登记一条键+校验；未登记的键**原样留痕**进 `human_inputs` 并列入 `unconfirmed_keys`（不丢弃、不静默放行）。`gates.final_gate` 现要求复杂分级必须 `confirmed_source == decision`。用例：`repro/complexity-human-carrier.py`。
- **卸载正常路径登记维护写者并留可核回执（2026-11-06 已交付，关闭 外部 3）**：`uninstall.py --apply` 在写权合法时先取维护持有（`state=held`、`holder.kind=maintenance`、代次 +1），移除资产与托管段后释放为空闲（代次再 +1、holder 清空），并向 `maintenance_results` 追加一条 `operation=uninstall` 的回执：`changes` **只列真正被删除的路径**（本地偏离项不列），`disposition.kind=uninstall`、`evidence={removed, assets_absent}`。该回执按新增的 `uninstall` 探针（「登记的路径当前都不存在」）派生为 `disposed`，**不依赖 Git 提交**——此前若照 commit/reverse 记，会因「资产已删」落 `pending_check` 并挡住后续任务开工（这正是本轮先定口径再改代码的原因）。用例：`repro/uninstall-records-maintenance.py`（注入=把 kind 写成 commit → 回执落 `applied_pending_commit`，判红）。仍未做：`--purge`（第三轮）；`maintenance-flow.md` 的 `control.uninstall.apply` 与本处实现同批核对后未再声明偏离。
- **就绪视图已交付（2026-11-06 关闭 外部 4；2026-11-12 补实例归组）**：新增只读子命令 `ready`——按创建时间列出活动/暂停任务的 `id/title/status/phase/created_at/eligible/ready/blockers`，并给出 `suggested`（ready 中最早的一个）。就绪判定＝独立接续资格通过 ∧ 已批准 ∧ 非「进行中未暂停」∧ 写权未被其他会话持有；命令**只读**，不写任何判定字段。实现稿 V1 的措辞恢复为「新会话先看 `ready`，再 `bind --task <id>`」。用例：`repro/ready-view.py`（注入=忽略全部阻断项 → 进行中任务仍被判就绪，判红）。
  **2026-11-12 补实例归组**：`ready` 增 `runs[]`（每个实例一行：`run_id`/`workflow_id`/`terminal`/`paused`/`tasks`），并把 `WF_BINDING_MISMATCH` 细分出 `run_in_flight`——同一个码原先同时覆盖「在途实例」「实例正常结束」「异常结束无保留许可」，人看不出该绑实例还是走 repair。判定本体移到 `runs.binding_state()`，`_eligible_task_bind` 与 `cmd_ready` 共用（不再两处各判一次）。悬空 `run_id` 进 `runs[]` 并标 `unknown`，不静默丢弃。用例：`scripts/tests/wf_runtime/test_ready_runs.py`（4 例）。**子仓库归组不做**：嵌套仓库是 charter T3 B2 的硬边界。
- **安装自检解析 skill frontmatter（外部 5，**2026-11-12 已交付**）**：`self_check` 原本核清单摘要、运行时导入、步骤/处理器/命令面/桩轮次，但不解析投放后的 `SKILL.md` frontmatter，设计稿 §1.2 的「frontmatter 可解析」一半缺失。现在对 `kind=skill` 的投放资产逐份核 `skill_frontmatter_problems()`：起止 `---` 成对、`name`/`description` 非空、无重复键；问题进 `problems` 汇总（不改文件、不判语义）。用例：`repro/skill-frontmatter-selfcheck.py`（把清单摘要改成与新内容一致，只留 frontmatter 检查能抓到；注入=关掉该分支 → 红）。
- **`repair` 尚未交付 project_id 重建（2026-11-06 第二十四轮复审外部 2）**：设计稿 §5.5 要求 repair 重建标识并显式失效旧确认记录，`repair.py` 目前只有 writer 恢复与 `--dispose`。因此 `baseline-apply` 在「历史有身份、现场缺失」时的出口改为两条：① 从 Git 恢复配置（旧值仍在历史里时）；② 等 repair 重建能力交付（第三轮，与机制稿 D09 一致）。在此之前不得静默生成新 id。
- **`uninstall` 不登记维护写者（外部 4）**：机制稿 §10.5 要求 writer 合法时正常 acquire maintenance；当前卸载只做「writer 空闲检查 + 锁互斥 + 令牌」，`writer.json` 无卸载痕迹。互斥可达、可恢复，但「卸载期间谁在维护」只存在于锁文件的 pid 事实中。承接：第二轮补登记与回执。
- **`spec_output_codepoints` 当前无行为效果（外部 6）**：`load_one_with_budget` 恒 `complete=true`，该键不截断也不约束任何对象；设计稿 §6.2 的降级阶梯无运行点（与 D18 同一缺口）。已由人裁登记为延期（该轮交付·第三轮，见 `pending-decisions.md` §6），读到时不得认为预算已生效。
- **skill 正文的否定式禁令与设计稿 §1.1 写作纪律（外部 7）**：设计稿要求禁用否定式禁令句，11 个 skill 普遍含「不做」段。两者当前互相矛盾，属需人裁的文档口径（改写 11 个 skill 或收窄机制稿纪律），本轮不擅改。
- **无锚点出口的语气债已修（2026-11-12）**：机制稿 §1.4 规定显式 `provider=wf` 信封**一律** `WF_IDENTITY_UNRESOLVED`（无本地证据），自动模式下 `issued_id` 由入口在执行边界派生；唯一可用的显式通道是 `provider=host`（宿主给出稳定 `session_id`）。此前四处出口写「用显式信封（--envelope/stdin）」而未点明 provider，等于把一条会被拒的路写成出路（本任务 `prework.md` §1 登记的残余）。现在四处共用一个常量 `cli.EXPLICIT_ENVELOPE_EXIT`，文案本身说明「`provider=wf` 的显式信封会被拒」。用例：`scripts/tests/wf_runtime/test_identity_exit_text.py`（文本断言：四处不再出现裸「用显式信封」）。**这是文案订正，不改任何身份判定**。
- **定义的准备与静态校验（2026-11-12 交付；实例创建/推进/终止仍未交付）**：`definition validate --id <id>` 只读跑机制稿 §7.2 的六阶段（格式/schema → 局部 id 与保留前缀 → 引用来源与顺序 → 路径 → required/skip 与替代映射 → 完成/验证/人判声明），问题清单按 `stage` 排序返回、`ok=false` 时给 `WF_DEFINITION_INVALID`；`definition prepare --id <id>` 落准备记录 `.wf/preparations/<id>.json`（`{session_key, scope_paths, authorization, definition_refs, validation, progress, wip, ended_at}`，该目录已在 `scope._is_control_record` 的固定职责控制记录里），**未通过的草稿照常保留**并在 `validation.ok=false` 中留痕；别的会话持写权时 `prepare` 报 `WF_WRITER_BUSY`（准备不例外于写权）。
  **机械/判断分界**：结构、id 唯一与保留前缀、引用存在与顺序、路径边界、跳过替代的下游一致性、必要验证是否被步骤承载——全是事实；「定义写得够不够清楚」「某个 skip 条件该不该被认可」由人判。`completion` 的自然语言不被求值，`content_version` 只作展示不参与门禁（机制稿 §7.1）。
  **仍未交付（登记）**：① 实例的推进/暂停/终止（`run advance/pause/terminate`）仍 `WF_CAPABILITY_UNAVAILABLE`（`run create`/`locate` 已于 2026-11-12 交付，见下条）；② ~~准备范围尚未登记到 `writer.holder.scope`~~ **2026-11-12 关闭**：`run create` 在锁内重核准备记录（`session_key` 属本会话、`scope_paths` 覆盖该定义、`validation.ok=true`、`ended_at` 为空），再以 `scope={object:{kind:run,id}, preparation:{id, scope_paths}}` 取写权；③ `definition prepare` 未写 writer 动作意图（`definition.prepare` 的 `action` 记录），因此准备期的中断恢复只有记录级、没有动作级四态。用例：`scripts/tests/wf_runtime/test_definition.py`（18 例）与 `repro/definition-static-check.py`（双模）。
- **`definition prepare` 的准备动作意图（2026-11-12 按机制稿 §5.1 补齐）**：准备动作的主记录是**准备记录本身**，所以 `definition.prepare` 动作登记在 `.wf/preparations/<id>.json` 的 `action` 字段（steps `static_check` / `write_preparation`），**未通过校验的草稿同样登记并结案**（摘要标 `draft-only`）——草稿也是准备动作的结果，不写就等于"做了但没留痕"。`facts` 回显动作 id 与状态。用例：`test_definition.py::PrepareActionTest`（2 例）+ `repro/definition-static-check.py` 的准备记录断言（缺动作或未结案即红）。
- **巡检四类三态（2026-11-12 按机制稿 §8.5 补齐）**：`inspect` 的 `governance.four_class_verdicts` 给出**四类各自** `passed/failed/unknown`——归档引用、归档终态、归档 id、知识——外加 `uncovered`（未覆盖对象）与 `overall`。口径：结构探针跑通且无处置项 = `passed`；有需处置/待核对条目 = `failed`；样本不足、条目不可解析、配置缺失 = `unknown`。**`unknown` 不等于通过**（有一条 unknown，`overall` 就不是 passed），整体顺序 failed > unknown > passed。只核结构，语义矛盾仍交人对照正文。用例：`test_four_class_verdicts.py`（6 例：全清通过、unknown 不当作过、failed 压过 unknown、归档不完整落 unknown、非 archived 状态落 id 类、治理清单落知识类）。
- **三处过程义务补齐（2026-11-12，机制稿 §6.2、机制稿 §6.3）**：① **返工普通任务分支在入口内 release**——T 暂停落盘后同一原子段内释放写权（`writer.release` + `_atomic_writer_action`），否则"暂停了但写权还握着"，新会话绑不了 R；同一实例分支不释放（游标还在实例内）。② **替换预览** `task-replace --preview`：只读列出继承路径、`touch_paths` 未覆盖项、下游重连对象、未归档返工、实例映射（`run/step_id/cursor`）与 T 的 `paused/suspended`；不建 S、不改 T、零写入。③ **复评未持权只报告待复评**：`task-reassess` 在写权不在本会话时返回 `waiting + pending_reassessment`（不是 `WF_WRITER_BUSY`）——它不影响任何已成立的归档，原 T 会话取权后补做。
  用例：`repro/task-replace-preview.py`（双模：注入空壳预览 → 红；另测覆盖后不报未覆盖、预览零写入）、`repro/task-rework.py` 第 ④ 步（复评 waiting）。
- **`task-replace`（2026-11-12 交付）**：机制稿 §6.3。`--decision` 的 `choice` 必须为 `替换`/`replace`（**该取值由本文定义**），并**必须给 `touch_paths`**（人确认的 S 拟触碰面）。顺序即机制稿 §6.3 的顺序：① 预检——T 未归档、无挂起、**暂停已处置**（`paused` 为真即拒，出口 `task-resume`）、S 的目标与候选图无环、**S 的 `touch_paths` 覆盖继承路径**（不覆盖即 `WF_SEMANTIC_DECISION` 并列出 `uncovered`，**零写入**、回规划）；② 建 S 的规划记录（**不代批准**：S 开工仍须自己当前版本批准，继承的历史触碰面不是许可）；③ 登记继承——写入 S 的 `attribution.inherited`（`{source_task, paths, decision}`，它是机制稿 §3.3「最终触碰集合」的一部分）；④ 下游重连——原本以 T 为前置的活动任务改挂 S；⑤ 在途实例把 `task_map[step].task_id` 改为 S 并记 `superseded_ids`，`cursor` 跟到 S；⑥ 按异常归档处置 T（**复用 `_apply_abandon`**），T 记 `successor_id`。
  **继承路径的口径**：只取 T 的**交付路径**（标记提交/归属裁决），**排除固定职责控制记录**——把 T 自己的任务目录算进继承会让「覆盖继承路径」永远不成立（实现时实测踩到）。
  用例：`repro/task-replace.py`（双模：注入不登记继承 → 目标断言红；另测「不覆盖继承路径 → 拒且零写入」与「S 未批准、未加入实例」）。
- **`task-rework`（2026-11-12 交付）**：机制稿 §6.2。`--decision` 的 `choice` 必须为 `返工`/`rework`（**该取值由本文定义**），否则 `WF_SEMANTIC_DECISION`。在 T 的动作里一次固定候选：R 继承 T 的原前置并记 `rework_of=T`，T 的 `prerequisites` 增 R 且 `suspended=true`；**先预检目标碰撞与候选图**（`_prerequisite_graph` + `_find_cycle`，环即 `WF_DEPENDENCY_UNMET`）再落盘。
  **同实例分支**：在 `sequence_changes` 追加 `{kind:"rework", step_id, source_task:T, task_id:R, resume_task:T, decision}`，`cursor.task_id` 临时定位 R，**T 不自动 paused**（R 完成后由 `task-reassess` 按登记返回 T）。**普通任务分支**：T 显式 `paused` 并记 `pause_reason`，出口是「释放写权后在新会话绑定 R」——R **不自动加入实例**，仍须独立批准与开工、**不消费 T 的批准**。
  **绑定口径（同批新增 `tasks.bind_task_for_write`）**：决策类入口（返工/复评）接受两种绑定——普通任务绑任务本身；**实例内的任务**绑实例且 `cursor.task_id` 指向它（机制稿 §6.1「在途实例的任务只可由绑定该实例且游标正确的会话推进」），写权 scope 相应按 `run` 核。用例：`repro/task-rework.py`（双模：注入不建 T→R 依赖 → 目标断言红）。
- **`task-reassess`（2026-11-12 交付，替换首轮「空挂起集直接通过」）**：`tasks.reassess_problems()` 逐条给五种事实——`task_suspended` / `rework_set_non_empty` / `rework_set_all_archived` / `prerequisites_satisfied`（复用 `dependency_blockers`）/ `no_pending_action`（`actions.pending`）。条件不满足**不是失败**：返回 `waiting` + `unmet` + 逐条事实（那正是"还在等返工"的正常状态，不造原因码）；未挂起则幂等返回。满足时清 `suspended`（**保留 `paused`**），若因此会出现第二个执行候选则同时置 `paused` 并记等待人恢复（机制稿 §6.2）。返工集合由 `rework_set()` 从**活动与归档**记录重建。用例：`test_rework_reassess.py`（5 例）+ 上面的 repro 第 ④ 步。
- **`run terminate` 的预览与固定提交步骤（2026-11-12 按机制稿 §7.4、机制稿 §5.1 补齐）**：① `--preview` 只读列出待处置清单——每个已生成任务的 `status/terminal/paused/suspended`、`uncommitted`/`existing_commits`/`downstream`/`unfinished_rework`，未生成步骤、`sequence_changes`、`cursor`、`task_map` 与外部依赖；不写任何记录。② 动作 steps 增 `persist_record`：**终态先落盘并把动作置 `persist_pending`**，有覆盖实例记录路径的 `commit` 授权才按精确路径提交并只读复核（`git ls-files` + `git status` 双核），提交后动作结案 `done`；无授权则停在 `persist_pending` 并如实说明。
  **计划元素形状**：`{object, decision_ref, reason}`，`decision_ref` 可为**单个 Decision 或 Decision 数组**——与 `task-abandon` 的 `--decision` 同形（首项是处置决定，其余可带提交授权），因此不必为同一任务写第二条计划项（先前用两条会被判重复）。
- **`step_results` 的产物引用与 `run create` 的续做（2026-11-12 收口两处登记项）**：① 步骤 `satisfied` 时把该步骤**声明的产物**解析成引用写进 `step_results[step].outputs`——字面路径直接用、`{input: name}` 按实例输入解析、**解不出的保留声明并标 `resolved: false`（不猜路径）**；机制只给事实，"能不能记复用"仍是你/人的判断（登记未做）。② `run create` 的动作意图现在**固定完整 creation 本体**（`instrument.inputs["creation"]`），中断续做不再依赖 creation 文件仍在；旧意图没有该字段时按最小事实续做并标 `degraded: true`，不假装恢复了完整输入。用例：`test_run_outputs.py`（4 例）+ 既有 `repro/run-create-once.py` 双模。
- **`bind --run` 与实例写权释放（2026-11-12 交付，跨会话接续闭环）**：`bind --run <id>` 让**新会话**接续在途实例；资格只核「实例存在且未终态」——正常结束只回报结果，异常结束要在新会话绑定**保留任务**（`independent_resume`），所以这两种终态都拒绑（`WF_BINDING_MISMATCH`，facts 写清该绑哪个）。绑定后运行态 `current_task` 取**实例游标所指的任务**（`_runtime_current_task`），不是 null。同时把 `writer release` 对 run 打开（`_ensure_run_releasable`）：与任务同一口径——对象已暂停或已终态才可释放，且当前任务不得留未处置 WIP；否则 `WF_SEMANTIC_DECISION`/`WF_WORKSPACE_UNRESOLVED` 并给出口。用例：`repro/bind-run.py`（双模：注入让运行态不带 `current_task` → 红；另测「暂停→释放→新会话绑定→解除暂停→继续推进」的完整接续链与「已结束实例拒绑」）。
- **`run finish`（2026-11-12 交付，实例正常结束）**：机制稿 §7.4。前置全是**事实核对**、不替人判断——所有**必需**步骤已 `satisfied`；可略步骤的 `skipped` 有声明或决定；`task_map` 里每个任务 `terminal=normal` 且 `archive_persisted` 可核；本实例任务不得留下未处置的保留 WIP（`WF_WORKSPACE_UNRESOLVED`）。任一不成立即 `WF_SEMANTIC_DECISION` 并列出 `unsatisfied_steps`/`illegal_skips`/`tasks_not_normal`，出口是「把缺口做完（**任务 finish 由人调用**）或改用 `run terminate`」。
  成立后写 `closing.mode=normal` → 核真实工作区 → 写 `terminal=normal`、`ended_at`、动作停在 `persist_pending`。**持久化**：只有 `--decision` 给出覆盖实例记录路径的 `commit` 授权才按精确路径提交并只读复核；没有授权就停在 `persist_pending`，`next` 如实写「记录组尚未提交」，不宣称已持久化。**不代调任务的 `finish`**（机制稿 §7.4 明文）。
  用例：`repro/run-finish.py`（双模：注入不写终态 → 红；另测未满足步骤被列名拒绝、无授权时 `persist_pending` 且措辞如实、终态后 `advance` 被拒）。顺带修正一条静态校验口径：定义级「必要验证」只在**存在任务步骤**时要求——纯 human 步骤的流程没有交付物，硬要一条验证只会逼人写假任务步骤（每条任务步骤仍逐条核）。
- **`run terminate`（2026-11-12 交付）**：机制稿 §7.4 的批量异常终止。**先整批预检、再逐个应用**：
  ① 计划归一——`{object, decision_ref, reason}`，`object` 必须是本实例已生成的任务；覆盖不全、名字不属于本实例、重复、`choice` 不在 `放弃/abandon|保留/keep`、`reason` 为空，任一即 `WF_SEMANTIC_DECISION` 且**零写入**；
  ② 放弃项预检——用 `_abandon_preview` 核未提交改动是否被 `disposition` 覆盖，不覆盖即 `WF_WORKSPACE_UNRESOLVED` 且**零写入**（机制稿 §7.4「先校改动处置」）；
  ③ 固定关闭意图：写 `closing={mode:"abnormal", at, decision[], task_dispositions, next_step:null}` 与 `run.terminate` 动作（targets 覆盖实例与每个任务）；
  ④ 逐 task 应用：**放弃走 `tasks._apply_abandon()`**（与 `task-abandon` 同一实现——本批把该函数从 `cmd_task_abandon` 里抽出来共用，参数化绑定/写权由调用方负责）；**保留写 `independent_resume={decision, termination_action=<终止动作 id>, reason}`**，执行中的先 `paused`；**已归档的不再次放弃**（中断后重入）；
  ⑤ 未生成的步骤记 `step_results[kind=not_executed]`，**不建空壳任务**；写 `terminal=abnormal` 与 `ended_at`，回报 `applied` 与 `closing`。
  出口如实：`next` 明说「保留任务在新会话按 `independent_resume` 独立接续；只报告退出完成与保留风险，**不报告业务验收通过**」。软停（`_apply_abandon` 返回非 OK）时实例保持 `closing.pending` 待决，不写终态。
  用例：`repro/run-terminate.py`（双模：注入不写终态 → 目标断言红；另测"含未知任务的计划被拒且零写入"与"未生成步骤记 not_executed、活动区不留空壳"）。
- **`run resume`（2026-11-12 交付；解除**实例**暂停的独立入口）**：机制稿 §2.2 补了「实例暂停/恢复」一行——暂停保存原因与当前步骤并把当前任务标 `paused`；**恢复只清实例 `paused` 并记录依据**，**不恢复任务、不动 cursor、不推进**。实现取三条判定：① 核绑定/写权/确实处于暂停态（不在暂停态时幂等返回、不写记录）；② 清 `paused`，`paused_reason` 原样保留为历史，另写 `resumed={at, session_key, lifted_paused_at}`；③ **`--decision` 可选**——不给时只登记事实；给了就存进 `resumed.decision`，并核 `subject` 含本实例 id 与**本次**暂停的 `paused_reason.at`（拿上一次的决定清这一次的暂停 → `WF_SEMANTIC_DECISION`）。
  **为什么 `--decision` 不强制**：恢复不属机制稿 §2 授权边界里的五类不可逆动作（提交/删除/外发/越界修改/仓库级规则文件），且本仓的 attestation 模型不防伪——强制一次决定文件只增加仪式成本、保护为零。机制提供**通道**，不强制**仪式**；人要附加约束（"先恢复但 task X 别动"）时用它承载，AI 把它当输入读。
  **为什么不顺手恢复任务**：任务的恢复是 `task-resume` 的判据（自核 WIP 指纹/身份/前置），机制代劳等于替人决定"这个任务可以继续"。`resume` 的 facts 会回显 `current_task_paused`，提醒这是另一个决定。用例：`repro/run-resume.py`（双模：注入不清 `paused` → 目标断言红；另核状态绑定与"任务仍暂停"）。
- **`run pause`（2026-11-12 交付；`terminate` 仍未交付）**：`pause --run <id> --reason <text>` 在锁内核绑定（会话绑定与写权 scope 都指向该实例）、实例未终态，然后写 `paused=true` 与 `paused_reason={reason, at, session_key, step}`，并把**当前步骤的任务**一并标 `paused`（清掉执行候选）。**不动 `cursor`**——机制稿 §7.3 明确「实例暂停须保存当前任务的暂停或等待原因及当前步骤，不能只移动游标绕过任务门禁」。幂等：已暂停再调返回同一状态、不重复写入。结案前核真实后置（`paused`、`paused_reason.reason`、任务 `paused`）。
  **待裁（不自行补）**：机制稿 §2.2 只为**任务**定义了「暂停/恢复」，实例的**解除暂停没有出处**（`run` 的子动作表也没有 `resume`）。当前 `paused` 实例的唯一出口是 `run terminate`。若要闭环，需要在三条里择一并在本文的命令面同批登记：① `run advance` 在人判决定成立时清 `paused`（不新增入口，但要给 `choice` 取值登记）；② 新增 `run resume` 子动作（新入口）；③ `run pause --clear`（新开关）。用例：`test_run_pause.py`（契约 2 例）、`repro/run-pause-and-advance.py`（双模；注入让 `pause` 不写 `paused` → 目标断言红）。
- **`run advance`（2026-11-12 交付最小闭环）**：每次推进先核绑定（会话绑定与写权 scope 都必须指向该实例）、写权持有者、实例未终态/未暂停、**固定快照**（记录里的 `digest` 必须仍等于快照文件本身的字节，源定义改动不影响已固定实例）。然后按顺序：
  ① **结算**：游标所指步骤的任务若已正常归档且归档持久化可核 → 记 `step_results[kind=satisfied]` 并推进；异常归档 → `WF_SEMANTIC_DECISION`（按机制稿 §6.4、机制稿 §7.4 处置，不冒充 satisfied）。
  ② **等待**：游标所指步骤已有任务但尚未正常归档 → 返回 `waiting`，**停在原地**（不跳到下一步）。
  ③ **可略步骤**：`creation.steps` 声明为 `skipped` 时，必须有含该步骤 id 的决定，否则 `WF_SEMANTIC_DECISION`；成立则记 `kind=skipped` 与决定，**不为保存答复强建任务**。
  ④ **human 步骤**：必须有答复且取值属于该步骤声明的 `choices`，成立记 `kind=satisfied` 与答复。
  ⑤ **task 步骤**：已映射则复用（重入不建第二份）；否则取上一个未略过 task 步骤的任务作顺序前置（human 步骤不生成边），要求它**正常归档**（否则 `WF_DEPENDENCY_UNMET`），预生成 task id、在实例记录上落 `run.advance` 动作把新任务与顺序边**一次固定**，再建任务目录（`run_id`=本实例、`prerequisites`=前置）、写 `task_map` 与 `cursor`，最后逐条核**真实后置**（任务记录的 `run_id`、`task_map` 映射、游标指向）。
  **机械/判断分界**：步骤顺序、适用性、前置是否满足、答复是否属声明选项——都是事实；「这一步算不算完成」「产物够不够用」由人在该任务上走四阶段判定，实例只引用任务结果（不复制 task 的 status/Check）。
  用例：`test_run_advance.py`（6 例：步骤顺序/前置跨 human 步骤/适用性默认与声明/答复 subject 与选项），`repro/run-advance-creates-task.py`（双模；注入让任务不记 `run_id` → 目标断言红；「重入不建第二份」因有三层保护而作正向断言）。
- **`run create` / `run locate`（2026-11-12 交付；推进与终态仍未交付）**：`create` 走 writer 上的**单一 `run.create` 父动作**（意图与写权授予同一次写入，目标含 `writer`/`run`/`binding`/`instance`/`definition`/`definition-digest` 后一次固定）：
  ① 载入定义并复核静态校验（`WF_DEFINITION_INVALID` 不建实例）；② 复核 `definition_digest` 与当前文件字节一致（不一致即 `WF_SEMANTIC_DECISION`，出口「按当前内容重新确认」或「改回已确认版本」）；③ 按定义的 `inputs` 声明核实际取值（必填缺失、类型不符、`secret_ref` **只接受引用**、未声明输入一律拒）；④ 重核准备范围（见上条）；⑤ 目标预检（实例记录与快照目录都不存在，否则 `WF_TARGET_COLLISION`）；⑥ 锁内取写权并把意图写入 writer；⑦ 逐步推进 `write_snapshot`（**原字节**落 `.wf/workflow-runs/<id>/definition.md`）→ `write_run`（机制稿 §1.5 全字段，`terminal`/`ended_at` 为 null）→ `acquire_writer`（核 holder scope 指向该实例）→ `bind`（`object={kind:run}`，写 `instance_id` 与运行态）；⑧ 结案前逐条核**真实后置**（快照摘要等于确认摘要、实例记录可解析且无终态、holder scope 匹配、绑定指向该实例）。实例创建**只取得规划权限**：不代批准业务、不建任务、不推进 `cursor`。
  **重入**：同会话未结案的 `run.create` 意图按**原意图目标**续做；若定义字节已变则拒绝（`WF_SEMANTIC_DECISION`，快照不可重建）。已知限制：续做路径在 `creation` 文件已不存在时无法恢复「输入与步骤适用性」，当前以空值续做——登记为后续项（正常路径不受影响，因为首次创建已把 `inputs_digest` 固定进动作）。
  `locate` 只读返回 `{run, definition, cursor, step_results, task_map, sequence_changes, tasks[]}`；任务状态一律**查 task**、查不到标 `unknown`，实例记录读不出即 `WF_HISTORY_UNRESOLVED`。用例：`test_run_create.py`（10 例）、`test_run_locate.py`（4 例）、`repro/run-create-once.py`（双模；注入把快照写成非原字节 → 目标断言红）。
- **判断指引的载体：就地安放、不成层（2026-11-12 人裁，删除 `wf-judging`）**：曾把 v42 §4 的十条判断指引单独做成 `wf-judging` skill 随发行投放。人裁改为按**判据位点**分布：交付面/扩面/与用户限制冲突 → `wf-continue`「实施期要自己判的几件事」；blocking 关闭 → `wf-repair-loop` 0 节；报告有效性 → `wf-review-action`；影响面/规模/计划没覆盖的缺口/未核实 → `wf-finish`「收工前要自己判的四件事」；标准变更 → `wf-spec-update`。`wf help judgments` 的 `guidance` 从「指向 skill wf-judging」改为「哪条口径在哪」的指针表。
  **为什么删**：独立 skill 让「帮助你判断」变成「先去读一份理论再回来干活」——多一个加载决策点（25→24 个 skill）、6 处编号引用（4.1–4.10 一改全错）、一个漂移源；而且它天然诱导"产出 judgments 条目"的仪式化行为，正是 v42 反例里的病。本批还在该 skill 里加过一节「机制与指引怎么分」，那等于把这层又加深一次——同批删除。
  **载体规则（2026-11-12 起唯一口径）**：判断类指引写在用得上它的判据位点上；同一口径的**完整论述只写一处**，其余位置只留一句判断句 + 指针（指针可跨文件，**论述不跨文件复制**）。独立 skill 只允许承载「被多处需要且无法就近落位」的口径。
  **边界**：本批只改载体形态，不改任何判定、字段、门禁与原因码；`sampling` 的类别枚举在 `sampling.py` 里自带，不依赖该 skill。
- **任务目录名只保留 ASCII（2026-11-07 B8）**：`slugify` 先剔除非 ASCII 再规范化，目录名形如 `<id>-<ascii-slug>`；标题仍原样存 `task.title`。修掉真实 dogfood 里中文目录在转录中出现乱码的风险。用例：`repro/task-dir-ascii.py`。
- **信封缓存与状态短视图（2026-11-07 B7）**：成功命令会把「身份 + activation + instance_id + generation」写进 `.wf/.runtime/last-envelope.json`（该目录在安装器 gitignore 托管段内，不提交）；后续调用可用 `--envelope-last` 免重拼信封。`status --short` 只回 `{id,title,status,phase,complexity,tdd,check}`，避免整份 `task.json` 进上下文。用例：`repro/envelope-cache-and-short.py`。
- **任务目录规范文件集（2026-11-07 B6）**：规范文件只有 `task.json`/`prd.md`/`design.md`/`implement.md` 与 `review/round-N/review-<agent>.md`；`status` 在绑定时回 `facts.task.files {count, unexpected}`，把自建的"证据/协议"文件点名出来（只读，不阻断）。审查导入目录同步改为 `review/round-N/review-<agent>.md`（旧名 `review/review-round-N/<slot>.md` 仍可读）。用例：`repro/task-dir-canonical.py`。
- **证据输入命令化（2026-11-07 B5，针对 dogfood 的"僵硬"）**：`baseline-apply` 新增 `--files a,b,c --decision <批准文件> [--preview]`——提案（哪些文件/前像/内容摘要）由入口从工作树生成，人只看摘要批准（`object_digest` 绑定提案内容）；`task-knowledge` 新增 `--no-update` 简写；`wf.py help <命令>` 给出各写命令的输入结构与最小示例。配套纪律写进 `wf-continue`/`wf-finish`/`wf-bootstrap` 技能：可写的只有决定文件/`--review-notes`/`--changes`/基线提案，验证结果、门禁预览、提交清单与摘要一律由入口生成，不自建。用例：`repro/baseline-apply-generated.py`、`repro/help-covers-write-commands.py`。
- **审查读取范围：排除声明必须有内容覆盖（2026-11-07 审计 665 后补）**：`review.decide` 现在核 `excluded-scope` 是否覆盖凭据（`.env`/`id_rsa`/`.npmrc`…）、私密配置（`.codex/config.toml`…）、项目外路径（以 `..`/`/` 开头）、其他任务目录（`.wf/tasks/**`）；缺任一类 → `WF_REVIEW_INVALID` 并点名缺失类别，**拒绝时同时给三档出口**。审计结论：此前只核「非空」，写 `["node_modules/**"]` 即可通过——该承诺从未有机制兜底；**无法核的部分**是 reviewer 实际读了什么（无遥测），如实登记。用例：`repro/review-excluded-scope-covers.py`。
- **复杂度条件②③④已改为事实核对（2026-11-07 关闭 外部 8）**：`scope.py` 新增三支探针——②`contract_surface_condition`（`.wf/bin/**`、`.wf/lib/**`、`.wf/templates/**`、`.wf/workflows/**` 命中，或 `AGENTS.md` 含 `TRELLIS:START` 托管块）；③`acceptance_surface_condition`（`.wf/baseline.md`、`.wf/project-config.json` 命中，或再次批准时 acceptance id 集合变化）；④`expansion_condition`（再次批准时触碰面覆盖上一版批准面之外）。`_complexity_proposal` 汇总四项，任一 true/**unknown** 即提出 complex（证据取不到时按 unknown 处理，不静默放行）。口径：改 spec 正文属知识更新，**不**自动算③（设计稿 §4.3 说的是「变化」不是「触碰」）。用例同上。
- **`cmd_enable` 的「人确认已停用」分支已接通（2026-11-06 关闭 外部 9）**：新增输入 `trellis_disabled_confirmed`——未声明时仍按 `WF_SEMANTIC_DECISION` 拒绝（不擅自放行）；人显式声明后放行，并把 `trellis_files_present_but_disabled_confirmed` 写进 `warnings`、`facts.trellis_disabled_confirmed=true` 留痕。用例：`repro/enable-disabled-branch.py`（注入=停用分支不可达时，声明后仍被拒 → 判红）。仍未做：`trellis_loaded` 与 `trellis_disabled_confirmed` 同时给出时的优先级（当前按冲突处理，先报 `WF_FLOW_CONFLICT`）。
- **巡检整数倍只算不触发（外部 10，**2026-11-12 已交付**）**：`inspect` 会算 `inspection.due`，但归档成功后不提示；设计稿 §5.4 的周期触发退化为「人恰好去看 inspect」。现在 `cmd_archive` 尾部的 `inspection_hint` **复用同一判定**（`_governance_summary` 的 `inspection`），删掉了原先硬编码的 `every = 10` 与「数全部归档（含异常与坏记录）」的第二份算法——两份算法必然漂移成「提示说到点、巡检说没到」。
  **同时修正一处过度压制（本轮发现）**：原先 `inspection.due` 在**任意** `unknown` 非空时都被压成 `null`，而 `unknown` 里混着知识回收窗口的「样本不足 / 路径失联」——于是年轻项目的巡检永远不到点，与机制稿 §8.5「正常归档累计达整数倍即触发」相反。现在只由**让计数不可信**的因素压制：归档记录不完整（`status`/`terminal`/`archived_at` 不合）与 `inspection_every_tasks` 非法。用例：`scripts/tests/wf_runtime/test_inspection_hint.py`（`every=2` + 2 正常 + 3 异常 → 到点；仅异常 → 不到点；键非法 → `unknown`）与既有 `r76`/`r77`。
- **`task-check` 的验证执行已移出 OS 锁（2026-11-06 登记，**2026-11-12 交付**）**：`cmd_task_check` 的锁内临界区原本覆盖 `run_check` 全程，其中步骤③用 `subprocess.run` 执行人的验证命令——验证命令有多长，互斥窗口就有多长（与机制稿 §4.1「长操作不长期持 OS 锁」冲突）。现在拆三段：
  ① **锁内准备**（`check.run_check_scope`）：范围核对、知识兜底、`resolve_verifications`、锚点与扫描快照固定——只读文件与记录，不执行任何外部命令；
  ② **锁外执行**（`check.run_check_execute`）：逐条跑已批准的验证命令并取证，不判 pass、不写记录；
  ③ **锁内定稿**（`check.run_check_finish`）：重取锁后**重核 holder 与代次**，**重算锚点**（与准备段不等即 `WF_CHECK_STALE`，facts 并列 before/after），再走既有的「结束前重算范围核对」与「扫描前后比对」，最后组装记录、写 `check_history` 与回执、结案动作。
  **不新增判定字段**（口径 A）：锁外窗口的对象稳定性由**既有**两处事实保证——回锁后重算的 `check_anchor`，与 `run_check_finish` 里本来就有的 `scan_after != scan_before → WF_CHECK_STALE`。因此没有把 `writer.checkpoint` 升格为「对象稳定性判据」，也不给 `writer.json` 加摘要字段（那需要先回机制稿 §1.4 登记）；代价是「锁外期间对象被改」会让本次 Check 白跑一次（语义正确，只是浪费）。
  保留的缓解仍在：`verification_timeout_seconds` 给单条命令加上界。用例：`scripts/tests/wf_runtime/test_check_lock_window.py`（3 例：执行段期间别的会话能取到项目锁、锁外期间内容变化被既有比对挡住、`cmd_task_check` 的两段锁与调用顺序）；既有 28 个套件的 `task-check` 覆盖全绿。
- **spec 三段索引已交付（2026-11-06 关闭 第二十五轮复审外部 5）**：两份 checklist 模板新增固定段 `## spec 指针`（含维护说明），`spec.py` 增加 `_sync_checklists`/`_sync_all`：`spec-update` 的 add/rename/delete **同批**更新 `index.md` 与两份 checklist 的指针行（改名同时重写标签与路径，删除移除该行）。用例：`repro/spec-three-part-index.py`（三段逐一断言；注入=只同步索引表则两份 checklist 缺条目，判红）。仍未做：`checklist` 里的**条目语义**（指针只是定位，具体检查项仍由人/纪律维护）；指针区不做「有效性核验」（指向不存在文件时不主动报错）。
- **`spec` 在身份不可核时整体阻断（外部 6）**：机制稿写的是「只读、不给完整读取回执」，实现走 `WF_IDENTITY_UNRESOLVED` 整体拒绝，方向更保守、无安全风险但严于字面；登记在此，避免被读成已按契约实现。
- **引导层无 Python 版本自检（外部 7）**：`python_min` 只在 `confirm-executor` 探测候选时核；系统 `python3` 存在但过旧时引导层可启动，移交语义层后可能直接 `SyntaxError`（用户看到崩溃而非三要素输出）。设计稿 §1.1 只给了「不存在」的出口。承接：引导层启动即核版本。
- **spec 索引三段同步（2026-11-06 交付，关闭 第八轮复审条目）**：同上，`_sync_all` 现在是三段同批更新的唯一入口；`r7r15` 的 R9 断言随之改为按**路径**计数（条目格式变为 `- [新文件名](新路径)`，文本里文件名会出现两次）。
- **`stop` 的只读预览已交付（2026-11-06 关闭 第八轮复审条目）**：`stop --decision <f> --preview` 返回`facts.buckets`（逐路径归属分类）、`facts.uncommitted` 与「预览只读；本次未写入任何记录」，**不写任何记录**；人看过预览后再去掉 `--preview` 执行。用例：`repro/stop-preview-readonly.py`（注入=预览落到执行分支 → 记录被改写，判红）。仍未做：预览不预估「提交后会剩下什么」（需要 commit 预演），以及不覆盖 `task-abandon` 的预览（后者已有 `--disposition` 预览形态）。
- **其余低优先观察（2026-11-05 第八轮复审，仅记录）**：①Check 锚点无条件纳入 baseline/project-config，失效面比契约宽（方向保守，表现为偶发 `CHECK_STALE`）；②`cmd_enable` 的托管块落点不分宿主，一律走 `WF_SEMANTIC_DECISION`，比设计稿 §3 的分级弱一档；③纯工作树删除的交付需先 `stop --choice commit` 才能过 Check（可达但绕）；④手动 `writer release` 对 paused+keep 任务要求先处置，比设计稿 §4.4 的字面更严（实际正确，未写明理由）；⑤`writer.blocking_receipts` 是运行期死代码（仅测试引用）；⑥`staging_root` 缺项目配置时退化为 `unknown-project` 前缀；⑦`_sync_index` 用子串匹配删除索引行，极端文件名可能误删相邻条目。
- **若干一致性偏差（低，逐项给处置与出口）**：
  ①**Decision 取值域统一登记（2026-11-12 已交付）**：原先 `Approval`/finish/external-checked/收工四值/提交授权/`debug-ruling`/验收结论七处各写字面量。现在唯一登记处是 `wflib/decisions.py::DOMAINS`（9 个操作：`plan_approval`/`mechanical_revision`/`replan`/`archive_finish`/`stop_choice`/`commit_grant`/`external_checked`/`debug_ruling`/`acceptance_conclusion`），调用点一律 `decisions.accepts/canonical`；**未登记的同义词被拒**（`WF_SEMANTIC_DECISION`），新增写法须回本节同批登记，不得在调用点就地放宽。机制稿 §1.1 仍只定 `Decision` 结构，取值域语义归本节。用例：`scripts/tests/wf_runtime/test_decision_domains.py`。
  ②**执行器确认元组比对 `python_version`（2026-11-06 已关闭）**：`executor_ready` 现在同时比对登记版本与探测版本，版本不符即 `WF_EXECUTOR_UNCONFIRMED`；用例 `repro/executor-version-change.py`（双模可证伪）。原出口「人工重跑 confirm-executor」保留为处置方式。
  ③**`project_key_approved` 覆盖归档区（2026-11-06 关闭；2026-11-12 语义级键值解析已交付）**：扫描范围扩为活动任务 + `.wf/tasks/archive/**`，归档任务的 PRD 只要其摘要仍等于批准摘要即作为证据；用例 `repro/project-key-archived-evidence.py`（双模可证伪）。**语义级解析**由 `bin/wf.py::declared_values(text, key)` 承担：逐行要求「键 + 分隔符 + 值」成对（`key = v` / `key: v` / `"key": "v"`），键前必须是分隔符或行首（避免 `my_python_executable` 误命中），值精确比对；不再用「键与取值各自出现」的文本包含。用例：`scripts/tests/wf_runtime/test_project_key_semantic.py`（含「键值分处两行」的缺陷形态）+ 既有两条 repro 双模仍绿。
  ④**`_apply_debug_inputs` 幂等键（2026-11-12 已交付）**：原先同一决定文件重入会重复累计 `counted`。现在 `_debug_idempotency_key()` 以结构化字段作键（声明＝`verification_id`+`counted`+排序后的 `evidence_refs`+`dedupe_refs`；裁定＝`subject`+`choice`+`evidence_refs`），同键即跳过，**不新增任何字段**；把同一事实换一句话重写仍会新增一条（那是第二次声明，须由 `dedupe_refs`/裁定处置）。用例：`scripts/tests/wf_runtime/test_debug_declaration_idempotent.py`。
  ⑤**spec 预算降级链路不可达**：单文件读取恒 `complete=true`，规范里的「缩小策展→退索引→汇总」「截断条目标记」没有运行点；方向安全（必需正文不被截断），出口是「需要时按设计稿 §6.2 人工选择策展范围」；承接位置：第三轮或按 charter T5 改判规范文本。
  ⑥**start 期验证证据入 action（2026-11-12 已交付）**：`consume_at=start` 的验证结果并入 `action.inputs["start_verifications"]`，并在**结案前按真实后置重核**——缺证据即 `WF_ACTION_INCOMPLETE`（把步骤标 done 不能代替证据）。这样「开工时那条验证真的跑过」在归档/复盘时可核对，不再只打印一次就消失。用例：`scripts/tests/wf_runtime/test_start_verification_action.py`（5 例，含「标 done 但无证据」）。
「写入目标类别」由 `paths.write_target_allowed()` 单一实现：`baseline-apply` 与 `spec-update` 都走它，控制记录一律拒绝，不在入口处各写前缀判据。

- **`repair` / `uninstall` 的令牌闸门没有 TTY 校验，与 `confirm-executor` 口径不一致（2026-11-06 查证，待裁）**：`wf.py::cmd_confirm_executor` 明确拒绝非 TTY（「不接受管道、脚本或代填」），而 `repair.py`/`uninstall.py` 的 `--apply` 路径只 `sys.stdin.readline()` 取令牌，`--nonce` 又允许调用方自定令牌（`repair.py:380`、`uninstall.py:405` 把 `args.nonce` 传给 `Token.issue`），因此**脚本可以完整走完预览→应用**。机制稿 §10.3 把「交互终端确认与令牌输入」列为人的动作、设计稿 §1.5 声明普通文件不防伪，所以这不是安全边界破损；但同一发行里两个入口按「拒绝代填」、两个入口不拒，属口径不一致，须由人裁定是统一为 `isatty` 还是把机制稿 §10.3 收窄为过程约束并在此登记。本批未改行为，只登记事实；`repro/repair-controlled-apply.py` 断言的是**存活事实不可被人工确认替代**（旧写者仍存活时零写入）。

- **运行时死代码（2026-11-06 查证；2026-11-12 追加一处）**：三处函数只有测试引用、运行期零消费——① `lock.verify_holder`（`lock.py:215`）：无任何调用方，见本节「`lock.verify_holder` 无运行时消费」条；② `writer.blocking_receipts`（`writer.py:307`）：仅 `r59_tests.py` 单测引用；运行期的 `WF_WIP_UNRESOLVED` 实际由 `tasks.py:1681`（`_block_overlapping_maintenance`）与 `tasks.py:937`（`changes_persisted_fact`）产生；③ `config.project_python_key`（`config.py`）：**零调用方**，项目键的批准核对实际在引导层 `bin/wf.py::project_key_approved`。三者都属清理或「接实」的维护项，不影响运行期行为；在清理前，任何文档/skill 不得把「`project_python_key` 在运行期核项目键」当作已生效事实。

### 2.4 输出契约

所有子命令返回机制稿 §11.1 的单一结构（字段名与语义以该节为准，本文不重述，只列名称供实现对齐）：`{tier, code, object, position, next, facts, exit, prohibited_repairs, warnings}`：

- `--json` 打印该结构的规范 JSON（`C(x)` 规则，机制稿 §1.1），供脚本与审查核对；默认输出由 `wflib/cli.py::render()` 渲染为人读文本，**两路同源**，不各造字段。`spec` 的正文两路都交付（`facts.content`），因为读取留痕记「完整读取」就必须真的交出正文。
- `exit` 是出口描述；进程退出码只作传输：`0` = `pass`，`1` = `blocked`，`2` = `needs_decision`，`70` = 实现内部错误（不用于业务判定）。退出码不新增判定档位：判定一律读 `tier`/`code`。
- `issues` 有序：先权限/结构问题，相关判断停止、无关只读诊断继续（机制稿 §11.1）。
- 输出不含秘密；`facts` 只列对象标识、路径、缺失项与决定性事实。
- 阻断类输出必须带 `prohibited_repairs`（机制稿 §11.1 的「禁止的错误修复」列）。

### 2.5 命令面纪律

- 一个子命令只调用一个固定处理器或一个父 action；跨多个对象的动作由父 action 的 `steps`/`next_step` 承载（机制稿 §5.1）。
- 只读子命令不写判定字段，只在例外允许处写本会话侧车（机制稿 §2.1、§8.3）。
- 交互终端确认与令牌输入只在 `upgrade --apply`、`repair`、`uninstall --purge` 三个入口出现，模型不代跑（机制稿 §10.3）。
- 子命令的帮助文本只写参数与出口，不复制门禁条文（避免第二套规则源）。

## 3. 命令引导与执行器解析

### 3.1 目标定位

| 场景 | 调用形态 | 目标判定 | 失败 |
|---|---|---|---|
| installed（已安装） | `<python> /abs/path/<项目>/.wf/bin/wf.py <子命令>`（任意 cwd） | 由脚本真实位置解析项目根并核对 `.wf/bin` 布局 | 布局/目标无法确认 → `WF_CAPABILITY_UNAVAILABLE` |
| 项目根内短称 | `<python> .wf/bin/wf.py <子命令>` | 同上（不依赖 cwd 选择项目） | 同上 |
| 源码/重取入口 | `<python> <重取路径>/wf.py --project <目标绝对路径> <子命令>` | 只接受显式绝对路径；不把源码目录或 cwd 当目标 | 缺 `--project` → `WF_PATH_INVALID` |

不做 PATH 安装、不做 shell shim（设计稿 §1.1）。引导层不判断业务门禁；判定全部在语义层（机制稿 §3、§11）。

### 3.2 执行器解析

顺序固定（机制稿 §8.2）：项目配置键 → `~/.wf/config.json` 全局键 → 系统 `python3`，按「已设置」选唯一候选。

- 全局键只接受绝对路径；项目键接受绝对路径或相对项目根且不以 `..` 越出项目根的路径；两者都不做变量展开、不接管道或 shell 片段；空串是非法配置，不回退。
- 解析取候选存在/可执行/`path_identity`/`size`/`mtime_ns`，与 `~/.wf/interpreters.json` 的完整元组集合精确匹配（字段名以机制稿 §8.2 的确认集合定义为准，本文不复述语义）。
- 未匹配或元组失配 → `WF_EXECUTOR_UNCONFIRMED`，出口提示人执行 `confirm-executor`。日常解析不自行探测版本（版本只用于展示与核对）。
- 已设置的项目键失效不得向下回退到全局/系统；系统 `python3` 不存在且两级键未设置时，出口是人把已核实可用的绝对路径配置到已有全局键后重入（不新增第四档回退）。
- `confirm-executor` 由引导解释器拉起，人在终端执行，启动候选取 `--version`、核 Python 3 与最低小版本（3.11），写入新元组；不写项目数据、不进项目锁、不覆盖其他 clone 的条目。模型不写、不代填。

### 3.3 独立恢复入口的启动例外

`.wf/bin/repair.py` 与 `.wf/bin/uninstall.py` 各自单文件、仅标准库、不导入 `wflib`，由系统或人显式选择的可用 Python 直接运行；该回退**只授权这两个入口**，不延伸到 `wf.py` 引导段之外的常规命令（设计稿 §1.1、机制稿 §10.5）。二者仍需最小互斥、人确认与预览令牌（`repair`、`uninstall --purge`），`uninstall` 默认模式按其预览确认要求取得明确人决定。

### 3.4 标准库与离网边界

- 运行时不导入第三方包；`wflib` 的 import 只允许标准库与自身模块；不联网、不调用 MCP、不读写项目外路径（审查暂存目录与 `~/.wf/` 是登记过的例外）。
- 需要 git 事实时只用**只读查询**，且不改变仓库状态（charter T3 B1、设计稿 §1.1 分支边界）。可用的查询类别（示例而非穷举；判定只要求「只读、不改状态、不写引用」）：
  - 解析与可达性：`rev-parse`、`rev-list`、`merge-base --is-ancestor`；
  - 提交内容与归属：`log --format=%B <range> -- <path>`（读 `wf-task:` trailer）、`cat-file -p`、`show --stat`；
  - 树与差异：`diff --name-status`、`diff-tree -r`、`ls-tree -r`（机制稿 §4.5 的「拓扑逆序逐个核对完整树状态」用这组）；
  - 忽略判定：`check-ignore -v`。
  禁止的限于**分支状态变更与历史改写**：`checkout`/`switch`/`branch`/`merge`/`rebase`/`worktree`/`reset`/`push`（charter T3 B1）。**授权范围内的暂存与提交不属于本条限制**：只在拿到「本次提交 + 精确路径」的授权后执行 `git add -- <path…>` 与 `git commit`，且不得捎带授权外路径（机制稿 §5.3）；`git init` 与首个 HEAD 同属另行授权的初始化动作（设计稿 §7.1）。
- 最低 Python 3.11（机制稿 §1.1 与 §10.2 的 `python_min` 是同一事实）。

## 4. 发行物组装

### 4.1 版本与发行引用

- 专用发行引用：`refs/tags/wf-v<major>.<minor>.<patch>`；正式发布前保持 `0.x.y`（机制稿 §10.2、`.trellis/spec/docs/index.md` 的预发布版本约束）。
- 解析链：人给的 tag → 本地已检出仓库解析为 commit → 读该提交根的 `wf-release.json` → 核 `version` 与 tag 一致、每源路径在发行根内、资产哈希一致。裸 SHA、未登记引用、同版异内容一律拒绝（`WF_RELEASE_CONFLICT`）。
- 同版本不可变：同一 `version` 已见不同 commit 或不同清单即冲突；首次无既往观察时只核当前身份一致，不声称远端不可移动。

### 4.1.1 安装与升级的完整语法

安装发生在目标项目还没有 `.wf/bin/` 的时候，因此用发行根的单文件入口；升级走已安装的引导脚本。两者都要求人给出确切的发行引用与本地已检出的发行目录（机制稿 §10.2 不在远端解析）：

```
python3 install.py --target <目标项目绝对路径> --release-ref <refs/tags/wf-vX.Y.Z> \
    --source <已检出的发行目录> --platform <平台> [--platform <另一个平台>] [--confirm]

<python> <目标>/.wf/bin/wf.py upgrade --apply --release-ref <refs/tags/wf-vX.Y.Z> \
    --source <已检出的发行目录> [--platform <平台>]
```

`--target` 必填且为绝对路径（不把源码目录或 cwd 当目标）；`--release-ref` 只接受已登记发行引用，解析到 commit 后核 `wf-release.json` 与资产哈希；应用阶段把该清单**原样写入** `.wf/install/release-manifest.json`，再与 `installation.json.manifest_digest` 比对（不一致即 `WF_PERSISTENCE_FAILED`）；`--platform` 至少一项，三种写法等价：`--platform a --platform b`、`--platform a b`、`--platform a,b`（别名 `claude`/`gemini`/`ghcopilot`）；技能目录由平台表解析到目标项目内，未知名直接拒绝并列支持项；升级省略时用安装记录里已确认的平台；运行时信封的 `host_id` 必须属于 `installation.platforms`，否则 `WF_IDENTITY_UNRESOLVED`（R93 起没有 `--host-id`、`--capability-evidence` 与 `session_profile`）；`--confirm` 表示人在终端确认预览（缺省时入口先出预览并要求交互确认）。升级不需要信封（维护入口，见本文 §2.2）。

### 4.2 `wf-release.json` 键表

| 键 | 值来源/生成 | 消费 |
|---|---|---|
| `schema_version` | 固定 `1` | 清单解释版本 |
| `version` | 人定版本（`0.x.y`），与 tag 一致 | 可发现标识；不参与兼容判断 |
| `delivery_round` | 打包脚本取 `gates.CURRENT_DELIVERY_ROUND`（当前 1）；不进入 `rules_digest` | 安装自检判定「当前交付集内步骤的命令不得是能力桩」；缺失/非法即拒绝启用 |
| `compatibility.python_min` | `{major: 3, minor: 11}` | 执行器确认与自检 |
| `compatibility.systems` | `["linux"]` | 锁能力与安装声明 |
| `compatibility.filesystems` | `{local_only: true, advisory_flock_required: true, network_or_sync_supported: false}` | 装前能力核实 |
| `compatibility.record_versions` | `{task, binding, preparation, run, writer, installation, config, spec}` 各 `{read: [1], write: 1}` | 记录兼容 |
| `compatibility.workflow_versions` | `{read: [1], write: 1}` | 用户定义格式 |
| `compatibility.rules_digest` | 由 `compute_rules_digest()` 计算（本文 §4.3） | `effective_rule_version` |
| `assets` | 打包脚本生成：`source_path`、`target_class`、`target_relative`、`kind`、`required`、`file_kind`、`executable`、`digest` | 安装/升级/自检/卸载 |
| `required_steps` | 由流程文档的 `[required · once\|repeatable]` 标记与固定 id 集合双向核对生成，每项含 `delivery_round`（机制稿 §11.2） | 门禁与自检；该字段进入 `rules_digest` |
| `template_markers` | `formats`（`required-field`/`{{WF_REQUIRED:<field>}}`、`required-value`/`__WF_REQUIRED__`）与 `uses`（`template_path`/`selector`/`format_id`/`required`） | 模板校验 |
| `gitignore_managed` | `{begin_marker, end_marker, lines}`（本文 §4.5） | 托管段处理 |

`target_class` 首版取三值：`skill_root`（投放根，`target_relative` 为 `<skill 名>/SKILL.md`）、`project_wf`（`target_relative` 为 `.wf/...`）、`release_only`（随发行交付但不投放目标项目、不参与卸载，只为发行身份与规则摘要的计算而登记——`source_path` 指向发行树内的文件，`target_relative` 为 null，`digest` 照算）。`install.py` 属 `release_only`：它执行安装判定，必须进 `rules_digest`，否则安装逻辑变更而摘要不变。`release_only` 路径不进入目标项目的 O/L/N 比较、不产生投放或卸载目标；每次安装/升级只按发行树内的字节重算哈希并与清单比对。`.gitignore` 托管段不是 `assets` 成员，按 `gitignore_managed` 处理（机制稿 §10.1 落点表单列）。清单不写自身 SHA、不写 `rules_digest` 自身、不复制 skill description（机制稿 §10.2）。

### 4.2.1 运行期清单的持久落点与唯一读取入口

机制稿 §11.2 的 `required_steps` 是「应执行步骤的唯一机读来源」，而发行源码在安装完成后可按授权清理（设计稿 §7.1）。因此完整清单必须随安装落到目标项目：

- **落点**：`.wf/install/release-manifest.json`——本次投放所选发行的 `wf-release.json` 原样副本（不重排、不裁剪，保留 `assets`/`required_steps`/`template_markers`/`gitignore_managed`/`compatibility`）。它属「本机投放事实」区，升级时被新清单覆盖、默认卸载保留、`purge` 时随 `.wf/` 删除。
- **一致性**：`installation.json.manifest_digest` 记录该副本的字节摘要；两者不符、副本缺失或不可解析 → `WF_ASSET_DECISION`（需人裁决：重新安装或 repair 重建依据），不按代码常量或流程 Markdown 重新拼装清单。
- **唯一读取入口**：`wflib/assets.py::load_installed_manifest()`。`required_steps`、兼容声明、模板使用位点与 `rules_digest` 的输入全部取自该副本；`effective_rule_version` 再用它加实际投放文件计算（机制稿 §10.2）。发行源码是否还在本机不影响运行期判定，`release_only` 资产的校验以该副本登记的 digest 为准。
- 首轮开发态部署同样写这份副本（来源为 `dev-manifest.json`），使首轮与正式安装在读取路径上没有分叉（本文 §4.6）。

### 4.3 `rules_digest` 与 `effective_rule_version` 的落点

公式、逐键输入与排序唯一见机制稿 §10.2 与 §1.1，本文不重列（重列即第二定义源）：

| 计算 | 实现落点 | 引用 | 用途 |
|---|---|---|---|
| `rules_digest` | `wflib/assets.py::compute_rules_digest(manifest)` | 机制稿 §10.2 的 `wf-rules-v1` 域与其输入键 | 规则字节标识 |
| `effective_rule_version` | `wflib/assets.py::effective_rule_version(rules_digest, installed_assets)` | 机制稿 §10.2 的 `wf-effective-rules-v1` 域与机制稿 §1.1 的 `installed_assets` 排序 | 规则类回执的 `rule_version`、`check.anchor.rule_version` |

本文不新增哈希域。任何新域须先在机制稿 §1.1 登记逐键定义；`wf-review` 报告的 `check-anchor` 复用机制稿 §3.2 的键集合与计算，不另立公式。

### 4.4 打包步骤（人执行提交与 tag）

1. 人在 authoring 仓库同步版本（源树 `dev-manifest.json` 与说明文档的版本行同批改）。
2. 运行 `scripts/build-wf-release.py --version <0.x.y>`：校验源树完整性 → 生成 `wf-release/` 与 `wf-release.json`（含 `rules_digest`）→ 输出差异摘要与哈希清单。
3. 人复核差异，按授权暂存精确路径并提交；人创建 `refs/tags/wf-v<0.x.y>`。
4. 安装器只接受该 tag；打包脚本不做提交、不做 tag、不推送。

打包产物是「可重建但不手改」的产物：源树与 `wf-release/` 不一致时自检报错（不静默以新源覆盖旧发行）。

### 4.5 `.gitignore` 托管段

首版段内容（顺序固定，逐行为精确忽略）：

```
# wf-managed-v1
/.wf/.runtime/
/.wf-lock
# wf-managed-end
```

- 安装/升级：按 `begin_marker`/`end_marker` 定位整段；不存在则追加到文件末尾；存在则比对段内容（与 `gitignore_managed.lines` 不符按偏离处理并由人裁决），重复运行不重复追加。
- 卸载：移除整段，并把 `/.wf-lock` 行以**不带标记串的裸行**留在原位置；安装/升级/卸载核对时对段外严格等于 `/.wf-lock` 的行容忍、不重复追加，直到人手工清理锁文件时一并移除。
- 自检：段内每条路径都用只读忽略判定确认实际生效；被后续否定规则遮住时报告命中的否定规则与位置并拒绝启用，不以标记存在代替（机制稿 §10.4）。
- 段外内容属用户；框架不整文件重写、不复制覆盖。

### 4.5.1 预览令牌的实现约定（repair / uninstall 自含）

机制稿 §10.3 已定令牌语义；本文只定两个独立入口各自实现一份时的形状，避免两份实现漂移：

- nonce 取 128 位随机（`secrets.token_hex(16)`），显示为十六进制；校验对象是该次预览对象的规范 JSON 摘要（`sha256:` + 64 hex）。
- 令牌只在同一交互进程内有效：重新预览即销毁旧 nonce，进程退出后必须重新预览；不写任何持久记录、不作跨会话凭据。
- `repair.py` 与 `uninstall.py` 各实现一份（设计稿 §1.1 要求这两个入口单文件且不导入框架运行时，因此不能共享 `wflib` 模块）；两份的生成、比对、失效行为必须一致，由 **authoring 发布前检查** `scripts/build-wf-release.py --verify-token-parity` 比对（不属于安装期自检，也不是运行期能力）：脚本用显式注入的 `--nonce`（仅测试形态，运行路径不使用）对同一预览对象分别跑两份实现，比对「nonce → 预览摘要 → 校验结果 → 失效后再次校验」四步输出，不一致即拒绝打包。
- `repair.py --dispose`（维护组处置回写）与 `--apply` 走同一套预览与令牌：先只读预览目标回执、当前写权状态与将写入的 `disposition`，再由人在同一终端输入令牌；回写只改该回执的 `disposition` 字段，不动 `holder`/`generation`/资产，互斥由同一最小锁保证，因此不要求写权空闲（2026-11-03 人裁落地，实测见任务记录 `validation.md` §17）。
- 第三轮的 `upgrade --apply` 用 `wflib/maintenance.py::preview/token_confirm` 实现同一规则，算法仍是这一份说明，不另立格式。

### 4.6 首轮开发态部署

首轮同时存在两条安装路径：**开发态** `wf-dev-deploy.py`（authoring 工具，不进发行清单）与**发行入口** `install.py`（首轮已交付，按发行引用安装；运行期升级侧的 `assets.parse_release` 仍属第三轮）。按设计稿 §8.1 的「首轮所需最小安装与自检按开发态部署处理」，首轮的日常最小闭环用开发态部署；`install.py` 提供从发行树的真实首装，f0 夹具即经它构造：

- 入口：`python3 scripts/wf-dev-deploy.py --target <目标项目绝对路径> --platform <平台> [--platform <另一个平台>] [--confirm]`（authoring 开发工具）；`--platform` 可重复、至少一项，解析出的项目内技能目录写入 `installation.json.roots`（一律相对路径）并把平台名写入 `installation.json.platforms`；不带 `--confirm` 时只打印预览（目标、文件清单、`.wf/`/`writer.json`/`.wf-lock`、托管段、skill 根、Trellis 资产风险提示）后退出，不做任何写入；带 `--confirm` 才按 `dev-manifest.json` 投放 `.wf/` 资产与 skill 根副本，写 `.wf/install/installation.json`（`release_ref` 记 `dev:<git describe>`，`version` 记 `0.0.0-dev`，`manifest_digest` 记部署清单摘要），并写入 `.gitignore` 托管段。`dev-manifest.json` 只登记资产清单、版本与必需标记，**不含手填字节哈希**；`wf-dev-deploy.py` 按源树实际字节现算每个资产的 `digest`、模板标记与 `rules_digest`，生成部署副本 `.wf/install/release-manifest.json`（与正式清单同 schema，运行期唯一读取入口，见本文 §4.2.1）——算法与 `scripts/build-wf-release.py` 同一份（同名函数），首轮锚点因此可复现。
- **Trellis 互斥风险提示**：预览固定列出已发现的 Trellis 线索（`.trellis/` 数据、hook 配置、项目指令文件中的 Trellis 托管块），并说明「人确认后可继续安装，但本会话不得混跑两套流程」（设计稿 §3、§7.1）。
- **维护组处置回写**：人确认维护组去向（独立提交 / 反向修正 / 具名承接 / 保留现状）后，由 `.wf/bin/repair.py --dispose <plan>` 写回原维护回执的 `disposition` 与真实路径状态。**解除条件只有上位规定的三条**：该组路径已被独立提交、已完成反向修正、或已由具名任务承接（承接任务已批准、路径归属明确）。**「保留现状」只留痕，不解禁**——回执仍按「已应用待提交」挡住重叠路径，直到其中一条实际落实。依据是设计稿 §5.5 的对象列举（「未收工关闭的写权、绑定/写权不明、**维护/交接残留**」）与机制稿 §4.5 的「入口将实际去向写回原回执」（该条未指定入口）；机制稿 §5.4 只有算法与边界句（repair 不代替日常删边、内容修改或范围批准），本条不越出该边界——处置回写只记录人已确认的去向，不改交付内容。三条之一落实并写回后，该回执在读取侧落「已处置」态：不再阻断重叠任务，但回执与处置证明保留，直到下一次维护预览按机制稿 §4.5 把它收敛出 `maintenance_results`；`disposition` 缺处置决定、缺核验事实或缺承接引用，或只记了「保留现状」时，仍按「已应用待提交 / 待核对」分别处理。**若人选择「按登记终态原样提交」则不需要这一步**：下一次启动按机制稿 §4.5 的可达提交查证直接派生 `persisted`，不改写回执。
  该查证由 `tasks.maintenance_persisted_probe()` 实现并**挂在唯一读取入口 `tasks.task_receipts()` 上**：以下界 `head_before` 找候选提交，要求该提交树里有 `.wf/writer.json`、其中同 `operation` 回执的 `changes` 路径集合与当前登记一致，**并按候选提交树逐项重建每个登记路径的完整指纹（存在/删除、类型、可执行位、内容摘要）与登记 `after` 比较**——看树终态，不要求与其他路径出现在同一次 diff；登记的 `after` 是历史纯摘要时只比摘要，是 `null` 时要求确实删除。回执登记侧由 `wf-dev-deploy.py` 写入完整指纹对象（机制稿 §1.4）。开工的重叠检查与 `inspect` 巡检都经这一入口，不再各自传 `probe=None`；读取本身不写 writer，回执 `result` 保持 `applied_pending_commit`。
  出口分工：重叠且仍待提交 → `WF_WIP_UNRESOLVED`（要人处置）；重叠且待核（回执不可解析、下界不可达、查证依据不足）→ `WF_HISTORY_UNRESOLVED`（只读核对），**待核不得被消费端静默忽略**。`pending_check` 的 facts 一并带 `paths`，门禁才能匹配。
- **首装契约（与正式安装同构）**：按设计稿 §4.4 的首装例外，dev-deploy 在同一最小互斥内先创建 `.wf-lock`、`.wf/` 与 `.wf/writer.json`（初始维护持有，`holder.kind=maintenance` 且带本次操作标识、`generation` 从 0 起递增），把这三项列入预览清单；投放与自检通过后释放为空闲（`state=idle`、`holder=null`），不保留伪会话写者。没有 `writer.json` 的项目不算已安装（机制稿 §4.2「缺 writer 或缺锁且有既有记录不视为首次安装」）。
- 自检：投放后核对资产哈希、skill 路由、`required_steps` 与已实现处理器的一致性、托管段忽略生效、`wf.py status` 可达；缺项按 `WF_CAPABILITY_UNAVAILABLE` 报告并保留维护检查点。
- 与正式发行的差异只在「身份来源」与「清单生成方式」；记录 schema、判定编码、命令面完全相同，避免首轮产物在第三轮被整体重写。

## 5. 审查适配

### 5.1 两副本与协议

| 副本 | 角色 | 关键约束（机制稿 §9.1） |
|---|---|---|
| `<skill 根>/wf-review` | reviewer 侧 | 只在给定暂存路径写报告；不写项目树、不改源码/控制字段、不提交；参数 `--task-id`、`--round`、`--reviewer-id`（= 槽位 id）、`--request <暂存>/request.json` 必备；`--review-focus` 由 wf 侧总提供，reviewer 侧按设计稿 §6.5 当作可选（缺省时按固定检查轴执行） |
| `<skill 根>/wf-review-action` | action 侧 | 读指定轮次报告并先汇总再决策；不代替主会话修改源码 |

**调用交接**：`review-launch` 为每个槽位在暂存目录写 `<staging>/request.json`（`task-id`、`round`、`reviewer-id`、`review-focus`、`check-anchor`、材料范围与排除项），并向终端打印一段**人可粘贴到 reviewer CLI 会话的 skill 调用文本**：

```
/wf-review --task-id <id> --round <N> --reviewer-id <slot> --review-focus <检查轴> --request <staging>/request.json
```

它不是 shell 命令：框架不安装名为 `wf-review` 的可执行入口，也不做 PATH 安装或 shell shim（本文 §2.1）；投放物只有 `<skill 根>/wf-review/SKILL.md`。宿主不能按文本调用 skill 时，由人在 reviewer CLI 中打开该 skill 并把 `<staging>/request.json` 作为唯一输入；skill 正文负责读取该文件与授权范围，报告写到 `<staging>/report.md`，不读项目树内的控制记录，导入由主会话完成（本文 §5.2）。

报告格式：Markdown 正文 + 唯一带协议标记的 JSON 块 `<!-- wf-review-report:v1 -->`，块内 `protocol` 取 `wf-review-v1`，字段按机制稿 §9.1 的 `task-id`/`round`/`reviewer-id`/`source-cli`/`review-time`/`review-focus`/`check-anchor`/`read-scope`/`excluded-scope`/`scope-exceptions`/`axes`/`findings`/`verdict`。不支持版本拒绝导入（`WF_REVIEW_INVALID`）。

**`--request` 属实现级增补（2026-11-05 人裁）**：设计稿 §6.5 的契约枚举只有 `--task-id`/`--round`/`--reviewer-id` 与暂存路径，`--review-focus` 明写"reviewer 侧可选"。本文在不改该枚举的前提下增加一个**输入载体**参数：把与本次审查有关的全部只读事实（锚点、材料范围、排除项）收进 `request.json`，避免 reviewer 侧再从项目树里自取控制记录。设计稿 §8.1 把"命令形态/脚本接口"委托给实现方案，故这属允许的实现级增补，不构成对设计稿 §6.5 契约的修改。

### 5.2 暂存目录与导入

- 发起时由 `review-launch` 输出确切暂存目录：每槽位一个 `<临时根>/wf-review/<project_id>/<task-id>/round-<N>/<slot>/`，并把全部槽位目录记入 `task.reviews.launches.temp_paths`。父目录不开放。槽位 id（`--slot`）与 reviewer 自报的 `--reviewer-id` 是同一字符串，暂存目录层名与报告文件名都用它。
- reviewer 写 `report.md`；主会话在**自己持有设计稿 §4.4 的写入权**时，重算当前锚点、核对元数据与槽位字段，再以同目录临时文件 + 原子发布写入 `<task-dir>/review/review-round-<N>/<slot>.md`（`<task-dir>` 是由稳定 id 解析出的**真实任务目录** `<task-id>-<slug>`，不是把 id 直接当目录名拼出来），读回哈希并更新 `reviews.imported`（机制稿 §9.2）。导入期间写权不转移。
- 暂存目录在导入成功且摘要/元数据核对后成为可清理项，由人确认后清理；未导入、冲突或恢复中的轮次默认保留。卸载/`purge` 清单只列残留位置，不授予删除权限。

### 5.3 自报身份与对象锚点

主会话交给 reviewer 的锚点：`check-anchor`（`check.id` + 机制稿 §3.2 定义的 `check_anchor`，含 Check 内容指纹、规划版本、相关 spec 与项目配置哈希、基线与定义快照哈希；逐键定义与计算只在该节，本文不重列）。导入前重算并与报告比对，不一致即该报告失效、按审查未通过处理（`WF_REVIEW_INVALID`），不导入为有效结论。

`source-cli` 是自报字段，只与人工声明核对，不是身份认证（设计稿 §1.5）。人数与差异按机制稿 §9.2：两个 reviewer CLI 彼此不同、且不在本次实施 CLI 集合中；只能凑一个时用同一 `review-launch`（`slots` 只列一项）发起，入口在 `launches` 记 `degraded: single-provider`；`review-decide` 按机制稿 §9.2 **拒绝输入、不产生 verdict**（人数不合格属输入不成立），facts 给出已导入报告与两个出口；复杂任务据此暂停或异常归档，不得据此判 pass。

### 5.4 首轮为何必须就绪

机制稿 §12.1 把 D25（身份声明与报告核对）、D26（读取/外发范围、报告写权与导入）、D31（副本投放/升级/卸载覆盖）定为**跨轮基础项**，理由是首轮的初始化任务或治理面命中任务可能即属复杂；复杂任务的正常归档要求对应当前对象的实际审查 pass（charter T4、设计稿 §6.5）。因此首轮若无成对适配，任何复杂任务都只能暂停或按机制稿 §6.4 异常归档，首轮闭环实际不可用。首轮因此交付：两副本投放 + `review-launch`/`review-import`/`review-decide` + 锚点核对；完整发行生命周期（三方升级、卸载覆盖的验收矩阵）留在第三轮。

## 6. 首轮最小闭环实现清单

### 6.1 轮次分界与「能力不可用」的表达

- 首轮 = 机制稿 §12.1 的全部「跨轮基础项」；第二轮 = D03、D07（返工/替换/建删边部分）、D11、D12、D13，以及两项延期子项：**D14 的 wf 自签发身份路径**、**D24 的巡检两类治理输出**（「需人工比对」清单与 `author` 复核顺序）；第三轮 = D22 的**运行期升级侧**清单解析（安装侧解析随 `install.py` 首轮交付）、**D24 的知识拒绝项 `.wf/out-of-scope/`**、D31 的完整发行生命周期（三方升级矩阵与卸载覆盖验收）、D09 的全部资产修复验收、D28 的升级/purge 令牌路径、D33 的落点表全部适用分支验收。（2026-11-05 人裁：`install.py` 的正式发行入口属**首轮已交付**，第三轮只剩 `upgrade --apply`、`uninstall --purge` 与上述验收矩阵，见本文 §6.4 与 D37。）（本段为分轮摘要；逐项归属以本文 §6.2 的 D 表与本文 §6.4 的单列为准，二者不一致时以后者为准。）
- **轮次串行门禁（设计稿 §8.2）**：第一轮未完成时（三夹具与五条最小验证的适用场景未达到各自预期结果——仅有失败记录不算完成，或依赖后续轮次的场景行未按设计稿 §8.1 的轮次归属登记为「等该轮交付」；审查链路既不可用也无不可用留痕；dogfood 未完成轻量闭环与一次中断恢复），第二轮的任何实现动作不得开始——`definition`/`run`/`dep`/`task-rework`/`task-replace` 继续返回 `WF_CAPABILITY_UNAVAILABLE`，不因「代码骨架已存在」提前解封；只允许文档、设计与计划活动。「人尚未安排 dogfood」不是豁免理由；要改这条门禁本身，须按设计稿 §0 的维护协议改判据并经独立复审。
- 未交付能力的命令**必须已存在且可调用**，行为为 `tier=blocked`、`code=WF_CAPABILITY_UNAVAILABLE`、`facts` 记未交付能力与所属轮次、`exit` 给「等该轮交付」或「改用已交付路径」。不存在的命令不得在文档与 skill 中宣称。

### 6.2 逐条落点（D01–D38）

| D | 义务 | 首轮落点（文件/函数/命令） | 轮次 | 验收场景行（设计稿 §8.2） |
|---|---|---|---|---|
| D01 | 任务 schema、状态/阶段、判定字段写者 | `wflib/records.py`（读取拒绝重复键/NaN、原子替换、未知字段保留）、`wflib/tasks.py::load_task/save_task`、`.wf/templates/task/task-record.json` | 跨轮 | `规划授权`、`未提交记录存在性` |
| D02 | skill/机制操作归属、只启用未绑定路由 | `<skill 根>/` 下 `wf-start`、`wf-continue`、`wf-finish`、`wf-bootstrap`、`wf-spec-update` 的 frontmatter 与正文路由、`wflib/cli.py::cmd_enable` | 跨轮 | `入口与基线子路由`、`会话固定绑定` |
| D03 | 准备定义/创建实例路由、静态与消费校验 | `wflib/runs.py::prepare/validate`（未交付：`WF_CAPABILITY_UNAVAILABLE`） | 第二轮 | `准备定义与自举`、`定义有界校验` |
| D04 | 批准触碰面、规划版本、复杂度/TDD（含治理面判定） | `wflib/tasks.py::cmd_task_approve`（规划版本由 `compute_plan_version` 计算）、`wflib/paths.py::touch_path_errors/validate_glob`、`wflib/scope.py::governance_condition` | 跨轮 | `规划授权`、`机读触碰面`、`复杂度分级一致性`、`TDD 开关` |
| D05 | 路径集合与内容指纹、检查有效性 | `wflib/fingerprint.py::items/content_digest/check_anchor`、`wflib/check.py::run_check` | 跨轮 | `同路径交替`、`指纹内容源`、`最终知识变更` |
| D06 | 未提交路径归属、外部变更与提交边界 | `wflib/scope.py::classify_candidates/attributed_paths`、`wflib/tasks.py::cmd_task_attribute` | 跨轮 | `机读触碰面`、`共存与重装`、`紧急变更边界` |
| D07 | 依赖建删边、返工/替换/放弃 | `wflib/tasks.py::cmd_task_abandon`（首轮仅机制稿 §6.4 的单任务路径）；`dependency.change`/`task.rework`/`task.replace` 未交付 | 第二轮（首轮异常退出走单任务放弃路径） | `异常归档边界`、`放弃改动处置`、`返工接续` |
| D08 | 跨任务目标碰撞预检、记录级幂等指纹 | `wflib/actions.py::action_id/targets_digest/new_action/pending/step_done/complete`；碰撞预检在各命令入口就地判定（`task-new`/`archive`/`task-abandon` 与 `spec` 的 `WF_TARGET_COLLISION`），**没有独立的 `preflight_collisions`/`begin`/`apply_steps`/`reenter` 函数** | 跨轮；第二轮加入全部依赖/实例目标 | `数据与恢复`、`受控修复` |
| D09 | repair 预览/确认/验证/留痕、关闭残留、历史锚点、不可解析记录 | **全部逻辑自含于 `.wf/bin/repair.py`**（预览、令牌、受控应用、回执、留痕；不导入 `wflib`，坏运行时下仍可达；首轮覆盖写权残留/绑定/锚点，资产修复第三轮）。`wflib/maintenance.py` 不承载 repair 的应用逻辑 | 跨轮+第三轮 | `受控修复`、`历史锚点不可达`、`所有权中断恢复` |
| D10 | 读未知字段保留、写回不丢未知字段 | `wflib/records.py::merge_unknown`（读写同源） | 跨轮 | `数据与恢复` |
| D11 | 工作流格式、准备/自举、动作与验证边界、固定快照及版本维护 | `wflib/runs.py::load_definition`（未交付） | 第二轮 | `定义与实例固定`、`验证分时解析` |
| D12 | 步骤人判/略过、动作消费、自动任务/边与幂等映射 | `wflib/runs.py::advance`（未交付） | 第二轮 | `人判与略过`、`顺序依赖授权` |
| D13 | 实例正常结束、批量异常终止、保留任务独立接续 | `wflib/runs.py::finish/terminate`（未交付） | 第二轮 | `实例正常与异常终态`、`实例放弃与保留` |
| D14 | 稳定会话身份、持久绑定、历史按需读取 | `wflib/session.py::session_key/check_profile/load_binding/save_binding`、`wflib/cli.py::cmd_bind`；自动身份：`cli.py::_establish_auto_session` + `identity_store.py` | 跨轮（身份判定与持久绑定 + **自动身份模式，2026-11-08 交付**；显式 wf 信封按设计拒绝，见机制稿 §1.4） | `会话固定绑定`、`压缩与新会话`、`无稳定会话身份`、`绑定历史按需读取` |
| D15 | 会话/维护写者、原子获取/释放、两段交接与旧代次失效 | `wflib/writer.py::acquire/release/handover_begin/handover_accept`、`wflib/lock.py` | 跨轮 | `单工作区串行写入`、`释放与显式交接`、`所有权中断恢复` |
| D16 | 同对象 WIP 收工/恢复限制 | `wflib/cli.py::cmd_stop`（WIP 处置在收工路径内，记录写入 `task.handoff.wip`） | 跨轮 | `日常收工`、`暂停插单恢复` |
| D17 | 项目配置类型/范围/缺省、自举骨架 | `wflib/config.py::load_project_config`、`.wf/templates/project-config.skeleton.json` | 跨轮 | `流程与配置`、`初始化自举` |
| D18 | spec 预算键、计数范围、数值缺省及降级 | `wflib/spec.py::load_spec` + `wflib/cli.py::cmd_spec`（码点计数、`超预算完整读取` 标注） | 跨轮基础项（单文件读取与不截断已交付）；多文件预算降级链与截断标记**由 2026-11-06 人裁延至第三轮**（见 `pending-decisions.md` §6，场景行 650/643 已移出首轮分母） | `spec 预算`、`读取留痕完整性` |
| D19 | 命令引导、installed/源码目标、坏配置独立恢复 | `.wf/bin/wf.py` 引导段、`.wf/bin/repair.py`、`.wf/bin/uninstall.py` | 跨轮 | `本地命令引导` |
| D20 | Python 三级解析、缺系统 Python 的已有配置出口 | 解析与确认都在引导层（`wf.py` 第 3 步 `confirm-executor` 写确认元组、第 4 步解析并匹配，唯一实现）；`wflib/config.py` 只读取解析结果与确认记录，不重复实现解析与匹配 | 跨轮 | `Python 执行器` |
| D21 | 执行器探测/确认、首次写入批准、项目标识匹配 | `wf.py` 引导层第 3 步的 `confirm-executor`（探测 + 写确认元组 + 解析时元组匹配，单一实现）、`project_id` 生成与 repair 重建；`wflib/config.py` 只读项目配置与确认记录用于展示/诊断，不做匹配判定 | 跨轮（**部分交付**：首次确认与项目键匹配已实现，`project_id` 由 `baseline-apply` 生成；确认集合负例已按 2026-11-06 人裁补齐 repro（`d21-executor-set-*`，见 `pending-decisions.md` §6）；`repair` 重建标识留第三轮）| `执行器配置可信`、`执行器确认绑定`、`确认记录身份`、`项目标识生命周期`、`执行器首次写入` |
| D22 | 发行引用与本地清单解析 | 安装侧由发行根 `install.py` 自含实现（`REF_RE`/`resolve_tag`/`rules_digest` 重算，首轮已交付）；运行时升级侧 `wflib/assets.py::parse_release` 仍是第三轮桩；`wflib/assets.py::load_installed_manifest` 读 `.wf/install/release-manifest.json`（运行期唯一入口，首轮即需要；来源为 `dev-manifest.json`） | 跨轮（安装侧已交付）+第三轮（运行期升级侧） | `发行身份` |
| D23 | spec 三时点加载、策展/读取侧车、排序/预算 | `wflib/spec.py::match/sort_key/record_read/load_spec`、`wflib/curation.py::active_entries/add/release`、`wflib/tasks.py::cmd_task_curate` | 跨轮基础项（首轮已接线） | `spec 正向积累`、`spec 跨任务复用`、`读取留痕完整性` |
| D24 | 本地 spec 全部变更、持久引用统计/治理 | `wflib/spec.py::apply_changes/curation_stats`、`wflib/tasks.py::cmd_spec_update`、`wflib/tasks.py::inspect`（治理面含归档终态、spec 复用回收候选、周期触发） | 跨轮基础项（首轮已接线）；**其中拒绝项延至第三轮、巡检两类治理输出延至第二轮**（2026-11-05 人裁，参见本文 §2.3.11） | `知识删除与依赖解除`、`策展引用统计`、`无 MCP 全流程` |
| D25 | 审查身份声明、报告核对及新鲜度 | `wflib/review.py::launch/import_report/decide`（锚点核对为 `decide` 内联 + `_current_anchor`）、`<skill 根>/wf-review` | 跨轮（首轮就绪） | `审查 CLI 身份确认`、`审查与正常完成（charter T4）` |
| D26 | 审查读取/外发范围、报告写权与导入 | `wflib/review.py::import_report`、`<skill 根>/wf-review-action` | 跨轮（首轮就绪） | `审查材料外发`、`审查读取范围`、`审查报告写权`、`审查回执锚定` |
| D27 | writer 公共字段与维护回执隔离、整文件提交 | **读取与派生首轮即落 `wflib/writer.py::receipt_state()`**（读 `.wf/writer.json` 的 `maintenance_results`，按机制稿 §4.5 把**每一项回执**派生为四态：**已持久化**（可达提交查证成立）/ **已应用待提交**（`applied_pending_commit`，未提交或提交失败但结果可核）/ **已处置**（`disposed`：**只有**满足设计稿 §4.4（维护变更持久化）与机制稿 §4.5 的三条之一才算——该组路径已被独立提交、已完成反向修正、或已由具名任务承接且承接任务已批准、路径归属明确；`disposition` 须同时记处置决定、核验事实与承接引用。**「保留现状」不在此列**：它只留痕（决定、风险、待处置项），回执仍按「已应用待提交」处理）/ **待核对**（事实不明或记录不可解析）。这里判的是回执 `result` 层面，与 `writer.state` 的 idle/held/recovering 不是同一枚举。消费口径：只有「已应用待提交」（含人选择「保留现状」的回执）且与本次请求对象/路径范围重叠时挡（`WF_WIP_UNRESOLVED`）；「已处置」不挡重叠任务，但回执保留、报告为「已处置未收敛」；「待核对」报 `WF_HISTORY_UNRESOLVED`。解除阻断看 `disposition` 的核验事实与承接引用是否成立，不看字段是否存在；把回执移出 `maintenance_results` 是下一次维护预览里的收敛动作，读取侧不做）；写入侧由 `repair.py` / `uninstall.py` 各自完成；`wflib/maintenance.py` 只承载第三轮 `upgrade` 的应用与回执收敛 | 跨轮 | `维护写者` |
| D28 | 预览令牌签发/校验 | 首轮：`repair.py` 与 `uninstall.py` 各自自含（nonce 生成、绑定预览摘要、同进程失效；规则见本文 §4.5.1，两处必须逐字一致，由发行自检用固定向量比对）。第三轮：`wflib/maintenance.py::preview/token_confirm` 服务 `upgrade --apply` | 跨轮+第三轮 | `判定物与原因码` |
| D29 | 固定原因码及输出三档 | `wflib/codes.py`（35 枚，只增不改义：首版 34 + `WF_TARGET_MISSING`）、`wflib/cli.py::emit/render` | 跨轮 | `判定物与原因码`、`固定流转程序化` |
| D30 | 模板占位标记集 | `.wf/templates/**` 内占位符、`wflib/templates.py::find_markers/find_value_markers`（批准/开工的唯一消费点）、`marker_uses/double_check`（清单双向核对）。（2026-11-05 人裁 A：删除无消费点的 `check_markers`，避免复审把死函数当成第二个判定入口） | 跨轮 | `判定物与原因码`、`规划授权` |
| D31 | 审查适配副本投放、三方升级和卸载覆盖 | 清单 `assets` 的 `wf-review`/`wf-review-action` 行、`wflib/assets.py::compare` | 跨轮（首轮投放）+第三轮 | `审查适配副本`、`资产落点` |
| D32 | 锁原语、落点、支持范围与存活探测 | `wflib/lock.py::acquire/LockHandle/LockBusy/LockUnavailable`（排他创建 + 标记校验）；存活探测由 `lock.verify_holder()`/`proc_start()` 实现：锁文件标记后追加 `holder pid=<pid> start=<启动时刻>` 行，探测读 `/proc` 判定同一进程；获取时刷新、释放时清除（见本文 §2.3.11） | 跨轮 | `互斥与锁生命周期`、`锁删除与人工清理`、`锁文件归属` |
| D33 | 资产类型/落点/所有者/升级卸载覆盖表 | 本文 §1.2；安装/卸载入口的路径来源 | 跨轮；第三轮验收全部适用分支 | `资产落点` |
| D34 | 最终门禁与正常/异常完成边界 | `wflib/gates.py::final_gate`、`wflib/tasks.py::cmd_archive` | 跨轮 | `审查与正常完成（charter T4）`、`异常归档边界`、`规划授权` |
| D35 | 每条门禁到验收场景的映射 | 本文 §7.2；`scripts/validate-wf-design.py` 的场景映射检查（机制稿侧） | 跨轮 | 全部场景行（映射面） |
| D36 | 每个固定 required 步骤的执行/检查面 | `.wf/workflows/*.md` 的 enforcement 行、`wflib/gates.py::HANDLERS`（id → 处理器）、`wflib/tasks.py::cmd_task_retrospect`（`task.retrospect` 状态动作；写 `task.retrospective` 与 `task.retrospective-done` 的 completed 回执） | 跨轮 | `固定流转程序化` |
| D37 | 最小安装/自检、完整安装/升级/退出 | `scripts/wf-dev-deploy.py`（开发态）、`payload/install.py`（**发行根首次安装入口，首轮已交付**：发行引用解析、清单与 `rules_digest` 重算、Trellis 线索预览、首装维护持有、托管段、投放后自检；`p5_f0` 实跑）、`.wf/bin/uninstall.py`（开发态退出）；`upgrade --apply`/`purge` 未交付 | 跨轮+第三轮（`install.py` 已计入首轮，见本文 §6.1） | `资产落点`、`Git 就绪`、`本地命令引导` |
| D38 | 机制/实现分工、使用速查与后续验证责任 | 本文 §0、本文 §8 | 跨轮 | `固定流转程序化`、`本地命令引导` |

### 6.3 首轮下限对齐（设计稿 §8.1）

| 下限项 | 首轮落点 | 覆盖方式 |
|---|---|---|
| 任务 schema | `wflib/records.py`、`wflib/tasks.py`、`templates/task/task-record.json` | 记录读写 + 未知字段保留 + 原子替换 |
| 写权与锁 | `wflib/lock.py`、`wflib/writer.py` | 原子获取/释放/交接 + 代次校验 + 存活线索 |
| 状态/门禁结构判定 | `wflib/tasks.py::cmd_task_replan/cmd_task_start`（动作名 `task.transition`）、`wflib/gates.py` | 状态迁移表 + `required_steps` 分派 |
| 内容指纹与检查有效性 | `wflib/fingerprint.py`、`wflib/check.py` | `check_anchor` 全键计算 + 锚点比对 |
| 开工与最终门禁 | `task-start`、`archive`/`wf-finish` | 开工核对序列 + 八项门禁 |
| 策展清单与读取留痕 | `wflib/curation.py`、`wflib/spec.py` | 持久策展 + 会话侧车 |
| 归档与终态 | `wflib/tasks.py::cmd_archive` | 目录移动 + 终态 + 提交后只读派生 |

### 6.4 第二轮与第三轮单列（未交付前只报告能力不可用）

| 轮次 | 条目 | 未交付时的行为 |
|---|---|---|
| 第二轮 | 定义准备与静态校验（**2026-11-12 已交付**）、实例创建与推进（**2026-11-12 已交付**）/暂停/终止、步骤人判与略过、自动建任务与顺序边（**建删边 `dep` 2026-11-12 已交付**）、返工/替换/建删边、挂起复评、**巡检的「需人工比对」清单与 `author` 复核顺序（D24 的两个治理输出）——2026-11-12 已交付**、**`.wf/out-of-scope/` 知识拒绝项（D24 的另一延期子项，2026-11-12 人裁 A 由第三轮提前到本轮并已交付）**（~~wf 自签发身份路径~~ **已于 2026-11-08 随自动身份模式交付，不属本轮**，见本节后「身份路径」段与机制稿 §1.4） | `definition`/`run`/`dep`/`task-rework`/`task-replace`/`task-reassess` 返回 `WF_CAPABILITY_UNAVAILABLE`，facts 记「第二轮交付」，exit 记「等第二轮」；已可用的单任务放弃路径照常走 `task-abandon`。**身份路径已交付（2026-11-08）**：`provider=wf` 由入口在执行边界上派生并自动签发 `issued_id`（附件承载 activation），显式 wf 信封按设计拒绝（`WF_IDENTITY_UNRESOLVED` + 两条出口）；解析不出执行边界的形态（无锚点宿主、容器逐命令、leader 先死）按 `WF_CAPABILITY_UNAVAILABLE` 阻断，不得由模型自行签发 id 绕过 |
| 第三轮 | 正式发行引用与清单解析（D22 的升级侧）、~~`.wf/out-of-scope/` 知识拒绝项~~（**2026-11-12 提前到第二轮并已交付**）、完整升级/卸载生命周期（D31，含三方升级矩阵与卸载覆盖验收）、`upgrade --apply` 与 `uninstall --purge` 的令牌路径（D28）、落点表全部适用分支验收（D33）、全部资产修复验收（D09） | `upgrade` 返回 `WF_CAPABILITY_UNAVAILABLE`；`repair` 只做写权/绑定/锚点最小恢复，资产缺失类修复杂交第三轮；`uninstall` 只做开发态退出（`--purge` 不可用）。**`install.py` 的首次安装不在此列**：它已在首轮交付并通过 `p5_f0` 实跑（2026-11-05 人裁） |

**首轮与复评触发的关系**：机制稿 §5.3、§5.4 要求每次归档持久化核实成功、以及每次启动校验通过后触发挂起复评。首轮不会出现挂起任务（挂起源于返工，属第二轮），因此这两处触发在首轮按**空挂起集合**处理：直接通过、不写记录、不产生待决项，也不得返回 `WF_CAPABILITY_UNAVAILABLE`（否则每次归档/启动都会留下无法补做的待复评）。`task-reassess` 的完整路径与有挂起任务时的复评属第二轮。

## 7. 验证与验收映射

### 7.1 实现阶段五条最小验证顺序

失败归因固定：**先判实现缺陷并修实现；只有实现正确而现有事实不足以判定时，才回修机制稿**（机制稿 §12.4）。下表为 2026-11-03 首轮实现的实跑结果；未覆盖项逐条记入任务记录 `validation.md`。

| # | 验证对象（机制稿 §12.4） | 夹具 | 初态 | 触发 | 预期输出三要素 | 归因规则 | 2026-11-03 实跑 |
|---|---|---|---|---|---|---|---|
| V1 | 宿主会话身份能力（机制稿 §1.4） | F1 | 已开发态部署，`.wf/` 无绑定、`writer` idle、`installation.platforms` 已声明（R93 后无 `session_profile`） | `wf-start` → `enable` → `task-new`（一次完成写权获取、首次绑定与任务创建）；再重复调用 `enable`、压缩后调用、新会话**直接**调用 `bind --task <id>` 接续（就绪候选枚举待第二轮交付）、标识丢失后恢复 | pass：`WF_OK`，position 含 `scope=session` 与绑定对象；needs_decision：`WF_IDENTITY_UNRESOLVED`，facts 列未核实的稳定性/传递事实，exit 给核验或 wf 签发路径；blocked：`WF_CAPABILITY_UNAVAILABLE`（已确认不支持该传递） | 首次绑定/压缩后恢复/新会话接续任一环节失败先判适配实现；该宿主全部身份路径不成立才回修身份编码，不先扩平台矩阵 | 11/11 用例通过（unknown→needs_decision、维护预览更新 profile、首次绑定、重复 enable、同实例标识重入、标识不符拒绝、暂停释放后新会话 bind）；真实压缩事件与 wf 签发路径未观察 |
| V2 | 恢复协议跨记录组合（机制稿 §5） | F1 | 任务位于 `finish`，归档已提交但进程未报告；随后同一实例文件被另一合法动作推进改写 | 独立进程重入 `status` 与 `archive` | pass：`WF_OK` 且报告「归档已持久化」；派生事实含该归档动作 `head_before` 为下界的可达提交查证；blocked：`WF_ACTION_INCOMPLETE`（动作事实可定位但未完成）；needs_decision：`WF_HISTORY_UNRESOLVED`（锚点/记录来源待核，出口为只读核对后 repair）；facts 给待核对项；不得出现重复归档/重复提交 | 先查「字段隔离/可达提交查证」实现；只有区分不了「未执行」与「已执行」才回修恢复机制 | 归档后另一合法动作改写公共字段再独立进程重入 → `WF_OK` 且 `archive_persisted.persisted=true`；同一任务仅一条 archive 提交；未做真实进程 kill |
| V3 | 维护组与后续任务共存（机制稿 §4.5） | F1 | 开发态 `repair` 完整应用并留回执、无提交授权 | 依次：不重叠任务开工并归档 → 重叠任务尝试开工 → 人明确处置维护组 → 恢复推进 | 不重叠任务 pass（`WF_OK`，不带入维护组）；重叠任务 blocked（`WF_WIP_UNRESOLVED`，facts 给路径组）；处置后 pass；writer 整文件未被无授权提交 | 失败先查 `writer` 公共字段与 `maintenance_results` 的字段隔离实现，不新增维护账本 | 维护组待提交时不重叠任务通过并归档、重叠任务被 `WF_WIP_UNRESOLVED` 挡、人处置后 `repair --dispose` 回写并恢复推进、任务提交未捎带 writer 整文件 |
| V4 | 复杂任务审查链路（机制稿 §9、§12.1 D25） | F2 | 复杂任务 Check pass，锚点已固定；已评测出两个异种 reviewer CLI | `review-launch` → 两个 reviewer 在暂存目录产出报告 → `review-import` → `review-decide` → `finish`；随后改一个交付文件再导入旧报告 | 首次全链路 pass（`WF_OK`，锚点核对通过）；改交付后 blocked（`WF_REVIEW_INVALID`，facts 记锚点失配）；材料不足时 reviewer 停止并回报，主会话不得据此 pass | 缺 CLI 只证明该环境不满足条件，不降审查要求；只有材料在既定读取边界内仍无法覆盖固定检查面，才形成机制回修依据 | codex 产出真实协议报告并导入（锚点核对通过）；改交付后重导旧报告 → `WF_REVIEW_INVALID`；claude（`unrecognized_model`）与 dsh（缺凭据）不可用 → `review-decide --unavailable`；复杂任务正常归档被 `WF_REVIEW_INVALID` 拒、异常退出成立；2026-11-03 补跑：codex + pi（glm-5.3-flash）两异种 reviewer 全链路 pass 并正常归档，同 CLI 双槽位 → 人数不合格，`review-decide` 拒绝且不落 verdict（`validation.md` §19 的历史记录为旧口径，按版本语境阅读） |
| V5 | 调试计数与复盘（机制稿 §1.3、§8.1、§11.2） | F2 | 同一 `verification_id` 的失败分布在 `check_history` 与 Execute 期声明 | 观察三种形态：单次 Check 内失败后重试成功；失败先声明后进入检查历史；复盘完成后再出现新触发事实 | 重试不产生 `check_history` failed 条目、机械检测不计数；合并累计跨阈值时 needs_decision（`WF_SEMANTIC_DECISION`，facts 记合并累计/阈值/倍数）；复盘后新触发使 P 与 occurrence 变化，归档前须补做 | 出现「重复判断而不改变结果」时优先收敛既有计算与消费方式，保留复盘承诺 | 12/12 用例通过（单 Check 单条最终结果、双源合并 1+2=3、未裁定倍数阻断归档、裁定后触发复盘、复盘后新事实须补做）；dedupe 双扣构造已在 2026-11-03 补跑（见本文 §7.3 与 `validation.md` §16） |

### 7.2 门禁 → 设计稿 §8.2 场景行的实现侧验收矩阵

G 编号沿用机制稿 §12.2（该表已给门禁与场景行的对应），本表补「实现面」与「夹具」，不重述断言内容。

| G | 实现面（文件/命令） | 场景行（设计稿 §8.2） | 夹具 |
|---|---|---|---|
| G01 | 本文与 skill 正文的人工判据（charter T2/T3/T5/T6 消费） | `扩展与取舍（charter T2、charter T5）`、`边界与边界外出口（charter T3）`、`减法与停止（charter T6）`、`使用负担与缺口（charter T5）`、`演进判断顺序（charter T5）`、`保留机制必答（charter T6）` | F0/F1/F2 |
| G02 | 本文 §0、skill 遵循声明 | `效力与冲突（charter T1）`、`修订同批义务（charter T7）`、`等效替换（charter T4）`、`闭环四条件（charter T4）` | F0/F1/F2 |
| G03 | `wflib/paths.py`（边界/嵌套判定）；`wflib/assets.py::branch_source_check` **首轮无调用方，第三轮 upgrade 才消费**（见本文 §2.3.11） | `多分支与嵌套仓库（charter T3）`、`分支来源核对` | F2 |
| G04 | `wflib/runs.py::load_definition/validate`（第二轮） | `用户定义零框架改造`、`定义有界校验`、`定义与实例固定`、`工作流兼容与迁移` | F0/F1 |
| G05 | `wflib/runs.py::advance`、`wflib/gates.py`（第二轮） | `单任务与多任务流程`、`准备定义与自举`、`验证分时解析`、`接续与任务归属`、`顺序依赖授权`、`人判与略过` | F0/F1 |
| G06 | `wflib/runs.py::finish/terminate`（第二轮） | `实例正常与异常终态`、`规划实例直接终止`、`实例放弃与保留`、`终止中断与历史校验`、`实例与产物隔离` | F1/F2 |
| G07 | `wflib/session.py`、`wflib/cli.py::cmd_enable` | `会话固定绑定`、`压缩与新会话`、`无稳定会话身份`、`会话实例标识`、`绑定历史按需读取` | F1 |
| G08 | `wflib/writer.py`、`wflib/lock.py`、`wflib/maintenance.py` | `单工作区串行写入`、`释放与显式交接`、`日常收工`、`所有权中断恢复`、`无 hook 强度`、`暂停插单恢复` | F1/F2 |
| G09 | `wflib/maintenance.py`、`wflib/writer.py`（字段隔离） | `维护写者`、`未提交记录存在性` | F1 |
| G10 | `.wf/bin/repair.py`（自含预览/令牌/应用/回执/处置回写）、`.wf/bin/uninstall.py`（自含）、`wflib/writer.py::receipt_state()`（首轮的只读派生，供启动校验⑩与 Check a 类）、`wflib/maintenance.py`（第三轮 upgrade 的维护路径） | `普通任务持久恢复`、`历史锚点不可达`、`数据与恢复`、`受控修复` | F1/F2 |
| G11 | `wflib/tasks.py::cmd_task_approve/cmd_task_start`、`wflib/scope.py::governance_condition`、`scripts/wf-dev-deploy.py` | `入口与基线子路由`、`规划授权`、`初始化自举`、`Git 就绪`、`执行器首次写入` | F0 |
| G12 | `wflib/scope.py`、`wflib/fingerprint.py`、`wflib/check.py` | `机读触碰面`、`同路径交替`、`指纹内容源`、`最终知识变更` | F1/F2 |
| G13 | `wflib/cli.py::cmd_enable`（Trellis 互斥核对）、`wflib/scope.py`、`.wf/bin/uninstall.py` | `共存与重装`、`Trellis 互斥`、`紧急变更边界` | F2 |
| G14 | `wflib/tasks.py::cmd_task_abandon`（首轮单任务）、`task-rework`/`task-replace`（第二轮） | `返工接续`、`异常归档边界`、`放弃改动处置` | F1/F2 |
| G15 | `wflib/spec.py`、`wflib/curation.py`、`wflib/gates.py::final_gate` | `extracted 生命周期`、`spec 正向积累`、`spec 跨任务复用`、`知识删除与依赖解除`、`策展引用统计`、`读取留痕完整性`、`无 MCP 全流程` | F0/F1 |
| G16 | `wflib/config.py`、`wflib/assets.py`、`wf.py upgrade`（第三轮） | `升级三方判断`、`流程与配置`、`发行身份` | F1/F2 |
| G17 | `.wf/bin/wf.py` 引导段、`wflib/config.py`、`wflib/maintenance.py` | `Python 执行器`、`本地命令引导`、`执行器配置可信`、`执行器确认绑定`、`确认记录身份`、`项目标识生命周期` | F0/F1 |
| G18 | `wflib/spec.py`（预算）、`wflib/codes.py`、`wflib/gates.py` | `spec 预算`、`固定流转程序化`、`判定物与原因码` | F1 |
| G19 | `wflib/review.py`、`<skill 根>/wf-review`、`wf-review-action` | `审查与正常完成（charter T4）`、`审查 CLI 身份确认`、`审查适配副本` | F2 |
| G20 | `wflib/review.py::import_report`、`_current_anchor` | `审查材料外发`、`审查读取范围`、`审查报告写权`、`审查回执锚定` | F2 |
| G21 | `wflib/lock.py`、`.wf/bin/uninstall.py`、本文 §4.5 | `资产落点`、`互斥与锁生命周期`、`锁删除与人工清理`、`锁文件归属` | F1/F2 |
| G22 | `wflib/tasks.py::cmd_task_approve`（复杂度/TDD）、`wflib/scope.py::governance_condition` | `复杂度分级一致性`、`TDD 开关` | F1 |

### 7.3 实跑状态与仍未运行的项

**夹具登记面**：逐场景的「场景行 → 夹具 → 初态 → 触发 → 预期输出 → 实跑证据」登记在 [`acceptance-fixtures.md`](./wf/acceptance-fixtures.md)；未覆盖项在该文件 §4 单列（F0 的"准备定义与自举/验证分时解析"属第二轮、真实压缩增量观察待触发）。该文件只抄实际断言，不按设计意图补写预期。

2026-11-03 首轮实现已实跑本文 §7.1 的五条最小验证顺序与三夹具；2026-11-04/05 又完成 44 轮评审与十二轮独立复审（R79–R92）的复核修订与回归；2026-11-05 按人裁把安装入口改为 `--platform` 单一入口（技能装在目标项目内），并取消 `--host-id`/能力证据：平台清单即身份事实，并补跑 D1 的真实压缩观察（`validation.md` §21–§80），全量回归由 `run_all.sh` 一次跑完并按实际执行项计数：`SUITES` 59 个套件 + 5 个专项（`r72` 卸载边界、`f0` 发行安装自举、`p5_spec`、`p5_v2v3`、`p5_v5`）+ `repro/` 68 条修复用例（green/red 双模），当前 **132 项**；**默认每次都从源码重建发行仓库**（`WF_REBUILD_RELEASE=0` 可复用），失败即非零退出。2026-11-12 收口复跑：132 项 0 失败（必过门通过、豁免债 0）、`repro` 68/68、发行字节复现 74 assets、令牌一致、单测 457（`scripts/tests`）+ 154（`scripts/tests/wf_runtime`）全绿。实跑暴露的缺陷全部落在实现层并已修正，未回修机制稿。

仍未运行的项与原因分类：①**真实压缩事件的绑定轴**——2026-11-04 已观察到两次真实压缩且 `$DSH_SESSION_ID` 未变、绑定键可由标识确定性重算（`validation.md` §71）；但「压缩后绑定仍可读」的观察性证据需下一次压缩，判据与快照写在任务记录 `d1-compaction-checkpoint.md` §1；②单 reviewer「人数不合格」派生分支——已用 `pi`/`glm-5.3-flash` 复验关闭（`validation.md` §19）。原先未运行的「归档提交后被强杀的真实进程中断」「`dedupe_refs` 双扣」「spec 拆分（原文件移除分支）」三项已在 2026-11-03 补跑并记录（`validation.md` §16）；拆分的「旧文件停用并保留」分支原为登记未断言项，2026-11-05 已补跑（`p5_spec` 的 6 条用例，含拆分前 active 正对照：停用后保留、`status: disabled`、索引同步、停用条目不再被 `match` 加载）。

评审复核后的处置状态：A 类 23 项（门禁核验、接线、工具与一致性）已全部完成并逐项留证（`validation.md` §12–§15）；B 组 5 项补跑完成（F2 的 Trellis 两分支与共存/外部提交、崩溃点、dedupe 双扣、spec 拆分，§16）；C 组两处裁量已裁定并落地——`repair --dispose` 纳入令牌（本文 §4.5.1，实测见 §17）、归档提交顺序维持设计稿 §4.2（本文 §2.3.1，§18）；D 组：真实压缩/签发路径按人决定保留「未运行 + 原因」；单 reviewer 分支已用同一 CLI 双槽位实跑（`validation.md` §19）。**独立复审已执行**：2026-11-03 至 11-05 的外部独立复审共二十余轮，逐轮修正批见 `validation.md` §90–§96 与 `11-05-…/execution-log.md`；覆盖轴与未覆盖轴以本文 frontmatter 的 `status` 为准。首轮真实 dogfood 亦已于 2026-11-09～10 跑完（8 轮，产出 [`wf/analysis/solution-review-v42.md`](./wf/analysis/solution-review-v42.md)）；按 dogfood 结论做的机制修订（v42 控制流修复、⑥ 修复态）属后续轮次，不在本文的验收面内。

审查 CLI 可用性以本次探测为准：`codex` 可用；`claude` 返回 `unrecognized_model`、`dsh headless` 缺凭据，二者在本机不可作非交互 reviewer。三夹具已建立并可重建（仓库外临时目录），宿主会话身份能力只在 `platforms=[dsh]` 下验证过（R93 起身份事实＝平台清单，不再有 `--host-id` 与能力声明）。

## 8. 单页使用速查

本章是设计稿 §8.1 第 2 项要求的「时刻 → 入口 → 人工动作/令牌 → 阻断出口」。它只引用调用权与命令，不复制门禁规则；表中的原因码与出口摘自机制稿 §11.1 的码表并作速查缩写，冲突时以码表为准，本章不新增、不改义任何原因码。

### 8.1 环境前提

- **单人、本机、单一共享工作区**：同一时刻只有一个写者。框架只在人显式启用 `/wf-start` 的会话内生效（设计稿 §1.2、§1.3 调用权分层）；未启用的会话照常做别的开发。
- **复杂度**：机制稿 §1.3 的四项条件（治理面、对外契约、验收/回退口径、范围扩张）**先汇总再提议**——任一为 `true`/`unknown` 即提出 `complex`；人工可指定 `light` 降级，但须给 `reason` 与 `evidence`，缺一即 `WF_SEMANTIC_DECISION`。条件事实与降级结论都写入 `plan.complexity_reasons`。产物检查使用**最终**分级，顺序在定级之后（详见本文 §2.3.5）。
- **复杂任务至少三个异种 CLI**：1 个实施 + 2 个彼此不同、且都与实施不同的审查 CLI（机制稿 §9.2）。不足时**只能暂停等待，或按机制稿 §6.4 异常归档**；不得降级完成、不得用单 reviewer 冒充（charter T4、设计稿 §6.5）。
- **连续独立短任务优先声明为用户工作流实例**：定义内顺序任务步骤即可承载，减少换会话来回避对象绑定；首轮无实例能力时只能逐任务新开会话，成本见本文 §8.5。
- **人工动作清单**：终端确认与令牌输入（`upgrade --apply`/`repair`/`uninstall --purge`）、`confirm-executor`、`finish` 调用、审查发起与材料外发授权、规划批准与 `plan-q` 作答。模型不代答、不代跑。
- **不做**：分支状态变更、嵌套仓库扫描、并行调度、常驻服务、外部 MCP（charter T3）。

### 8.2 时刻 → 入口 → 人工动作/令牌 → 阻断出口

| 时刻 | 入口 | 人工动作/令牌 | 阻断出口（原因码 → 出口） |
|---|---|---|---|
| 首次投放（开发态/正式发行） | 开发态 `python3 scripts/wf-dev-deploy.py --target <abs> --platform <平台> [--confirm]`（先出预览）；正式发行 `python3 install.py --target <abs> --release-ref <refs/tags/wf-vX.Y.Z> --source <发行目录> --platform <平台>`（首轮已交付；升级侧仍属第三轮） | 给目标绝对路径与发行引用；确认预览与投放根；Trellis 资产风险确认 | `WF_ASSET_DECISION` → 保留/移走/改名；`WF_RELEASE_CONFLICT` → 核正确发行引用；`WF_TARGET_COLLISION` → 保留双方并确认目标 |
| 首次解释器确认 | `<python> .wf/bin/wf.py confirm-executor --scope system\|global\|project`（终端，人执行） | 人在终端执行，入口探测 `--version` | `WF_EXECUTOR_UNCONFIRMED` → 确认当前解释器 / 换已批准解释器 / 回到未设置 |
| 开始会话 | 宿主 skill `wf-start`（唯一启用方式） | 人显式调用 | `WF_FLOW_CONFLICT` → 清理 Trellis 来源后换新会话；`WF_IDENTITY_UNRESOLVED` → 核实宿主身份或改用受支持宿主（wf 签发路径属第二轮，首轮不可选）；`WF_WRITER_BUSY` → 等待或已确认交接 |
| 选择对象 | `wf-start` → `wf.py task-new`（普通任务）/ `run create`（第二轮） | 人选对象；实例另需确认版本/输入/展开规则 | `WF_BINDING_MISMATCH` → 原对象结束后新会话选择；`WF_DEPENDENCY_UNMET` → 等前置或人确认返工/重连；`WF_APPROVAL_MISSING` → 先批准规划 |
| 准备定义（第二轮） | `wf-start` → `wf.py definition prepare --id <workflow-id>` | 人批准准备范围 | `WF_DEFINITION_INVALID` → 按校验清单改定义；`WF_TEMPLATE_INCOMPLETE` → 填模板必填位 |
| 批准规划 | `wf-continue` → `wf.py task-approve --task <id> --decision <path>` | 人批准规划+复杂度+TDD；一轮内批量作答 `plan-q-<n>` | `WF_APPROVAL_MISSING` → 重新呈现规划；`WF_SEMANTIC_DECISION` → 澄清未决语义；`WF_TEMPLATE_INCOMPLETE` → 填模板 |
| 开工 | `wf-continue` → `wf.py task-start --task <id>` | 无（门禁自动） | `WF_SCOPE_UNRESOLVED` → 回 Plan 补可证包含条目；`WF_WORKSPACE_UNRESOLVED` → 逐路径核归属；`WF_WIP_UNRESOLVED` → 同对象核指纹恢复或实际处置；`WF_VERIFICATION_UNREADY` → 补来源/设施 |
| 读规则 | `wf.py spec --file <RepoPath>` | 无 | `WF_SPEC_INCOMPLETE` → 分批读全文后重试 |
| 检查 | `wf-continue` → `wf.py task-check --task <id>` | 无 | `WF_SCOPE_VIOLATION` → 回 Plan 扩范围重批；`WF_CHECK_FAILED` → 修复后重跑；`WF_CHECK_STALE` → 重算锚点后重检 |
| 重新规划（实质变更） | `wf-continue` → `wf.py task-replan --task <id> --decision <文件>`；随后 `task-approve` → `task-start` | 人决定改方案并说明变更范围；重批时确认范围/验收/取舍 | `WF_GENERATION_STALE` → 重读当前代次后重试；未重批即再入 → `WF_APPROVAL_MISSING` |
| 放弃任务（异常归档） | `wf-continue` → `wf.py task-abandon --task <id> --decision <path> [--disposition <path>]` | 人给停止决定与逐项去向；未提交改动须先授权提交或由人实际处置 | `WF_COMMIT_NOT_AUTHORIZED` → 先取提交授权或改去向；`WF_WORKSPACE_UNRESOLVED` → 逐路径处置后再结案 |
| 复杂任务审查发起 | `wf.py review-launch …`，再由人打开两个异种 CLI 会话 | 人声明实施 CLI、两个 reviewer CLI 与槽位；授权本次外发材料范围 | `WF_REVIEW_UNAVAILABLE` → 暂停或异常归档；`WF_REVIEW_INVALID` → 补真实审查 |
| 审查导入与判定 | `wf.py review-import …` → `wf.py review-decide …` | 人核对报告与锚点 | `WF_REVIEW_INVALID` → 锚点失配则重审；报告缺失/身份矛盾不判 pass |
| 完成门禁与归档 | 人调用 `wf-finish` → `wf.py archive --task <id> --decision <path>` | 人了解结果与未核实项后调用 finish；该 Decision 记调用证据与按精确路径的提交授权 | `WF_COMMIT_NOT_AUTHORIZED` → 等人处理；`WF_SEMANTIC_DECISION` → 裁定未决项；`WF_WORKSPACE_UNRESOLVED` → 处置工作区 |
| 日常收工 | `wf-continue` → `wf.py stop --decision <path>` | 人给**一个**去向（提交 / 保留 WIP / 反向修正 / 具名承接），`subject` 列出覆盖路径或承接对象；提交与反向修正的授权写在同一 Decision 数组里 | `WF_WORKSPACE_UNRESOLVED` → 落实际处置后再释放；`WF_WIP_UNRESOLVED` → 同对象恢复或处置 |
| 未完成收工就关闭 | 新会话先人直调 `.wf/bin/repair.py`（预览 + 令牌），再 `wf-start` | 人确认旧写者已停止、核对 Git/产物/WIP、输入令牌 | `WF_HISTORY_UNRESOLVED` → 只读核原文/Git 后 repair；`WF_GENERATION_STALE` → 停止写并重核 |
| 升级（第三轮） | `wf.py upgrade --apply --release-ref <refs/tags/wf-vX.Y.Z> --source <发行目录> [--platform <平台>]` | 预览 + 终端令牌；另有提交授权 | `WF_PREVIEW_STALE` → 重新预览；`WF_ASSET_DECISION` → 逐项选保留/恢复/合并 |
| 受控修复 | `.wf/bin/repair.py`（人直调；`--dispose <plan>` 处置维护组） | 预览 + 终端令牌；确认旧写者停止 | `WF_RECORD_INVALID` → 保留原文并按人指定事实重建；`WF_HISTORY_UNRESOLVED` → 只读核对 |
| 卸载 | `.wf/bin/uninstall.py`（`--purge` 另确认，第三轮） | 预览 + 确认；确认无 wf 进程后手工清理 `.wf-lock` 与 `/.wf-lock` 忽略行 | `WF_ASSET_DECISION` → 逐项选保留/移走/删除；`WF_WRITER_BUSY` → 先核实旧写者 |
| 巡检 | `wf.py inspect`（人发起，或每 10 个正常归档的整数倍） | 无 | 只读报告三类结果；要修复则另取授权 |

表中 `WF_ASSET_DECISION`、`WF_IDENTITY_UNRESOLVED`、`WF_SCOPE_UNRESOLVED`、`WF_WORKSPACE_UNRESOLVED`、`WF_HISTORY_UNRESOLVED`、`WF_SEMANTIC_DECISION` 属 `needs_decision` 档（列名沿用设计稿 §8.1 的「阻断出口」，档位以机制稿 §11.1 码表为准）；其余码为 `blocked` 档。速查不合并两档，只为省行。

- **安装维护组处置（首轮真实使用最先撞上的维护语义）**：`inspect` 显示 `applied_pending_commit` 时只有两条出口——按登记路径提交（须明确覆盖维护组），或走 `repair --dispose`；否则触碰 `.wf/bin`、`.wf/lib`、`.wf/workflows` 等路径的任务会在开工时被判与维护组重叠。

### 8.3 收工与关闭

- 日常收工：`wf-continue` 走 `wf.py stop`，预览逐路径归属与状态，人就整份 WIP **选择一个**去向（`commit`/`keep`/`reverse`/`transfer`）并用 `--decision` 给出覆盖路径或承接对象；入口记录真实状态后暂停并释放写权（设计稿 §4.4）。混合处理要拆成多轮或先改机制稿，命令面不表达。保留后释放只适用于当前任务批准范围内、归属明确的 WIP；同一对象可恢复，其他对象与普通升级必须先行实际处置。
- 直接关闭终端/崩溃/未完成上述动作**不算释放**：写权记录仍占用。原会话恢复需核身份与代次；新会话先经 `repair.py` 确认旧写者停止、核对 Git/产物/WIP 去向，再恢复（机制稿 §5.4；设计稿 §5.5 的受控修复）。不按超时抢占、不补称「关闭前已交接」。

### 8.4 对象结束后的下一个对象

1. 所绑定普通任务或整个实例**正常/异常结束** → 按机制稿 §4.4 处理工作区（提交/保留/反向修正/具名承接）并释放写权。
2. 在**新会话**调用 `/wf-start` 选择下一对象。原会话仍可查看原对象结果，**不能承接下一对象**：绑定终身不变（设计稿 §1.3）。
3. 「新会话」以取得不同会话身份为准；**压缩或恢复原会话不算新会话**，不产生改绑许可。
4. 同一实例内任务结束后仍按机制稿 §7.3 继续推进，不因此要求新会话；只有换对象（另一普通任务或另一实例）才需要新会话。

### 8.5 如实提示的成本

- 每换一个独立对象就要新开会话、重新 `wf-start`、重新加载规则与交接材料；连续短任务的会话切换与上下文重载成本是固定绑定的已知代价，不预先认定可忽略（设计稿 §8.2）。
- 复杂任务每次审查都要人打开两个异种 CLI 会话并核对锚点；不可用时只能暂停或异常归档。
- 首轮无实例能力，短任务也只能逐任务换会话；第二轮起可用用户工作流实例把连续短任务放进同一实例，减少换对象次数（仍不减少任务级的批准与检查）。

## 9. 未落地项与已裁定事项

### 9.1 本阶段未做（原因分类）

| 项 | 原因 | 说明 |
|---|---|---|
| 框架代码、脚本、skill 副本、`.wf/` 实例 | 首轮已交付并实跑（`run_all.sh` 132 项；2026-11-12 收口复跑 0 失败） | 编码另立任务；本文给出的路径与函数名是其输入 |
| 机制稿 §0.2 四项机检扩展 | 未安排（已登记为后续项） | 见本文 §9.2 第 1 项 |
| 三夹具 F0/F1/F2 与五条验证顺序 | 已实跑（2026-11-03） | 结果见任务记录 `validation.md` 与本文 §7.3；未运行项逐条记原因分类 |
| reviewer CLI 可用性（`claude`/`codex`/`dsh`） | 环境未验证 | 命令存在不等于可作非交互 reviewer；须实测 |
| 宿主会话身份能力（压缩稳定、新会话区分、结构化传递） | 环境未验证 | 机制稿 §1.4 要求按宿主核实；未核实前 `status=unknown` |

### 9.2 已裁定事项与剩余待办

**已裁定（2026-11-02，人）**

1. **机制稿 §0.2 四项机检扩展 → 登记为后续项**。四项为①按 schema 表逐键核对写者/消费者/失败出口；②码表档位与处理器映射表一致；③表间引用悬空；④机制稿的两张场景映射表与设计稿 §8.2 同源核对。现状：④ 与输入摘要、哈希域逐键段已落地；②在运行输出中无对应字段；①③未见实现。排期按 charter T6.3 顺序（先改既有产物 → 造确定性机检 → 新增规则），排在首轮实现收口之后，不阻塞首轮。登记落点为本节与任务记录；机制稿 §0.2 原文未改（它是已审稿，写回须同批复审），落地前由该节规定的固定反查动作与人工复审兜底。
2. **入站指针 → 只在机制稿 §12.4 加一行指针**（已落地）。机制稿不在四份摘要文件内，`输入摘要 4/4` 与索引表均未变动；索引登记未做，若日后要求须同批改索引、重算四份摘要并写回机制稿 §0.1。
3. **`scripts/check-doc-refs.py` 已扩展 `机制稿` 前缀**（已落地，约定见本文 §0）。改动含：登记前缀新增 `机制稿 `、新增「列举继承」规则（前缀与 `§` 之间只有同类引用与 `、，,与和`/空白时继承前缀，出现其他语义文字则不继承）、支持多文件参数并给总数（单文件输出格式不变）、默认仍查 `workflow-implementation.md`。本文已用该脚本自检通过；它不在 `validate-wf-design.py` 的七项检查内，二者互不替代。
4. **复盘登记为独立机制操作 `task.retrospect`**（已落地）：机制稿 §11.3 的状态动作集合与机制稿 §5.1 的当前任务主记录归属同批登记，`control.task.retrospect` 按该节公式派生；处理器 `wflib/tasks.py::cmd_task_retrospect`（本文 §6.2 D36），门禁仍由机制稿 §11.2 的 `task.retrospective-done` 核验。该改动触及已审稿，须同批复审。
5. **打包脚本不入发行清单，只写发行说明**（已落地，见本文 §1.5 的发行说明要求与理由）。**发行安装器 `install.py` 相反：它属发行资产**，按 `release_only` 登记进 `assets` 并计入 `rules_digest`；`target_class` 的取值域由本文定义（机制稿 §10.2 只给字段名，未定域），因此这一登记不需要改机制稿。作者机工具（打包、开发态部署）不属发行资产，两者不要混为一谈。

**本轮修订（2026-11-02，处置复审两条中级发现）**

| 编号 | 复审原文摘要 | 复核结论 | 证据（修订前绑定的行号） | 类 | 改动落点 | 联动 |
|---|---|---|---|---|---|---|
| M1 | 实质重新规划的状态动作没有明确调用形态 | 成立 | 本文 §2.3 原 230–231 行（只登记「批准规划」「首次开工／再入 Execute」）、原 300 行（本表外的操作名不因存在于机制稿就成为命令）、本文 §8.2 原 638/640 行（已把「回 Plan」当出口）；机制稿 §2.2 的「实质规划变更」行、机制稿 §11.3 的状态动作集合 | A | 本文 §2.3 新增 `task-replan` 行与「阶段回退的承载与再入路径」段；本文 §2.2 的代次列举；本文 §8.2 新增「重新规划（实质变更）」行 | 无：映射到已登记的 `task.transition`，不新增操作名、不改机制稿 |
| M2 | 首轮 `task-abandon` 的人工输入接口仍是省略号 | 成立 | 本文 §2.3 原 239 行（`--task <id> …`）、原 261–262 行（`--decision` 用途表与 `--plan` 的「只用于」）、本文 §6.4 原 563 行（首轮「照常走 `task-abandon`」）；机制稿 §6.4 的停止决定与逐项去向、机制稿 §1.3 的 `disposition`/`commit_grants` | A | 本文 §2.3 拆出 `task-abandon` 行并写显式参数；`--decision` 用途补该命令、新增 `--disposition` 承载与记录映射；本文 §8.2 新增「放弃任务（异常归档）」行 | 无：字段、取值与落实判据均引用机制稿 §1.3、§6.4 |

**本轮绑定**：修订前 700 行 / `sha256 75667055f3efbfe28824bc6d434af7cc26fefd799c5b05b809f010f8d989163e` / HEAD `fdc328b`，该绑定**作废**。修订后的行数与 sha256 由本轮修订回复与任务记录给出（文件内写自身哈希会自指）；HEAD 仍为 `fdc328b`（本轮未提交）。两条均属 A 类，无需同批复审，无「需人裁决」项；`task-rework`/`task-replace` 的参数仍按其第二轮交付轮次确定，本轮只拆行、不改其形态（复审原文允许）。

**复审记录（2026-11-02）**

| 来源 | 独立性边界 | 绑定 sha256 | 覆盖轴 | 结论 |
|---|---|---|---|---|
| 同模型同仓库会话（原 Codex 会话，全文重审） | 满足未参与编写与修订；不满足独立工具口径（同模型、同工作树，非新冷启动，不宣称防伪） | `b8eddf075af3ff3f773b2f82015db9df60e72958d9b81cc19ca145c88a4b09d8`（717 行） | 全文逐节不抽样、命令与记录接口闭合性、五条流程纸面推演、交付轮次、设计稿 §8.1 承接、审查写权边界；未覆盖：框架执行、三夹具、故障注入、打包与安装生命周期、宿主身份与 reviewer 非交互能力 | 可作为首轮实现阶段基线；高级 0 / 中级 0 / 低级 0；不构成实现验收 |
| 不同 CLI（独立复审） | 满足未参与编写与修订；不同 CLI 口径成立，但同一操作者、同一工作树，不宣称防伪 | 同上 `b8eddf07…`（717 行）；其后 L2/L3 两处小修的 delta 复核通过，正文绑定更新为 `051aade5…` | 可执行性（五条流程纸面实例化）、闭合性、一致性、上位承接（设计稿 §8.1 逐子句）、定点核对九项；未覆盖：夹具实跑、宿主身份与 reviewer 可用性、任务记录逐条比对 | 可作为首轮实现阶段基线；高级 0 / 中级 0 / 低级 5（L1–L5，处置见本节「低级发现处置」）；不构成实现验收 |

登记编辑仅改 `status:` 与本文 §9.2，正文条款未动，绑定 `051aade51681f9b33ba7fbf2e21c44f20045c273772f796caa72c4f1e7e4d952` 仍成立。

**低级发现处置（2026-11-02）**

分诊口径：① 真低级（措辞、示例或可自然补全，不影响照抄）；② 照抄会踩空（应重判为中级）；③ 与机制稿或已声明裁定不一致。

| 编号 | 复审原文摘要 | 复核结论 | 分诊 | 改/不改 | 理由 |
|---|---|---|---|---|---|
| L1 | 本文 §0 四层表与本文 §1.5 把 authoring 源树 `docs/workflows/wf/` 写成既有形态（该目录 2026-10-28 已退役、当前不存在），且首轮清单无建立源树条目 | 成立（事实成立，影响限于清单缺项） | ① | 不改 | 首轮交付物清单缺「建立源树 + dev-manifest.json」，由首轮实现任务输入说明承接，本文 §9.2 剩余待办登记 |
| L2 | 本文 §2.3 把 `asset.compare` 与 `verification.resolve` 并列写成由 `task-start`/`task-check`/`archive`/`run` 内部步骤暴露，消费面错置（机制稿 §11.3 中 `asset.compare` 的消费面是发行侧三方比较） | 成立（消费面错置） | ③ | 改 | 改动落点：本文 §2.3「没有公开子命令的机制操作」段（:306）拆句——`verification.resolve` 保留原内部步骤列举，`asset.compare` 写明消费面是发行侧三方比较，落点见本文 §6.2 D31、本文 §7.2 G16 |
| L3 | 本文 §2.3 的 `enable` 行机制操作格写 `gate.evaluate` 的只读形态，而启用检查实为机制稿 §2.1 的 Trellis 互斥、身份与 activation 核验 | 成立（机制内容错标） | ③ | 改 | 改动落点：本文 §2.3 表 `enable` 行机制操作格（:224）改为「只读启用核对（Trellis 互斥、身份能力与 activation；不属固定操作集合，见机制稿 §2.1）」，其余五格不动 |
| L4 | 本文 §7.1 的 V1 初态写 `session_profile.capability=unknown`，触发列又把 `wf-start` → `enable` → `task-new` 并列，核验出口未写入触发列 | 成立（编排缺口，判定无歧义） | ① | 不改 | 框架行为以机制稿 §1.4 为准且无歧义：`status=unknown` 时先经核验出口更新 `session_profile`，缺的只是 V1 触发序列首步，属实现阶段的测试编排，照抄不产生门禁分歧 |
| L5 | 本文 §6.2 的 D28 行「由发行自检用固定向量比对」与本文 §4.5.1「不属于安装期自检，也不是运行期能力」存在措辞张力 | 部分成立（措辞张力，非事实冲突） | ① | 不改 | 「发行自检」可读作打包期自检，与本文 §4.5.1 的 authoring 发布前检查同指一场检查；该节已排除安装期与运行期两义，无验收分歧，属跨节词面统一 |

**2026-11-12 事实订正（D14 与执行项计数）**

- **D14**：删除「wf 自签发身份路径」的第二轮归属。该能力已随 2026-11-08 的自动身份模式交付（执行边界派生 + 自动签发 `issued_id`，见机制稿 §1.4 与 §12 的 D14 行），显式 wf 信封按设计拒绝（无本地证据）。同批订正机制稿 §1.4 两句失实表述（原写「第二轮交付」「人显式选择并可携带」）。
- **执行项计数**：本文 §7.3 与本文 §9.1 的「76 项 / 54 套件 / 17 条 repro」按 2026-11-12 实跑订正为「132 项 / 59 套件 + 5 专项 / 68 条 repro」。
- 本批只改事实表述，不改任何判定、码表、门禁顺序或字段；机制稿的判定条款未动。

**剩余待办**

| 项 | 状态 | 出口 |
|---|---|---|
| 机制稿 §0.2 四项机检扩展的实现 | 后续项（不阻塞首轮） | 首轮实现收口后另立维护任务，按 charter T6.3 顺序落地并重跑机检 |
| 索引表登记本文 | 未做（人裁「只加机制稿指针」） | 若日后要求，同批改索引、重算四份 SHA-256、写回机制稿 §0.1 摘要表并由人确认 |
| 本文冻结 | 2026-11-03 首轮实现按本文 §7 实跑结果更新本文 §0、§7.1、§7.3、§9.1；2026-11-12 两次收口/订正（11-03 收口 + D14 与计数订正）更新本文 §7.3、§9.1、§9.2、§6.4 与 D14 行的事实表述，同批订正机制稿 §1.4，不涉及任何判定或条款。当前绑定与行数由任务记录 `validation.md` §97 登记（文件内不写自身哈希） | 定稿口径为「按已覆盖轴」：真实断电/fsync、并发竞争、`repair` 接管路径的完整负例矩阵仍属未覆盖轴（见本文 §2.3.11），不得读作已覆盖 |
| 三夹具、五条最小验证顺序、审查链路、宿主身份、reviewer 可用性 | 三夹具、五条最小验证顺序与审查链路**已实跑**（见本文 §7.3，2026-11-12 复跑）；真实压缩的绑定轴与 `repair` 重建后的旧确认失效**未运行**（等事件 / 第三轮交付） | 未运行项按「未运行 + 原因分类」保留，见本文 §7.3 与 `validation.md` §97 |
