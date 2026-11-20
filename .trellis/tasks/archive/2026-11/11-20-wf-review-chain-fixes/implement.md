# 实施计划：wf 审查链路与发行身份修正

## 前置

- 基线验证已完成：T0 1323 项通过；`validate-wf-design.py` 绿；`build-wf-release.py --verify` 字节复现。
- 本任务只在用户批准计划后开始；最终提交/收尾另经用户同意。
- 不修改 `traffic_monitor` 项目；不创建 tag、不推送。

## 步骤

### 1. 读取并固定规范

- 读 `.trellis/spec/docs/wf-delivery-discipline.md` §9/§10/§11、`.trellis/spec/docs/wf-design-revision-gate.md`。
- 读设计稿 §1.1/§6.5/§8.2、机制稿 §9.1/§9.2、`docs/workflows/wf/README.md`、`scripts/build-wf-release.py`。
- 记录本任务 `implement.jsonl`/`check.jsonl` 为空（inline 模式），启动时用 `task.py start --allow-empty-context`。

### 2. F1：Check 有效性复用

- 改 `wflib/review.py` 的 `launch`：锁内 `check_validity`，非 valid 抛出。
- 改 `context`：核对 launch anchor 与当前锚点，漂移即 `WF_CHECK_STALE`。
- 新增/改测试：`scripts/tests/wf_review/test_review_gates.py` 或新文件，覆盖 launch/context 两侧。
- 回退注入验证：临时恢复「只核 result」/「context 不核 anchor」，新断言变红。

### 3. F2：覆盖消费 reliance/sources

- 改 `merged_coverage(main_review, axis_reports)`；更新 `validate_main_review`、`status_of_round`、`decide`。
- 改 `review-status` 投影 facts（`main_review_ready`、`adopted`、`sources`）。
- 更新 `scripts/tests/wf_review/test_review_coverage.py`：
  - 全 uncovered + 两报告 none → `WF_REVIEW_INVALID`；
  - primary 全贡献；
  - partial 仅 source 列出的轴贡献；
  - 无 main 时 status 展示原始覆盖。
- 回退注入：临时忽略 reliance，新增断言变红。

### 4. F3：verdict 由未关闭 blocking 触发

- 新增 `round_open_blocking` 派生函数（复用 `open_findings`）。
- `decide` 在 dispositions 校验后计算本轮开放项；仅非空时 fail；facts 保留 `report_failures` 与 `open_blocking`。
- 更新 `scripts/tests/wf_review/test_review_coverage.py`：误报 accepted 同轮 pass；未关闭仍 fail；已修复需新锚点/新轮。
- 更新 `docs/workflows/wf/skills/wf-repair-loop/SKILL.md` 的 fail 轮重判表述。
- 回退注入：临时改回「报告原始 blocking 即 fail」，新增断言变红。

### 5. F4/F5：错误码与回显

- 缺 `--main-review`、主会话 fail 无 finding → `WF_REVIEW_INVALID`。
- `decide` 的 `next` 按 verdict 分流。
- 更新测试期望与 `wf-review-action` 的出口文案（保持「误报关闭后可重判」）。
- 回退注入可选（文案断言 + code 断言）。

### 6. F6：外发声明与物化绑定

- 新增 `scope_binding_problems`；`context` 传 `submitted_scope.diff.paths` 给 `write_materials`；旧 launch 回退并标 `legacy_scope`。
- `report_input_problems` 增可选 `launch`，检查 `read-scope` 命中 `launch.exclusions`；导入/判定传入 launch，lint 不传。
- 新增测试：
  - 缩小声明只物化子集；
  - 放大声明被拒；
  - 报告读声明命中 launch 排除面被拒；
  - 旧 launch 缺声明回退且标 `legacy_scope`。
- 回退注入：临时改回固定 `delivery_set`，缩小断言变红。

### 7. F7：版本身份

- `README.md` 目标版本改 `0.1.3`，删除失实 tag 句。
- `build-wf-release.py` 增 README 版本一致检查与「已存在 tag 拒绝同版重建」守卫。
- 运行 `python3 scripts/build-wf-release.py --version 0.1.3` 重建发行树；再跑 `--verify --verify-token-parity`。
- 新增 `scripts/tests/wf_runtime/test_release_version_guard.py`（或并入现有 release 测试）：README 不一致拒绝、tag 存在拒绝、占位符仍允许。
- 回退注入：临时移除守卫，测试变红。

### 8. F9：§1.1 判据补全

