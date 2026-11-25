# 设计：wf 第四轮复审判定的机制收口

## 1. 边界与目标

只改 `docs/workflows/wf/` 内的实现与随批文档，不动 charter、设计稿 §1.1 的原则文本、原因码表的新值。
三处缺陷的共同形态是「事实已由机制算出或可稳定算出，但没有出现在 AI/人做决定的位置」——修法一律是
**把已有事实接到唯一消费点**，不新增判断步骤。

## 2. F1：批准草稿的事实面

### 2.1 唯一来源

- 复杂度提议：`tasks._complexity_proposal(ctx, task, block, extra)`（已存在，`tasks.py:1648`）。
  正式批准在 `tasks.py:1917` 调用它；草稿分支此前在 `tasks.py:1803` 就返回，未调用。
- TDD 生效值：正式批准的四段解析在 `tasks.py:1950-1963`（决定 → inputs → 项目配置 → 内置缺省）。
  抽成 `tasks._resolve_tdd(ctx, plan_decision, inputs)` 单实现，草稿传 `plan_decision=None` 复用，
  避免两处各写一段解析。

### 2.2 草稿输出（`task-approve --draft`）

facts 追加：

```json
{
  "complexity_proposal": {"value": "light|complex",
                           "reasons": [{"condition": "governance|contract|acceptance|scope",
                                        "value": "true|false|unknown", "fact": "..."}]},
  "tdd": {"value": false, "source": "inputs|project-default|built-in-default"}
}
```

approve 条目追加 `plan: {complexity: <提议值>, tdd: <生效值>}`；机械修订条目**不**带 plan
（它不是重新批准，带 plan 会让等价链看起来像人重新分级）。

草稿仍只读、不落盘、不取写权；`pending_plan_questions` 保留。

### 2.3 正式批准的来源真值

`confirmed_source` 三值：

| 条件 | 值 |
|---|---|
| 决定 `plan.complexity` 有值 | `decision` |
| 否则请求 `inputs.complexity` 有值 | `inputs` |
| 都没有（取机器提议） | `proposed`（新值，机制稿 §2.3 行同批登记） |

`proposed` 时在结果 warnings 里加一条可见提示（分级按机器提议、未获人确认）；`complex`
仍必须 `decision`（`gates.py:1120` 不变），因此 `proposed` 只可能是 `light`。

兼容：旧决定文件（无 plan）继续可用，只是记录更如实；mechanism 稿
「`confirmed_source` 取 `decision`/`inputs`」改为三值并说明 `proposed` 的含义与门禁关系。

### 2.4 指引

`wf-continue/SKILL.md:20` 的「呈现复杂度与 TDD」不改——它要求的正是本轮补上的事实；
在同行补一句指针「取值与理由见 `task-approve --draft` 的 `complexity_proposal`/`tdd`」。

## 3. F2：审查入口的终态与必需性

### 3.1 唯一判定

`review.round_entry_gate(task)` 返回：

```json
{"task_status": "archived|in_progress|not_started",
 "complexity": "light|complex|null",
 "terminal": true,
 "external_review_required": false}
```

口径：`terminal = status == "archived"`；`external_review_required = complexity == "complex" and not terminal`。
「复杂任务审查是完成条件」的定义在设计稿 §6.5，此处只把它变成可判事实，不新增承诺。

### 3.2 消费点

- `cli.cmd_review_status`：`round < 1` 分支改为按 gate 分派：
  - `terminal` → 「对象已归档：审查轮次已关闭；结论见归档记录，需要对新的对象再发起」；
  - `complexity == "light"` → 「轻量任务不要求外部审查轮（以 Check 的双轴内部审查为准）；
    确需外部审查再 review-launch」；
  - 其余 → 保留原文案。
  facts 增 `entry_gate`，让只看 JSON 的调用方不必解析 next 文案。
- `review.launch`：进入锁前的第一道核验改为 `entry_gate(task)`，`terminal` 时抛
  `WF_SEMANTIC_DECISION`（facts：`status`、`reason: task is archived`、`exits` 指向新对象/归档记录），
  **先于** `_is_approved_plan`——后者的「规划批准已失效」是归档后 PRD 移位的副作用，不是真实原因。

### 3.3 不做

不禁止轻量任务自愿发起外部审查（设计稿没有这条禁令）；不新增「审查必需」的硬门禁
（`gates` 的 `review-passed` 已按复杂度适用），只修投影与诊断。

## 4. F3：pass 结果的 `exit`

`codes.result` 改为 `exit = exit_of(code) if tier != "pass" else None`：

- 与机制稿 §11.1「exit 是失败/待决时可走的出口」一致；
- 与文本渲染器 `cli.py:738`（pass 不显示 exit）一致；
- `next` 是 pass 的唯一「下一步」通道，消除同一结果里两句话互相矛盾。

同批把机制稿 §11.1 那句补明「pass 结果 `exit` 为 null」。

## 5. 兼容、风险与回退

| 项 | 影响 | 处置 |
|---|---|---|
| 旧决定文件无 `plan` | 记录从 `inputs` 变 `proposed` | 更如实；判定门禁不变；无迁移 |
| 草稿新增 `plan` | 复制草稿即产生 `decision` 来源 | 这是人确认的正确语义；`--draft` 仍只读 |
| `proposed` 值 | 现有消费者的取值域 | 全仓无按枚举值分支的消费者（仅 `gates` 判 `!= "decision"`），同批更新文档与文本断言测试 |
| pass `exit` 置 null | JSON 消费方 | 文本渲染已不看；唯一断言 exit 的用例是 blocked 场景（`full/repro/record-missing-in-worktree.py`） |
| 终态拦截位置 | `review-launch` 的首报项 | 只影响已归档对象的新报错文案；归档对象其余入口已有同类判定（如 `task-check`） |

回退点：四处改动各自独立（tasks 草稿/来源、review gate/投影、codes、文档），可逐项回退；任一失败
不会破坏任务记录格式。不做数据迁移。

## 6. 验证策略

1. 新增/改用例（行为断言，不锚源码字符串）：
   - `scripts/tests/wf_runtime/test_approve_draft_facts.py`：草稿含提议与 TDD；复制后确认来源 `decision`；
     省略 plan 时来源 `proposed` 且有 warning；`complex` 仍拒 `proposed`。
   - `scripts/tests/wf_review/test_review_entry_gate.py`：已归档/轻量/复杂三态下 `review-status` 的 next；
     已归档对象 `review-launch` 的终态 facts。
   - `scripts/tests/wf_runtime/test_result_exit.py`：pass → `exit is None`；blocked → 非空。
2. T0 全量；设计闸门 / doc-refs / validate-skills；`build-wf-release.py --verify --verify-token-parity`。
3. 全量 runner（144 单元）复跑，要求 GATE-OK。
4. 手工 dogfood 复核：在临时项目按本轮修好的入口重跑「草稿 → 批准 → 检查 → 收工」，确认新事实可见。
