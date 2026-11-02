---
doc: wf 独立框架实现方案
scope: 目标项目的文件布局、脚本接口、命令形态、发行物构成与单页使用速查
audience: 框架实现者、安装者与日常使用者
status: 首版草稿（2026-11-02）；未经未参与编写会话复审，不构成实现验收
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

**「未运行」纪律**：本文第 7 章列出的验证顺序、第 5 章的审查链路、第 1 章的投放自检，全部为待运行断言，一律标「未运行」。本文不把夹具、故障注入、宿主身份能力或 CLI 可用性写成已通过；被文本引用也不能推出可用性。

**四层对象（后文一律按此命名）**：

| 层 | 位置 | 说明 |
|---|---|---|
| authoring 源树 | 本仓库 `docs/workflows/新项目开发工作流/` | 模块源，不是可运行应用；作者侧编辑与打包输入 |
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

`<skill 根>` 由安装时人声明，缺省候选 `.agents/skills/`（设计稿 §1.2）。不同根的同名副本共享同一逻辑来源与版本，不发展平台差异门禁（机制稿 §10.1）。

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

### 1.4 运行态与本机用户层

| 对象 | 位置 | 谁写 | 说明 |
|---|---|---|---|
| 会话定位缓存 | `.wf/.runtime/sessions/<session-key>.json` | 入口（可丢弃） | 只能由持久绑定与实例游标重建（机制稿 §1.4） |
| 读取留痕侧车 | `.wf/.runtime/spec-reads/<session-key>.json` | 当前会话入口，按会话隔离 | 无写权会话可写本会话侧车，不写判定字段（设计稿 §4.4）；`complete=false` 表示未完整装载 |
| 锁对象 | `<项目根>/.wf-lock` | 锁原语 | 只创建不删除；内容固定 `wf-lock-v1\n`（机制稿 §4.1） |
| 用户层全局配置 | `~/.wf/config.json` | 人（或人显式执行的确认动作） | `{schema_version: 1, python_executable?: 绝对路径}`；缺失=未设置（机制稿 §8.2） |
| 解释器确认集合 | `~/.wf/interpreters.json` | 只由 `confirm-executor` 子命令写 | 独立于 `config.json`；按完整元组集合保存，多条并存互不覆盖（机制稿 §8.2） |
| 审查暂存目录 | `<临时根>/wf-review/<project_id>/<task-id>/round-<N>/<slot>/` | reviewer 进程 | 项目树外；隔离键为任务/轮次/槽位（本文 §5.2）；槽位 id 与 `--reviewer-id` 是同一标识；卸载清单不覆盖，只列残留位置 |

临时根取 `tempfile.gettempdir()`，不读环境变量拼接；用 `project_id` 而非项目路径分目录，避免把本机路径带进 reviewer 可见范围。

### 1.5 authoring 源树与打包发行树

**源树**（作者侧维护，不被安装）：

