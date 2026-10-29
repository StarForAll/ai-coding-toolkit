# workflow-implementation 四项实质缺口修复

## Goal

修掉 `docs/workflows/workflow-implementation.md` 里上一任务留下的四条需判断的实质问题：A1（§3.7 说不实现基线流程，却实现了 `wf baseline --light`）、A2（`wf check` / `wf route` 标只读却会写账本清挂起）、A3（§9.7 自封规范却在 normative 清单外）、A11（裸 `§x` 引用与本地同名章节撞号）。先出方案，人审通过再改。

## Requirements

1. A1 必须消除“不实现 / 已实现”的矛盾，且不违背设计稿 §9.1 第一段③（需要改基线 → 回 §5.5）与 §5.5 轻量用法。
2. A2 必须给“派生清除挂起”一个明确类别：写什么、谁提交、提交消息、洁净检查如何适用，并同步 §2.4 / §3.5 / §3.6 / 附录 A / 变体里“只读”的表述。
3. A3 必须让 `normative` front-matter 与 §9 各小节的实际效力一致。
4. A11 必须建立引用约定并修正所有真正含糊的裸引用；附录 D 左列按约定处理。
5. 不得改动设计稿与依赖机制说明；不得顺手重构无关章节。
6. 交付物是方案（task 目录内），不是直接改正文；通过后才落笔。

## Non-goals

- 不动审查（§8.5）与上一任务已定的裁决。
- 不做字面以外的增删（如新增命令）除非方案里明确选择。

## Acceptance Criteria

- [x] 方案对四项各给选项、推荐与影响面（A2 经三轮补细节），人审已定：A1 ①、A2 ①、A3 ②、A11 ①。
- [x] A1/A2 的结论均以设计稿条款为据（§4.4、§4.3、§5.5、§6.4），无偏离需登记 §9。
- [x] 已按结论改完；`scripts/check-doc-refs.py` 0 命中、`trellis-library validate --strict-warnings` 为 0、`validate-skills.sh` OK。

## 结果

- A1：§3.7 ③ 改为按 §5.5 两分支分派，保留 `wf baseline --light`，加 W24。
- A2：新增“只读 + 派生写入”类别（五条件 + 洁净检查 + 单独提交组），`route`/`check` 在 §2.4/§3.5/§3.6/§3.8/附录 A/变体同步，加 W26。
- A3：§9.7 并入 §8.2.1 后删除，M1–M3 留痕在 §9.5。
- A11：立引用约定、修 8 处含糊引用、附录 D 表头声明，新增 `scripts/check-doc-refs.py` 与 W25。

## Notes

- 四条均出自上一任务的缺口清单（已归档任务 `10-29-wf-review-skill-internal-proposal/gaps.md`）。