- 改设计稿 §1.1 判据句、§8.2 覆盖缺口行。
- 更新索引 #109 语义消费点、机制稿 §0.1 摘要。
- 运行 `python3 scripts/validate-wf-design.py`、`python3 scripts/check-doc-refs.py`。
- 回退注入不适用（文档）；以 checker 与人工反查为准。

### 9. 验证

按顺序：

```bash
PYTHONPYCACHEPREFIX=/tmp/wf-unit-pycache /softwares/python/bin/python3 -m unittest discover -s scripts/tests -t .
WF_TAGS=review bash scripts/tests/wf_runtime/full/run_all.sh   # 或相关 suite 子集
python3 scripts/build-wf-release.py --verify --verify-token-parity
python3 scripts/validate-wf-design.py
python3 scripts/check-doc-refs.py
./scripts/validate-skills.sh
```

必要时跑 `bash scripts/tests/wf_runtime/full/run_all.sh --representative --repro green`。收尾核对 `git status`，确认没有意外 pyc/临时文件。

### 10. 收尾（需用户同意）

- 复核 `git diff`、发行树字节、测试结果。
- 汇报未做新版真实 dogfood 的边界与 `upgrade` 未交付事实。
- 用户同意后再提交；提交前只暂存本任务路径，不建 tag、不推送。

## 风险文件与回滚点

| 文件 | 风险 | 回滚 |
|---|---|---|
| `wflib/review.py` | 审查链路核心；改错会导致所有复杂任务无法判定 | 按函数块回滚；保留旧测试绿 |
| `scripts/tests/wf_review/*` | 断言变化可能掩盖旧行为 | 先加新断言，再改实现；回退注入验证 |
| `scripts/build-wf-release.py` | 守卫误伤正常构建 | 保留 `--verify` 路径不受影响；守卫只在 `--version` |
| `docs/workflows/wf-release/**` | 生成物；重建后字节变化大 | 回退到已提交的 0.1.0 树 |
| `docs/workflows/wf-framework-design.md` + index + mechanism | 设计修订闸门 | 保留修改前摘要；checker 绿后再继续 |

## 完成判据

- PRD 验收项逐条有测试或 checker 证据。
- 新增断言做过回退注入（至少 F1/F2/F3/F6）。
- 不在未获同意时提交、建 tag、推送。
## 执行记录（2026-11-20）

- 代码修改：`wflib/review.py`（F1/F2/F3/F4/F5/F6）、`scripts/build-wf-release.py`（F7 守卫）、
  `wf-repair-loop`/`wf-review-action`/`wf-review` 文案、设计稿 §1.1/§6.5/§8.2、机制稿 §9.2/§0.1、
  实现稿 §2.3.10、索引 #109。
- 新增/更新断言：`test_launch_mechanized`（launch 复用 `check_validity`）、`test_report_boundary`
  （context 漂移拒绝、声明路径物化、读取面命中 launch 排除面）、`test_review_coverage`
  （reliance none/partial、误报 accepted 同轮 pass、错误码）、`test_build_wf_release`
  （README/tag 守卫）、`test_source_coverage`（候选审计版本不一致时显式 skip）。
- 回退注入验证：F1（launch/context 守卫）、F2（忽略 reliance）、F3（报告原始 blocking 即 fail）、
  F6（忽略声明路径）各自恢复旧实现时新断言变红；恢复后字节一致。
- 验证结果：
  - T0：`python3 -m unittest discover -s scripts/tests -t .` → 1334 tests，OK（43 skip，其中候选审计
    因冻结版本 0.1.0 与当前 0.1.3 不一致而显式 skip）。
  - T1：`WF_TAGS=review .../run_all.sh` → 6 suites，fail=0。
  - 代表集：`.../run_all.sh --representative --repro green` → 6 suites + 2 flows + 54 repro，fail=0。
  - 发行：`build-wf-release.py --version 0.1.3` 重建；`--verify --verify-token-parity` 字节复现与令牌一致。
  - 设计：`validate-wf-design.py` 绿；`check-doc-refs.py` 0 problem；`validate-skills.sh` 通过。

## 未完成 / 边界

- `upgrade --apply` 仍是第三轮能力，未实现；traffic_monitor 未机械升级。
- `wf-v0.1.3` tag 未创建（按约定由人在提交后创建）；候选审计 `candidate-audit.json` 仍冻结在
  0.1.0，0.1.3 需要一次新的 candidate run 才能更新其身份与树摘要。
- 新版真实项目 dogfood 未做；本任务只证明机制行为与发行字节，不宣称使用体验验收完成。
- 不提交、不推送、不建 tag。

## 第二轮审查修正（2026-11-20）

