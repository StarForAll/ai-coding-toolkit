# 实施清单（顺序执行）

## 步骤

- [ ] 1. §2.3 表：`task-start` 行后插入 `task-replan` 行（机制操作 `task.transition`）。
- [ ] 2. §2.3 表后插入「阶段回退的承载与再入路径」一段（承载者 / 输入 / 迁移边界 / 再入两步 / 引用机制稿 §1.3、§2.2、§2.3）。
- [ ] 3. §2.2「必须携带」列举中加 `task-replan`。
- [ ] 4. §2.3 表：拆 `task-rework / task-replace / task-abandon` 行 → `task-rework`/`task-replace`（轮次 2，保留 `…`）+ `task-abandon`（首轮，显式参数）。
- [ ] 5. §2.3「结构化人工输入」：`--decision` 用途补 `task-abandon`；新增 `--disposition <path>` 条目与其记录映射；领域文件名单补 `--disposition`。
- [ ] 6. §8.2：新增「重新规划（实质变更）」「放弃任务（异常归档）」两行。
- [ ] 7. §9.2：加「本轮修订」块（两条各一行 + 新绑定 + 旧绑定作废）。
- [ ] 8. frontmatter `status:` 改「修订后待复审（2026-11-02，处置复审两条中级发现；绑定见 §9.2）」。

## 校验命令（实跑并贴原始输出）

```
/softwares/python/bin/python3 scripts/validate-wf-design.py
/softwares/python/bin/python3 scripts/check-doc-refs.py
/softwares/python/bin/python3 scripts/check-doc-refs.py docs/workflows/wf-framework-charter.md docs/workflows/wf-framework-design.md docs/workflows/wf-framework-design.index.md docs/workflows/wf-framework-design.sources.md docs/workflows/wf-framework-implementation.md docs/workflows/wf-framework-mechanism.md
/softwares/python/bin/python3 -m unittest scripts.tests.test_validate_wf_design
git diff --stat
git diff -- docs/workflows/wf-framework-implementation.md
wc -l docs/workflows/wf-framework-implementation.md
sha256sum docs/workflows/wf-framework-implementation.md
```

- 预期：引用 559 / 二值 91/91 / 三档 13/13 / 输入摘要 4/4；七项检查 + 覆盖率断言通过；六份 wf-framework 文档各 0 problem；19 tests OK。
- 边界：`git diff --name-only` 只允许出现 `docs/workflows/wf-framework-implementation.md`；四份受保护文件与其他路径必须为空。

## 回滚点

- 修订前：700 行 / sha256 75667055f3efbfe28824bc6d434af7cc26fefd799c5b05b809f010f8d989163e / HEAD fdc328b。
- 单条回滚：按 §2.3 行 / 说明段 / §8.2 行分别回退，互不影响。

## 停止条件

两条处置完、机检全绿、diff 边界证明完毕即停；不做冻结登记，不自我复审代替独立复审，不提交、不归档、不 finish。

## 实施结果（2026-11-02）

- M1、M2 复核结论均为「成立」，均按 A 类只改本稿；未触发 B/C，未改机制稿与四份受保护文件。
- 改动落点：本文 §2.3（新增 `task-replan` 行、「阶段回退的承载与再入路径」段、拆分 `task-abandon` 行、`--decision` 用途、新增 `--disposition` 承载与记录映射、领域文件名单）、本文 §2.2（代次列举）、本文 §8.2（新增两行）、本文 §9.2（本轮修订表 + 本轮绑定 + 剩余待办「本文冻结」行状态）。frontmatter `status:` 改为「修订后待复审」。
- 新绑定（工作树内容）：**717 行 / sha256 `b8eddf075af3ff3f773b2f82015db9df60e72958d9b81cc19ca145c88a4b09d8` / HEAD `fdc328b`**。
- 旧绑定 `75667055f3efbfe28824bc6d434af7cc26fefd799c5b05b809f010f8d989163e`（700 行）作废。
- 机检：`validate-wf-design.py` → 引用 559 / 二值 91/91 / 三档 13/13 / 输入摘要 4/4 + 七项检查 + 覆盖率断言通过；`check-doc-refs.py` 默认与六份 wf-framework 文档各 0 problem；`unittest` 19 tests OK；`git diff --stat` 仅 1 文件（+23/−6）。
- 未提交、未归档、未冻结；`check-doc-refs` 对 `wf-variant.md`、`依赖机制设计说明.md`、`workflow-design.md` 的既有 problem 属修订前基线，本轮未涉及。

## 复审收口（2026-11-02 晚）

- 复审轮在**同一工作树**完成：原 Codex 会话全文重审（高级 0／中级 0／低级 0）+ 不同 CLI 独立复审（高级 0／中级 0／低级 5，L1–L5 处置见文档 §9.2）；被审版本绑定即本轮交付的 `b8eddf07…`（717 行），与本任务记录一致。
- 复审轮另在文档内做了三处编辑（`enable` 行机制操作格、`asset.compare` 消费面拆句、`status:` 与 §9.2 复审/处置/冻结登记），故工作树当前为 **738 行 / sha256 `371fe74b455780b90d7edf0069cb1fc3331a5a01cd9b88ce904d6a2153bbf72b`**；本任务的 717 行绑定自此仅作历史。
- **待核**：文档 §9.2 冻结行登记的「正文绑定 sha256 `051aade5…`」未能从当前工作树复现（按 frontmatter/§9.2 各前缀截断扫描均未命中），该值所对应的版本不在当前树内。本任务不对已冻结正文作任何改动，仅记录该差异，交后续核对。
- 机检（收口时实跑）：`validate-wf-design.py` 引用 559 / 二值 91/91 / 三档 13/13 / 输入摘要 4/4 + 七项检查 + 覆盖率断言通过；`check-doc-refs.py` 六份 wf-framework 文档各 0 problem；`unittest` 19 tests OK。
