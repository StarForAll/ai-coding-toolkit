# brainstorm: record-session 自动提交失败时升级执行机制

## Goal

分析当前项目 workflow 中 `record-session` 相关链路，确认当 Trellis 的 `record-session` / `add_session.py` 在只读文件系统或受限沙箱中自动提交失败时，应该如何在当前项目 workflow 中补充“跳出只读系统执行”的机制，并给出后续修改方案。

## What I Already Know

* 当前项目是 Trellis 管理项目，`record-session` 通过 `.trellis/scripts/add_session.py` 写 journal 和 index
* 本次实际执行 `record-session` 时，session 内容已落盘，但自动 `git add` 失败
* 失败表现为：无法创建 `.git/index.lock`，提示只读文件系统
* 用户当前要求先分析，不直接改代码

## Assumptions (temporary)

* 需要分析的补充机制范围，既可能包含 workflow 文档，也可能包含 helper / patch / script 级实现
* “跳出只读系统执行”更接近当前 CLI/agent 的升级执行或用户授权外沙箱执行机制，而不是普通重试

## Open Questions

* 触发点应放在 `record-session` 命令文档、`record-session-helper.py`，还是 `add_session.py`/自动提交守卫里
* 失败后是自动升级执行，还是输出明确的升级提示并要求当前 CLI 发起外沙箱命令

## Requirements (evolving)

* 梳理当前 `record-session` 的实现链路、失败处理和相关补丁
* 确认当前项目 workflow 对自动提交失败的现有约束和缺口
* 给出可落地的机制补充方案，不直接修改

## Acceptance Criteria (evolving)

* [ ] 已定位 `record-session` 的相关命令文档、patch、helper、脚本实现
* [ ] 已说明只读文件系统 / 沙箱失败点出现在哪一层
* [ ] 已给出后续修改方案与推荐落点
