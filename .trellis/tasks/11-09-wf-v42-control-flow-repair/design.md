# 设计：P0 —— 证据固化 + protocol 单一事实源 + 6 条不变量

本文件只覆盖 P0；P1–P6 的语义设计由 v42 唯一承载（见 PRD §2），不在此重述。

## 1. 承载物与落点

| 承载物 | 落点 | 是否发行资产 | 理由 |
|---|---|---|---|
| v42 决策记录 | `docs/workflows/新项目开发工作流/analysis/solution-review-v42.md` | 否（authoring） | 决策记录属 authoring 文档族，不投放目标项目 |
| 证据包 + 说明 | `.../analysis/evidence/` | 否（authoring） | 证据是 authoring 侧的复算材料 |
| protocol 机器事实 | `.../payload/protocol/{states,codes,thresholds,redaction}.json` | 是 → `.wf/protocol/` | `wf help`/`wf status` 在目标项目运行期消费，必须随发行投放 |
| protocol 加载器 | `.../payload/lib/wflib/protocol.py` | 是 → `.wf/lib/wflib/` | 语义层读取唯一事实源 |
| 文档片段生成器 | `scripts/wf-protocol-docs.py` | 否（authoring 工具） | 只服务文档一致性与人审 |
| 证据打包/复核 | `scripts/wf-evidence-snapshot.py` | 否（authoring 工具） | 只服务证据复算 |
| 6 条不变量 | `scripts/tests/wf_protocol/test_invariants.py` | 否（authoring 测试） | 源仓库常驻测试 |

新增发行资产类别 `protocol`：`scripts/wf_release_common.py` 的 `PROJECT_CLASSES` 增加一行 `payload/protocol/ → .wf/protocol/`，`dev-manifest.json` 逐文件登记。安装/升级/卸载按清单资产泛化处理（已核实：`install.py`、`bin/uninstall.py` 只按 `target_relative`/`digest` 枚举，不按 `kind` 分派），故新类别只影响清单与 `rules_digest`。

## 2. 单一事实源方向（纪律 #4）

`protocol/*.json` 是机器事实的**唯一**存放处；Python 侧只做加载与渲染，不再持有第二份枚举。

- `wflib/codes.py`：删除手写 `CODES` 表，改为 `from .protocol import CODES`（保留 `CODES`/`tier_of`/`exit_of`/`prohibited_of`/`process_exit`/`result` 公共名，调用点零改动）。判据：`codes.py` 源码内不再出现任何 `WF_` 字面量。
- `wflib/protocol.py`：加载四个 JSON + schema 版本校验 + 派生查询（`tier_of` 不在本模块重复，由 codes 转出）。加载失败一律 `WF_CAPABILITY_UNAVAILABLE`（资产缺失即资产问题，不是业务问题）。
- 机制稿 §11.1 的码表仍是**语义**权属（码值/档位/出口/禁止修复动作以它为准）；protocol 是它的机器形态。两者由不变量⑤比对，禁止各自演化。

## 3. protocol 四个文件的内容与来源

| 文件 | 内容 | 唯一来源 |
|---|---|---|
| `states.json` | `status` 三态、`phase` 四态、阶段模型句、状态转移表（动作/源/前置与目标/失败码）、`next_by_position` | 设计稿 §1.3、§4.1；机制稿 §2.2、§11.1 |
| `codes.json` | 35 枚码的 `tier`/`exit`/`prohibited_repairs` | 机制稿 §11.1 码表 |
| `thresholds.json` | 机制稿 §8.1 全部配置键的 `type`/`default`/`consumer` | 机制稿 §8.1 |
| `redaction.json` | S7 脱敏口径：`keep`（入库保留项）/`runtime_only`（敏感原文留 runtime）/`direction`（单向加严） | v42 S7、S10、K6 |

阶段模型按**人裁定 A**：`phases = ["plan","execute","check","finish"]`，不含 `fixing`，**`check` 是持久阶段**。

`next_by_position` 只登记"状态/阶段 → 具名下一操作"这一条事实，用于 `wf status` 的 `next` 字段与不变量③；它不表达流程纪律（纪律在 SKILL 与机制稿）。

## 4. 不变量 6 条的判据（何为绿）

| # | 不变量 | P0 的判定方式 |
|---|---|---|
| ① | 可达性 | 以 `states.json.transitions` 建图，BFS：每个可达 `(status,phase)` 都存在到 `archived/archived_at` 的路径；`terminal` 标记与图一致 |
| ② | 门禁错误带可执行出口 | `codes.json` 中非 `pass` 档的每条都有非空 `exit` 且 `prohibited_repairs` 非空；`payload/lib/wflib/**` 出现的每个 `WF_*` 字面量都已登记（未登记=红） |
| ③ | `status.next` 与真实错误码一致 | `cli.cmd_status` 两处 `next` 必须由 `protocol.next_for()` 取值；测试断言每个 `(status,phase)` 的 next 与 `states.json` 等值，且该 next 命名的操作存在于 `cli.COMMANDS` |
| ④ | 投影/骨架重建等值 | P0 覆盖范围：`codes.py` 是 `codes.json` 的纯投影（往返等值）。`open-items` / `attribution_index` / 判断骨架 `--check` 的等值断言随 P5 投影落地（P0 无该投影，不编造夹具） |
| ⑤ | 文档机器事实与 protocol 一致 | `scripts/wf-protocol-docs.py --check` 解析机制稿 §11.1 码表、§2.2 状态/阶段句、§8.1 阈值表，与 protocol 逐项比对 |
| ⑥ | 脱敏规则只增不减 | `redaction.json` 的规则集必须 ⊇ `redaction.baseline.json`（首版冻结），且 `direction=strictly-tighten`：放松需改不变量并留痕，测试对"基线规则被删除或降级"直接判红 |

## 5. 证据包结构（可复算）

```
analysis/evidence/
  README.md                       来源、范围、敏感性、复核命令
  archived-task/                  dogfood 归档任务全树（69 文件）
  sessions/                       4 份 Codex 会话 JSONL（16:12 / 17:00 / 17:10 / 17:16）
  wf-review-tree/                 /tmp/wf-review 全树（7261 文件）
  target-lib/                     traffic_monitor/.wf/lib/wflib 与源树的 diff + 两侧摘要
  manifests/*.sha256              逐文件清单（相对路径 + sha256 + 字节数）
```

打包与复核都用 `scripts/wf-evidence-snapshot.py`：打包确定性（路径排序、`mtime=0`、`uid/gid=0`、`gzip mtime=0`），故 `--verify` 可用"重打包→比字节"证明证据未被改动；源侧被清理后仍可用 `manifests/*.sha256` 做离线校验。

## 6. 明确不做的选择（及理由）

- 不为 protocol 建第二套"命令表"：命令清单属 `cli.COMMANDS`，P0 不搬（纪律 #4 的命令/参数部分随 P5 的"单一 protocol 源与文档生成"落地，避免一次搬入未经测试的 40+ 条命令形态）。
- 不改机制稿把片段"注入"回正文：改写上位文档属 T7 人审动作，P0 只做"生成片段 + 反向校验"，文档正文保持人手维护。
- 不重建 `docs/workflows/wf-release/` 之外的东西；不提交。