- S1：`anchor_identity_problems` 统一核 `check_id` + `check_anchor`；`review.launch`/`context`/`import`/
  `report_input_problems`/`status_of_round` 消费。新增 context/import/decide 回归。
- S2：`review.launch` 在发起时核 `submitted_scope` 与交付集合/PRD/当前 Check；新形状缺
  `diff.paths` 直接拒绝。`report_input_problems` 核 read-scope 与 launch exclusions
  （含目录包含排除子目录）及 readable_scope。新增 launch/报告边界测试。
- S3：`validate_main_review` 核 `sources` 槽位必须被采信且报告确实覆盖该轴；`merged_coverage`
  按 `sources` 归属，不再一律记 main。新增测试。
- S4：`decide` 允许 fail/未判定后追加修正复核（旧记录 `supersedes`）；pass/unavailable 后拒绝；
  仍有 fail 轴不得产 pass。新增测试。
- S5：主会话独立 finding 的出口改为「修复重查，或登记 judgment 交人」；不新增 finding 模型。
- S6：launch `scope`、context `narrowed`/`delivery_path_count`、`review-status` 与
  `status --short` 的 `launch_scope`；review/action skill 指引。新增断言。
- S7/S8：pass next 补 `status --short`；`match_path` docstring 修正。
- 同步：设计稿 §6.5、机制稿 §9.2、实现稿 §2.3.10、交付纪律 §14 的 Check id/readable/
  revision/收窄可见性口径；`status --short` 增 `launch_scope`；`task-rework` 权威注释改为
  「机制稿保留、v42 为审查稿」，机制稿 §6.2 同批登记；`wf-finish`/`wf-review-action` 指引。
- 验证：T0 1346 tests OK（43 skip）；review 套件 6/6；representative 6 suites + 2 flows + 54 repro
  全过；`validate-wf-design`/`check-doc-refs`/`validate-skills` 绿；release 0.1.3 字节复现与令牌一致。
  期间观察到 fixture lease 偶发失败，干净重跑通过；未归因到本轮审查代码，作为测试基础设施边界记录。

## 第三轮审查修正（2026-11-20）

- T1：复核确认 `judgments.validate` 不要求 `evidence_refs`，原“指向必拒路径”不成立；把 skill 的最小判断形状
  改为 `{"kind":"规模","outcome":"applied","basis":"..."}`，并注明 `evidence_refs` 可省。
- T2/T3：`review.launch` 对 `diff.paths` 的缺/`null`/非数组统一拒绝，拒绝出口补「去掉 --launch-request
  让入口重建」；`scope_binding_problems` 在发起阶段即核路径集合/PRD/Check/排除面。
- T4：`scope_binding_problems` 增 diff.paths 与 launch exclusions 交叠检查；`null`/非数组拒绝；
  重复路径去重后计 `selected`；launch/context 各加回归。
- T5：dispositions 校验与未关闭 blocking 前置到覆盖缺口之前；有 blocking 直接 fail，缺口接受只在
  pass 路径要求；新增“blocking + 未覆盖轴”回归。
- T6：保留主会话独立 finding 的边界——修复重查或登记 judgment 交人；不新增 finding 模型。
- T7：`validate_main_review` 增「pass 不得引用该轴判 fail 的报告」；`decide` 增「verified finding 的
  accepted 关闭须带 evidence_refs」；新增回归。
- T8：`write_materials` 的 `check.json` 只写 `id/result/anchor`，移除 `internal_review`；新增材料测试。
- 验证：T0 1356 tests OK（43 skip）；review 套件 6/6；representative 6 suites + 2 flows + 54 repro
  全过；release 0.1.3 字节复现与令牌一致；设计/文档/技能校验绿。

## 第四轮审查修正（2026-11-20）

- D1：`context` 的旧布尔 `diff` 回退先按 launch `exclusions` 过滤；launch 的 `scope` 对旧形状记录
  过滤后的 selected/total/narrowed/legacy；`status.json` 的 `buckets` 只列本轮物化路径；
  `read-scope-readable` 从 `match_path` 改为 `subsumes` 可证包含，防止 `pkg/**` 借 `pkg/*` 字面匹配放宽。
- D2：`review_scope_facts` 把 selected/unselected/total/narrowed/legacy 写入 `review-decide` 的
  `result.scope` 与 `facts.scope`；action/finish skill 要求说明未选路径的处理，判断仍归主会话。
- D3：`all_uncovered` 仅在无未关闭 blocking 时拒绝；已有经复核 blocking 时允许记录 fail。
  主会话独立 finding 仍保留「修复重查或 judgment 交人」，不新增自证 finding 模型。
