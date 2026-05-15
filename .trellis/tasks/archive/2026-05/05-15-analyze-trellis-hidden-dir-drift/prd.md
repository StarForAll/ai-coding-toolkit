# analyze trellis hidden-dir drift

## Goal

基于当前仓库中的 `.trellis/` 与其他隐藏目录，梳理 Trellis 在本项目里的实际运行机制，并与 `/tmp/trellis-0.5.15` 临时项目中的 Trellis 原生基线进行对照，识别当前项目隐藏目录内存在的数据漂移、缺漏和错配，再区分哪些问题属于 Trellis 原生机制/产物，哪些属于本项目定制或维护层的问题。

## What I already know

* 当前仓库是 Trellis workflow authoring source project，不是消费端 target project。
* `.trellis/workflow.md`、`.trellis/config.yaml`、`.trellis/spec/`、`.trellis/tasks/`、`.trellis/workspace/`、`.trellis/.runtime/`、`.trellis/.template-hashes.json` 是本地 Trellis 核心载体。
* `.codex/`、`.claude/`、`.opencode/`、`.qoder/`、`.kiro/`、`.agents/` 中存在 Trellis 的 hooks、skills、agents、config 等平台承载文件。
* 当前仓库启用了 `codex.dispatch_mode: inline` 语义，Codex 主会话不应使用 sub-agent。
* `.trellis/.backup-*` 下保留了多份历史备份，可能对“漂移”观察造成噪音，需要和 live carrier 分开判断。

## Assumptions

* `/tmp/trellis-0.5.15` 可作为 Trellis 0.5.15 的原生基线对照样本。
* 用户当前要的是证据化分析，不要求本轮直接修复。
* “数据漂移”既包括内容漂移，也包括应该同步但未同步、应该清理但残留、应该分层却混层的情况。

## Open Questions

* 当前是否存在 live carrier 与 hash registry、文档说明、平台注入逻辑之间的不一致。
* 当前隐藏目录中的异常差异，是否可被 `/tmp/trellis-0.5.15` 证明为 Trellis 原生行为，还是项目侧定制造成。

## Requirements

* 深度分析 `.trellis/` 和其他隐藏目录中的 Trellis 相关文件与职责。
* 明确本项目 Trellis 的运行链路：配置、workflow、hook、task runtime、workspace、platform carrier、hash/sync 管理。
* 读取 `/tmp/trellis-0.5.15`，抽取 Trellis 原生目录结构与关键文件。
* 对比当前项目与基线，列出存在的漂移、错漏、疑点。
* 对每个发现给出归因：Trellis 原生问题 / 当前项目问题 / 合理定制非缺陷。

## Acceptance Criteria

* [ ] 给出本项目 Trellis 机制的结构化说明。
* [ ] 给出当前仓库隐藏目录的关键差异与漂移清单。
* [ ] 每个问题都有对照证据和归因判断。
* [ ] 明确哪些差异只是定制，哪些是真问题。

## Out of Scope

* 本轮不直接修改 Trellis 实现或修复漂移。
* 不把 `docs/workflows/**` 的目标项目产品规则直接当成当前 source repo 的运行规则，除非它们确实影响当前 live carrier。

## Technical Notes

* 首要分析对象：`.trellis/`, `.codex/`, `.claude/`, `.opencode/`, `.qoder/`, `.kiro/`, `.agents/`
* 对照对象：`/tmp/trellis-0.5.15`
* 需要特别区分：
  * live carrier
  * 历史备份 `.trellis/.backup-*`
  * runtime state `.trellis/.runtime/*`
  * managed registry `.trellis/.template-hashes.json`
