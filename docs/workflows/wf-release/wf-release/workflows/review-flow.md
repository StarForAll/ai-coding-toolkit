# 审查流程（review-flow）

> 复杂任务在 Check pass 后、人判前由人打开顺序独立的异种 CLI 审查会话。
> 报告只写项目树外的暂存目录；导入由持有写权的主会话完成；判定由入口按事实推导。

## required 步骤

### control.review.launch [required · repeatable]

- 时点：审查发起动作结束
- enforcement: `wflib/review.py::launch`
- 动作：记录实施 CLI 声明、槽位、锚点与材料范围，为每个槽位写 request.json 并回显可粘贴的 skill 调用文本。
- 出口：无有效 Check pass → `WF_CHECK_FAILED`；人数/声明不合格 → `WF_REVIEW_INVALID`。

### control.review.import [required · repeatable]

- 时点：单个槽位报告导入结束
- enforcement: `wflib/review.py::import_report`
- 动作：核协议块、元数据、槽位与当前锚点后原子发布到任务目录并记录哈希。
- 出口：锚点失配/协议不支持 → `WF_REVIEW_INVALID`；报告不在其暂存目录 → `WF_PATH_INVALID`。

### control.review.decide [required · repeatable]

- 时点：审查判定动作结束
- enforcement: `wflib/review.py::decide`
- 动作：按导入报告与人工声明推导 pass/fail/unavailable，并记录逐条处置。
- 出口：单 reviewer 或 CLI 重叠 → fail（`WF_REVIEW_INVALID`）；缺 CLI → `WF_REVIEW_UNAVAILABLE`。
