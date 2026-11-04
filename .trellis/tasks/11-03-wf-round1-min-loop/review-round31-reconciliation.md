# 第三十一轮：后续阶段三项（审查判定 / repair 预览 / 独立入口锁）

- 处置编号 R68；实跑见 `validation.md` §57

## 0. 结论

上一轮登记待办的三项**全部成立**，本轮修完。

| # | 原判 | 复核 | 处置 |
|---|---|---|---|
| 1 | 审查判定对旧锚点、阻塞发现、未声明 CLI、缺材料声明仍能 pass | **成立** | `review.decide` 在定稿前核这四类，命中即 `WF_REVIEW_INVALID` |
| 2 | `repair` 预览后写者已变，仍清空新写者 | **成立** | 令牌改为**由预览摘要派生**；应用时只认当前摘要派生的令牌 |
| 3 | `repair`/`uninstall` 接管已有空锁文件 | **成立** | 与运行时一致：排他创建才写标记，已有文件标记不全即拒绝 |

## 1. 审查判定（`review.decide`）

导入后的报告逐份核四项：

- **锚点**：报告 `check-anchor.check_anchor` 必须等于**当前**锚点——导入时核对过、之后重跑 Check 也不算数（机制稿 §9.2「失效锚点一律重审」）。
- **阻塞发现**：`findings` 里出现 `blocker/blocking/critical/high` 即拒（机械稿「存在阻塞项即 fail」）。
- **声明来源**：`source-cli` 必须等于 launch 时为该槽位声明的 `reviewer_cli`。
- **材料声明**：`read-scope` 与 `excluded-scope` 不得为空。

四项都是**拒**（`WF_REVIEW_INVALID`）而非判 fail：它们说明判定输入本身不成立，不是"审查意见为否"。判 fail 仍留给"意见为否/人数不足/CLI 重叠"。

## 2. repair 预览漂移

原来的令牌是随机数，应用进程会**重新预览**再拿新摘要，随机令牌照样匹配——于是"人看到的预览"与"实际应用的状态"可以不是同一份。

改为：`PreviewToken.derive(digest) = sha256("wf-preview-token-v1:" + digest)[:32]`，预览打印派生值；应用时用 `confirm_derived()` 只认**当前摘要派生**的令牌。写者代次一变，摘要变，旧令牌立即失效（`WF_PREVIEW_STALE`）。
`issue(nonce=...)` 保留给 `--verify-token-parity` 的确定性比对，不影响应用路径。

## 3. 独立入口锁

运行时 `lock.py` 的契约是：排他创建成功才写 `wf-lock-v1` 标记；已存在的文件若标记为空或不认识，一律 `LockUnavailable`（不认领）。
`repair.py`/`uninstall.py` 原来对空文件直接写标记——等于承认"初始化未完成"的锁对象。现在改为同样的两分支：`O_CREAT|O_EXCL` 成功才写标记；否则必须读到完整标记，缺失即 `ValueError` 并在调用侧转成结构化阻断。

## 4. 边界

- 不新增原因码：审查输入问题用 `WF_REVIEW_INVALID`、令牌问题用 `WF_PREVIEW_STALE`、锁问题沿用既有阻断出口。
- 不改报告协议字段，只加校验。
- 令牌仍是 32 位十六进制，人机交互形态不变（预览打印、终端输入）。

## 5. 新增回归

`r68_tests.py` 9 条：审查正例 + 四类应拒 + 令牌三类（正常、漂移、可应用）+ 空锁不被认领。已加入 `run_all.sh`（38 项）。
