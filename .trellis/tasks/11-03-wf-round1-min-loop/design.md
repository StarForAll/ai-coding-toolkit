# 技术设计：wf 首轮最小闭环

## 1. 分层与落地

```
docs/workflows/新项目开发工作流/          # authoring 源树（不入安装）
├── payload/{bin,lib,workflows,templates,install.py}
├── skills/<11 个>/SKILL.md
├── dev-manifest.json                     # 资产清单/版本/required_steps 来源；不含手填哈希
└── README.md                             # 发行说明（人读，不投放）

docs/workflows/wf-release/                # 生成产物（scripts/build-wf-release.py 产出）
├── wf-release.json  install.py  wf-release/{bin,lib,workflows,templates,skills}
```

目标项目：`.wf/{bin,lib,workflows,templates,install,tasks,preparations,user-workflows,workflow-runs,session-bindings,writer.json,project-config.json,baseline.md,spec,out-of-scope,.runtime}` + 项目根 `.wf-lock` + `.gitignore` 托管段（实现稿 §1.1、§4.5）。

## 2. 模块职责（`payload/lib/wflib/`）

| 模块 | 唯一职责 | 机制稿落点 |
|---|---|---|
| `module_main.py` | 以 `lib` 在 `PYTHONPATH` 内拉起 `cli.main()` | — |
| `codes.py` | 34 枚原因码 → 档位、出口、禁止修复；处理器→码映射 | §11.1 |
| `records.py` | `C(x)`/`H(domain,payload)`/文件摘要、拒绝重复键与 NaN 的读、原子写、`merge_unknown` | §1.1 |
| `paths.py` | RepoPath 校验、glob 段匹配、**可证包含**、字面前缀、嵌套仓库边界 | §3.1、§3.4.2 |
| `fingerprint.py` | 指纹项、`content_digest`、`check_anchor`、`paths_digest` | §3.2 |
| `scope.py` | 治理面块解析与条件①、候选路径分类 a–f、外部变更核对、工作区分类 | §3.3–§3.5、§4.4 |
| `actions.py` | `action.id`、意图写入、步骤推进、四态重入 | §5.1、§5.2 |
| `lock.py` | `flock` 互斥、标记校验、等锁 5s、holder 存活线索 | §4.1 |
| `writer.py` | acquire/release/两段交接、`receipt_state()` 四态派生 | §4.2、§4.5 |
| `session.py` | `SessionKey`、身份核对、持久绑定、定位缓存 | §1.4 |
| `tasks.py` | 记录读写、创建、批准、迁移（含 `replan`）、策展、Check 入口、知识/复盘、归属、放弃、归档 | §1.3、§2.2、§2.3、§5.3、§6.4 |
| `gates.py` | `required_steps` 投影、occurrence/anchor、`HANDLERS`、最终八项门禁 | §11.2、§11.3、§9.3 |
| `check.py` | 固定五步 | §3.2、§3.5 |
| `curation.py` | 策展写入与读取统计 | §8.3、§8.4 |
| `spec.py` | frontmatter、匹配排序、读取侧车、变更、预算 | §8.3、§8.4 |
| `runs.py` | `prepare/validate/create/advance/pause/locate/terminate`（第二轮：可调、`WF_CAPABILITY_UNAVAILABLE`） | §7 |
| `review.py` | launch/verify_anchor/import_report/decide | §9.1、§9.2 |
| `maintenance.py` | 第三轮 upgrade 的 preview/token_confirm（未交付）+ repair 共用形状说明 | §10.3 |
| `assets.py` | `load_installed_manifest`、`compute_rules_digest`、`effective_rule_version`、`compare`、`branch_source_check`、`parse_release`（第三轮） | §10.2、§10.4 |
| `config.py` | 项目配置读取（类型/范围/缺省）、执行器确认记录读取 | §8.1、§8.2 |
| `templates.py` | 占位标记 `{{WF_REQUIRED:<f>}}` / `__WF_REQUIRED__` 的双向核对 | §2.3、§10.2 |
| `cli.py` | 参数面、信封解析、代次核验、分派、输出渲染与退出码 | §11.1、§2.2–§2.4 |