```
docs/workflows/新项目开发工作流/
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

**发行根安装入口**：正式安装由发行根的单文件 `install.py`（仅标准库、自包含）承接，因为安装发生时目标项目还没有 `.wf/bin/`。它不投放目标项目、不属于 `.wf/` 资产，因此不参与三方升级，也不出现在卸载清单里；但它是**发行资产**，按 `target_class=release_only` 登记进清单 `assets` 并计入 `rules_digest`（本文 §4.2）。每次安装/重装都从所选发行重取，安装结果记入 `.wf/install/installation.json`（`release_ref`、`source_commit`、`version`、`manifest_digest`、`roots`、`assets`、`decisions`、`session_profile`）。机制稿 §10.1 的落点表只登记 `.wf/` 内脚本，本条补的是该类资产的发行侧落点；它的资产类型判定与是否纳入发行清单见本文 §9.2 第 5 项。

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
3. `argv[1] == confirm-executor` → 由引导层自身在当前解释器内执行：只写 `~/.wf/interpreters.json`、只读项目配置、不写项目数据、不进项目锁，完成后退出。该分支必须在第 4 步之前，否则「未确认即停」会让确认动作本身不可达（机制稿 §8.2 要求该子命令由引导解释器拉起）。
4. 只读 `.wf/project-config.json` 取 `python_executable`，缺失则读 `~/.wf/config.json` 同名键，再回落到 `python3`；按机制稿 §8.2 取候选存在/可执行/路径身份/`size`/`mtime_ns` 并与 `~/.wf/interpreters.json` 元组匹配。未匹配即输出 `WF_EXECUTOR_UNCONFIRMED` 并停（不在引导解释器继续判定，出口是第 3 步的 `confirm-executor`）。
5. `os.execve(executor, [executor, <lib>/module_main.py, *rest], env)`，env 只追加 `PYTHONPATH=<lib>`、`WF_PROJECT_ROOT=<根>`、`WF_BOOTSTRAP=1`。这三个变量是进程间移交标记，**不作为身份、配置或授权来源**（身份只经请求信封，机制稿 §1.4）。

### 2.2 请求信封（会话入口的唯一身份通道）

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
  - **必须携带**：其余会写项目判定字段、且**不建立新代次**的子动作——`task-approve`/`task-start`/`task-pause`/`task-resume`/`task-curate`/`task-check`/`task-knowledge`/`task-retrospect`/`task-attribute`/`task-rework`/`task-replace`/`task-abandon`/`task-reassess`、`dep`、`stop`、`archive`、`review-launch`/`review-import`/`review-decide`、`baseline-apply`、`spec-update`、`run advance`/`run pause`/`run terminate`。**未携带与不匹配同判** `WF_GENERATION_STALE`：facts 区分「未携带 generation」与「generation 不符」，出口都是重新读取当前代次后重试，不自行递增、不按当前 writer 补用新代次。
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
| `status` | `[--json]` | `gate.evaluate`（只读） | 只读断言，不迁移 | 机制稿 §3.1 边界核对 | 1 |
| `gate` | `--due before_execute\|before_check\|before_archive` | `gate.evaluate`（只读） | 只读断言 | 机制稿 §3.2（指纹）、机制稿 §3.5（范围） | 1 |
| `spec` | `--file <RepoPath>`（信封必需） | 只读查询 + 本会话读取侧车 | 无（不写判定字段） | 机制稿 §3.1 | 1 |
| `inspect` | `[--json]` | 只读巡检（机制稿 §8.5） | 无 | 全库只读视图 | 1 |
| `enable` | 信封 | `gate.evaluate` 的只读形态（start 的只读段；不属固定操作集合） | 无迁移 | 机制稿 §3.1 | 1 |
| `bind` | `--task <id>` \| `--run <id>`（信封） | `session.bind`（在写权获取动作内成组写入；机制稿 §4.2「首次绑定按本文 §5 成组写入」） | 空闲态下新会话对**既有就绪对象**的首次绑定；**不承担首次创建**（见 `task-new`），**不承担交接接收**（见 `writer-handover accept`） | 机制稿 §3.1、机制稿 §4.4 工作区分类 | 1 |
| `writer` | `acquire` \| `release` | `writer.acquire` / `writer.release` | 写权获取/释放 | 机制稿 §4.4 | 1 |
| `writer-handover` | `begin --to <session-key>` \| `accept` | `writer.handover.begin` / `writer.handover.accept` | 两段交接：`begin` 由旧写者发起（失效旧代次、写接收者与待恢复）；**`accept` 由接收方一次性完成绑定核验与代次授予**，接收方不再单独调 `bind` | 机制稿 §4.3、§4.4 | 1 |
| `stop` | `--decision <path>`（数组：收工选择一条 commit/keep/reverse/transfer + 提交/反向修正授权若干条；subject 列覆盖路径或承接对象）（信封） | `session.stop` + `task.pause` | 日常收工（设计稿 §4.4） | 机制稿 §4.3（同对象 WIP）、机制稿 §4.4 | 1 |
| `task-new` | `--kind ordinary\|initialize\|bootstrap --title <t> --template <path>`（信封） | `writer.acquire` + `session.bind` + `task.create`（**单一父 action**，主记录 writer） | 创建规划 + 首次绑定 | 机制稿 §3.1、机制稿 §5.2 目录防撞 | 1 |
| `task-approve` | `--task <id> --decision <path>` | `task.transition` | 批准规划（含复杂度/TDD/plan-q 答复） | 机制稿 §2.3 提取、机制稿 §3.4 条件① | 1 |
| `task-start` | `--task <id>` | `task.transition` | 首次开工 / 再入 Execute（写 `entry_snapshot`） | 机制稿 §3.1、§3.3 | 1 |
| `task-pause` / `task-resume` | `--task <id> [--reason]` | `task.pause` / `task.transition` | 暂停 / 恢复 | 机制稿 §4.4 | 1 |
| `task-curate` | `--task <id> --spec <path> --purpose <text>` | `task.curate` | 策展写入 | 机制稿 §3.1 | 1 |
| `task-check` | `--task <id> [--decision <path>] [--review-notes <path>]` | `task.check` | Check（固定五步，机制稿 §3.2）；并写 `task.work-satisfied` 的 completed 回执 | 机制稿 §3.5 范围核对 | 1 |
| `task-knowledge` | `--task <id> --decision no-update\|updated`（`updated` 的具体操作由 `changes` 按机制稿 §8.4 的 `{operation, …}` 记录） | `task.knowledge-dispose` | 知识处置留痕 | 机制稿 §3.1 | 1 |
| `task-retrospect` | `--task <id> --evidence <path> [--decision <path>]` | `task.retrospect` | 复盘记录（人要求或触发后执行） | — | 1 |
| `task-attribute` | `--task <id> --commit <oid>` | `task.attribute` | 归属裁决 | 机制稿 §3.3 | 1 |
| `dep` | `add\|rm --task <id> --prereq <id>` | `dependency.change` | 建边/删边 | 机制稿 §6.1 图校验 | 2 |
| `task-rework` / `task-replace` / `task-abandon` | `--task <id> …` | `task.rework` / `task.replace` / `task.abandon` | 返工/替换/放弃 | 机制稿 §6.2–§6.4 | 1（仅单任务放弃）、2（返工/替换/建删边） |
| `task-reassess` | `--task <id>` | `task.reassess` | 挂起复评 | 机制稿 §6.2 | 2 |
| `review-launch` | `--task <id> --launch-request <path>`（结构化声明，骨架见本节末） | `review.launch` | 审查发起；round/attempt/anchor/temp_paths 由入口生成并回显 | 机制稿 §3.5 前置 | 1 |
| `review-import` | `--task <id> --round <n> --slot <id> --report <绝对路径>`（round/slot 取 launch 回显值） | `review.import` | 导入与锚点核对（机制稿 §9.2） | 机制稿 §3.2 锚点 | 1 |
| `review-decide` | `--task <id> --round <n> [--plan <path>] [--unavailable <path>]`（`--plan` 为逐条 finding 处置，元素 `{finding, decision_ref, reason}`；`--unavailable` 为人声明的审查环境不足及证据） | `review.decide` | 审查判定（**由入口按机制稿 §9.2 的事实推导**，不是人选）与逐条处置 | — | 1 |
| `archive` | `--task <id> --decision <path>`（人调用 finish 的证据 + 提交授权 `commit_grants`） | `task.archive` | 正常归档（由 `wf-finish` 调用） | 机制稿 §3.5、机制稿 §9.3 门禁 | 1 |
| `baseline-apply` | `--task <id> --proposal <path>` | `baseline.apply` | 基线/配置成组应用 | 机制稿 §3.4 | 1 |
| `spec-update` | `--task <id> --changes <path>` | `spec.update` | 知识变更成组应用 | 机制稿 §3.1、§8.4 | 1 |
| `definition` | `prepare --id <workflow-id>`（建立准备代次） \| `validate --id <workflow-id>`（只读校验） | `definition.prepare` / `definition.validate` | 准备定义 / 静态校验 | 机制稿 §3.1、§7.2 | 2 |
| `run` | `create --creation <path>`（建立实例代次并首次绑定） \| `advance --run <id> [--decision <path>]` \| `pause --run <id> --reason <text>` \| `locate --run <id>`（只读） \| `terminate --run <id> --plan <path>`（信封） | `run.advance` / `run.terminate`（`create` 由 writer 主记录承载首次创建与首次绑定、`pause` 是该动作的受控字段写入、`locate` 是只读断言） | 实例创建、推进与终态 | 机制稿 §7.3、机制稿 §7.4 | 2 |
| `upgrade` | `--apply`（预览 + 令牌） | `asset.apply` | 维护（机制稿 §10.3） | 全路径 | 3 |
| `repair` | 转交 `repair.py`（预览 + 令牌）；第二形态 `--dispose <plan>` 做维护组处置回写（见本文 §4.6） | `repair.apply` | 受控修复（机制稿 §5.4） | 机制稿 §5.4 | 1（写权/绑定/锚点最小恢复）、3（全部资产修复） |
| `uninstall` | 转交 `uninstall.py`（`--purge` 单独确认） | `uninstall.apply` | 退出（机制稿 §10.5） | 机制稿 §10.5 | 1（开发态退出）、3（purge 与发行清单） |
| `confirm-executor` | `--scope system\|global\|project` | 引导层例外（机制稿 §8.2） | 无（只写 `~/.wf/interpreters.json`） | — | 1 |
| `version` | `[--json]` | 只读 | 无 | — | 1 |

**结构化人工输入（约定）**

人的决定只有两种承载方式，其余一律不塞进命令行：

- **封闭枚举（可留在命令行）**：取值由机制稿固定、不超过三个值的「选一个」开关——`task-knowledge --decision no-update|updated`——这两个值由**本文**定义，语义取设计稿 §6.3（「本次无更新」与「新增/更新/合并/改名/删除后的结论」），机制稿 §1.3 只登记 `knowledge` 的三个字段、未登记值域，因此扩展值域须先回机制稿登记；`run pause` 等带说明文本的子动作不在此列（它们有 `--reason`）。审查结论**不是**封闭枚举：pass/fail 由入口按机制稿 §9.2 的事实推导，只有「环境不可用」需要人声明（`--unavailable <path>`）。
- **JSON 文件（承载具体内容）**：
  - `--decision <path>`：单条 `Decision` 或其数组，结构照机制稿 §1.1；`subject` 写该决定覆盖的对象与具体路径，`choice` 取机制稿已登记的取值。用于 `task-approve`（批准）、`stop`（**收工选择一条** + 提交/反向修正授权若干条）、`archive`（finish 调用证据 + `commit_grants`）、`run advance`（人判答复）。
  - `--plan <path>`：**对象级**批量处置计划，元素为 `{object|finding, decision_ref, reason}`；只用于实例批量终止（`run terminate`，元素是任务）与审查逐条处置（`review-decide`，元素是具名 finding）。它不表达「同一组路径各用不同处理」——收工是单一选择（机制稿 §4.3 的 `decision` 只有 commit/keep/reverse/transfer 四值，wip 记录的 `paths` 只存逐路径状态、不含 per-path choice），混合去向要先改机制稿该节的 wip schema，属机制侧变更。

其余领域文件沿用各自名称（`--launch-request`、`--creation`、`--proposal`、`--changes`、`--review-notes`、`--evidence`）；文件只承载人的决定，不承载身份（身份只走信封）。

**证据与裁定的输入通道（Check / 复盘）**

Check 的固定五步里有四类事实脚本无法自造，各自的入口如下（都不新增判定，只是把既有人判与材料落到机制稿已有的字段）：

| 事实 | 输入 | 落点 |
|---|---|---|
| `argv` 验证结果 | 入口按批准声明执行并自行取证；无输入参数 | `check.commands` |
| `manual` 验证与 `verification_ids` 为空的验收 | `--decision <path>`：每条 Decision 的 `subject` 记 `verification_id` 或 `acceptance_id` 与当前 `plan.version`；**不要求文件预含 `check.anchor`**——本次 `check_anchor` 要到 Check 内部才算得出，由入口在写入 `acceptance_results` 时把该 Decision 核绑到本次锚点并在记录里补记 | `check.commands`（manual）/ `check.acceptance_results` |
| 内部双轴审查 | `--review-notes <path>`：标准轴与需求轴各一段结论与依据；它是材料，不是人的决定 | `check.internal_review` |
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

  `slots` 至少一项：两项且每个 `reviewer_cli` 与 `implementation_clis` 全项不同、彼此也不同时满足复杂任务的完成条件；只有一项时**同一命令照常放行**（人声明环境不足，见本文 §5.3），入口只在 `task.reviews.launches` 记 `degraded: single-provider`；判定由 `review-decide` 按机制稿 §9.2 给出（单 reviewer 属「人数不合格」，结果为 fail），degraded 事实随 `reviews.result` 引用的 launches 条目呈现，**不写入 result 字段**（该字段写者与取值见机制稿 §9.2）。**槽位 id 即 `--reviewer-id`**：同一字符串用于暂存目录层名、报告文件名与导入槽位，不设第二套标识。
- `run create --creation <path>` 给定义 id 与内容哈希、输入值/引用、步骤适用性与顺序展开规则的人确认引用；入口据此固定快照、创建实例并完成首次绑定（writer 主记录）。`run terminate --plan <path>` 给逐任务放弃/保留的批量处置（元素为任务，不是路径）。

**`task.retrospect` 的登记说明**：2026-11-02 人裁「复盘作为独立机制操作」，机制稿 §11.3 的状态动作集合与机制稿 §5.1 的主记录归属已同批登记 `task.retrospect`（`control.task.retrospect` 随之按该节公式派生），门禁侧仍由机制稿 §11.2 的 `task.retrospective-done` 核验。本文只给命令与落点：处理器 `wflib/tasks.py::retrospect`，写入 `task.retrospective`，并在同一 action 内写 `task.retrospective-done` 的 completed 回执（机制稿 §11.2 的回执写者句；人裁 ①：该操作即该步骤的执行入口）。该操作不新增判定，只把一个已有记录字段提升为可独立期次化的动作。

**没有公开子命令的机制操作**：`verification.resolve`、`asset.compare` 作为只读断言由内部调用（`task-start`/`task-check`/`archive`/`run` 内部步骤）暴露，不单设命令；`run` 的子动作按机制稿 §5.1、§7.2、§7.4 由 writer 主记录与 `run.advance` 承载（实例首次创建与暂停都不是独立操作名），第二轮随实例能力一起交付。**操作名不自动新增公开命令**：本表之外的任何操作名不因为存在于机制稿就成为命令；新增命令必须同时满足「映射到已登记机制操作或已定义只读查询」与「在本文与用户文档同批登记」。

### 2.4 输出契约

所有子命令返回机制稿 §11.1 的单一结构（字段名与语义以该节为准，本文不重述，只列名称供实现对齐）：`{tier, code, object, position, next, facts, exit, prohibited_repairs, warnings}`：

- `--json` 打印该结构的规范 JSON（`C(x)` 规则，机制稿 §1.1），供脚本与审查核对；默认输出由 `wflib/cli.py::render()` 渲染为人读文本，**两路同源**，不各造字段。
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
| installed（已安装） | `python3 /abs/path/<项目>/.wf/bin/wf.py <子命令>`（任意 cwd） | 由脚本真实位置解析项目根并核对 `.wf/bin` 布局 | 布局/目标无法确认 → `WF_CAPABILITY_UNAVAILABLE` |
| 项目根内短称 | `python3 .wf/bin/wf.py <子命令>` | 同上（不依赖 cwd 选择项目） | 同上 |
| 源码/重取入口 | `python3 <重取路径>/wf.py --project <目标绝对路径> <子命令>` | 只接受显式绝对路径；不把源码目录或 cwd 当目标 | 缺 `--project` → `WF_PATH_INVALID` |

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
    --source <已检出的发行目录> --skill-root <投放根绝对路径> [--skill-root <另一个根>] [--confirm]

python3 <目标>/.wf/bin/wf.py upgrade --apply --release-ref <refs/tags/wf-vX.Y.Z> \
    --source <已检出的发行目录> [--skill-root <投放根绝对路径>]
```

