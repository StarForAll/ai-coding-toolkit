# 执行计划：dsh-trellis 0.1.1 实际调用验证

## 前置检查清单

- [ ] T0 环境探测：web profile 非交互能力（`dsh web --help`、`--json` 支持）；
      `trellis` CLI 可用性与版本（~/projects/other/Trellis 源码 vs 全局安装）；
      插件在 web profile 的挂载确认（`--dump-config`）。
- [ ] T0.1 确定证据等级策略：真实事件流（强）/ 真实进程+事件回放（中，标注）/
      单元测试（弱，仅作补充，不作通过依据）。

## 阶段 A：环境与临时项目搭建

- [ ] A1 `/tmp/dsh-trellis-verify/` 创建 proj-basic（git init + trellis init --dsh）、
      proj-nogit（无 git）、proj-plain（空）。
- [ ] A2 记录 trellis init 产物清单（.dsh/、.trellis/config.yaml 等）作为 C10 的
      基线事实。

## 阶段 B：核心链路验证（证据收集）

- [ ] B1 (C1) 面包屑：no_task → in_progress 状态流、去重、no-trellis 跳过。
- [ ] B2 (C8) bootstrap 一次性、子代理不注入。
- [ ] B3 (C2) 会话身份隔离：双会话并行任务指针。
- [ ] B4 (C6) dispatch_mode 引导三种 config 形态。
- [ ] B5 (C7) spec 注入 deny/ticket/持久化/compaction。
- [ ] B6 (C3) 子代理 + trellis_wait 成功/失败两路。
- [ ] B7 (C4) 子代理首步 push 内容核对。
- [ ] B8 (C5) /trellis-status、/trellis-finish、/trellis-doctor 实际调用。
- [ ] B9 (C9) 非 Trellis 项目静默与命令行为。
- [ ] B10 (C10) init 产物与插件读取逻辑双向比对（源码级 + 实际产物）。

## 阶段 C：交叉验证与缺漏排查

- [ ] C-a 对照 Trellis 本体源码（hooks、task.py、workflow.md DSH 段落）核对插件
      依赖的每个契约（退出码、路径、键名）。
- [ ] C-b 对照 Codex 在本仓库的部署（.codex/ hooks）梳理"Codex 效果"基准清单，
      逐项标注插件达成情况。
- [ ] C-baseline 不装插件的 dsh 使用 Trellis 基线（哪些能力缺失）→ 验证"补足"。
- [ ] C-c 运行插件自身测试套件确认无回归（补充证据，非通过依据）。

## 阶段 D：报告

- [ ] D1 写 verification-report.md：C1–C10 逐项证据 + 结论（通过/不通过/无法验证）。
- [ ] D2 问题清单 P0–P3 + 每问题修复方案（不执行）。
- [ ] D3 向用户汇报，等待确认。

## 验证命令

- `dsh --profile web --dump-config | grep -A5 trellis`（挂载确认）
- `/softwares/python/bin/python3 ./.trellis/scripts/task.py current`（本任务状态）
- 插件测试：`cd dsh-plugins/dsh-trellis && pnpm test`（或 package.json 中的脚本）

## 审查门

- 阶段 B 每项结论必须有命令输出/文件 diff/事件流摘录作为证据，报告里注明证据来源
  等级；引用插件自述文档的结论一律标"未采信为独立证据"。
- D3 后停止：不进入修复，等用户确认。

## 回滚点

- 无主仓库代码改动；临时项目可整体删除重建。
