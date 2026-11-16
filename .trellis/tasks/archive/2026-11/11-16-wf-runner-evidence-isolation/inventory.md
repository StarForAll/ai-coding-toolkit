# 覆盖清点基线与计数依据

> 基线：`b74d60101bf874f7940af1e20dd1aa73eb8a6ee3`；本轮 HEAD 与基线相同。
> 仅静态读取源码和 JSON，不导入/执行测试脚本，不代表行为测试已经通过。
> 本文件定义 PRD R9 / AC17–18 使用的清点集合；语义来源与候选实跑仍由实施阶段逐项核实。

## 1. repro 的不同集合

| 集合 | 基线数量 | 唯一来源及含义 |
|---|---|---|
| D：运行器可发现全集 | 85 | `scripts/tests/wf_runtime/full/repro/repro_select.py:60` 的 `all_cases()`：目录中 `[a-z0-9]*.py`，前 4000 个字符匹配独立行 `import _harness as H` |
| G：分组成员并集 | 54 | `scripts/tests/wf_runtime/full/repro/groups.json` 的五个 `groups` 展开并去重；不是全量发现入口 |
| U：未分组成员 | 31 | `D - G`；仍是合法可发现用例，不能因未分组而从来源销账排除 |
| M：显式 case 元数据 | 10 | 同一 JSON 的 `cases` 键；它是元数据表，不是发现全集，当前 `M ⊆ G ⊆ D` |
| C：候选合格声明 | 3 | `cases` 中显式 `candidate_clean=true`；目前为 `branch-source-preview`、`reinstall-preserves-data`、`release-identity-commit` |
| dev representative 的分组展开 | 54 | `representative` 指向全部五组，去重展开恰等于 G；只描述默认代表集，不是 full |

五组分别为 review=12、archive=10、identity=16、writer=7、install=9，合计 54；当前没有重复成员，所有分组成员与显式元数据键都存在于 D。

选择语义由 `repro_select.py:253` 的 `_chosen()` 定义：指定组时选分组成员；不指定组时选 `all_cases()` 全集；之后才应用 only/candidate 过滤。`scripts/tests/wf_runtime/full/plan.py:504` 为 representative 指定默认组，`:520` 在没有显式组的 full/subset 路径不给组过滤。一次具体运行仍须以实际冻结计划为准。

所以当前全量基线为 `85 = 54 + 31`。85 是不同 case ID 的数量，green/red 是执行相位，不能用相位次数再乘后冒充用例数。

历史交叉证据（只读保留，不以历史数字代替当前静态发现）：

- `.trellis/tasks/archive/2026-11/11-14-wf-runner-round2-contracts/evidence/final/full2/summary.json`：`repro_ran=85`。
- `.trellis/tasks/archive/2026-11/11-15-wf-runner-boundaries-followup/evidence/verification-2026-11-16.json`：repro 对拍为 `[85,85]`。
- 同一归档任务的 `validation-2026-11-15.md:77`：59 suite + 5 flow/extra + 85 repro = 149。

### 未分组的 31 个 ID

```text
d21-executor-set-move
d21-executor-set-multi-clone
d21-executor-set-purge-reconfirm
d21-executor-set-venv-rebuild
definition-static-check
dep-edges
enable-disabled-branch
external-change-boundary
f7-1-touch-paths
f7-3-scope-single-source
help-covers-write-commands
history-anchor-unreachable
record-missing-in-worktree
run-advance-creates-task
run-create-once
run-finish
run-pause-and-advance
run-resume
run-terminate
skill-frontmatter-selfcheck
snapshot-broken-type
snapshot-empty-check
snapshot-empty-stop
snapshot-empty-write
snapshot-missing-check
snapshot-missing-stop
snapshot-missing-write
spec-three-part-index
startup-checks-anchor-assets
task-start-surface
wf-repair-handoff
```

保留这些 ID 的目的在于防漏核；本任务不以清点为由强制给它们分组或改变运行器选择语义。

## 2. 注册单元与候选声明

来源为 `scripts/tests/wf_runtime/full/units.json` 的完整 `units` 数组。按 kind 与字段状态分别统计：