`--target` 必填且为绝对路径（不把源码目录或 cwd 当目标）；`--release-ref` 只接受已登记发行引用，解析到 commit 后核 `wf-release.json` 与资产哈希；应用阶段把该清单**原样写入** `.wf/install/release-manifest.json`，再与 `installation.json.manifest_digest` 比对（不一致即 `WF_PERSISTENCE_FAILED`）；`--skill-root` 可重复，省略时用安装记录里已确认的根；`--confirm` 表示人在终端确认预览（缺省时入口先出预览并要求交互确认）。升级不需要信封（维护入口，见本文 §2.2）。

### 4.2 `wf-release.json` 键表

| 键 | 值来源/生成 | 消费 |
|---|---|---|
| `schema_version` | 固定 `1` | 清单解释版本 |
| `version` | 人定版本（`0.x.y`），与 tag 一致 | 可发现标识；不参与兼容判断 |
| `compatibility.python_min` | `{major: 3, minor: 11}` | 执行器确认与自检 |
| `compatibility.systems` | `["linux"]` | 锁能力与安装声明 |
| `compatibility.filesystems` | `{local_only: true, advisory_flock_required: true, network_or_sync_supported: false}` | 装前能力核实 |
| `compatibility.record_versions` | `{task, binding, preparation, run, writer, installation, config, spec}` 各 `{read: [1], write: 1}` | 记录兼容 |
| `compatibility.workflow_versions` | `{read: [1], write: 1}` | 用户定义格式 |
| `compatibility.rules_digest` | 由 `compute_rules_digest()` 计算（本文 §4.3） | `effective_rule_version` |
| `assets` | 打包脚本生成：`source_path`、`target_class`、`target_relative`、`kind`、`required`、`file_kind`、`executable`、`digest` | 安装/升级/自检/卸载 |
| `required_steps` | 由流程文档的 `[required · once\|repeatable]` 标记与固定 id 集合双向核对生成（机制稿 §11.2） | 门禁与自检 |
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
- 第三轮的 `upgrade --apply` 用 `wflib/maintenance.py::preview/token_confirm` 实现同一规则，算法仍是这一份说明，不另立格式。

### 4.6 首轮开发态部署

首轮尚无正式发行引用（机制稿 §12.1 D22 属第三轮）。按设计稿 §8.1 的「首轮所需最小安装与自检按开发态部署处理」：

- 入口：`python3 scripts/wf-dev-deploy.py --target <目标项目绝对路径> --skill-root <投放根绝对路径> [--skill-root <另一个根>] [--confirm]`（authoring 开发工具）；`--skill-root` 可重复、至少一项，值写入 `installation.json.roots`（项目内根记相对路径、项目外根记绝对路径），缺省候选 `.agents/skills/` 只作提示不作默认；不带 `--confirm` 时只打印预览（目标、文件清单、`.wf/`/`writer.json`/`.wf-lock`、托管段、skill 根、Trellis 资产风险提示）后退出，不做任何写入；带 `--confirm` 才按 `dev-manifest.json` 投放 `.wf/` 资产与 skill 根副本，写 `.wf/install/installation.json`（`release_ref` 记 `dev:<git describe>`，`version` 记 `0.0.0-dev`，`manifest_digest` 记部署清单摘要），并写入 `.gitignore` 托管段。`dev-manifest.json` 只登记资产清单、版本与必需标记，**不含手填字节哈希**；`wf-dev-deploy.py` 按源树实际字节现算每个资产的 `digest`、模板标记与 `rules_digest`，生成部署副本 `.wf/install/release-manifest.json`（与正式清单同 schema，运行期唯一读取入口，见本文 §4.2.1）——算法与 `scripts/build-wf-release.py` 同一份（同名函数），首轮锚点因此可复现。
- **Trellis 互斥风险提示**：预览固定列出已发现的 Trellis 线索（`.trellis/` 数据、hook 配置、项目指令文件中的 Trellis 托管块），并说明「人确认后可继续安装，但本会话不得混跑两套流程」（设计稿 §3、§7.1）。
- **维护组处置回写**：人确认维护组去向（独立提交 / 反向修正 / 具名承接 / 保留现状）后，由 `.wf/bin/repair.py --dispose <plan>` 写回原维护回执的 `disposition` 与真实路径状态。**解除条件只有上位规定的三条**：该组路径已被独立提交、已完成反向修正、或已由具名任务承接（承接任务已批准、路径归属明确）。**「保留现状」只留痕，不解禁**——回执仍按「已应用待提交」挡住重叠路径，直到其中一条实际落实。依据是设计稿 §5.5 的对象列举（「未收工关闭的写权、绑定/写权不明、**维护/交接残留**」）与机制稿 §4.5 的「入口将实际去向写回原回执」（该条未指定入口）；机制稿 §5.4 只有算法与边界句（repair 不代替日常删边、内容修改或范围批准），本条不越出该边界——处置回写只记录人已确认的去向，不改交付内容。三条之一落实并写回后，该回执在读取侧落「已处置」态：不再阻断重叠任务，但回执与处置证明保留，直到下一次维护预览按机制稿 §4.5 把它收敛出 `maintenance_results`；`disposition` 缺处置决定、缺核验事实或缺承接引用，或只记了「保留现状」时，仍按「已应用待提交 / 待核对」分别处理。**若人选择「按登记终态原样提交」则不需要这一步**：下一次启动按机制稿 §4.5 的可达提交查证直接派生 `persisted`，不改写回执。
- **首装契约（与正式安装同构）**：按设计稿 §4.4 的首装例外，dev-deploy 在同一最小互斥内先创建 `.wf-lock`、`.wf/` 与 `.wf/writer.json`（初始维护持有，`holder.kind=maintenance` 且带本次操作标识、`generation` 从 0 起递增），把这三项列入预览清单；投放与自检通过后释放为空闲（`state=idle`、`holder=null`），不保留伪会话写者。没有 `writer.json` 的项目不算已安装（机制稿 §4.2「缺 writer 或缺锁且有既有记录不视为首次安装」）。
- 自检：投放后核对资产哈希、skill 路由、`required_steps` 与已实现处理器的一致性、托管段忽略生效、`wf.py status` 可达；缺项按 `WF_CAPABILITY_UNAVAILABLE` 报告并保留维护检查点。
- 与正式发行的差异只在「身份来源」与「清单生成方式」；记录 schema、判定编码、命令面完全相同，避免首轮产物在第三轮被整体重写。

