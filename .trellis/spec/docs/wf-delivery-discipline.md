# wf 模块交付纪律（轮次收口的可执行契约）

> 适用范围：`docs/workflows/wf/**`（模块源码）、`docs/workflows/wf-framework-*.md`（三份上位稿）、
> `scripts/tests/wf_runtime/**`（用例）。来源：2026-11-12 的 `11-12-wf-round2` 任务——该任务的三轮审计
> 各漏一批义务，本文把"为什么漏"和"怎么核"固定下来，避免下次重新推导。

---

## 1. 轮次收口核对（Scope / Trigger）

**Trigger**：声称为某一轮（首轮/第二轮/第三轮）"已交付"之前。

**Contract**：以下三份清单**逐行**核过才算收口，缺一张都不算：

| 清单 | 位置 | 核什么 |
|---|---|---|
| 义务表 | 机制稿 §12.1（D 编号 → 机制节 → 轮次标签） | 该轮每一行的机制节是否都有实现 |
| 轮次表 | 实现稿 §6.4（第二轮/第三轮单列） | 该轮列出的能力是否逐项可用 |
| 实现面矩阵 | 实现稿 §7.2（G 编号 → 文件/命令 → 场景行） | 矩阵点名的**文件与函数**是否真有实现与用例 |

**反例（真实发生）**：第二轮曾按"命令从 `WF_CAPABILITY_UNAVAILABLE` 变可跑"验收，于是漏掉 G05 点名的
`wflib/gates.py`（实例绑定时 `gate` 仍抛能力不可用）与 G04 点名的 `runs.py::load_definition`（抛桩、零调用者）。
两张表绿、契约没落实。

**Rule**：验收判据写成"**文档点名的实现面 → 有实现 + 有能区分的断言**"，不写成"命令名可跑"。

---

## 2. 机制义务逐句核（不只核主流程）

**Contract**：每条机制义务按**句子**核对，尤其这段里容易被当成"叙述"的过程义务：
- "**预览**/逐个列出"（§6.3 替换、§7.4 异常终止）
- "**授权提交**并只读确认持久化"（§5.1、§7.4）
- "**并 release**""保存交接/工作区"（§6.2 返工普通分支）
- "未持权只报告待复评"（§6.2）
- "报告四类各自 passed/failed/unknown 及未覆盖对象"（§8.5）

**Wrong**：`run terminate` 只写终态、直接 `done`，把"固定提交步骤"当成可选。
**Correct**：动作 steps 增 `persist_record`，无授权停在 `persist_pending` 并如实说明（§5.1 的终态语义）。

**Rule**：句子里的动词（预览/列出/保存/释放/提交/报告）都是义务；主流程跑通不等于义务落实。

---

## 3. 双模 repro 的契约

**Contract**：`scripts/tests/wf_runtime/full/repro/<name>.py` 必须同时过两面：

| 面 | 命令 | 含义 |
|---|---|---|
| green | `python3 repro/x.py --expect green` | 正确实现上断言成立 |
| red | `WF_REPRO_INJECT=1 python3 repro/x.py --expect red` | 注入缺陷后**目标断言**变红 |

**注入必须可达**：注入后用 `patch()` / `_harness` 改的代码必须真的在目标路径上执行。三层守卫（绑定 + 写权 + 幂等）
会让"重入/二次调用"类缺陷注入不可达——此时**改注入单层可观察事实**（如 `run_id` 取值、快照字节、记录字段），
不要伪造一个到不了的缺陷。
**反例**：三次注入落在守卫外（`dep` 自环双锁、`run create` / `run advance` 的三重守卫），red 面形同虚设。

---

## 4. 同一判定只有一处实现

**Contract**：同一判据被多个入口需要时，抽一处实现并参数化输入，调用点不各自复制：

| 判据 | 唯一实现 | 消费者 |
|---|---|---|
| 放弃一个任务 | `tasks._apply_abandon()` | `task-abandon`、`run terminate`、`task-replace` |
| 定义加载 | `runs.load_definition()` | `definition validate/prepare`、`run create` |
| 归属存疑（d 档） | `scope.cross_task_conflicts(root, task, touch_paths)` | `check`、`inspect` |
| 实例可绑定资格 | `cli._eligible_run_bind()` | `bind --run`、`ready` |
| 复评写权事实 | `tasks.reassess_write_right()` | `task-reassess` |

**Wrong**：`check` 自己再算一遍 `cross_task_conflicts` → 两处判定、一次注入改不动全部（red 面失效）。
**Correct**：`touch_paths` 作为参数传入，只推导一次。

---

## 5. 新增资产 / 字段的登记链

**Contract**：新增 payload 文件或记录字段，同批完成四项：

1. `docs/workflows/wf/dev-manifest.json` 增 asset 条目（否则发行预检的清单/源码树不一致会失败）；
2. `scripts/build-wf-release.py --version 0.1.0` 重建发行树（单独一笔 `chore(wf): 重建发行树` 提交）；
3. 机制稿的字段表登记（判定字段）或"只读信息字段"登记（如 `paused_reason`/`resumed`/`closing.pending`）；
4. 写者、消费者与失败出口各写清（机制稿 §1.1 的登记纪律）。

**反例**：`wf-judging` 删除时只改源码不动 manifest → 预检失败；`handoff.wip` 在返工分支漏写 → 新会话看不到未提交改动。

---

## 6. "有实现、无断言" = 未验证，必须登记或补断言

**Contract**：任何分支若只有实现、没有能区分的断言，收口时二选一：补断言，或写进任务的"无断言清单"并说明为什么现在补不了。

**为什么**：本任务两次因此抓到真缺陷——`_previous_task_step` 不过滤被略过的任务步骤（会报 `WF_DEPENDENCY_UNMET`）、
返工普通分支不写 `handoff.wip`。两处都是"读代码像对、跑起来才不对"。

**Tests Required（断言点）**：每条分支至少一条断言锚在**行为**上（记录字段/返回码/下游重连/写权状态），不锚排版或文案。

---

## 7. 并行纪律：`run_all.sh` 独占夹具

`run_all.sh` 使用 `/tmp/wf-fixtures/*` 与发行仓库副本（默认 `~/.cache/wf-release-repo`），**同时跑两份会让双方挂起**
（本任务实际遇到一次 SIGTERM，另一次 `r71_tests` 报 `KeyError: 'directory'` 属夹具竞态）。
跑全量前先确认没有并发实例；单跑某套件用 `WF_SUITES="<name>" bash scripts/tests/wf_runtime/full/run_all.sh`
（它会自己重建夹具），不要直接 `python3 rXX_tests.py`。

---

## 8. 收口前的最小证据集

```bash
/softwares/python/bin/python3 -m unittest discover -s scripts/tests
/softwares/python/bin/python3 -m unittest discover -s scripts/tests/wf_runtime
bash scripts/tests/wf_runtime/full/run_all.sh          # 独占，勿并发
/softwares/python/bin/python3 scripts/build-wf-release.py --verify
/softwares/python/bin/python3 scripts/build-wf-release.py --verify-token-parity
/softwares/python/bin/python3 scripts/validate-wf-design.py
/softwares/python/bin/python3 scripts/check-doc-refs.py
./scripts/validate-skills.sh
```

任一失败先归因（实现缺陷 → 修实现；实现正确但事实不足 → 才回修机制稿），不改判据迁就绿灯。