- D4：修正 `pass` 引用失败报告的出口文案（`reliance` 取 primary/partial/none，`disputed` 只属
  `finding_review.check`）；设计稿 §8.2 覆盖缺口改为“能同轮补证就同轮重判”。
- 验证：T0 1362 tests OK（43 skip）；review 套件 6/6；representative 6 suites + 2 flows + 54 repro
  全过；release 0.1.3 字节复现与令牌一致；设计/文档/技能校验绿。

## 第五轮审查修正（2026-11-20）

- E1：新增 `mandatory_exclusions`，launch 的请求排除面只能追加必排面；未声明 `readable_scope` 用入口默认，
  显式空 `{}` 表示不授权额外读取，报告有 read-scope 即拒绝。
- E2：`merged_coverage(..., narrowed=True)` 时 `primary` 也按主会话该轴 `sources` 显式列出的槽位贡献；
  未列出的轴保持 uncovered，由主会话决定补读/补证。
- E7：有未关闭 blocking 时，提交的缺口接受文件记入 `gap_acceptance_ignored`，不再静默吞掉。
- E8：设计稿 §4.2 的 `.wf/writer.json` 改为运行态不整体提交，维护回执随维护组路径处理。
- 未采纳 E6：`readable_scope` 是 launch 声明的授权读取面，读过范围外应停止回报；保留 `read-scope-readable`
  硬拒绝，避免把“诚实申报”变成删除读取声明的激励。
- E3 边界：主会话独立 finding 仍走「修复重查或 judgment 交人」，不新增自证 finding 模型。
- 验证：T0 1366 tests OK（43 skip）；review 套件 6/6；representative 6 suites + 2 flows + 54 repro
  全过；release 0.1.3 字节复现与令牌一致；设计/文档/技能校验绿。

## 第六轮审查修正（2026-11-20）

- F1：`main_review_draft` 的 axes `sources` 不再预填报告槽位；`review_scope_facts` 对旧布尔/缺省 launch
  按当前交付集合减必排面重算 selected/unselected/narrowed；收窄时 `uncovered` + 报告 `primary` 在
  `validate_main_review` 作为矛盾拒绝。
- F2：`report_input_problems` 的 readable 检查把 `.wf/`、`.git/` 控制面拒绝，spec/PRD 显式放行除外。
- F3：`read-scope` 支持 `materials`（只读材料包）；显式空 `readable_scope` 下空数组表示未补读。
- F5：action skill 收窄指引改为 basis 说明 + 仅残余风险才登记 judgment，不再要求每次收窄记规模判断。
- F6：撤销“收窄时 primary 需逐轴 sources”的机械枚举，改为拒绝 `uncovered`+`primary` 矛盾，保留 reliance 语义。
- 验证：T0 1369 tests OK（43 skip）；review 套件 6/6；representative 6 suites + 2 flows + 54 repro
  全过；release 0.1.3 字节复现与令牌一致；设计/文档/技能校验绿。

## 第七轮审查修正（2026-11-20）

- G1：`coverage_conflicts` 从 `validate_main_review` 的输入拒绝移到判定后；有未关闭 blocking 时先 fail 并记
  `coverage_conflicts`，只有本来要产 pass 时才拒绝。
- G2：`read-scope-launch`/`read-scope-excluded` 对 `readable_scope.prd` 精确路径跳过 `.wf/tasks/**` 冲突。
- G3：launch 轮次 `decision`/`export_decision` 改写实际核验的 `original_digest`，不再读请求原字段。
- G4：主会话 `main_findings[]` 进入 `open_findings`/`open_blocking`/C2/处置空间；`fail` 可用
  `slot:"main"` 引用，关闭走 dispositions `slot:"main"`；修正复核不得静默丢弃上一份 main finding。
- G6：旧 launch 范围重算失败返回 `scope_recompute_failed`，不再静默当成材料完整。
- 验证：T0 1374 tests OK（43 skip）；review 套件 6/6；representative 6 suites + 2 flows + 54 repro
  全过；release 0.1.3 字节复现与令牌一致；设计/文档/技能校验绿。

## 第八轮审查修正（2026-11-20）

- H1：修正复核对上一份 blocking main finding 的 severity 降级要求 accepted disposition；只改
  severity 即 `WF_REVIEW_INVALID`。