## 5. 审查适配

### 5.1 两副本与协议

| 副本 | 角色 | 关键约束（机制稿 §9.1） |
|---|---|---|
| `<skill 根>/wf-review` | reviewer 侧 | 只在给定暂存路径写报告；不写项目树、不改源码/控制字段、不提交；参数 `--task-id`、`--round`、`--reviewer-id`（= 槽位 id）必备，`--review-focus` 由 wf 侧总提供 |
| `<skill 根>/wf-review-action` | action 侧 | 读指定轮次报告并先汇总再决策；不代替主会话修改源码 |

**调用交接**：`review-launch` 为每个槽位在暂存目录写 `<staging>/request.json`（`task-id`、`round`、`reviewer-id`、`review-focus`、`check-anchor`、材料范围与排除项），并向终端打印一段**人可粘贴到 reviewer CLI 会话的 skill 调用文本**：

```
/wf-review --task-id <id> --round <N> --reviewer-id <slot> --review-focus <检查轴> --request <staging>/request.json
```

它不是 shell 命令：框架不安装名为 `wf-review` 的可执行入口，也不做 PATH 安装或 shell shim（本文 §2.1）；投放物只有 `<skill 根>/wf-review/SKILL.md`。宿主不能按文本调用 skill 时，由人在 reviewer CLI 中打开该 skill 并把 `<staging>/request.json` 作为唯一输入；skill 正文负责读取该文件与授权范围，报告写到 `<staging>/report.md`，不读项目树内的控制记录，导入由主会话完成（本文 §5.2）。

报告格式：Markdown 正文 + 唯一带协议标记的 JSON 块 `<!-- wf-review-report:v1 -->`，块内 `protocol` 取 `wf-review-v1`，字段按机制稿 §9.1 的 `task-id`/`round`/`reviewer-id`/`source-cli`/`review-time`/`review-focus`/`check-anchor`/`read-scope`/`excluded-scope`/`scope-exceptions`/`axes`/`findings`/`verdict`。不支持版本拒绝导入（`WF_REVIEW_INVALID`）。

### 5.2 暂存目录与导入

- 发起时由 `review-launch` 输出确切暂存目录：每槽位一个 `<临时根>/wf-review/<project_id>/<task-id>/round-<N>/<slot>/`，并把全部槽位目录记入 `task.reviews.launches.temp_paths`。父目录不开放。槽位 id（`--slot`）与 reviewer 自报的 `--reviewer-id` 是同一字符串，暂存目录层名与报告文件名都用它。
- reviewer 写 `report.md`；主会话在**自己持有设计稿 §4.4 的写入权**时，重算当前锚点、核对元数据与槽位字段，再以同目录临时文件 + 原子发布写入 `<task-dir>/review/review-round-<N>/<slot>.md`（`<task-dir>` 是由稳定 id 解析出的**真实任务目录** `<task-id>-<slug>`，不是把 id 直接当目录名拼出来），读回哈希并更新 `reviews.imported`（机制稿 §9.2）。导入期间写权不转移。
- 暂存目录在导入成功且摘要/元数据核对后成为可清理项，由人确认后清理；未导入、冲突或恢复中的轮次默认保留。卸载/`purge` 清单只列残留位置，不授予删除权限。

### 5.3 自报身份与对象锚点

主会话交给 reviewer 的锚点：`check-anchor`（`check.id` + 机制稿 §3.2 定义的 `check_anchor`，含 Check 内容指纹、规划版本、相关 spec 与项目配置哈希、基线与定义快照哈希；逐键定义与计算只在该节，本文不重列）。导入前重算并与报告比对，不一致即该报告失效、按审查未通过处理（`WF_REVIEW_INVALID`），不导入为有效结论。

`source-cli` 是自报字段，只与人工声明核对，不是身份认证（设计稿 §1.5）。人数与差异按机制稿 §9.2：两个 reviewer CLI 彼此不同、且不在本次实施 CLI 集合中；只能凑一个时用同一 `review-launch`（`slots` 只列一项）发起，入口在 `launches` 记 `degraded: single-provider`；`review-decide` 按机制稿 §9.2 判 fail（单 reviewer 属人数不合格），degraded 事实由 result 引用的 launches 条目呈现，不另写 result 字段；复杂任务仍按机制稿 §9.2 暂停或异常归档。

### 5.4 首轮为何必须就绪

机制稿 §12.1 把 D25（身份声明与报告核对）、D26（读取/外发范围、报告写权与导入）、D31（副本投放/升级/卸载覆盖）定为**跨轮基础项**，理由是首轮的初始化任务或治理面命中任务可能即属复杂；复杂任务的正常归档要求对应当前对象的实际审查 pass（charter T4、设计稿 §6.5）。因此首轮若无成对适配，任何复杂任务都只能暂停或按机制稿 §6.4 异常归档，首轮闭环实际不可用。首轮因此交付：两副本投放 + `review-launch`/`review-import`/`review-decide` + 锚点核对；完整发行生命周期（三方升级、卸载覆盖的验收矩阵）留在第三轮。

## 6. 首轮最小闭环实现清单

### 6.1 轮次分界与「能力不可用」的表达

- 首轮 = 机制稿 §12.1 的全部「跨轮基础项」；第二轮 = D03、D07（返工/替换/建删边部分）、D11、D12、D13；第三轮 = D22 的发行引用与清单解析、D31 的完整发行生命周期、D37 的正式发行入口、D09 的全部资产修复验收、D28 的升级/purge 令牌路径、D33 的落点表全部适用分支验收。
- 未交付能力的命令**必须已存在且可调用**，行为为 `tier=blocked`、`code=WF_CAPABILITY_UNAVAILABLE`、`facts` 记未交付能力与所属轮次、`exit` 给「等该轮交付」或「改用已交付路径」。不存在的命令不得在文档与 skill 中宣称。

### 6.2 逐条落点（D01–D38）

