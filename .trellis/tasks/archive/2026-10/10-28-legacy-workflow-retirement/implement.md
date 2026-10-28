# Implement：执行计划

> 交付：一次"退役收口"提交（删除 + 文档收敛 + 维护 skill 退役）。不新增模块、不写代码。

## 1. 前置（已核）

- [x] 现状实测：101 个未提交删除；旧模块 236 文件中 100 个曾入库、136 个为缓存类（`.pytest_cache`/`__pycache__`/`.pyc`）
- [x] 四个 skill 未被 hooks / `.template-hashes.json` / `trellis-library/manifest.yaml` 引用（只有本机 `settings.local.json` 的权限条目，未入库、不动）
- [x] R4 沿用路径名；R5 全部采纳 M1–M3；R7 文档不引用 `tmp/`
- [x] 方案内待改规模：`〔1.2` 34 行、`1.2 §` 86 行、`tmp/…` 8 行、`旧模块` 12 行、附录 C 35 行

## 2. 执行步骤

| # | 步骤 | 判据 | 门 |
|---|---|---|---|
| 1 | 冻结证据：记录 `git status --porcelain -uall`（应为 101 D + 任务目录），与 design §4.1 清单比对 | 无未预期改动 | — |
| 2 | 叙述层收敛：方案 §0.2（P-d）、删除附录 C（P-c）、正文 `〔1.2` 标注（P-a，34 行）、`1.2 §/D` 叙述（P-b，除附录 C 外）；§9.4 标题改述 | `grep -c '〔1\.2'` = 0；附录 C 标题不存在 | — |
| 3 | 结构层收敛：方案 §2.1 / §2.2 / §2.5 / 附录 B.1 / §8.2 ① | `grep -c 'tmp/新项目开发工作流'` = 0 | — |
| 4 | M1–M3 落定：§8.2 P0 ⑤/⑩/⑫ 与 P1；§9.7 表改写（含新增 M3 行、删 N4/D5） | §8.2 两行含"账本读取/最小 `wf close`/W18 归 P1"字样 | **G1** |
| 5 | 裁决留痕：§9.5 追加 3 行（M1–M3、G3 改判、四 skill 退役）；§9.6 G3 行改判 | §9.5 前三行原文未变，仅追加 | — |
| 6 | constraints 同步：Authority order 删 1.2 句；"Before implementation" 改写为"旧模块已退役"；Known traps 的 M1/M2 标"已裁决" | 无 `1.2` 字样、无 `tmp/` | — |
| 7 | 仓库指路收敛：`AGENTS.md:25`、`docs/workflows/自定义工作流制作规范.md:469-470`、`git rm docs/Trellis隐藏目录边界清单.md` | 两文件无旧路径；后者已不在工作区 | — |
| 8 | 新增 `.trellis/spec/docs/workflow-asset-audit-guards.md`（5 条通用误报守卫，不含已退役路径） | 文件存在且 grep 无旧路径 | — |
| 9 | 退役四个 skill：`git rm -r` 六个目录（222 文件）+ 四个 spec 契约 + `spec/scripts/workflow-*-contracts.md` 两个；改 `spec/skills/index.md`（删 25–28、46–93、98–111 段）、`spec/scripts/index.md`（删 2 行） | 目录不存在；两个 index 无死链 | **G2** |
| 10 | 其余 spec 改述：`workflow-support-inventory.md`、`spec/docs/index.md`、`spec/agents/index.md`、`spec/guides/workflow-repeat-issue-triage.md` | `grep -rn 新项目开发工作流 .trellis/spec/` 仅剩方案 §2.1 的合法引用（新模块源） | — |
| 11 | `commands/shell/init-trellis-temp-project.sh`：先查是否调用旧产品脚本；只写死路径 → 改指 `docs/workflows/新项目开发工作流/`；依赖旧产品 → 删除脚本 | 决定与理由写入提交说明 | — |
| 12 | 全量验证（§3）+ 提交（单一 commit） | A1–A9 全过 | **G3** |

## 3. 验证命令

```bash
# A2 / A3：已删文档与 tmp 路径零引用（排除 tmp 自身）
grep -rn "1\.2-零补丁嵌入方案" --include="*.md" . --exclude-dir=tmp --exclude-dir=.git
grep -rn "tmp/新项目开发工作流" --include="*.md" . --exclude-dir=tmp --exclude-dir=.git

# A4：skill 侧零引用
grep -rln "新项目开发工作流" skills/ .claude/skills/ .agents/skills/ 2>/dev/null

# A5：目录与死链
for d in .claude/skills/workflow-audit .claude/skills/workflow-capability-audit \
         .agents/skills/workflow-audit .agents/skills/workflow-capability-audit \
         skills/workflow-repair skills/workflow-scan; do [ -e "$d" ] && echo "STILL EXISTS $d"; done
grep -rn "workflow-audit\.md\|workflow-capability-audit\.md\|workflow-scan\.md\|workflow-repair\.md\|workflow-installer-upgrade-contracts\.md\|workflow-command-doc-contracts\.md" .trellis/spec/ docs/

# A6：方案文档
grep -c '〔1\.2' docs/workflows/workflow-implementation.md          # 0
grep -n '^## 附录 C' docs/workflows/workflow-implementation.md        # 无输出
grep -n '最小 `wf close`\|账本读取\|W18' docs/workflows/workflow-implementation.md | head

# A7 / A8：项目校验与冒烟
/softwares/python/bin/python3 trellis-library/cli.py validate --strict-warnings
./scripts/validate-skills.sh
python3 ./.trellis/scripts/get_context.py | head -5
python3 ./.trellis/scripts/get_context.py --mode phase | head -3
```

## 4. 审查门与回滚

| 门 | 位置 | 通过条件 |
|---|---|---|
| G1 | 步骤 4 后 | §8.2 两行与 §9.7 与 M1–M3 一致；§9.5 尚未动 |
| G2 | 步骤 9 后 | 六个目录消失；两个 index 无死链；`validate-skills.sh` 通过 |
| G3 | 步骤 12 前 | A1–A9 全过，`git status` 只剩待提交改动 |

**回滚**：整个任务是一个提交，`git revert <sha>` 即可整体撤回；`tmp/` 与设计稿未被触碰。

## 5. 提交

单条提交，信息包含三件事：旧模块/1.2 退役的删除、文档收敛、四个维护 skill 退役（含守卫摘录）。不包含 T2/T3 的任何新建内容。
