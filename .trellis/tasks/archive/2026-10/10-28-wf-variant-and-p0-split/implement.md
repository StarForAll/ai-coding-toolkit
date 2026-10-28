# Implement：执行计划

> 两个交付物：`docs/workflows/wf-variant.md`（新文件，核心）+ `docs/workflows/workflow-implementation.md` 的 §9.6 两行与新增 §9.7。
> 其余文件零改动。

---

## 1. 前置（已核）

- [x] 三份权威文档 + 硬约束文件已读；`workflow-implementation.md` 1447 行（§3.5 / §3.7 / §3.8 / §2.1 / §9.5 / §9.6 逐节读过）
- [x] 原生契约实测：`get_context.py --mode phase` 剥状态块（C4）、`## Phase 1: Plan` 是唯一截断点（C3）、`--step` 可用（C5）
- [x] 事实核对：`wf` CLI 不存在、旧目录未移动、工作区干净、上一轮任务已归档
- [x] 用户已选 G6 选项 1（三段 · 资产先行）；本任务 = T1

## 2. 执行步骤

| # | 步骤 | 产出 / 判据 | 门 |
|---|---|---|---|
| 1 | 建 `docs/workflows/wf-variant.md` 头部：版本注释行 + 文件说明（暂存落点 / T2 迁入模板 / 判定权威）+ 哨兵行 | R1、R3 成立；说明里不出现"平台分支"字样 | — |
| 2 | 写 `## Phase Index`：四段结构表（设计稿 §4.1，含承载 / 产物 / 出口 / 机制入口） | 四段齐全；每行有命令名 | — |
| 3 | 写"入口：三段判定"表（设计稿 §9.1 + 方案 §3.7），逐段写命中条件与"命中即停" | 三段行数 1+1+3；每行给 `wf route` / `wf repair` / 卸载 指引 | — |
| 4 | 写"机制入口"表（方案 §3.5 全量命令 + 只读/副作用/人类专用分类）与"自检与修复"段（§3.8） | 命令名与附录 A 一致；`repair` 标注人类专用 | — |
| 5 | 写三个 `[workflow-state:*]` 块（planning / in_progress / completed） | R2：仅三值；每块 2–5 行且给出下一步命令 | — |
| 6 | 写步骤正文：`## Phase 1: Plan`（项目层 1.1–1.4）、`## Phase 2: Execute`（2.1–2.5）、`## Phase 3: Finish`（3.1–3.3）、`## 持续使用`（4.1–4.2） | C3、C5 成立；每节首行标注对应设计稿四段 | **G1 自检门**（见 §3 全部静态断言） |
| 7 | 夹具验证 W1 / W2 + 平台中立性 + 状态块裁剪行为 | A1 全过；夹具删除；本仓库 `git status` 干净 | **G2 验证门** |
| 8 | 改 `workflow-implementation.md`：§9.6 的 G5/G6 两行改为已裁决 + 指向 §9.7；新增 §9.7（三段拆分表 + 两处修正提案 + 传递项） | A4：与变体、与用户裁决一致；§9.5 零改动 | — |
| 9 | 交付说明：三层映射对应表（变体哪段 ↔ §3.5 / §3.7 / §3.8 哪条）+ 哨兵串原值 | A3 成立 | **G3 交付门** |
| 10 | Phase 3.3 spec 更新：把 C2/C3/C4/C6 四条解析契约与"P0 不自洽"两条追加到 `.trellis/spec/docs/workflow-implementation-constraints.md` 的 "Known traps" | 后续会话不必再自行推导 | — |

## 3. 验证命令

> 全部在仓库根执行；`V=docs/workflows/wf-variant.md`。

```bash
V=docs/workflows/wf-variant.md

# R1 哨兵（精确串，恰好 1 次）
grep -c 'WF-VARIANT-SENTINEL:1d9c4b7e' "$V"

# R2 三值块：开标签 3 个，且取值集合恰为三值
grep -o '^\[workflow-state:[A-Za-z0-9_-]*\]' "$V" | sort | uniq -c
grep -nE '\[workflow-state:(wf-|blocked|paused|terminated|verified)' "$V"   # 期望无输出

# R3 版本注释行
grep -n 'wf:module_version=' "$V"

# R4 两张映射表 + 每段有命令名（人工核对表格行）
grep -n '^### \|^## ' "$V"

# R6 平台中立：无 marker 形独立行、无平台名
grep -nE '^\[[A-Za-z][^][]*\]$' "$V"                                        # 期望无输出
grep -niE 'claude|codex|zcode|deepseek|pi\b' "$V"                           # 期望无输出

# R7 无证据链环节
grep -niE 'declare|verify|impl_sha|证据' "$V"                                # 期望无输出

# R5 无自造状态机：不出现转移表样式
grep -nE '无记录 *→|挂起 *→|→ *正常' "$V"                                    # 期望无输出
```

夹具验证（W1/W2，用完即删）：

```bash
F=tmp/wf-variant-probe/.trellis
mkdir -p "$F/workflows"
printf 'default_workflow: wf\n' > "$F/config.yaml"
cp docs/workflows/wf-variant.md "$F/workflows/wf.md"

python3 ./.trellis/scripts/get_context.py --mode phase | grep -F 'WF-VARIANT-SENTINEL:1d9c4b7e'   # W1
python3 ./.trellis/scripts/get_context.py --mode phase --step 2.4 | head -5                      # W2
python3 ./.trellis/scripts/get_context.py --mode phase --platform dsh | grep -c 'workflow-state' # 期望 0（C4）
python3 ./.trellis/scripts/get_context.py --mode phase --step 1.1 | head -3

rm -rf tmp/wf-variant-probe
git status --porcelain    # 只应有本任务的两个路径 + 任务目录
```

## 4. 审查门与回滚点

| 门 | 位置 | 通过条件 | 不通过 |
|---|---|---|---|
| G1 | 步骤 6 后 | §3 静态断言全过 | 就地改变体，不进夹具 |
| G2 | 步骤 7 后 | W1/W2 绿 + 夹具已删 + 本仓库配置零改动 | 停手报告，不放宽断言 |
| G3 | 步骤 9 后 | 映射表逐条可核 + 用户确认 | 补表或回退步骤 8 |

**回滚**：`docs/workflows/wf-variant.md` 为新增文件，删除即回退；`workflow-implementation.md` 的改动只有 §9.6 两行与新增 §9.7，`git checkout -- docs/workflows/workflow-implementation.md` 即可恢复。无其它副作用。

## 5. 不做（复核用）

- 不建 `.trellis/workflows/`、不设 `default_workflow`、不改平台目录、不移动旧目录、不写 CLI / 安装器 / skill 正文。