| D | 义务 | 首轮落点（文件/函数/命令） | 轮次 | 验收场景行（设计稿 §8.2） |
|---|---|---|---|---|
| D01 | 任务 schema、状态/阶段、判定字段写者 | `wflib/records.py`（读取拒绝重复键/NaN、原子替换、未知字段保留）、`wflib/tasks.py::load/save`、`.wf/templates/task/task-record.json` | 跨轮 | `规划授权`、`未提交记录存在性` |
| D02 | skill/机制操作归属、只启用未绑定路由 | `<skill 根>/` 下 `wf-start`、`wf-continue`、`wf-finish`、`wf-bootstrap`、`wf-spec-update` 的 frontmatter 与正文路由、`wflib/cli.py::cmd_enable` | 跨轮 | `入口与基线子路由`、`会话固定绑定` |
| D03 | 准备定义/创建实例路由、静态与消费校验 | `wflib/runs.py::prepare/validate`（未交付：`WF_CAPABILITY_UNAVAILABLE`） | 第二轮 | `准备定义与自举`、`定义有界校验` |
| D04 | 批准触碰面、规划版本、复杂度/TDD（含治理面判定） | `wflib/tasks.py::approve_plan`、`wflib/paths.py::parse_touch_paths`、`wflib/scope.py::governance_condition` | 跨轮 | `规划授权`、`机读触碰面`、`复杂度分级一致性`、`TDD 开关` |
| D05 | 路径集合与内容指纹、检查有效性 | `wflib/fingerprint.py::items/content_digest/check_anchor`、`wflib/check.py::run_check` | 跨轮 | `同路径交替`、`指纹内容源`、`最终知识变更` |
| D06 | 未提交路径归属、外部变更与提交边界 | `wflib/scope.py::classify_candidates/check_external_changes`、`wflib/tasks.py::attribution` | 跨轮 | `机读触碰面`、`共存与重装`、`紧急变更边界` |
| D07 | 依赖建删边、返工/替换/放弃 | `wflib/tasks.py::abandon`（首轮仅机制稿 §6.4 的单任务路径）；`dependency.change`/`task.rework`/`task.replace` 未交付 | 第二轮（首轮异常退出走单任务放弃路径） | `异常归档边界`、`放弃改动处置`、`返工接续` |
| D08 | 跨任务目标碰撞预检、记录级幂等指纹 | `wflib/actions.py::action_id/begin/apply_steps/reenter`、`wflib/tasks.py::preflight_collisions` | 跨轮；第二轮加入全部依赖/实例目标 | `数据与恢复`、`受控修复` |
| D09 | repair 预览/确认/验证/留痕、关闭残留、历史锚点、不可解析记录 | **全部逻辑自含于 `.wf/bin/repair.py`**（预览、令牌、受控应用、回执、留痕；不导入 `wflib`，坏运行时下仍可达；首轮覆盖写权残留/绑定/锚点，资产修复第三轮）。`wflib/maintenance.py` 不承载 repair 的应用逻辑 | 跨轮+第三轮 | `受控修复`、`历史锚点不可达`、`所有权中断恢复` |
| D10 | 读未知字段保留、写回不丢未知字段 | `wflib/records.py::merge_unknown`（读写同源） | 跨轮 | `数据与恢复` |
| D11 | 工作流格式、准备/自举、动作与验证边界、固定快照及版本维护 | `wflib/runs.py::load_definition`（未交付） | 第二轮 | `定义与实例固定`、`验证分时解析` |
| D12 | 步骤人判/略过、动作消费、自动任务/边与幂等映射 | `wflib/runs.py::advance`（未交付） | 第二轮 | `人判与略过`、`顺序依赖授权` |
| D13 | 实例正常结束、批量异常终止、保留任务独立接续 | `wflib/runs.py::finish/terminate`（未交付） | 第二轮 | `实例正常与异常终态`、`实例放弃与保留` |
| D14 | 稳定会话身份、持久绑定、历史按需读取 | `wflib/session.py::session_key/identity_check/bind` | 跨轮 | `会话固定绑定`、`压缩与新会话`、`无稳定会话身份`、`绑定历史按需读取` |
| D15 | 会话/维护写者、原子获取/释放、两段交接与旧代次失效 | `wflib/writer.py::acquire/release/handover_begin/handover_accept`、`wflib/lock.py` | 跨轮 | `单工作区串行写入`、`释放与显式交接`、`所有权中断恢复` |
| D16 | 同对象 WIP 收工/恢复限制 | `wflib/writer.py::stop_work/check_wip` | 跨轮 | `日常收工`、`暂停插单恢复` |
| D17 | 项目配置类型/范围/缺省、自举骨架 | `wflib/config.py::load_project_config`、`.wf/templates/project-config.skeleton.json` | 跨轮 | `流程与配置`、`初始化自举` |
| D18 | spec 预算键、计数范围、数值缺省及降级 | `wflib/spec.py::load_with_budget`（码点计数、`超预算完整读取` 标注） | 跨轮 | `spec 预算`、`读取留痕完整性` |
| D19 | 命令引导、installed/源码目标、坏配置独立恢复 | `.wf/bin/wf.py` 引导段、`.wf/bin/repair.py`、`.wf/bin/uninstall.py` | 跨轮 | `本地命令引导` |
| D20 | Python 三级解析、缺系统 Python 的已有配置出口 | 解析与确认都在引导层（`wf.py` 第 3 步 `confirm-executor` 写确认元组、第 4 步解析并匹配，唯一实现）；`wflib/config.py` 只读取解析结果与确认记录，不重复实现解析与匹配 | 跨轮 | `Python 执行器` |
| D21 | 执行器探测/确认、首次写入批准、项目标识匹配 | `wf.py` 引导层第 3 步的 `confirm-executor`（探测 + 写确认元组 + 解析时元组匹配，单一实现）、`project_id` 生成与 repair 重建；`wflib/config.py` 只读项目配置与确认记录用于展示/诊断，不做匹配判定 | 跨轮 | `执行器配置可信`、`执行器确认绑定`、`确认记录身份`、`项目标识生命周期`、`执行器首次写入` |
| D22 | 发行引用与本地清单解析 | `wflib/assets.py::parse_release`（安装/升级时解析发行引用，第三轮）；`wflib/assets.py::load_installed_manifest` 读 `.wf/install/release-manifest.json`（运行期唯一入口，首轮即需要；来源为 `dev-manifest.json`） | 第三轮 | `发行身份` |
| D23 | spec 三时点加载、策展/读取侧车、排序/预算 | `wflib/spec.py::match/sort/record_read`、`wflib/curation.py` | 跨轮 | `spec 正向积累`、`spec 跨任务复用`、`读取留痕完整性` |
| D24 | 本地 spec 全部变更、持久引用统计/治理 | `wflib/spec.py::update`、`wflib/spec.py::curation_stats`、`wf.py inspect` | 跨轮 | `知识删除与依赖解除`、`策展引用统计`、`无 MCP 全流程` |
| D25 | 审查身份声明、报告核对及新鲜度 | `wflib/review.py::launch/verify_anchor`、`<skill 根>/wf-review` | 跨轮（首轮就绪） | `审查 CLI 身份确认`、`审查与正常完成（charter T4）` |
| D26 | 审查读取/外发范围、报告写权与导入 | `wflib/review.py::import_report`、`<skill 根>/wf-review-action` | 跨轮（首轮就绪） | `审查材料外发`、`审查读取范围`、`审查报告写权`、`审查回执锚定` |
| D27 | writer 公共字段与维护回执隔离、整文件提交 | **读取与派生首轮即落 `wflib/writer.py::receipt_state()`**（读 `.wf/writer.json` 的 `maintenance_results`，按机制稿 §4.5 把**每一项回执**派生为四态：**已持久化**（可达提交查证成立）/ **已应用待提交**（`applied_pending_commit`，未提交或提交失败但结果可核）/ **已处置**（`disposed`：**只有**满足设计稿 §4.4（维护变更持久化）与机制稿 §4.5 的三条之一才算——该组路径已被独立提交、已完成反向修正、或已由具名任务承接且承接任务已批准、路径归属明确；`disposition` 须同时记处置决定、核验事实与承接引用。**「保留现状」不在此列**：它只留痕（决定、风险、待处置项），回执仍按「已应用待提交」处理）/ **待核对**（事实不明或记录不可解析）。这里判的是回执 `result` 层面，与 `writer.state` 的 idle/held/recovering 不是同一枚举。消费口径：只有「已应用待提交」（含人选择「保留现状」的回执）且与本次请求对象/路径范围重叠时挡（`WF_WIP_UNRESOLVED`）；「已处置」不挡重叠任务，但回执保留、报告为「已处置未收敛」；「待核对」报 `WF_HISTORY_UNRESOLVED`。解除阻断看 `disposition` 的核验事实与承接引用是否成立，不看字段是否存在；把回执移出 `maintenance_results` 是下一次维护预览里的收敛动作，读取侧不做）；写入侧由 `repair.py` / `uninstall.py` 各自完成；`wflib/maintenance.py` 只承载第三轮 `upgrade` 的应用与回执收敛 | 跨轮 | `维护写者` |
| D28 | 预览令牌签发/校验 | 首轮：`repair.py` 与 `uninstall.py` 各自自含（nonce 生成、绑定预览摘要、同进程失效；规则见本文 §4.5.1，两处必须逐字一致，由发行自检用固定向量比对）。第三轮：`wflib/maintenance.py::preview/token_confirm` 服务 `upgrade --apply` | 跨轮+第三轮 | `判定物与原因码` |
| D29 | 固定原因码及输出三档 | `wflib/codes.py`（34 枚，只增不改义）、`wflib/cli.py::emit/render` | 跨轮 | `判定物与原因码`、`固定流转程序化` |
| D30 | 模板占位标记集 | `.wf/templates/**` 内占位符、`wflib/templates.py::check_markers` | 跨轮 | `判定物与原因码`、`规划授权` |
| D31 | 审查适配副本投放、三方升级和卸载覆盖 | 清单 `assets` 的 `wf-review`/`wf-review-action` 行、`wflib/assets.py::compare` | 跨轮（首轮投放）+第三轮 | `审查适配副本`、`资产落点` |
| D32 | 锁原语、落点、支持范围与存活探测 | `wflib/lock.py::acquire_lock/verify_holder/proc_start` | 跨轮 | `互斥与锁生命周期`、`锁删除与人工清理`、`锁文件归属` |
| D33 | 资产类型/落点/所有者/升级卸载覆盖表 | 本文 §1.2；安装/卸载入口的路径来源 | 跨轮；第三轮验收全部适用分支 | `资产落点` |
| D34 | 最终门禁与正常/异常完成边界 | `wflib/gates.py::final_gate`、`wflib/tasks.py::archive` | 跨轮 | `审查与正常完成（charter T4）`、`异常归档边界`、`规划授权` |
| D35 | 每条门禁到验收场景的映射 | 本文 §7.2；`scripts/validate-wf-design.py` 的场景映射检查（机制稿侧） | 跨轮 | 全部场景行（映射面） |
| D36 | 每个固定 required 步骤的执行/检查面 | `.wf/workflows/*.md` 的 enforcement 行、`wflib/gates.py::HANDLERS`（id → 处理器）、`wflib/tasks.py::retrospect`（`task.retrospect` 状态动作；写 `task.retrospective` 与 `task.retrospective-done` 的 completed 回执） | 跨轮 | `固定流转程序化` |
| D37 | 最小安装/自检、完整安装/升级/退出 | `scripts/wf-dev-deploy.py`、`.wf/bin/uninstall.py`（开发态退出）；`install.py`/`upgrade --apply`/`purge` 未交付 | 跨轮+第三轮 | `资产落点`、`Git 就绪`、`本地命令引导` |
| D38 | 机制/实现分工、使用速查与后续验证责任 | 本文 §0、本文 §8 | 跨轮 | `固定流转程序化`、`本地命令引导` |

