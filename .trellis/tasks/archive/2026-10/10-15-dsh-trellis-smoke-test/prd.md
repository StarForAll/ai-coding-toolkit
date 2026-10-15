# DSH 平台 Trellis 全链路冒烟测试

## Goal

在 DeepSeek Harness（dsh）上端到端验证 Trellis 0.7.0-beta.4 的任务生命周期是否真的可用，并留下可复现的证据。

本次安装新增了 dsh 平台层（`.dsh/`），既有 `.claude/`、`.codex/`、`.pi/`、`.zcode/` 已在使用中，但 dsh 从未跑过完整任务生命周期。需要确认的不是"文件装上了"，而是"流程能走通"。

## Requirements

- R1 会话身份：主会话写入的活动任务指针，必须能被 `task.py current --source` 在同一会话内解析出来，且 `Source` 行带 `dsh_session-<id>` 命名空间。
- R2 子代理链路：按 DSH 兜底契约（无 `trellis_wait` 时用 `run_in_background: false`）派发子代理，子代理必须能加载 `trellis-agent-implement` 并按 `Active task:` 前导行读到任务上下文。
- R3 交付物落地：子代理把验证结果写入任务目录内的 `smoke-evidence.md`，内容必须来自它自己实际执行的命令，不得转述主会话结论。
- R4 质量门：评审代理按 `check.jsonl` + PRD 校验 R3 中的每条断言，复跑关键命令，指出不成立的断言。
- R5 归档与会话记录：任务能归档、能记入开发者 journal，且自动提交**只**暂存任务自身路径与 journal 路径。

## Acceptance Criteria

- [ ] AC1 `task.py current --source` 在主会话返回 `.trellis/tasks/10-15-dsh-trellis-smoke-test` 且 Source 为 `session:dsh_session-ebe...` 命名空间
- [ ] AC2 子代理回报自己拿到的 `DSH_SESSION_ID`，并明确它与主会话 id 不同（这是本次要固化的已知限制）
- [ ] AC3 `.trellis/tasks/10-15-dsh-trellis-smoke-test/smoke-evidence.md` 存在，含 R1/R2 的原始命令输出与逐项通过/失败结论
- [ ] AC4 评审代理对 smoke-evidence.md 给出至少一条独立复核结论（复跑命令或指出证据不足）
- [ ] AC5 `task.py archive` 在 `main` 上先拒绝、加 `--skip-branch-validation` 后成功；归档后 `task.py current` 返回 `(none)`
- [ ] AC6 `add_session.py` 追加 journal 记录并自动提交，最终 `git status` 除任务归档外的无关文件保持未暂存

## Notes

- 轻量任务，PRD-only；不新增 `design.md` / `implement.md`。
- 交付物只写入本任务目录，不改动仓库其他任何文件。
- 本任务的副产物是一条真实结论：DSH 上哪些 Trellis 能力可用、哪些不可用。