- H2：launch 强制 `readable_scope.prd` 等于入口算出的本任务 PRD；其他任务 PRD 不再能借例外放行。
- H3：轮次 `decision`/`export_decision` 优先写 `authorize.require` 的 `original_digest`；请求字段不覆盖。
- H4：`main_findings` 的 `finding_review` 可省，入口自动按 `verified` 记；要 `disputed/unable` 才写。
- H5：main blocking 走 `assertion_index`/`assertion_ref_problem`，与 reviewer finding 同核 K4c。
- H6 边界：`recheck_by=human:` 仍是标签，不升级为 attestation；§1.5 不防伪，避免新增人工凭据层。
- 验证：T0 1375 tests OK（43 skip）；review 套件 6/6；representative 6 suites + 2 flows + 54 repro
  全过；release 0.1.3 字节复现与令牌一致；设计/文档/技能校验绿。

## 第九轮审查修正（2026-11-20）

- I1：`verified_closure_problems` 合并全部 `main_reviews` 的 finding_review check；跨轮关闭按提出轮
  check 核 `evidence_refs`，不再因当前轮没有该 check 放过。
- I2：`main_findings` 的 `check_fix_kind=broken-reference` 加入 `lifted`，与 reviewer finding 同要求
  `recheck_by=human:`。
- I3：`all_findings` 纳入每轮最新 `main_findings`；复核草稿与 `f:` 判断引用可见。
- I4 边界：单 reviewer 时正式 verdict 仍拒绝；已核实缺陷走修复重查/`--unavailable`/暂停，不在无效轮
  写正式 fail。
- I5 边界：`recheck_by=human:` 仍是标签，不升级 attestation；§1.5 不防伪。
- 验证：T0 1379 tests OK（43 skip）；review 套件 6/6；representative 6 suites + 2 flows + 54 repro
  全过；release 0.1.3 字节复现与令牌一致；设计/文档/技能校验绿。

## 内部对照审查修正（2026-11-20）

- 文档一致性：设计/机制/实现稿统一“all_uncovered 仅在无经复核 blocking 时输入不成立；有 blocking 可 fail”。
- 旧 launch：`scope_binding_problems` 统一用 `mandatory_exclusions`，旧 dict/布尔回退不再绕过必排面。
- 主会话 finding：当前 main findings 补入 `proposers`，同批 plan 关闭不再误报 unknown；新增同批关闭测试。
- 草稿：从本轮最新 main review 预填 `main_findings`；`all_findings` 已含 main finding，草稿/`f:` 引用可见。
- 请求形状：launch 校验 `diff/requirement/test_results` 仅对象/字符串/旧布尔；`exclusions`/`readable_scope` 字段形状；非法即 `WF_REVIEW_INVALID`。
- context：PRD/范围校验先于 materials 目录创建；旧 launch 的 `submitted_scope`/`readable_scope` 非对象时安全降级。
- 控制面：`.wf`/`.git` 目录本身也拒绝读取。
- 文档：实现稿 §2.3.10 同步 main_findings、控制面、范围/授权摘要口径。
- 验证：T0 1392 tests OK（43 skip）；review 套件 6/6；representative 6 suites + 2 flows + 54 repro
  全过；release 0.1.3 字节复现与令牌一致；设计/文档/技能校验绿。

## 第十轮审查修正（2026-11-20）

- J1：`evidence_ref_problems` 核 `v/a/f/p/j` 引用存在、`v:` 验证 passed；`verified_closure_problems`
  接收 `evidence_check`，全量与 register-only 都消费。证据是否足够仍由 AI 判断。
- J2：`broken_reference_problems` 消费现有+本次 dispositions；main broken-reference 只对所引规则
  确实改过（`changed_rules`）才要求人复核。
- J3：`main_review_draft` 不再把 main finding 放进 `finding_review`，由入口按 verified 自动补；
  `main_findings` 仍预填。
- J4：`--register-only --main-review` 可先登记 main_findings，不产生 verdict；仍要求 launch/round；
  正式判否仍需完整审查。`review-decide` help 与 action skill 同步。
- J5：机制稿/action skill/实现稿/交付纪律登记 severity 降级与 broken-reference 规则。
- J6：`recheck_by=human:` 仍为标签，不升级 attestation；§1.5 不防伪。
- 验证：T0 1392 tests OK（43 skip）；review 套件 6/6；representative 6 suites + 2 flows + 54 repro
  全过；release 0.1.3 字节复现与令牌一致；设计/文档/技能校验绿。

## 第十一轮审查修正（2026-11-20）

