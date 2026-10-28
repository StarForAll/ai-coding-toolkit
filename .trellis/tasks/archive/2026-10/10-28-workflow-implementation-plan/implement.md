# Implement：交付执行计划

> 交付物只有一个新文件：`docs/workflows/workflow-implementation.md`。不改其它文件。

---

## 1. 前置确认（已完成）

- [x] 设计稿 `workflow-design.md` 全文 850 行已读
- [x] `依赖机制设计说明.md` 结构与 §4/§5/§13 已读
- [x] `1.2-零补丁嵌入方案.md` 正文 §0–§9 已读，§10 审查记录按性质略读
- [x] 仓库事实核实：Trellis `0.7.0-beta.42`、变体链存在、`task.py` 命令集、archive 两道分支门、start 的 manifest 门、五平台目录、`.zcode/config.json` 加固形态
- [x] 用户确认落点：`docs/workflows/workflow-implementation.md`

## 2. 执行步骤

| # | 步骤 | 产出 / 判据 |
|---|---|---|
| 1 | 落 frontmatter 与 §0 定位（三份文档层级、术语复用、证据四档） | 无版本绑定决策进入正文 |
| 2 | §1 实现前提与目标形态：三条前提、写入面结论、零补丁地基三条实测、T0/T1a/T1b/T1c/T2 五层边界与写入面清单 | 写入面清单可机械核对；T1c 解释 zcode |
| 3 | §2 目录布局与生命周期：模块源、目标项目布局、进出库流向、安装/升级/卸载动作 | 每条路径标注归属层 |
| 4 | §3 状态、账本与门禁：三值任务状态、账本载体与格式（JSON + 派生视图）、雪花标识与占用校验、选择性提交、七个机制入口、选择规则、启动自检分类 | 设计稿表 4-1/4-2 每条转移都能找到入口 |
| 5 | §4 平台支持：数据表（五平台）、接入四条件、frontmatter 渲染、五平台分节、通用 agent、G0 | 每平台四段齐全 |
| 6 | §5 ZCode 加固：成因（cwd 绑定 + exit 2 阻断）、四条命令模板、安装期步骤、漂移债务、撤销条件、验收 | 模板与当前 `.zcode/config.json` 语义等价 |
| 7 | §6 记录与写入纪律：原生字段纪律表、不设证据链的替代判定、提交归属、AGENTS.md 块外路由、护栏取舍 | 逐条注明"写入/不写入" |
| 8 | §7 升级与拆卸：三轴版本、探针、升级 SOP 与回滚、拆卸契约对齐设计稿 §9.4 两种模式、往返验收 | 卸载入口不依赖机制运行时 |
| 9 | §8 验收与实施路线：探针清单（必需/增强）、阶段 P0–P4、每阶段判据、复杂度闸门 | 每阶段可被一个真实任务验证 |
| 10 | §9 冲突与待裁决登记：12 条以上，六字段 | A/B/C 分类齐全 |
| 11 | 附录 A 命令面、B 路径清单、C 来源映射表 | 与 design.md §3 一致 |
| 12 | 自检与汇报 | 见 §3 |

## 3. 验证命令

```bash
# 结构
grep -c '^## ' docs/workflows/workflow-implementation.md

# 平台四要素（每个平台标题下应各有 4 段）
for p in "Claude Code" "Codex" "ZCode" "Pi" "DSH" "通用"; do echo "== $p"; done
grep -n '^### ' docs/workflows/workflow-implementation.md

# 占位符检查（应为空）
rg -n 'TBD|TODO|待补|FIXME' docs/workflows/workflow-implementation.md

# 设计稿条款覆盖（人工核对清单）
grep -n '不变量\|表 4-1\|表 4-2\|关卡\|三段入口' docs/workflows/workflow-implementation.md

# 相对链接存在性
python3 - <<'PY'
import re, pathlib
p = pathlib.Path("docs/workflows/workflow-implementation.md")
for m in re.finditer(r'\]\((\./[^)#]+)', p.read_text()):
    t = (p.parent / m.group(1)).resolve()
    print(("OK " if t.exists() else "MISSING "), m.group(1))
PY
```

## 4. 风险与回滚

| 风险 | 处理 |
|---|---|
| 文档过长导致自洽性下降 | 每章写完即回看与设计稿条款的对应；冲突只出现在 §9，正文不复述 |
| 术语漂移（设计稿"返工任务/替换指向" vs 1.2 "wf 记录"） | 统一采用设计稿术语，1.2 词汇只在映射表中出现 |
| 把 1.2 的版本绑定决策带进正文 | 附录 C 逐条标注"剔除/改写"，自检时 grep `D20|D21|D22|D23|wf-verified|wf-impl` |
| 冲突表与正文结论不一致 | §9 每条给"建议处置"，正文对应处写"按 §9-Cn 处置" |

**回滚**：仅新增一个文件；如需撤销，删除该文件即可，无其它副作用。

## 5. 交付后动作（待用户决定）

- 是否在 `docs/workflows/` 的某个索引或 README 中登记该文档（本仓库根 README 有双语同步契约，不在本任务范围）。
- 是否按 Trellis Phase 3.4 提交本次改动。
