# 第二轮审查裁定（2026-11-09）

判据同前：先核，再改；只治根因；不引入新锁死。审查里 **a 侧两条、b 侧 N1/N2 属实**，N3 的四条摩擦全部有据。

| 审查条目 | 核实 | 处置 | 提交 |
|---|---|---|---|
| **a-P1a 项目 spec 被当 vendor → 初始化任务无法归档** | ✅ 属实。`vendor_assets` 的数据前缀只有 `.wf/tasks/`、`.wf/install/` | 前缀补 `.wf/spec/`（实现方案：spec 由 `spec.update` 写入、升级不覆盖 = 项目数据） | `ec38b95` |
| **a-P1b 漂移不可得被当成"没有漂移"** | ✅ 属实。`anchor_parts` 异常时 `return []` | 改为 `WF_SEMANTIC_DECISION` + 两条出口（重跑 Check / 人确认按当前标准继续并记 judgment）；锚点无 parts 同样处理 | `ec38b95` |
| **b-N1 writer.json 生成"既提交又被改"的夹缝** | ✅ 属实。托管忽略段只有两项，而 v42 S10 要五项 | 与 v42 S10 对齐：补 `/.wf/session-bindings/`、`/.wf/writer.json`、`/.wf/.cache/`（运行态可丢弃重建） | `ec38b95` |
| **b-N2 subject 空格分隔直接失败** | ✅ 属实 | `_subject_paths` 接受空格；help 写明"数组或逗号/分号/换行/空格" | `ec38b95` / `c211154` |
| **b-N3 写权 idle 但未持有报 `WF_WRITER_BUSY`、无出路** | ✅ 属实（语义还反了） | 改报 `WF_SEMANTIC_DECISION` + 出口 `wf writer acquire --task <id>` | `ec38b95` |
| **b-N3 出口 2（task-attribute）走不到终点** | ✅ 属实。`_external_checked` 只看 trailer | 让 `_external_checked` 消费 `attribution.decisions`（按 OID 前缀匹配） | `ec38b95` |
| **b-N3 help 缺 generation / plan-q 形态** | ✅ 属实 | `task-approve` help 补两条（generation 必填、plan-q 答复用 `choice="plan-q"` 且 subject 含编号；旧夹具的 `choice="是"` 已不接受） | `c211154` |
| **b-N3 存量项目 bootstrap 顺序无提示** | ✅ 属实 | `complexity condition requires complex` 的 facts 加 `hint`；平台校验失败的 next 也指向"先建 bootstrap 任务" | `c211154` |
| **a 的 F1 夹具用 `choice="是"`** | ✅ 属实（`f1_init.py:88`、`f1_ordinary.py:80`） | **未改**：这两个文件属你未提交的在途工作，我没动；协议侧已在 help 写明新形态 | — |

## 两处我判断"不改"，理由

1. **F1 夹具的 `choice="是"`**：属你的 WIP 文件，改它混进我的改动不合适；且 help 已说明现协议。
   若要我把这两个夹具迁到 `choice="plan-q"`，一句话即可（会修改你的未提交文件）。
2. **b-N1 的另一半（机制稿把 writer/journal 归 committed 与 v42 S10 冲突）**：我按 **v42 S10** 对齐了实现
   （它是唯一写明分层的一份）。机制稿 §146 只登记 writer.json 的字段，**没有**说它在 committed 层，
   所以严格意义上不构成口径冲突；若你认为机制稿应显式声明分层，需要你裁一句，我再补正文。

## 共同根因（这轮的教训）

两轮审查的实质缺陷都落在同一类：**"事实不可得"被折叠成"事实为空"**（锚点清单、漂移、事件池），
以及**"项目数据 vs 框架资产"的边界靠前缀猜**（`.wf/spec/` 漏了）。
前者是诚实性问题（宁可交人，不可默认通过），后者是边界问题（该由声明表驱动，不该由前缀推断）。

## 验证

279 条用例全绿（+6）；`--verify` 字节复现（69 assets）；设计门禁 / 文档引用 / 协议一致全绿。