- K1：`evidence_ref_problems` 的验证项定义取计划，passed 只取 Check 实际 commands；计划状态不再作为证据。
- K2：`evidence_refs` 只接受 `v/a/f/p/j` 或当前锚点差异中的 `d:`；`s/g/h` 拒绝，关闭前先确认引用指向事实。
- K3：全量与 register-only 的 `verified_closure_problems` 只核本次 dispositions；历史关闭不按新计划重验。
- K4：register-only main review 允许 superset 追加（保留原 id、不降 severity），旧记录标 `supersedes`；
  丢 finding/只降 severity 拒绝。
- K5：机制稿/实现稿/交付纪律/repair skill 同步证据与 register 口径。
- K6：`recheck_by=human:` 仍为标签，不升级 attestation。
- 验证：T0 1392 tests OK（43 skip）；review 套件 6/6；representative 6 suites + 2 flows + 54 repro
  全过；release 0.1.3 字节复现与令牌一致；设计/文档/技能校验绿。

## 第十二轮审查修正（2026-11-20）

- L1：register-only 改写现有 main review 前检查 `latest_decision`；已 pass/unavailable 拒绝，提示开新一轮。
- L2：全量判定对已落盘关闭只核 evidence_refs 非空（不按新 Check 重解），当前复核把 finding 标
  verified 时缺证据即拒绝；K3 的历史证据不被新 Check 重验。
- L3：register-only 支持最小 `task/round/main_findings`，入口补 discovery 复核（axes 全 uncovered），
  status `main_review_ready=false`；完整判定仍需完整主会话复核。
- L4：`recheck_by=human:` 仍为标签，不升级 attestation。
- 验证：T0 1392 tests OK（43 skip）；review 套件 6/6；representative 6 suites + 2 flows + 54 repro
  全过；release 0.1.3 字节复现与令牌一致；设计/文档/技能校验绿。

## 第十三轮审查修正（2026-11-20）

- M1：已落盘关闭在本次复核标 verified 时也走 `evidence_ref_problems`；历史证据用
  `include_history=True` 回退 `check_history`，不存在的 `v:` 仍拒绝。
- M2：`verified_closure_problems` 按同一 finding 的最新处置计算；旧空证据被后续有效处置覆盖后
  不再阻断。
- M3：`validate_main_review` 把唯一推断出的 `slot` 写回 `finding_review`，关闭证据索引按精确
  slot 核。
- 验证：T0 1395 tests OK（43 skip）；review 套件 6/6；representative 6 suites + 2 flows + 54 repro
  全过；release 0.1.3 字节复现与令牌一致；设计/文档/技能校验绿。

## 第十四轮审查修正（2026-11-20）

- N1：当前 dispositions 在判定前写 `check_id`；`evidence_ref_problems` 有绑定只读该次 Check 的
  commands；历史关闭按 `check_id` 找到 check_history，旧记录无绑定才回退历史。当前关闭不再借
  同名旧 passed。
- N2：`verified_closure_problems` 的 latest 映射纳入全部 decision（含 amended）；最新不是 accepted
  就不做关闭证据校验，撤回关闭可如实登记 fail。
- N3：`wf-continue` 增加 vendor_dirty 路由指引；`wf-review-action` 增加判据外 blocking 的
  judgment/扩判据出口。
- 验证：T0 1397 tests OK（43 skip）；review 套件 6/6；representative 6 suites + 2 flows + 54 repro
  全过；release 0.1.3 字节复现与令牌一致；设计/文档/技能校验绿。

## 第十五轮审查修正（2026-11-20）

- O1：`open_findings` 有主会话复核时只把 verified/disputed 的 accepted 算关闭；unable/未复核
  标 unverified，blocking 保留。
- O2：`review.decide` 正式判定前调用 `gates.check_validity`；失效返回 `WF_CHECK_STALE`，
  register-only/unavailable 不走该阻断。
- O3：`_mechanical_revision` 对验证项定义做 `wf-plan-verifications-v1` 摘要比对；命令/cwd/
  required/consume_at 变化即 `WF_SEMANTIC_DECISION`。
- O4：status 单列 `writing`，`arrived/material_ready` 只认 imported/done；`report_input_problems`
  归一化非数组/非对象形状并给逐项问题、不产 verdict；wf-review skill 改为先 lint 后 done。
- O5：wf-continue 明确 `task-attribute --commit` 只处理已提交历史；设计稿表改为发起声明实施
  CLI、审查身份判定时事后核验。
- O6：默认 `readable_scope.spec` 覆盖 `.wf/spec/**` 与策展条目。
- O7：设计稿把 read-scope 边界改为“不拦截读取、声明矛盾按输入不成立；诚实越界停止回报/修正/换轮”，
  不新增放行层；P1/P2/P3/复杂度仍为声明边界。
