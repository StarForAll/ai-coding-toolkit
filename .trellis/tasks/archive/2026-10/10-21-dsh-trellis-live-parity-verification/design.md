# 技术设计：dsh-trellis 0.1.1 实际调用验证

## 环境事实（已核实）

- dsh 0.2.1-rc.2，位于 /softwares/nodeNpm/nodejs/bin/dsh。
- `dsh-trellis@0.1.1` 安装在 `web` profile（`dsh plugin --profile web list` 确认）；
  `headless` profile 未安装该插件。
- 插件源码（本仓库 dsh-plugins/dsh-trellis）：lib/ 含 30 个模块，test/ 含 40+ 测试文件。
- Trellis 本体源码：~/projects/other/Trellis（pnpm workspace）。

## 验证驱动方式（关键决策）

headless profile 没有插件，因此所有需要插件运行时的验证必须经 `web` profile。
两种路径：

1. **`dsh web --json` headless 事件流**（主要路径）：web profile 是否支持类 headless
   的一次性任务模式需要先行探测（`dsh web --help`）。若 web profile 不支持非交互
   运行，则退路为：
2. **直接单元级验证 + 事件回放**：用插件自身测试 harness（test/helpers fixtures）
   模拟 dsh 事件（agent/pre-step、tools/pre-execute、subagent/end、compaction/end），
   但这不是"一面之词"——fixtures 是插件作者写的。为满足"实际调用"要求，组合使用：
   - 真实 dsh 进程挂载插件（`--dump-config` 确认 loader 挂载）
   - 真实 Trellis CLI（~/projects/other/Trellis 构建/已装的 trellis 命令）初始化项目
   - 真实 `task.py` 交互改变状态
   - dsh 事件流（若可非交互获得）驱动插件

**先决探测（第一步）**：确认 web profile 的非交互能力，这决定 C1/C7/C8 用真实
事件流还是事件回放（回放时明确标注证据等级降级）。

## 临时项目布局

```
/tmp/dsh-trellis-verify/
  proj-basic/        # trellis init 的标准项目（git init + trellis init --dsh）
  proj-nogit/        # 无 .git 的 Trellis 项目（验证 projectRootMarkers）
  proj-plain/        # 完全无 Trellis 的普通项目（验证静默）
```

## 各能力验证设计

### C1 面包屑
- 新会话 no_task → 期望注入 no_task 面包屑。
- `task.py create` + `start` → in_progress 面包屑（状态变化触发新注入）。
- 同状态第二轮 → 不重复。
- prompt 含 `no-trellis` → 跳过。
- 证据：dsh 事件流或会话存储文件（~/.dsh/sessions/）。

### C2 会话身份
- 两个 headless 会话（不同 --session-id）在 proj-basic 各自 create/start 不同任务，
  `task.py current` 按 DSH_TRELLIS_CONTEXT_ID 会话指针解析，互不串扰。
- 对照 Trellis 侧 task.py 的指针存储机制（.trellis/.runtime/ 下 session 指针）。

### C3 子代理 + trellis_wait
- 派发一个 trellis-agent-implement 子代理执行小任务 → trellis_wait 返回 completed。
- 构造必然失败的子代理（任务指示其报错）→ trellis_wait 返回 failed，不误报。
- 对照 Trellis workflow.md 对 DSH 平台的 wait 契约描述。

### C4 子代理上下文 push
- 派发时检查子代理首步注入：`.dsh/skills/trellis-agent-implement/SKILL.md` 正文
  （去 frontmatter、去 pull 段）+ curated context（implement.jsonl 清单内容）。
- 缺失 skill 文件时回退路径提示。

### C5 命令面
- `/trellis-status`、`/trellis-finish`、`/trellis-doctor` 在 proj-basic 实际调用。
- 验证 rc.1 退出码契约（current --json）。

### C6 dispatch_mode 引导
- proj-basic（config 无 dsh 键）→ 挂载后 diff config.yaml：应添加
  `dsh: dispatch_mode: inline`，保留注释。
- 构造显式 `auto` 的 config → 不被覆盖。
- 构造带注释 config → 注释保留。

### C7 spec 注入
- 在 proj-basic 写一个 spec（.trellis/spec/ 下带 glob 匹配 src/），
  headless 会话让 agent 编辑匹配路径 → 观察 deny-once + ticket 送达 + 
  `.trellis/.runtime/spec-inject/<session>.json` 持久化。
- 重启会话不重复 deny；compaction 后重新注入。

### C8 bootstrap
- 新会话首轮 no_task → bootstrap 提示一次；第二轮不再出现；
  子代理会话无 bootstrap。

### C9 非项目行为
- proj-plain 中跑会话与命令 → 无注入、命令返回"未初始化 Trellis"。

### C10 init 双向一致性
- `trellis init --dsh`（用 Trellis 本体源码的 CLI）产出的 `.dsh/skills/trellis-agent-*`
  、config 键，与插件 lib/subagent-context.js、lib/trellis-config.js 的读取逻辑
  逐键比对。
- 检查 Trellis 上游对 dsh 平台的文档（workflow.md 的 DSH 段落）与插件实现的互相引用
  是否自洽。

## 问题记录与报告

- 每个问题记录：现象、复现命令、根因初步定位（结合 dsh/Trellis 源码）、等级、修复方案。
- verification-report.md 是唯一交付物（任务目录内）。

## 回滚

- 全部工作在 /tmp 临时项目 + 任务目录文档，主仓库只有任务 artifacts，
  无代码改动，无需回滚。