| kind | 总数 | candidate_clean=false | candidate_clean=true | 字段未声明 |
|---|---:|---:|---:|---:|
| suite | 59 | 59 | 0 | 0 |
| flow | 4 | 0 | 0 | 4 |
| extra | 1 | 1 | 0 | 0 |
| candidate | 1 | 0 | 1 | 0 |
| manual | 2 | 2 | 0 | 0 |
| 合计 | 67 | 62 | 1 | 4 |

62 项显式 false 中，suite 之外是 `r72_tests`（extra）、`d1_tests` 和 `d1_wf_tests`（manual），不是 flow。未声明不得在清点证据中改写为显式 false，也不能据此推导 candidate 已验证。full 的 64 个主池单元与全部 67 个注册单元是不同口径，后者还含 candidate 兜底和两个人工单元。

## 2.1 实施后审计更新（2026-11-16）

`candidate-audit.json`（由 `candidate_audit.py` 可复现生成）记录 59 个 suite 在 candidate 0.1.0
上的真实运行：56 个通过并已把 `candidate_clean` 置为 true。`r67_tests` 是 fake-tree runner
技术审计，保留理由是 `units.json` notes 的模拟运行器契约（其 candidate 运行失败是模拟环境的
plan/scope 错误，不作为断言证据）；`r90_tests`（R93 追加平台资产不一致）与 `p5_v1`
（`[V1] 追加平台…: FAIL — False`）保留 dev-only，具体 `failures`/`expected`/`observed` 见该文件。
注册单元总数仍为 67；
新的 candidate 分布为 **57 true / 6 false / 4 未声明**（false 由 3 suite + 1 extra + 2 manual 组成）。
repro 的 D/G/U/M/C 基线不变（85/54/31/10/3）。

## 3. 清点与验收规则

1. 基线清点为完整 67 单元 + D 的 85 个 repro；G、M、C 是独立维度。覆盖表的每个 ID 同时记录 kind、分组成员关系、显式元数据状态和真实对象来源，不能用其中某一子集代替全集。
2. 逐 ID 比对，不能只核总数。新增/删除/改名必须列出基线与当前集合的差集及原因；保留集合必须逐项处置，未分组/无显式元数据不是排除理由。
3. 执行通过、排除、manual、不适用和待验证分别记账；完整来源清点不等于全部用例会在每个模式中执行，也不把未执行项计 passed。
4. 数量仅为该固定基线的快照。实施增加用例后重新派生当前数量和差集，不删新用例来凑基线总数；同数量但换 ID 仍必须报差异。
5. 本规则不新增发现算法：实施的运行期清点消费 `all_cases()` 的真实产出，分组消费现有 JSON；下面的独立只读复算仅核对本次规划证据。

## 4. 只读复算命令

在仓库根运行；只解析文本和 JSON，不执行 `scripts/tests/**` 中的任何入口：

```bash
PYTHONDONTWRITEBYTECODE=1 /softwares/python/bin/python3 -B - <<'PY'
import json
import re
from collections import Counter
from pathlib import Path

root = Path.cwd()
repro = root / "scripts/tests/wf_runtime/full/repro"
doc = json.loads((repro / "groups.json").read_text())
discovered = {
    p.stem for p in repro.glob("[a-z0-9]*.py")
    if re.search(r"(?m)^import _harness as H\s*$", p.read_text()[:4000])
}
members = [case for group in doc["groups"].values() for case in group]
grouped = set(members)
units = json.loads((root / "scripts/tests/wf_runtime/full/units.json").read_text())["units"]
print("D/G/U/M/C:", len(discovered), len(grouped), len(discovered - grouped),
      len(doc["cases"]), sum(v.get("candidate_clean") is True for v in doc["cases"].values()))
print("groups:", {k: len(v) for k, v in doc["groups"].items()})
print("duplicate memberships:", {k: v for k, v in Counter(members).items() if v > 1})
print("unknown group/meta IDs:", sorted(grouped - discovered), sorted(set(doc["cases"]) - discovered))
print("ungrouped:", sorted(discovered - grouped))
print("units:", len(units), dict(Counter(u["kind"] for u in units)))
for state in (False, True):
    print("candidate_clean", state, dict(Counter(u["kind"] for u in units if u.get("candidate_clean") is state)))
print("candidate_clean missing:", dict(Counter(u["kind"] for u in units if "candidate_clean" not in u)))
PY
```