- 验证：T0 1401 tests OK（43 skip）；review 套件 6/6；representative 6 suites + 2 flows + 54 repro
  全过；release 0.1.3 字节复现与令牌一致；设计/文档/技能校验绿。

## 第十六轮审查修正（2026-11-20）

- P1：`review.launch`/`review.decide` 在 `check_validity` 前核 `_is_approved_plan`；当前 PRD
  不再对应批准版本即 `WF_APPROVAL_MISSING`。
- P2：`report_input_problems` 增 `findings-shape`，finding 必须是对象且有 id。
- P3：当前 dispositions 强制 `check_id = 当前 Check`，显式历史值被覆盖。
- P4：`read-scope` 逐条拒绝绝对路径、盘符、`~` 与含 `..` 的路径（materials 除外）。
- P5：`review-status` 在 material/eligibility 后先提示 `--main-review-draft` 与同轮补证，再提示
  gap-acceptance。
- P6：设计稿 §1.5 改为先由 AI 在授权内收敛，仍无法消解再交人；wf-start 第 1 步在用户明确
  禁写 `.wf/` 时不得先 enable/试写。
- 保留：P1 身份轮换、P2 复核面复杂度、设计/机制重复、机械修订粗粒度、read-scope 激励结构。
- 验证：T0 1410 tests OK（43 skip）；review 套件 6/6；representative 6 suites + 2 flows + 54 repro
  全过；release 0.1.3 字节复现与令牌一致；设计/文档/技能校验绿。

## 第十七轮审查修正（2026-11-20）

- R1：`review.context` 在物化前核批准版本与 `check_validity`；发起后实质改 PRD/Check 失效即阻断。
- R2：`DEFAULT_EXCLUSIONS` 增 `**/.env`、`**/id_rsa`、`**/.npmrc` 等子目录同名敏感文件。
- R3：`report_input_problems` 的 `findings-shape` 检查单份报告内 finding id 唯一。
- R4：`gap_acceptance` 支持 `task_id`，校验并把 task 纳入摘要；`review-decide` 传当前 task。
- R5：status 增 `ready_to_import`，先提示 review-import；fail 轮提示同轮 plan+main-review 重判。
- R6：`wf-review-action` 改为原触碰面内能修就继续修并说明缺判据，只有改验收/承诺/授权才请人扩判据。
- S1：默认 `readable_scope.spec` 增 `.wf/baseline.md`。
- 保留：身份轮换、复核面复杂度、设计/机制重复、机械修订粗粒度、read-scope 激励结构。
- 验证：T0 1410 tests OK（43 skip）；review 套件 6/6；representative 6 suites + 2 flows + 54 repro
  全过；release 0.1.3 字节复现与令牌一致；设计/文档/技能校验绿。

## 第十八轮审查修正（2026-11-20）

- T1：`review.decide` 检查至少一份 reviewer 报告有 pass/fail 轴；主会话自查全 pass 不能替代
  两份全 uncovered 的异种审查。
- T2：`review.context` 对 `plan.approval` 键（包括 task-replan 置 null）做批准与 Check 复查。
- T3：`normalize_scope_path` 统一读/排除声明比较；`./.wf/tasks/...` 与 `.wf/tasks/...` 同判。
- T4：`default_launch_request` 的 diff.paths 先扣必排面，默认请求可通过同一范围校验。
- T5：status 先提示 ready_to_import；wf-repair-loop 明确失效 Check 必须先重查，不存在先重判。
- 保留：身份轮换、复核面复杂度、设计/机制重复、机械修订粗粒度、read-scope 激励结构。
- 验证：T0 1413 tests OK（43 skip）；review 套件 6/6；representative 6 suites + 2 flows + 54 repro
  全过；release 0.1.3 字节复现与令牌一致；设计/文档/技能校验绿。

## 第十九轮审查修正（2026-11-20）

- V1：`review.decide` 逐份检查 reviewer 报告至少有一个 pass/fail 轴；一份全 uncovered 不能由
  另一份或主会话代偿。
- V2：`standard_drift_gate` 只在正式判定执行；unavailable/register-only 仍可如实登记。
- V3：`review.context` 命中同 agent/轮次的 `status=in-progress` 时返回同一 materials/report_path，
  标 `resumed: true`；只有 done 才拒绝并指向 review-import。
- V4：`report_input_problems` 校验 round 正整数；lint 对非数组 findings 使用空列表，不遍历原值。
- V5：disposition 歧义出口改为 AI 在 plan 补 round+slot；wf-review 明写 finding id 单份唯一。
- 保留：身份轮换、重试率埋点、机械修订粗粒度、设计/机制重复、read-scope 激励结构。
- 验证：T0 1417 tests OK（43 skip）；review 套件 6/6；representative 6 suites + 2 flows + 54 repro
  全过；release 0.1.3 字节复现与令牌一致；设计/文档/技能校验绿。