`bin/wf.py` 引导层五步（实现稿 §2.1）与 `bin/repair.py`/`uninstall.py`（自含）不 import `wflib`。

## 3. 关键判定实现要点

1. **canonical JSON**：`C(x)` 键按 Unicode 排序、`separators=(',',':')`、`ensure_ascii=False`、无尾换行；集合型数组按元素 `C` 的 UTF-8 字节序去重排序（除非 schema 指定排序键）。
2. **check_anchor 十键**：`plan_version, entry_snapshot_digest, touch_paths_digest, paths_digest, content_digest, acceptance_digest, spec_versions, baseline_digest, config_digest, workflow_snapshot_digest`；等价链归一 `plan_version`/`acceptance_digest`。
3. **occurrence/anchor**：任务步骤 `H("wf-step-occurrence-v1", C({task_id, step_id, P}))`；控制步骤 `H("wf-control-occurrence-v1", C(P))`；anchor 按规则类/内容类分派（§11.2）。
4. **可证包含**：`p ⊆ g` 枚举 `g` 的 `**` 对齐（0..剩余段数），要求 p 字面段被 g 段接受、p 段内通配与 g 对应段逐字符相同或 g 段为 `**`、p 的 `**` 必须对 g 的 `**`。
5. **锁**：`flock(LOCK_EX|LOCK_NB)`，5s/50ms 有界等待；标记 `wf-lock-v1\n`；只创建不删除。
6. **动作**：意图写主记录 `action`；步骤后置核验；`persist_pending` 只用于 `task.archive`/`run.terminate`；恢复四态按 §5.2。
7. **代次**：建立代次的动作免携带；写判定字段的子动作必须携带并与 holder 比对，缺失/不符同判 `WF_GENERATION_STALE`。
8. **信封**：`session` 对象原样入 `SessionKey`；`inputs` 只承载规范化参数；身份不接受命令行/环境变量覆盖。
9. **审查**：报告协议块 `<!-- wf-review-report:v1 -->`；暂存目录 `tempfile.gettempdir()/wf-review/<project_id>/<task-id>/round-N/<slot>/`；导入前重算锚点。
10. **发行**：`rules_digest=H("wf-rules-v1", C({schema_version, compatibility_without_rules_digest, assets, required_steps, template_markers, gitignore_managed}))`；`effective_rule_version=H("wf-effective-rules-v1", C({rules_digest, installed_assets}))`。

## 4. 取舍

- **不新增判定**：`wf.py` 只做定位/转交/执行器解析与 `confirm-executor`；所有业务判定在 `cli.py` 之后。
- **二/三轮命令**：统一由 `cli.py` 的 `_unavailable(round_no, …)` 产出 `tier=blocked / WF_CAPABILITY_UNAVAILABLE / facts=轮次`，命令签名照实现稿 §2.3，不建半成品处理器。
- **首轮无挂起集合**：`task-reassess` 与归档/启动触发的复评按空集合通过（不写记录、不返回 unavailable），完整路径留第二轮。
- **fixture 放在仓库外**（`/tmp/wf-fixtures-<date>/`），避免污染工作树与既有校验。
- **session_profile**：dev-deploy 的预览确认即人声明点；`--host-id` 记录宿主标识，`capability.status` 由人用 `--verify-capability` 显式声明 verified（缺省 unknown → `WF_IDENTITY_UNRESOLVED`，正是 V1 的待裁定分支）。

## 5. 兼容与回滚

- 目标项目记录只增字段、不删不改义；未知字段保留。
- 每个阶段产物可单独重建：源树 → `docs/workflows/wf-release/` 字节复现；目标项目侧任何 `.wf/` 数据可由 dev-deploy 重投（数据区不覆盖）。
- 回滚点：P1–P5 每阶段结束做一次机检 + 该阶段出口验证；失败先修实现，不改上位。
