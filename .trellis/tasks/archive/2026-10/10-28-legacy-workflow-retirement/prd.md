# PRD：旧模块退役收口

## 1. 背景（实测事实）

范围已收敛为：`workflow-design.md`、`依赖机制设计说明.md`、Trellis 源码、五平台（Claude Code / Codex / ZCode / Pi / DSH）规范；
实现方案（B1）与 constraints（B2）可参考；`Trellis隐藏目录边界清单.md`（B3）暂停参考，待按 Trellis 现状重写。

用户已手工完成：删除 `docs/workflows/1.2-零补丁嵌入方案.md`；把 `docs/workflows/新项目开发工作流/`（236 文件）移入 `tmp/`。

因此仓库现状是"事实已变、记录未变"：

| 事实 | 仓库里的残留 |
|---|---|
| 1.2 已删 | 方案 102 行引用它（含附录 C 38 行）；constraints 的 Authority order |
| 旧模块已移出 | git 里 101 个未提交删除；12 个 spec 文件、2 个 docs 指路、`AGENTS.md:25`、`commands/shell/init-trellis-temp-project.sh:111` 仍指向该路径 |
| 四个维护 skill 服务的是旧产品 | 222 个文件仍存在，且 5 个 spec 契约文档把"修改范围锁定在旧路径"写成规则 |

## 2. 目标

让仓库在"旧模块已退役、1.2 已删"这一事实下自洽：文档不再声称旧资产存在，维护工具不再指向它，删除进入版本库。

## 3. 范围（四组）

| 组 | 内容 |
|---|---|
| **G1** | 提交既有删除（101 个：1.2 + 100 个旧模块已跟踪文件） |
| **G2** | 文档收敛：方案文档、constraints、AGENTS.md、docs 指路、spec 11 文件、commands 脚本 |
| **G3** | 四个维护 skill（222 文件）与其契约 spec 退役；删前摘录通用误报守卫 |
| **G4** | M1–M3 落定；§9.6 的 G3（模块源位置）改判；§9.5 追加裁决行 |

## 4. 不做

- 不建新模块源骨架、不写 CLI / 安装器 / `render.py`（属 T2）。
- 不改变体正文内容（`wf-variant.md` 标题沿用产品名，R4 已定沿用路径名）。
- 不改 `workflow-design.md`、`依赖机制设计说明.md`、`.trellis/workflow.md`。
- 不删除 `tmp/新项目开发工作流/`（留到 T3 完成后再删）。
- 不动 `.claude/settings.local.json`（本机文件，未入库）。
- 不按 Trellis 现状重写 `Trellis隐藏目录边界清单.md`（另任务）。

## 5. 验收判据

| ID | 判据（可机械执行） |
|---|---|
| A1 | `git status` 干净；本任务产生"退役"提交 |
| A2 | `grep -rn "1\.2-零补丁嵌入方案" --include="*.md" . \| grep -v '^./tmp/'` → 0 |
| A3 | `grep -rn "tmp/新项目开发工作流" --include="*.md" . --exclude-dir=tmp` → 0 |
| A4 | `grep -rln "新项目开发工作流" skills/ .claude/skills/ .agents/skills/` → 0 |
| A5 | 四个 skill 目录不存在；`spec/skills/` 四个契约文档不存在；`spec/skills/index.md`、`spec/scripts/index.md` 无死链 |
| A6 | 方案：无 `〔1.2`、无附录 C、§0.2 已改述、§2.1/§2.2/§2.5/附录 B.1 无 `tmp/`；§8.2 与 §9.7 体现 M1–M3；§9.5/§9.6 有对应裁决 |
| A7 | `trellis-library validate --strict-warnings` 与 `./scripts/validate-skills.sh` 通过 |
| A8 | `get_context.py`（默认与 `--mode phase`）正常 |
| A9 | 新增的误报守卫文档存在，且不含任何已退役路径 |

## 6. 传递

| 事项 | 承接 |
|---|---|
| 新模块源骨架、变体迁入、renderer | T2 |
| 新模块的 installer / command 契约 spec | T2 / T3 |
| B3 按 Trellis 现状重写 | 另任务 |
| `tmp/` 的最终删除 | T3 完成后 |