### 6.3 首轮下限对齐（设计稿 §8.1）

| 下限项 | 首轮落点 | 覆盖方式 |
|---|---|---|
| 任务 schema | `wflib/records.py`、`wflib/tasks.py`、`templates/task/task-record.json` | 记录读写 + 未知字段保留 + 原子替换 |
| 写权与锁 | `wflib/lock.py`、`wflib/writer.py` | 原子获取/释放/交接 + 代次校验 + 存活线索 |
| 状态/门禁结构判定 | `wflib/tasks.py::transition`、`wflib/gates.py` | 状态迁移表 + `required_steps` 分派 |
| 内容指纹与检查有效性 | `wflib/fingerprint.py`、`wflib/check.py` | `check_anchor` 全键计算 + 锚点比对 |
| 开工与最终门禁 | `task-start`、`archive`/`wf-finish` | 开工核对序列 + 八项门禁 |
| 策展清单与读取留痕 | `wflib/curation.py`、`wflib/spec.py` | 持久策展 + 会话侧车 |
| 归档与终态 | `wflib/tasks.py::archive` | 目录移动 + 终态 + 提交后只读派生 |

### 6.4 第二轮与第三轮单列（未交付前只报告能力不可用）

| 轮次 | 条目 | 未交付时的行为 |
|---|---|---|
| 第二轮 | 定义准备与静态校验、实例创建/推进/暂停/终止、步骤人判与略过、自动建任务与顺序边、返工/替换/建删边、挂起复评 | `definition`/`run`/`dep`/`task-rework`/`task-replace`/`task-reassess` 返回 `WF_CAPABILITY_UNAVAILABLE`，facts 记「第二轮交付」，exit 记「等第二轮」；已可用的单任务放弃路径照常走 `task-abandon` |
| 第三轮 | 正式发行引用与清单解析（D22）、`install.py` 与完整升级/卸载生命周期（D37/D31）、`upgrade --apply` 与 `uninstall --purge` 的令牌路径（D28）、落点表全部适用分支验收（D33）、全部资产修复验收（D09） | `upgrade` 返回 `WF_CAPABILITY_UNAVAILABLE`；`repair` 只做写权/绑定/锚点最小恢复，资产缺失类修复杂交第三轮；`uninstall` 只做开发态退出 |

**首轮与复评触发的关系**：机制稿 §5.3、§5.4 要求每次归档持久化核实成功、以及每次启动校验通过后触发挂起复评。首轮不会出现挂起任务（挂起源于返工，属第二轮），因此这两处触发在首轮按**空挂起集合**处理：直接通过、不写记录、不产生待决项，也不得返回 `WF_CAPABILITY_UNAVAILABLE`（否则每次归档/启动都会留下无法补做的待复评）。`task-reassess` 的完整路径与有挂起任务时的复评属第二轮。

## 7. 验证与验收映射

### 7.1 实现阶段五条最小验证顺序

失败归因固定：**先判实现缺陷并修实现；只有实现正确而现有事实不足以判定时，才回修机制稿**（机制稿 §12.4）。下列全部标「未运行」。

| # | 验证对象（机制稿 §12.4） | 夹具 | 初态 | 触发 | 预期输出三要素 | 归因规则 |
|---|---|---|---|---|---|---|
| V1 | 宿主会话身份能力（机制稿 §1.4） | F1 | 已开发态部署，`.wf/` 无绑定、`writer` idle、`session_profile.capability=unknown` | `wf-start` → `enable` → `task-new`（一次完成写权获取、首次绑定与任务创建）；再重复调用 `enable`、压缩后调用、新会话按就绪选择 `bind --task <id>` 接续、标识丢失后恢复 | pass：`WF_OK`，position 含 `scope=session` 与绑定对象；needs_decision：`WF_IDENTITY_UNRESOLVED`，facts 列未核实的稳定性/传递事实，exit 给核验或 wf 签发路径；blocked：`WF_CAPABILITY_UNAVAILABLE`（已确认不支持该传递） | 首次绑定/压缩后恢复/新会话接续任一环节失败先判适配实现；该宿主全部身份路径不成立才回修身份编码，不先扩平台矩阵 |
| V2 | 恢复协议跨记录组合（机制稿 §5） | F1 | 任务位于 `finish`，归档已提交但进程未报告；随后同一实例文件被另一合法动作推进改写 | 独立进程重入 `status` 与 `archive` | pass：`WF_OK` 且报告「归档已持久化」；派生事实含该归档动作 `head_before` 为下界的可达提交查证；blocked：`WF_ACTION_INCOMPLETE`（动作事实可定位但未完成）；needs_decision：`WF_HISTORY_UNRESOLVED`（锚点/记录来源待核，出口为只读核对后 repair）；facts 给待核对项；不得出现重复归档/重复提交 | 先查「字段隔离/可达提交查证」实现；只有区分不了「未执行」与「已执行」才回修恢复机制 |
| V3 | 维护组与后续任务共存（机制稿 §4.5） | F1 | 开发态 `repair` 完整应用并留回执、无提交授权 | 依次：不重叠任务开工并归档 → 重叠任务尝试开工 → 人明确处置维护组 → 恢复推进 | 不重叠任务 pass（`WF_OK`，不带入维护组）；重叠任务 blocked（`WF_WIP_UNRESOLVED`，facts 给路径组）；处置后 pass；writer 整文件未被无授权提交 | 失败先查 `writer` 公共字段与 `maintenance_results` 的字段隔离实现，不新增维护账本 |
| V4 | 复杂任务审查链路（机制稿 §9、§12.1 D25） | F2 | 复杂任务 Check pass，锚点已固定；已评测出两个异种 reviewer CLI | `review-launch` → 两个 reviewer 在暂存目录产出报告 → `review-import` → `review-decide` → `finish`；随后改一个交付文件再导入旧报告 | 首次全链路 pass（`WF_OK`，锚点核对通过）；改交付后 blocked（`WF_REVIEW_INVALID`，facts 记锚点失配）；材料不足时 reviewer 停止并回报，主会话不得据此 pass | 缺 CLI 只证明该环境不满足条件，不降审查要求；只有材料在既定读取边界内仍无法覆盖固定检查面，才形成机制回修依据 |
| V5 | 调试计数与复盘（机制稿 §1.3、§8.1、§11.2） | F2 | 同一 `verification_id` 的失败分布在 `check_history` 与 Execute 期声明 | 观察三种形态：单次 Check 内失败后重试成功；失败先声明后进入检查历史；复盘完成后再出现新触发事实 | 重试不产生 `check_history` failed 条目、机械检测不计数；合并累计跨阈值时 needs_decision（`WF_SEMANTIC_DECISION`，facts 记合并累计/阈值/倍数）；复盘后新触发使 P 与 occurrence 变化，归档前须补做 | 出现「重复判断而不改变结果」时优先收敛既有计算与消费方式，保留复盘承诺 |

### 7.2 门禁 → 设计稿 §8.2 场景行的实现侧验收矩阵

G 编号沿用机制稿 §12.2（该表已给门禁与场景行的对应），本表补「实现面」与「夹具」，不重述断言内容。

