# P5 交付记录（K8 投影重建 / K9 审计线索 / S5b 未核实项生命周期）

## 1. 本轮改动

| 文件 | 动机 | 编号 |
|---|---|---|
| `payload/lib/wflib/projection.py`（新） | `open_items`（未核实 + 未处置 finding + 被驳回未处置判断，可重建投影）；`attribution`（提交三态：`wf-task:` 标记 / 人裁决 / 外部）；`audit_chain`（动作 id 序列、`write_mark` 锚定、时间单调；**承诺写明"只到局部损坏/提交后改写可检出，不防伪造"**）；`build`/`check` | K8、K9、S8 |
| 同上 | `is_required` / `required_unverified` / `resolve`：`kind=narrow` 必须给齐 4.9 的四项（id/客观原因/影响与放弃的保障/补偿），`kind=inspection` 必须有证据；写进 `task.unverified_resolutions` | S5b、4.9 |
| `gates.py::final_gate` | **required 未核实 → 阻断归档**（`WF_SEMANTIC_DECISION` + 三条出口：收窄 / 人工核验 / 异常归档），不接受"接受风险" | S5b、4.9、S6 第 5 项 |
| `judgments.py` | 骨架增 `unverified[]`（未结案的 required 验收项）→ §0.2 的"未核实"事件池不再是空集 | §0.2、S5b |
| `cli.py` | `project --kind open-items|attribution|audit|skeleton --task [--check]`（`--check` 断言等值：纯函数性 + 缓存漂移）；`verify resolve --task --id --kind narrow|inspection` | K8、S5b |
| `dev-manifest.json` | 登记 `projection.py`（69 assets） | — |
| `scripts/tests/wf_review/test_projection.py` | 15 条（含链头 3 条）：四种投影都是纯函数、缓存漂移可检出、写链三类问题、承诺边界、required 阻断、收窄四项缺一即拒、人工核验要证据、门禁已消费 | K8/K9/S5b |

## 2. 验证

| 命令 | 结果 |
|---|---|
| `unittest discover` | **203 tests OK**（188 → 203） |
| `build-wf-release.py --verify` | **OK** byte reproduction（69 assets） |
| `wf-protocol-docs.py --check` | **OK** 36 码 / 16 配置键 / 11 转移 |
| `validate-wf-design.py` | **OK** 定义 100% / 消费 100% / 输入摘要 4/4 |
| `check-doc-refs.py` | **0 problem(s)** |

## 3. K9 链头锚定（已补）

- `tasks._chain_trailer`：归档的两段提交消息都带 `wf-chain-head: <write_mark.action_id>`；
- `projection.chain_head_check`：读任务记录最后一次提交的 `%B`，比对 trailer 与当前链头；没有 trailer 时**如实报"未锚定"**而不是猜；
- 测试 3 条（trailer 由 write_mark 派生、归档提交带 trailer、缺 trailer 如实报告）。

**K9 的承诺边界仍写明**：只到"局部损坏/提交后改写可检出"，不承诺防伪造。

## 4. 观察

- `attribution` 的 `unattributed_paths` 目前恒为空（未提交路径的归属由 `scope.classify_candidates` 负责，不重复实现）。
- 投影一律不落盘，因此"删掉重建"恒成立；`--check` 真正能抓到的是"缓存副本漂移"与"投影不再是记录的函数"。
