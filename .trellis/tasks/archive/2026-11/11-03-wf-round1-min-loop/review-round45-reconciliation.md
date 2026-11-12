# 第四十五轮：第二轮独立复审（codex，新会话）的复核与修正

- 复审主体：`codex exec` 全新会话（未参与修订），只读，独立夹具在 `/tmp`
- 处置编号 R80；实跑见 `validation.md` §72
- 结论：**8 条 → 5 条缺陷成立并已修、1 条文档说明错误已改正、2 条通过**

## 0. 逐条判定

| 判据 | 复审结论 | 我的复核 | 处置 |
|---|---|---|---|
| D01 公式 | 通过；兼容说明错误 | **成立**（公式对，说明错） | R80-a |
| D02 Check 结构复核 | 缺陷·高 | **成立** | R80-b |
| D03 处置事实核验 | 缺陷·高 | **成立** | R80-c |
| D04 裁定标识 | 缺陷·中（`²` 触发 ValueError） | **成立** | R80-d |
| D05 覆盖数量 | 缺陷·中（r72 不计数） | **成立** | R80-e |
| D06 函数落点 | 通过（79 符号缺失 0） | 同意 | — |
| D07 脱敏 | 缺陷·高（facts/日志仍泄漏） | **成立** | R80-f |
| D08 死函数 | 通过 | 同意 | — |

## 1. R80-a：D01 的兼容说明写错了

我上一轮写「旧回执会失配、判 `WF_CHECK_STALE`」——**不成立**。机制稿 §11.2 规定回执**选择**按 id/occurrence（规则类再加 rule_version），`receipt_state()` 也确实不比 `anchor`。所以旧回执照样被选中，差别只是记录里的 `anchor` 字段与当前公式输出不一致（记录内不自洽、不产生阻断）。

已把实现稿那段改成事实描述。公式本身经复审独立编码比对，两类都逐字节相等，不动。

## 2. R80-b：Check 结构复核只做了一半（高）

原实现只核"非空"和"id 集合覆盖"。复审用真实夹具证明：`conclusion=failed` 的验收、被替换的 invocation、`exit_code=7`、`ended_at=None`、重复结果、未知 verification id 全部**照样通过**；反过来 `required=false` 的可选验证没执行却**被误挡**。

根因是生成端与门禁端各写一套判据。改为**共用同一实现**：`check.validate_check_result(task, check)` 放在生成端模块，门禁端 `gates.check_result_problems()` 直接调它。核验项：

- `result=pass`、`anchor.rule_version` 存在；
- 命令项必须对应**批准声明的 verification**（kind 一致；argv 类把两侧都过同一脱敏后逐项比对），状态 `passed`、`exit_code=0`、`ended_at` 非空；
- 命令 id 不得重复、不得出现未声明的 id；
- **必要集合**按 `required is not False` 计算，可选验证未执行不阻断；
- 验收结果必须覆盖计划里的每个 acceptance（`conclusion=passed`），不得有未知或重复 id；
- 内部双轴各有 `pass` 与 `basis`。

## 3. R80-c：处置事实核验还能被空值绕过（高）

三处：
- `change.get("before")` 把「字段缺失」和「显式 null」混为一谈 → reverse 缺 before 也判结案；
- `_fp_matches({}, …)` 对空对象**无条件返回 True** → `before={}` 也结案；
- 承接任务的 `approval={}` 被当成"已批准"（原来只判 `is None`）。

修法：reverse 分支要求 `"before" in change`；`_fp_matches` 拒绝空对象/无字段对象、空串摘要；transfer 要求 `approval` 是**非空对象且含 decision、任务 plan 有 version**。另在 `writer._disposition_complete()` 增加一条：**处置决定的 choice 必须等于 kind**（`kind=commit` + `choice=reject` 不再结案）。

## 4. R80-d：`²` 触发内部异常（中）

`tail.isdigit()` 对 `²` 为真、`int()` 抛 `ValueError`，写入口把内部异常抛给调用方。改为 `tail.isascii() and tail.isdigit()`，写入路径稳定返回 `WF_RECORD_INVALID`。

## 5. R80-e：实际执行 48 项，脚本报 47（中）

`run_all.sh` 执行 r72 后没有 `ran=$((ran+1))`。改为 `run_extra` 统一计数（跑脚本、断 PASS 数、计 ran），并把实现稿的覆盖数字改为按实际执行集合声明：**当前 49 项**（本轮又加了 r80）。

## 6. R80-f：脱敏规则两套，facts 与日志仍泄漏（高）

命令记录走 argv 级脱敏、facts 与日志走文本级，两者覆盖不同：`--api_key <值>`、`--access-token <值>`、`Authorization: Bearer xyz`（短值）都漏。改为**一份实现**：

- `redact_text()` 统一处理 `Bearer <任意值>`（去掉 8 字符门槛）、`--token/--api-key/--access-token/--client-secret` 等分离与 `=`/`:` 写法、`key: value` 形态；
- `redact_secrets` 保留为别名，调用点全部走同一函数；`redact_argv()` 只在"分离参数的相邻位置"上补充，逐项再过 `redact_text`。

## 7. 复审同时确认的两件事

- 「未知压制候选」不会让正常项目永远拿不到结论：完整记录时 `statistic_complete=true`、有候选、`due` 有结论。
- §6.2/G11/G22 的 79 个符号引用独立 AST 核对缺失 0。
