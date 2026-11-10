# P0 交付记录（v42 阶段 0）

会话日期：2026-11-09。本文件是本阶段的交付物 1–4（改动清单 / 验证记录 / 与 v42 的偏差 / 未完成项）。

## 1. 改动清单（文件 → 动机 → 编号）

| 文件 | 动机 | 编号 |
|---|---|---|
| `analysis/solution-review-v42.md` | v42 全文入库为唯一决策记录（逐字节，sha256 `d06c57e7…cadd`） | §8 起步动作 3 |
| `analysis/evidence/archived-task.tar.gz` | 固化 dogfood 唯一归档任务树（69 文件） | P0 证据 |
| `analysis/evidence/sessions.tar.gz` | 固化 4 份 Codex 会话 JSONL | P0 证据 |
| `analysis/evidence/wf-review-tree.tar.gz` | 固化 `/tmp/wf-review` 审查材料树（7261 文件） | P0 证据 |
| `analysis/evidence/target-lib/{lib.diff,lib-files.sha256}` | 固化「作者侧源树 ↔ 目标侧 `.wf/lib`」漂移事实 | P0 证据 / E3 |
| `analysis/evidence/manifests/*.sha256` | 证据摘要清单（离线可校验） | P0 证据 |
| `analysis/evidence/README.md` | 证据来源、范围、敏感性、复核命令 | P0 证据 |
| `scripts/wf-evidence-snapshot.py` | 确定性打包 + 复算（`--pack/--verify/--offline-verify`） | P0 证据 |
| `payload/protocol/states.json` | 状态/阶段/转移/位置合法集/next 表的机器事实源 | 纪律 #4、S5、K10 |
| `payload/protocol/codes.json` | 35 枚原因码的 tier/exit/prohibited 机器事实源 | 纪律 #4、K10 |
| `payload/protocol/thresholds.json` | 机制稿 §8.1 全部配置键的类型/缺省/消费 + 禁止回流的 cap 名 | 纪律 #4、S6、4.6 |
| `payload/protocol/redaction.json` | S7 脱敏口径（保留项/留 runtime 项/只可加严） | S7、S10、K6 |
| `payload/protocol/redaction.baseline.json` | 脱敏单向不变量的冻结锚（不变量⑥的比较基） | S7、v36 |
| `payload/lib/wflib/protocol.py` | protocol 唯一加载器 + schema 自校验 + `next_for` | 纪律 #4 |
| `payload/lib/wflib/codes.py` | 删手写码表，改为 protocol 投影（公共名不变） | 纪律 #4、⑤ |
| `payload/lib/wflib/config.py` | 删手写阈值缺省/类型集合，改为 protocol 投影 | 纪律 #4、④ |
| `payload/lib/wflib/cli.py` | `wf status` 的两处 `next` 改由 `protocol.next_for()` 取值 | ③、S9 |
| `scripts/wf-protocol-docs.py` | 从 protocol 渲染文档片段 + 反向核对上位文档机器事实 | 纪律 #4、⑤ |
| `scripts/tests/wf_protocol/test_invariants.py` | 6 条常驻不变量（+1 条 §7.1 回流守卫） | §6、§7.1 |
| `scripts/wf_release_common.py` | `PROJECT_CLASSES` 增 `payload/protocol/ → .wf/protocol/`（新发行资产类 `protocol`） | S1/S10 资产落点 |
| `dev-manifest.json` | 登记 6 个新资产（5 个 protocol JSON + `protocol.py`） | S10 |
| `docs/workflows/wf-release/**` | 重建发行树（`--verify` 恢复绿，63 assets） | P0 收口 |

## 2. 验证记录（命令 + 结果）

| 命令 | 结果 |
|---|---|
| `python3 scripts/build-wf-release.py --verify` | **通过**：`OK byte reproduction (0.1.0, 63 assets)`（基线为 57 assets） |
| `python3 -m unittest discover -s scripts/tests -t . -q` | **通过**：`Ran 88 tests … OK`（基线 81；新增 7 条：6 条不变量 + §7.1 回流守卫） |
| `python3 scripts/wf-protocol-docs.py --check` | **通过**：`OK: protocol 与上位文档机器事实一致（35 码 / 15 配置键 / 11 条转移）` |
| `python3 scripts/wf-evidence-snapshot.py --verify` | **通过**：`evidence OK (sources re-packed, byte-identical)` |
| `python3 scripts/wf-evidence-snapshot.py --offline-verify` | **通过**：`evidence OK (offline digests + manifests)` |
| `python3 scripts/validate-wf-design.py` | **通过**：设计期机检七项 + 覆盖率断言通过，消费点缺项 0 |
| `./scripts/validate-skills.sh` | **通过**：`OK: validated 25 skill(s) + spec cross-check passed` |
| `python3 scripts/check-doc-refs.py` | **通过**：`0 problem(s)` |
| `sha256sum /tmp/wf-solution-review-2026-11-09.md analysis/solution-review-v42.md` | **一致**：`d06c57e7d5e7b6cf60e82d673e4227b66531f523787b18e9716496e33331cadd` |
| `python3 -c "from wflib import codes; …"` | 35 码、`tier_of`/`process_exit` 正常；`codes.py` 内 `WF_` 字面量计数为 0 |

6 条不变量逐条状态：