## 第十九轮补充（2026-11-20）

- register-only 带 --plan 关闭时同核 `_is_approved_plan` 与 `check_validity`；失效 Check/批准拒绝，
  不能借旧 Check 的 passed。
- 正式判定失效 Check 的 exits 删除“用 --unavailable 留痕”；Check 失效不属审查不可用声明。
- 更新 identity repro：in-progress 草稿可续写，status=done 后仍只允许导入；注入点改为 done 守卫。
- 验证：T0 1417 tests OK（43 skip）；review 套件 6/6；representative 62 全过；release 0.1.3
  字节复现/令牌一致；设计/文档/技能校验绿。

## 第二十轮审查修正（2026-11-20）

- X1：`scope.is_vendor_asset(path) = is_vendor ∧ ¬is_project_data`；`delivery_set` 的 e/f 桶与策展
  路径、`vendor_assets` 统一用它。`.wf/spec/**` 归本任务时进交付集合/材料/提交。
- X2：`report_input_problems` 的 `findings-shape` 核 severity ∈ blocking|suggestion；非法值不产 verdict。
- X3：`assertion_ref_problem` 对 spec-rule 的 `#clause` 引用要求精确存在（broken-reference 例外）。
- X4：`report_input_problems(require_done=)`；lint 以 `require_done=False` 运行，in-progress 只出 notes；
  import/decide 仍要求 done；wf-review skill 同步。
- X5：`import_report` 先跑共享形状检查再比 task-id/round/署名；round 解析容错，不再抛裸 ValueError。
- 验证：T0 1420 tests OK（43 skip）；review 套件 6/6；representative 62 全过；release 0.1.3
  字节复现/令牌一致；设计/文档/技能校验绿。

## 第二十一轮审查修正（2026-11-20）

- Z1：删除 wf-review 协议块后多余的代码围栏（后半篇曾被包进代码块）。
- Z2：tasks/check/scope 五处出口改为「未提交路径按批准触碰面归属；已提交才 task-attribute --commit」。
- Z3：dispositions 记 `submitted_round`；`unable` 只在同轮阻断关闭，后续轮 accepted 需可解析证据。
- Z4：`all_findings` 用 `open_findings` 的关闭集合，消除 closed 口径矛盾。
- Z5：只有 blocking finding 必须 `finding_review`；建议未核实记 `deferred_suggestions`。
- Z6：`merge_main_findings` 按 id 并集合并，修正复核只需交新增/改动项。
- Z7：`evidence_ref_problems` 绑定 check_id 不存在时返回不可核实，不回退当前 Check。
- Z8：`review.context` 的 stale facts 列 `stale_round_drafts` 并给出口。
- Z9：规则/基线修复用 `p:` 表达（spec 已进交付面），出口与 repair skill 同步。
- Z10：wf-continue 写明「补测试文件属 AI；新增/改验证项属规划变化」。
- 验证：T0 1425 tests OK（43 skip）；review 套件 6/6；representative 62；release 0.1.3 复现一致。

## 第二十二轮审查修正（2026-11-20）

- AA1：`merge_main_findings` 除并集 `main_findings` 外，同时沿用被并入项的 `finding_review`；
  追加新 finding 不再把旧 `unable` 改成 `verified`。
- AA2：`main_review_draft` 只为 blocking finding 生成 `finding_review` 占位；建议留空即延后。
- AA3：复核确认跨轮 unable→accepted 已要求可解析证据（Z3 实现），补 `CrossRoundClosureTest`
  两条用例锁定：无证据拒绝、有证据通过。
- 验证：T0 1429 tests OK（43 skip）；review 套件 6/6；representative 62 全过；release 0.1.3 一致。

## 第二十三轮审查修正（2026-11-20）

- AB1：`merge_main_findings` 改为两件事独立判断——`main_findings` 按 id 补回、`finding_review`
  按 (id, slot) 继承；不再因为“没有待补回 finding”就整体提前返回。
- AB2：discovery 模式已知 finding 集合改取任务全量（`all_findings`），继承回来的 reviewer 核实
  条目不再被判未知；`validate_main_review(discovery=True)` 只登记不产结论，不再要求逐条核实
  reviewer blocking finding。
- 验证：T0 1431 tests OK（43 skip）；review 套件 6/6；representative 62 全过；release 0.1.3 一致。
