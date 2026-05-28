# sync stale repo docs and spec facts

## Goal

同步修正当前仓库中已经落后于真实项目状态的说明性文档与 repo-local spec，
避免 AI CLI 或用户继续依据过时描述误判 source/deploy 边界、命令承载方式、
当前目录现状或 runtime 清理状态。

## What I already know

* 本轮范围是“文档事实漂移”，不是 workflow 行为修复。
* `AGENTS.md` 仍把 `agents/` 描述成 README-only placeholder，但当前
  `agents/` 已有多套真实 source agent 资产。
* `README.md` / `README.en.md` 仍写 `skills/` 为 4 个、`commands/shell/`
  只有 README、以及把 `commands/<tool>/` 泛化映射到 `.<tool>/commands/`，
  这会误导到不存在的 Codex commands carrier。
* `.trellis/spec/commands/index.md` 的 Current State 仍写
  `commands/claude/` / `commands/codex/` / `commands/shell/` 都是空目录，
  但 `commands/shell/init-trellis-temp-project.sh` 已存在。
* `docs/Trellis隐藏目录边界清单.md` 末尾把“已清理 stale session”写成了既成事实，
  但当前 `.trellis/.runtime/sessions/*.json` 仍全部指向不存在任务。

## Assumptions (temporary)

* 本轮只修正文档事实，不顺手清理 runtime residue、backup 目录或 template hashes。
* 若某 spec 明确声明自己是在描述目标架构而非当前现状，则只修其中“当前状态”段落，
  不改变目标架构设计。
* 根 README 的中英文版本必须在同一改动中同步。

## Open Questions

* 无阻塞问题；按已确认范围执行。

## Requirements (evolving)

* 修正 `AGENTS.md` 对 `agents/` 当前状态的过时描述。
* 修正 `README.md` / `README.en.md` 中关于 `skills/` 数量、
  `commands/shell/` 状态、以及 Codex command carrier 的过时表述。
* 修正 `.trellis/spec/commands/index.md` 中与当前 `commands/` 现状不一致的
  Current State 描述。
* 修正 `docs/Trellis隐藏目录边界清单.md` 中把 runtime stale session
  清理写成已完成事实的段落，避免误导后续审计。
* 保持现有规范边界清晰：source repo 现状、目标架构、目标项目装后行为三者不混写。

## Acceptance Criteria (evolving)

* [ ] `AGENTS.md` 不再把 `agents/` 误写成 README-only placeholder。
* [ ] `README.md` 与 `README.en.md` 同步反映当前 `skills/` 数量、
      `commands/shell/` 现状和 Codex 实际承载模型。
* [ ] `.trellis/spec/commands/index.md` 的 Current State 与当前仓库磁盘现状一致。
* [ ] `docs/Trellis隐藏目录边界清单.md` 不再宣称 stale session 已被清理，
      而是保持规则性描述。
* [ ] 验证命令通过，且工作树只包含本轮文档修正。

## Definition of Done (team quality bar)

* 相关文档修改保持中英文与 spec 边界一致
* 验证命令通过
* 不引入新的 source/deploy 边界误导

## Out of Scope (explicit)

* 清理 `.trellis/.runtime/`、`.trellis/.backup-*`、`__pycache__`
* 修改 workflow 产品行为、脚本、安装器或 tests
* 处理 `.template-hashes.json` 缺失 key 或 overlay 语义

## Technical Notes

* 重点文件：
  `AGENTS.md`、`README.md`、`README.en.md`、
  `.trellis/spec/commands/index.md`、
  `docs/Trellis隐藏目录边界清单.md`
* 关键对照来源：
  `agents/README.md`、`commands/README.md`、
  `commands/shell/init-trellis-temp-project.sh`、
  `docs/workflows/新项目开发工作流/commands/codex/README.md`
