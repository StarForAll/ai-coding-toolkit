# 修正 wf 脚本校验与文件句柄管理

让 wf 方案文档的断链能使校验失败，并显式关闭本任务核实的文件句柄。资源验收要能区分「单测通过但仍有未关闭文件」和「单测通过且没有该警告」。下列行号取自基线 `924e8091`。

## 需求

**R1　按完整编号核对本地章节引用。** [check-wf-analysis.py](../../../scripts/check-wf-analysis.py) 第 35–46 行有两条互不一致的路径。首条要求 `hist_start == 0`，此时 `live` 又必为空，所以无法报告任何引用。余下逐行逻辑仅匹配数字开头的二级引用。旧全局正则也会把 `§6a.1` 截成 `§6a`。替换为唯一的检查流程，支持一、二级及各级可带字母后缀的编号，逐行报告完整悬空引用，禁止回退到同号上级章节。超过二级的数字编号也要完整报告。

引用检查只豁免 §9 历史小节。当前 `hist_start` 截取到文末，误跳过了 §10 的正式裁定。同期订正 [方案 D3](../../../docs/workflows/wf/analysis/proposal-repairing-state.md) 第 374 行和 [backlog D3](../../../docs/workflows/wf/analysis/backlog-excluded-from-item6.md) 第 100 行的旧 §4.1 指向。两处改指现行 §4 的 C2 行，依据方案第 206 行对 A8 的明确指向及第 358 行的合并记录。D3 裁定文本与历史表保留。

**R2　显式关闭已核实的文件句柄。** 下表覆盖两个作者侧命令的三处读取，以及四个测试文件的七处读写。审查方报告的九条测试警告是输出次数。此前会话观察到其中三个测试文件的警告，本轮按源码确认全部七个测试位置。对 `check-doc-refs.py` 的只读复核中，`-W error::ResourceWarning` 打印了三条文件析构警告，进程仍退出 0。

| 文件 | 基线行号 | 操作 |
|---|---:|---|
| [scripts/check-wf-analysis.py](../../../scripts/check-wf-analysis.py) | 11、81 | 读取方案正文及逐个统计 Python 文件行数 |
| [scripts/check-doc-refs.py](../../../scripts/check-doc-refs.py) | 75 | 读取待校验文档 |
| [scripts/tests/wf_protocol/test_invariants.py](../../../scripts/tests/wf_protocol/test_invariants.py) | 199、203 | 读取阈值 JSON 和配置源码 |
| [scripts/tests/wf_runtime/test_ready_runs.py](../../../scripts/tests/wf_runtime/test_ready_runs.py) | 98 | 读取任务记录 |
| [scripts/tests/wf_runtime/test_rules_digest_parity.py](../../../scripts/tests/wf_runtime/test_rules_digest_parity.py) | 34、41 | 读取开发清单 |
| [scripts/tests/wf_runtime/test_scope_d_bucket.py](../../../scripts/tests/wf_runtime/test_scope_d_bucket.py) | 37、40 | 写入基线和修改后的夹具文件 |

保留现有编码、读取解析、写入顺序和错误传播。文件关闭后再执行依赖文件内容的 Git 操作。

## 验收

- **AC1（R1）** 运行隔离副本中的实际校验入口。有效编号通过，缺失的一级、二级和带字母编号各自以退出码 1 报告完整编号及实际行号。含点的长编号不能靠已有前缀通过。旧引用放在 §9 内通过，放在其后的正式小节则失败。缺少历史小节时，引用检查覆盖整个文档。撤回词和矩阵标签仍只检查旧边界之前的内容。
- **AC2（R1、R2）** 当前仓库的 `check-wf-analysis.py`、`check-doc-refs.py`、`validate-wf-design.py` 均通过。前两个命令保留默认入口、正常输出和退出码约定。
- **AC3（R2）** 按 [实施计划](implement.md) 检查两个作者侧命令及 T0 的 stderr。任一命令非零，或出现 `ResourceWarning: unclosed file`，验收非零。实施时用修正前的代码验证门槛能拒绝已知警告，再用修正后的代码证明通过。unittest 的 `OK` 单独不足以判定该项通过。
- **AC4（R1、R2）** T0 通过，完成项目适用的收口验证。按实施计划逐条核对两份文档的 D3 指向同一个方案 §4 C2 行，保留「选 A：接受成本、A8 后补」的裁定。最终差异限定为本任务工件、R2 清单、R1 的两个引用位置和新增引用回归测试。

## 范围边界

- 校验器面向现有 wf 方案格式。通用 Markdown 引用解析、缺判据表的诊断、其余校验规则及文档语义判断另属范围。历史范围调整仅用于章节引用检查。
- `wf-evidence-snapshot.py` 第 257、267 行也有裸读。这是历史证据工具的独立入口，常规单测和本任务的文档检查不执行该路径。将这两处留作独立的证据工具维护项，可用合成归档单独验证。原始证据包只在本地留存，不是本任务的验证输入。
- wf 产品运行时、runner 生命周期、发行产物、耗时指标和领域异常策略沿用现有约定。裸 `open` 的检索结果仅用于定位，故障探针、嵌入的子进程代码和独立 `full/` 套件未列入资源修复范围。