| G | 实现面（文件/命令） | 场景行（设计稿 §8.2） | 夹具 |
|---|---|---|---|
| G01 | 本文与 skill 正文的人工判据（charter T2/T3/T5/T6 消费） | `扩展与取舍（charter T2、charter T5）`、`边界与边界外出口（charter T3）`、`减法与停止（charter T6）`、`使用负担与缺口（charter T5）`、`演进判断顺序（charter T5）`、`保留机制必答（charter T6）` | F0/F1/F2 |
| G02 | 本文 §0、skill 遵循声明 | `效力与冲突（charter T1）`、`修订同批义务（charter T7）`、`等效替换（charter T4）`、`闭环四条件（charter T4）` | F0/F1/F2 |
| G03 | `wflib/paths.py`（边界/嵌套判定）、`wflib/assets.py::branch_source_check` | `多分支与嵌套仓库（charter T3）`、`分支来源核对` | F2 |
| G04 | `wflib/runs.py::load_definition/validate`（第二轮） | `用户定义零框架改造`、`定义有界校验`、`定义与实例固定`、`工作流兼容与迁移` | F0/F1 |
| G05 | `wflib/runs.py::advance`、`wflib/gates.py`（第二轮） | `单任务与多任务流程`、`准备定义与自举`、`验证分时解析`、`接续与任务归属`、`顺序依赖授权`、`人判与略过` | F0/F1 |
| G06 | `wflib/runs.py::finish/terminate`（第二轮） | `实例正常与异常终态`、`规划实例直接终止`、`实例放弃与保留`、`终止中断与历史校验`、`实例与产物隔离` | F1/F2 |
| G07 | `wflib/session.py`、`wflib/cli.py::cmd_enable` | `会话固定绑定`、`压缩与新会话`、`无稳定会话身份`、`会话实例标识`、`绑定历史按需读取` | F1 |
| G08 | `wflib/writer.py`、`wflib/lock.py`、`wflib/maintenance.py` | `单工作区串行写入`、`释放与显式交接`、`日常收工`、`所有权中断恢复`、`无 hook 强度`、`暂停插单恢复` | F1/F2 |
| G09 | `wflib/maintenance.py`、`wflib/writer.py`（字段隔离） | `维护写者`、`未提交记录存在性` | F1 |
| G10 | `.wf/bin/repair.py`（自含预览/令牌/应用/回执/处置回写）、`.wf/bin/uninstall.py`（自含）、`wflib/writer.py::receipt_state()`（首轮的只读派生，供启动校验⑩与 Check a 类）、`wflib/maintenance.py`（第三轮 upgrade 的维护路径） | `普通任务持久恢复`、`历史锚点不可达`、`数据与恢复`、`受控修复` | F1/F2 |
| G11 | `wflib/tasks.py::approve_plan/start`、`wflib/scope.py::governance_condition`、`scripts/wf-dev-deploy.py` | `入口与基线子路由`、`规划授权`、`初始化自举`、`Git 就绪`、`执行器首次写入` | F0 |
| G12 | `wflib/scope.py`、`wflib/fingerprint.py`、`wflib/check.py` | `机读触碰面`、`同路径交替`、`指纹内容源`、`最终知识变更` | F1/F2 |
| G13 | `wflib/cli.py::cmd_enable`（Trellis 互斥核对）、`wflib/scope.py`、`.wf/bin/uninstall.py` | `共存与重装`、`Trellis 互斥`、`紧急变更边界` | F2 |
| G14 | `wflib/tasks.py::abandon`（首轮单任务）、`task-rework`/`task-replace`（第二轮） | `返工接续`、`异常归档边界`、`放弃改动处置` | F1/F2 |
| G15 | `wflib/spec.py`、`wflib/curation.py`、`wflib/gates.py::final_gate` | `extracted 生命周期`、`spec 正向积累`、`spec 跨任务复用`、`知识删除与依赖解除`、`策展引用统计`、`读取留痕完整性`、`无 MCP 全流程` | F0/F1 |
| G16 | `wflib/config.py`、`wflib/assets.py`、`wf.py upgrade`（第三轮） | `升级三方判断`、`流程与配置`、`发行身份` | F1/F2 |
| G17 | `.wf/bin/wf.py` 引导段、`wflib/config.py`、`wflib/maintenance.py` | `Python 执行器`、`本地命令引导`、`执行器配置可信`、`执行器确认绑定`、`确认记录身份`、`项目标识生命周期` | F0/F1 |
| G18 | `wflib/spec.py`（预算）、`wflib/codes.py`、`wflib/gates.py` | `spec 预算`、`固定流转程序化`、`判定物与原因码` | F1 |
| G19 | `wflib/review.py`、`<skill 根>/wf-review`、`wf-review-action` | `审查与正常完成（charter T4）`、`审查 CLI 身份确认`、`审查适配副本` | F2 |
| G20 | `wflib/review.py::import_report`、`verify_anchor` | `审查材料外发`、`审查读取范围`、`审查报告写权`、`审查回执锚定` | F2 |
| G21 | `wflib/lock.py`、`.wf/bin/uninstall.py`、本文 §4.5 | `资产落点`、`互斥与锁生命周期`、`锁删除与人工清理`、`锁文件归属` | F1/F2 |
| G22 | `wflib/tasks.py::approve_plan`（复杂度/TDD）、`wflib/scope.py::governance_condition` | `复杂度分级一致性`、`TDD 开关` | F1 |

### 7.3 未运行声明

本文第 7 章、第 5 章的链路与第 1 章的投放自检**全部未运行**。夹具 F0/F1/F2 尚不存在；`claude`、`codex`、`dsh` 是否为可用的非交互 reviewer 未实测；宿主会话身份能力未在任一宿主核实。任何「本文已定义」的说法都不表示可用；实现阶段须按机制稿 §12.3 的夹具绑定逐场景记录初态、入口、输出与实际结果。

## 8. 单页使用速查

本章是设计稿 §8.1 第 2 项要求的「时刻 → 入口 → 人工动作/令牌 → 阻断出口」。它只引用调用权与命令，不复制门禁规则；表中的原因码与出口摘自机制稿 §11.1 的码表并作速查缩写，冲突时以码表为准，本章不新增、不改义任何原因码。

### 8.1 环境前提

- **单人、本机、单一共享工作区**：同一时刻只有一个写者。框架只在人显式启用 `/wf-start` 的会话内生效（设计稿 §1.2、§1.3 调用权分层）；未启用的会话照常做别的开发。
- **复杂度**：触碰治理面即按复杂处理（机制稿 §3.4 条件①），分不清时按复杂（设计稿 §4.3）。
- **复杂任务至少三个异种 CLI**：1 个实施 + 2 个彼此不同、且都与实施不同的审查 CLI（机制稿 §9.2）。不足时**只能暂停等待，或按机制稿 §6.4 异常归档**；不得降级完成、不得用单 reviewer 冒充（charter T4、设计稿 §6.5）。
- **连续独立短任务优先声明为用户工作流实例**：定义内顺序任务步骤即可承载，减少换会话来回避对象绑定；首轮无实例能力时只能逐任务新开会话，成本见本文 §8.5。
- **人工动作清单**：终端确认与令牌输入（`upgrade --apply`/`repair`/`uninstall --purge`）、`confirm-executor`、`finish` 调用、审查发起与材料外发授权、规划批准与 `plan-q` 作答。模型不代答、不代跑。
- **不做**：分支状态变更、嵌套仓库扫描、并行调度、常驻服务、外部 MCP（charter T3）。

### 8.2 时刻 → 入口 → 人工动作/令牌 → 阻断出口