| # | 不变量 | 状态 |
|---|---|---|
| ① | 可达性 BFS（每个可达位置都有到终态的路径） | 通过 |
| ② | 门禁错误带可执行出口（非 pass 码必须有 exit + prohibited；wflib 内无未登记码） | 通过 |
| ③ | `status.next` 与真实错误码一致（表内 next 均点名真实命令；`cmd_status` 无字面量） | 通过 |
| ④ | 投影/骨架重建等值（`codes`/`thresholds` 纯投影；`open-items`/`attribution`/骨架随 P5） | 部分（P0 覆盖面见偏差 D3） |
| ⑤ | 文档机器事实与 protocol 一致 | 通过 |
| ⑥ | 脱敏规则只增不减 | 通过 |

## 3. 与 v42 的偏差

| # | 哪条 | 为什么必须偏 | 影响面 |
|---|---|---|---|
| D1 | **阶段模型**：v42 K10/S5 用 `plan/execute/fixing/finish` 且要求删「持久阶段 `check`」 | 与设计稿 §1.3/§4.1 + 机制稿 §2.2 冲突；**人已裁定出口 A**（保留上位四阶段） | `protocol/states.json` 落 `plan/execute/check/finish`；`fixing` 不落盘；v42 的 S5/K10 文字仍待按 A 回收（本轮未改 v42 文档） |
| D2 | v42 §9「5 条不变量」 | 与 §6 及本任务 P0 退出判据（6 条）冲突 | 按 6 条实现；v42 §9 计数属笔误，未改文档 |
| D3 | 不变量④「投影/骨架重建等值」 | P0 尚无 `open-items`/`attribution`/判断骨架投影（v42 把它们排在 P5） | ④ 在 P0 只覆盖 `codes`/`thresholds` 两组投影；等值断言随 P5 投影落地，未编造夹具 |
| D4 | 纪律 #4「命令、参数」入 protocol | P0 范围只列「状态/转移、阶段模型句、阈值、错误码」 | 命令/参数表仍在 `cli.COMMANDS`/`COMMAND_HELP`，随 P5「单一 protocol 源与文档生成」搬入；本轮不搬（避免一次搬入未测试的 40+ 命令形态） |
| D5 | 生成方向：文档片段由 protocol 生成 | `--check` 反向核对上位文档，但**不把片段注入机制稿正文** | 改写上位文档属 T7 人审；P0 只保证「不漂移」（不变量⑤），正文仍人手维护 |
| D6 | `schema_version` 现在同时受类型校验 | 删手写 `POSITIVE_INT_KEYS` 后按类型统一派生，`schema_version` 本属正整数 | 非法 `schema_version` 会多报一条 field 级问题（原只有 structure 级）；行为更严，不影响合法配置 |

## 4. 未完成项与原因

1. **v42 §4 的旧机制删除**（`task-rework`、`five_state`、轮次额度…）——按计划随其覆盖者所在阶段一起删；P0 先建覆盖事实（protocol + 不变量），不先删。
2. **跨文档漂移两处（P1/P5 前置，未在本轮裁）**：
   - **阻断 002（身份口径）**：机制稿 §1.4 同时写「身份来源由安装清单 `platforms` 声明、不另接受环境变量或命令行覆写身份」与「自动模式下由执行边界派生」；v42 K1 的四档来源（DSH env / host hook / 祖先 cmdline / terminal）落在这两种口径之间。**原因码** `WF_SEMANTIC_DECISION`；**决定性事实**：机制稿 §1.4 请求协议段 vs 设计稿 §1.3 自动模式段 vs v42 K1；**出口**：(a) 把 env/cmdline 定为适配层的**派生输入**（identity 仍由 `provider=host` 承载，host_id 必属 platforms），(b) 把自动模式写进机制稿并给 env 派生留位置，(c) 禁 env 派生、只用执行边界。**禁止的错误修复**：猜环境变量当身份、退回项目全局指针。P1 开工前需裁定。
   - **K9「链头锚定提交 trailer」**：机制稿未定义该锚（`wf-task:` trailer 只承载任务归属）。属 P5 审计链落点，需在机制稿补位或由 v42 收回该措辞。
3. **平台事实**：`cli.py` 的 `TRELLIS_HOST_CONFIGS` 仍在语义层（S12 ② 要求迁适配层），`PLATFORMS` 缺 `zcode`/`pi`（8 项 vs 6 项）——均已在 v42 §12 I1/I3 登记为「已定稿、未改代码」，属 P6。
4. **build 脚本的破坏性顺序（观察，不作为本任务修复项）**：`build-wf-release.py --version` 在「源树有未登记文件」检查之前就删除发行树；本轮因此删过一次 `docs/workflows/wf-release/`，随后重建恢复（基线 `--verify` 已证明现有发行树与源树字节一致，故重建无损）。该顺序问题建议单独登记。

## 5. 代码规范复核（trellis-check Step 4）

- 新脚本按 `.trellis/spec/scripts/python-conventions.md` 改为 `pathlib`、`raise SystemExit(main())`、`argparse`；改后证据复核仍报 `byte-identical`，说明改动是行为等价的。
- 删掉三处未被消费的表面（`States.raw`、`States.display_of`、`DocError`），并把脱敏规则改为经 `protocol.redaction()` 消费，使其不只是摆设。
- 新增测试 7 条，逐条在 docstring 写明「防的失败实际发生过或可具体推演」（对应 G3/B5/B7/F3/G2/v36，及 §7.1 的 cap 回流）。

## 6. 未做的（纪律边界）

- 未提交、未推送、未建 PR。
- 未改 charter / 设计稿 / 机制稿 / 实现稿任何条款。
- 未动 `.trellis/` 之外的 Trellis 资产，未动上游 Trellis 仓库；保留了工作区里既有的未提交改动。
