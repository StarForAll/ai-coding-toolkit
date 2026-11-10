# 收口交付（PRD §8 四项一次给全）

> 生成于 2026-11-10。P0–P6 的逐阶段细节在 `p0..p6-delivery.md`；四轮外部审查的裁定在
> `review*-adjudication.md`；测试实跑的完整链条在 `harness-run.md`。本文只做**收口**。

## 1. 改动清单（文件 → 动机 → 编号）

| 文件/目录 | 动机 | 编号 |
|---|---|---|
| `docs/workflows/wf/`（原中文目录） | 源树目录改英文，显示名不变 | S11 |
| `payload/protocol/**` | 机器事实唯一源（码表/状态/阈值/项目数据集合） | K1 / K10 / §11.1 |
| `payload/lib/wflib/protocol.py` | 纯投影，不持有第二份枚举 | 不变量 4 |
| `payload/lib/wflib/paths.py::path_list` | 路径清单归一唯一实现（三处历史炸点收敛） | K10 |
| `payload/lib/wflib/maintenance.py` | 提交层回执账本 `.wf/install/maintenance.jsonl` | S6 / 方案 D |
| `payload/lib/wflib/tasks.py` | 抽样门禁、归档续做、abandon 形态归一、spec 读取留痕、持久化事实 | K2 / K4c / S4 / §4.4 |
| `payload/lib/wflib/sampling.py` | 冻结/选样单一状态形状 | §0.2 |
| `payload/lib/wflib/gates.py` | 步骤表顺序（抽样排最后）、debug 阈值、终局挂起 | K3 / §0.2 |
| `payload/lib/wflib/judgments.py` | 判断项校验、drift 重建、预览行 | §5.2 / §5.3（部分） |
| `payload/lib/wflib/review.py` | 判定物一致性（B1）、缺口/未覆盖项、锚点 | S3 / v42 B1 |
| `payload/lib/wflib/check.py` | 检查门禁、spec 覆盖率事实透出 | K4 |
| `payload/lib/wflib/authorize.py` | 确认覆盖路径匹配（空 glob 不可用） | K6 |
| `payload/install.py` / `scripts/wf-dev-deploy.py` | 自包含回执写账本 | S6 |
| `scripts/tests/wf_runtime/full/**`、`repro/**` | 夹具跟上门禁；静默失败改"先打印事实" | §0.2 抽样 / K10 |
| `scripts/tests/wf_runtime/full/run_all.sh` | 必过门 + 豁免清单 + 串行记账 | CI |

## 2. 验证记录（命令 → 结果）

| 命令 | 结果 |
|---|---|
| `python3 -m unittest discover -s scripts/tests -t . -q` | **305 OK**（每次改动后**重跑全文**，不再只跑子集） |
| `python3 scripts/tests/wf_runtime/full/run_all.sh` | **132 项 / 失败 0 / GATE-OK（豁免 0）**；repro 68/68 |
| `python3 scripts/build-wf-release.py --verify` | **OK 字节复现（70 assets）** |
| `python3 scripts/validate-wf-design.py` | **OK**（定义命中 100% / 消费点缺项 0） |
| `python3 scripts/check-doc-refs.py` | **0 problem(s)** |
| `python3 scripts/wf-protocol-docs.py --check` | **OK**（36 码 / 16 配置键 / 11 条转移） |
| `python3 -m unittest discover -s scripts/tests/wf_protocol -t . -q` | **OK**（6 条不变量断言） |

## 3. 与 v42 的偏差（每条：哪条 / 为什么 / 影响面）

| v42 条目 | 偏差 | 原因 | 影响面 |
|---|---|---|---|
| §5.3「判断质量对照 / 依据对照」预览 | **已实现（2026-11-10 补齐）** | —— | 预览现含 13 段中全部条目：`[判断质量]` 按顶层目录重叠选"上次同类任务"、`[依据对照]` 并列 basis 全文与 refs；另补 `[扩面]/[规则文件]/[缺口]/[未核实]/[有效性]` |
| A7 类「轮次上限」 | 不做机械拒绝 | 代码里 `round_ids` 明确"只作观察与历史重建，不再作为拒绝依据" | 再开一轮由人/判定决定，不靠计数拦 |
| 报告声明的"未覆盖项" | 按**缺口**留痕，不判 fail | v42 B1 三态判定：fail 仅当存在 blocking finding | 缺口进 4.8/4.9，不进 failures |
| 阶段模型 | 保留四阶段，`fixing` 不落盘 | 人裁定出口 A | 与 v42 S5 的差异已登记 |

## 4. 未完成项与原因

| 项 | 状态 | 原因 / 下一步 |
|---|---|---|
| §5.3 判断质量对照预览 | **已完成**（`judgments.quality_comparison`） | —— |
| `trellis-finish-work` | 未跑 | 任务仍 `in_progress`；归档与 workspace journal 待执行 |
| 证据原始 tar.gz | 不发布 | 已决定（README 已写明），非遗漏 |
| `.trellis` 历史路径回填 | 有意不做 | S11 只要求脚本/测试从清单取路径 |
| 用户未提交的在途改动 | 未动 | 保持原样（13 M / 2 D / 2 ??） |