| 时刻 | 入口 | 人工动作/令牌 | 阻断出口（原因码 → 出口） |
|---|---|---|---|
| 首次投放（开发态/正式发行） | 开发态 `python3 scripts/wf-dev-deploy.py --target <abs> --skill-root <abs> [--confirm]`（先出预览）；正式发行 `python3 install.py --target <abs> --release-ref <refs/tags/wf-vX.Y.Z> --source <发行目录> --skill-root <abs>`（第三轮） | 给目标绝对路径与发行引用；确认预览与投放根；Trellis 资产风险确认 | `WF_ASSET_DECISION` → 保留/移走/改名；`WF_RELEASE_CONFLICT` → 核正确发行引用；`WF_TARGET_COLLISION` → 保留双方并确认目标 |
| 首次解释器确认 | `python3 .wf/bin/wf.py confirm-executor --scope system\|global\|project`（终端，人执行） | 人在终端执行，入口探测 `--version` | `WF_EXECUTOR_UNCONFIRMED` → 确认当前解释器 / 换已批准解释器 / 回到未设置 |
| 开始会话 | 宿主 skill `wf-start`（唯一启用方式） | 人显式调用 | `WF_FLOW_CONFLICT` → 清理 Trellis 来源后换新会话；`WF_IDENTITY_UNRESOLVED` → 核实宿主身份或选 wf 签发路径；`WF_WRITER_BUSY` → 等待或已确认交接 |
| 选择对象 | `wf-start` → `wf.py task-new`（普通任务）/ `run create`（第二轮） | 人选对象；实例另需确认版本/输入/展开规则 | `WF_BINDING_MISMATCH` → 原对象结束后新会话选择；`WF_DEPENDENCY_UNMET` → 等前置或人确认返工/重连；`WF_APPROVAL_MISSING` → 先批准规划 |
| 准备定义（第二轮） | `wf-start` → `wf.py definition prepare --id <workflow-id>` | 人批准准备范围 | `WF_DEFINITION_INVALID` → 按校验清单改定义；`WF_TEMPLATE_INCOMPLETE` → 填模板必填位 |
| 批准规划 | `wf-continue` → `wf.py task-approve --task <id> --decision <path>` | 人批准规划+复杂度+TDD；一轮内批量作答 `plan-q-<n>` | `WF_APPROVAL_MISSING` → 重新呈现规划；`WF_SEMANTIC_DECISION` → 澄清未决语义；`WF_TEMPLATE_INCOMPLETE` → 填模板 |
| 开工 | `wf-continue` → `wf.py task-start --task <id>` | 无（门禁自动） | `WF_SCOPE_UNRESOLVED` → 回 Plan 补可证包含条目；`WF_WORKSPACE_UNRESOLVED` → 逐路径核归属；`WF_WIP_UNRESOLVED` → 同对象核指纹恢复或实际处置；`WF_VERIFICATION_UNREADY` → 补来源/设施 |
| 读规则 | `wf.py spec --file <RepoPath>` | 无 | `WF_SPEC_INCOMPLETE` → 分批读全文后重试 |
| 检查 | `wf-continue` → `wf.py task-check --task <id>` | 无 | `WF_SCOPE_VIOLATION` → 回 Plan 扩范围重批；`WF_CHECK_FAILED` → 修复后重跑；`WF_CHECK_STALE` → 重算锚点后重检 |
| 复杂任务审查发起 | `wf.py review-launch …`，再由人打开两个异种 CLI 会话 | 人声明实施 CLI、两个 reviewer CLI 与槽位；授权本次外发材料范围 | `WF_REVIEW_UNAVAILABLE` → 暂停或异常归档；`WF_REVIEW_INVALID` → 补真实审查 |
| 审查导入与判定 | `wf.py review-import …` → `wf.py review-decide …` | 人核对报告与锚点 | `WF_REVIEW_INVALID` → 锚点失配则重审；报告缺失/身份矛盾不判 pass |
| 完成门禁与归档 | 人调用 `wf-finish` → `wf.py archive --task <id> --decision <path>` | 人了解结果与未核实项后调用 finish；该 Decision 记调用证据与按精确路径的提交授权 | `WF_COMMIT_NOT_AUTHORIZED` → 等人处理；`WF_SEMANTIC_DECISION` → 裁定未决项；`WF_WORKSPACE_UNRESOLVED` → 处置工作区 |
| 日常收工 | `wf-continue` → `wf.py stop --decision <path>` | 人给**一个**去向（提交 / 保留 WIP / 反向修正 / 具名承接），`subject` 列出覆盖路径或承接对象；提交与反向修正的授权写在同一 Decision 数组里 | `WF_WORKSPACE_UNRESOLVED` → 落实际处置后再释放；`WF_WIP_UNRESOLVED` → 同对象恢复或处置 |
| 未完成收工就关闭 | 新会话先人直调 `.wf/bin/repair.py`（预览 + 令牌），再 `wf-start` | 人确认旧写者已停止、核对 Git/产物/WIP、输入令牌 | `WF_HISTORY_UNRESOLVED` → 只读核原文/Git 后 repair；`WF_GENERATION_STALE` → 停止写并重核 |
| 升级（第三轮） | `wf.py upgrade --apply --release-ref <refs/tags/wf-vX.Y.Z> --source <发行目录> [--skill-root <abs>]` | 预览 + 终端令牌；另有提交授权 | `WF_PREVIEW_STALE` → 重新预览；`WF_ASSET_DECISION` → 逐项选保留/恢复/合并 |
| 受控修复 | `.wf/bin/repair.py`（人直调；`--dispose <plan>` 处置维护组） | 预览 + 终端令牌；确认旧写者停止 | `WF_RECORD_INVALID` → 保留原文并按人指定事实重建；`WF_HISTORY_UNRESOLVED` → 只读核对 |
| 卸载 | `.wf/bin/uninstall.py`（`--purge` 另确认，第三轮） | 预览 + 确认；确认无 wf 进程后手工清理 `.wf-lock` 与 `/.wf-lock` 忽略行 | `WF_ASSET_DECISION` → 逐项选保留/移走/删除；`WF_WRITER_BUSY` → 先核实旧写者 |
| 巡检 | `wf.py inspect`（人发起，或每 10 个正常归档的整数倍） | 无 | 只读报告三类结果；要修复则另取授权 |

表中 `WF_ASSET_DECISION`、`WF_IDENTITY_UNRESOLVED`、`WF_SCOPE_UNRESOLVED`、`WF_WORKSPACE_UNRESOLVED`、`WF_HISTORY_UNRESOLVED`、`WF_SEMANTIC_DECISION` 属 `needs_decision` 档（列名沿用设计稿 §8.1 的「阻断出口」，档位以机制稿 §11.1 码表为准）；其余码为 `blocked` 档。速查不合并两档，只为省行。

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
| 框架代码、脚本、skill 副本、`.wf/` 实例 | 未安排（本阶段范围只到文档） | 编码另立任务；本文给出的路径与函数名是其输入 |
| 机制稿 §0.2 四项机检扩展 | 未安排（已登记为后续项） | 见本文 §9.2 第 1 项 |
| 三夹具 F0/F1/F2 与五条验证顺序 | 未安排 | 本文 §7 全部标「未运行」 |
| reviewer CLI 可用性（`claude`/`codex`/`dsh`） | 环境未验证 | 命令存在不等于可作非交互 reviewer；须实测 |
| 宿主会话身份能力（压缩稳定、新会话区分、结构化传递） | 环境未验证 | 机制稿 §1.4 要求按宿主核实；未核实前 `status=unknown` |

### 9.2 已裁定事项与剩余待办

**已裁定（2026-11-02，人）**

1. **机制稿 §0.2 四项机检扩展 → 登记为后续项**。四项为①按 schema 表逐键核对写者/消费者/失败出口；②码表档位与处理器映射表一致；③表间引用悬空；④机制稿的两张场景映射表与设计稿 §8.2 同源核对。现状：④ 与输入摘要、哈希域逐键段已落地；②在运行输出中无对应字段；①③未见实现。排期按 charter T6.3 顺序（先改既有产物 → 造确定性机检 → 新增规则），排在首轮实现收口之后，不阻塞首轮。登记落点为本节与任务记录；机制稿 §0.2 原文未改（它是已审稿，写回须同批复审），落地前由该节规定的固定反查动作与人工复审兜底。
2. **入站指针 → 只在机制稿 §12.4 加一行指针**（已落地）。机制稿不在四份摘要文件内，`输入摘要 4/4` 与索引表均未变动；索引登记未做，若日后要求须同批改索引、重算四份摘要并写回机制稿 §0.1。
3. **`scripts/check-doc-refs.py` 已扩展 `机制稿` 前缀**（已落地，约定见本文 §0）。改动含：登记前缀新增 `机制稿 `、新增「列举继承」规则（前缀与 `§` 之间只有同类引用与 `、，,与和`/空白时继承前缀，出现其他语义文字则不继承）、支持多文件参数并给总数（单文件输出格式不变）、默认仍查 `workflow-implementation.md`。本文已用该脚本自检通过；它不在 `validate-wf-design.py` 的七项检查内，二者互不替代。
4. **复盘登记为独立机制操作 `task.retrospect`**（已落地）：机制稿 §11.3 的状态动作集合与机制稿 §5.1 的当前任务主记录归属同批登记，`control.task.retrospect` 按该节公式派生；处理器 `wflib/tasks.py::retrospect`（本文 §6.2 D36），门禁仍由机制稿 §11.2 的 `task.retrospective-done` 核验。该改动触及已审稿，须同批复审。
5. **打包脚本不入发行清单，只写发行说明**（已落地，见本文 §1.5 的发行说明要求与理由）。**发行安装器 `install.py` 相反：它属发行资产**，按 `release_only` 登记进 `assets` 并计入 `rules_digest`；`target_class` 的取值域由本文定义（机制稿 §10.2 只给字段名，未定域），因此这一登记不需要改机制稿。作者机工具（打包、开发态部署）不属发行资产，两者不要混为一谈。

**剩余待办**

| 项 | 状态 | 出口 |
|---|---|---|
| 机制稿 §0.2 四项机检扩展的实现 | 后续项（不阻塞首轮） | 首轮实现收口后另立维护任务，按 charter T6.3 顺序落地并重跑机检 |
| 索引表登记本文 | 未做（人裁「只加机制稿指针」） | 若日后要求，同批改索引、重算四份 SHA-256、写回机制稿 §0.1 摘要表并由人确认 |
| 本文冻结 | 首版草稿，未经未参与编写会话复审 | 按设计稿 §0 的复审规则由独立会话按轴复审、声明覆盖轴与未覆盖项后，才可作为实现阶段基线 |
| 三夹具、五条最小验证顺序、审查链路、宿主身份、reviewer 可用性 | 未运行（见本文 §9.1） | 实现阶段逐项运行并记录初态/触发/输出/归因 |
