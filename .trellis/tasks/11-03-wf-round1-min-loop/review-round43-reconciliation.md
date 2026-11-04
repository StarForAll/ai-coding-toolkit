# 第四十三轮外部评审的复核与修正（2 条）

- 处置编号 R78；实跑见 `validation.md` §69
- 判定：1 成立（归档样本的事实完整性没核）、2 成立（文档落后一轮）

## 1. 归档记录事实不完整仍被当样本（成立）

原来判"正常样本"只看两件事：路径在 archive 区、`terminal == "normal"`。于是：
- 缺 `archived_at` 的记录以空时间参与窗口排序，`(archived_at, id)` 的稳定性被破坏；
- 目录在归档区但 `status` 仍是 `in_progress` 的记录也被当样本。

机制稿要求 `archived` 必须有 `terminal` 与 `archived_at`。处置：把归档事实完整性作为**同一组前置**——`status == "archived"`、`terminal ∈ {normal, abnormal}`、`archived_at` 可解析且可排序；任一项不满足即记 `archive record incomplete: …` 到 unknown，**压制候选**；`inspection.due` 同时置 `null`（记录不完整时正常归档计数本身不可信，不能给触发结论）。

`archived_at` 解析用新增的 `_parse_stamp()`：接受 `Z` 结尾、要求带时区（缺失按 UTC 处理），返回可比较的 `datetime`，因此窗口排序是真正的时间序而不是字符串序。

## 2. 文档落后一轮（成立）

frontmatter 与 §7.3 还写"41 轮 / §65–§67"，而验证记录已到 §68（R77b）。已改为 43 轮 / §65–§69（含本文 §69），并在 §2.3.11 的未知纪律里补上「归档记录事实不完整」这一来源，以及「记录不完整时 `due` 也为 `null`」。

## 3. 用例

`r77_tests.py` 增 4 条（共 17 条）：完整记录可统计（正例，`due` 有结论）；缺 `archived_at` → 候选 0 且 `due=None`；目录在归档区但 `status≠archived` → 候选 0 且带状态未知；`terminal` 非法 → 候选 0 且带 terminal 未知。
