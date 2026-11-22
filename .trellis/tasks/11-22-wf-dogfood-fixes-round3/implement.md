# implement.md — wf dogfood 三轮修正（第 2 版，吸收外部审查）

> 上下文顺序：implement.jsonl → prd.md → design.md → 本文件。
> 分组提交语义见 design.md §7；**全部提交动作仅在用户同意后执行**。

## 阶段 1：a 组 + b 组（源码 LIB/SK + 上位稿 + 断言）

- [ ] 1.1 W1-a1：`LIB/authorize.py` 合并段并入 `content_bound_patterns`。
- [ ] 1.2 W1-a4：`covers()` 与 `record_authorization` 记录侧同批改用
      `records.file_digest_state`（missing=删除例外判定、unreadable=未覆盖/
      未绑定；删除两处内联 except-OSError）。
- [ ] 1.3 W1-a3：`LIB/review.py:2704` `started` → `started_at`。
- [ ] 1.4 W1-a2：`cmd_task_approve --draft` 补机械修订骨架（**占位文案写明
      "仅已有批准后使用"**）；`cmd_task_replan --draft` 删该骨架；replan 拒绝
      补 next_/exits 指向 task-approve；注释入口指向同步；SK/wf-continue:28
      路由句改 `task-approve`。
- [ ] 1.5 W2-1：`ACTIONS` 删 commit；docstring 守卫清单修正（四类 + finish
      唯一通道句 + vendor 笔误）；MECH K6 登记段 + DSGN §6.5 通道句。
- [ ] 1.6 W2-2：`fingerprint.check_anchor` 键白名单十→十一键 +
      `anchor_parts` 增 `control_plane_digest` 与可选 `classified` 参数
      （delivery_set 同型；v 桶单一来源、file_digest_state 归因入摘要；
      **classify 异常归因**：`CheckError`（WF_RECORD_INVALID 等）原样传播，
      仅非 CheckError 包为 WF_SCOPE_UNRESOLVED）；MECH §3.2（键集合 +
      一次性失效声明 + 只读面 classified 口径）/§3.5 + DSGN §3.2。
- [ ] 1.7 W2-3：单 reviewer 接受记录通道（`review-decide
      --single-reviewer-acceptance`、`reviews.single_reviewer_acceptance`
      轮绑定、判定分支消费、facts/review-status 投影、help 注册）；
      MECH §9.2 + DSGN §6.5 + SK/wf-review 适用面。
- [ ] 1.8 W2-4/5/6/7：SK/wf-continue 审查外发确认步 + vendor 判断句（按
      真实 CLI 形态：judgment 文件条目 kind=框架改动 经 `judgments add
      --task --file`，无 --kind 旗标）；judgments `KINDS` 增中文类
      **框架改动**（MECH §9.4 kind 列表 + cli.py prefs --kind + judgments
      帮助枚举同批）；cli.py:2342 review-notes 帮助；tasks.py:1250 next_
      分档；check/archive facts 投影 vendor_judgments。
- [ ] 1.9 W2-9：工作习惯收敛（wf-continue 唯一完整定义位，**合并 wf-finish
      版独有的 generation 句**；wf-start/wf-finish 判断句+指针；
      wf-review-action 复述收敛）；DSGN §1.1 本地完整路径句。
- [ ] 1.10 断言批（scripts/tests/wf_review + **wf_runtime**）：a-1 组合、
      a-2 草稿/拒绝双面（含占位前置文案）、a-3 端到端、a-4 三态+记录侧、
      commit 类拒绝、control_plane（变化/常量/一次性失效/分类失败归因）、
      单 reviewer 接受/拒绝/投影、kind=框架改动、archived next 分档、
      help 注册表更新。
- [ ] 1.11 回退注入自检（W1 各项 + control_plane + commit 拒绝，各一次）。
- [ ] 1.12 阶段验证：T0 unittest discover；T1 定向套件 + validate-wf-design
      + check-doc-refs + validate-skills。

**阶段 1 审查门**：完成后向用户呈报，确认后进入阶段 2。

## 阶段 2：P0-1 会话身份

- [ ] 2.1 W3-1：`enable --new-session`（终态前置判定、`replace_owner`
      组更新、写权语义、help/flag 登记）；SK/wf-start 指引句；MECH §1.4 登记。
- [ ] 2.2 W3-2 建立语义（四态解析次序 + **解析结果单一结构**）：
      `_auto_resolve` 返回扩为 `{state, key, attachment, evidence,
      host_identity_present}` 单一实现（auto_session/cmd_enable/
      _identity_facts 只消费不重判；ctx 缓存同型）；`cmd_enable` 建立条件
      扩为"key 为 None 或映射命中且路由无在途会话"；**② 在途会话续用**
      （路由命中会话有附件、**绑定文件存在且可读、实例标识匹配
      （instance_expected ∈ {None, "", binding.instance_id} 即匹配——历史
      会话 None 视为匹配）**、对象未终态 ⇒ 续用、不接管；**无绑定文件
      （启用未绑定）⇒ 不算在途 ⇒ 走③**；instance_expected=None/空 ⇒
      以 binding.instance_id 回填附件（`sync_attachment_instance` 既有唯一
      写回实现）后恢复会话实例标识（否则 auto_session 把 None 作
      instance_id、写入口拒绝）；已有不同值 ⇒ unresolved 人裁档；
      绑定不可读/实例不符 ⇒
      `state=unresolved` + evidence——**只在写/推进入口阻断，status/gate/help
      等只读面降级为 facts 可见事实继续运行**（只读诊断仍可运行）；
      ②态轮换出口 = 完成/暂停/放弃对象后重试（不指 bind）；`_establish_
      auto_session` 扩展（③ 以 host 身份建立：host_id 按 platforms 清单核；
      建立前对同锚点既有其他 owner `replace_owner` 路由接管；接管启用未
      绑定会话时 facts 点明"旧会话路由已让出，需重新 enable"）；
      `_auto_resolve`/`auto_session` 前置映射查询；`_identity_facts` 拆
      host_identity_present/session_provider（不覆盖 source）。
- [ ] 2.3 W3-2 hook 资产：`payload/hooks/codex-session-identity.py`（**先定位
      项目根并核 `.wf/`**——根取脚本落点上两级，无 `.wf/` exit 0；载荷
      session_id → wflib.session 锚点（import 失败写 import-error 标记）→
      host-session-map 写入）；**资产链八处**：wf_release_common
      `target_of` 映射、install.py `ASSET_CLASSES`/`plan_writes`/
      `self_check` 类分发（host_hook 按声明平台落点，不走 skill 根；
      **self_check 增平台集入参**）、**add_platforms 增 host_hook 分发**
      （追加平台投放 hook + hooks.json 条目）、uninstall 三处类分支、
      **清单 assets[] per-asset 平台条件**（进 rules_digest；可选附加键
      不递增 schema 版本，**兼容声明收窄为"platform 键对已知类不破坏"——
      host_hook 类本身需新安装器，安装器与清单同发行单元、无正常混用
      路径，登记 MECH §10.2**；**非法组合三处拒**：verify_assets/
      self_check/plan_writes 拒"platform 出现在非 host_hook 资产或
      host_hook 缺/错 platform"）、DSGN §7.1 + MECH §10.1/§10.2 schema、
      dev-manifest。
- [ ] 2.4 W3-2 hooks.json 合并/卸载：codex 平台投放 + 保序追加幂等 +
      命令串所有权判定 + 同名冲突报人裁决；uninstall 只删自己条目与文件；
      平台条件断言（--platform dsh 不投放 .codex/hooks/）。
- [ ] 2.5 W3-2 可见性与次序登记：`status` facts 投影 host_mapping 状态
      （hit/absent/import-error）；`_identity_facts` 拆两字段
      （host_identity_present / session_provider，不覆盖 source）；
      **MECH §1.4 取用次序改写**（边界在途会话续用 → 宿主标识 → 进程锚，
      人裁改写 + 理由登记，整句改写非补句）+ **DSGN §1.3 已知限制句补登**
      （在途期内 /clear 仍不可区分——声明边界、非回归、覆盖到对象终态为止，
      与 MECH §1.4 互指）+ 不变量补句 + session.py 模块头。
- [ ] 2.6 W3-2 登记：MECH §1.4/§10.1、IMPL 部署表消费段 + DSH 显式信封
      指引、DSGN §1.3 指针句；gitignore 不动（.wf/.runtime 已整目录忽略）。
- [ ] 2.7 断言批：new-session（终态可换/在途拒/历史保留）、host 建立/
      并存/回落/覆盖/**import-error 可见与恢复**（失败→标记→成功→标记消失
      且映射命中）、**unresolved 只读降级**（绑定不可读时 status/gate/help 仍
      出 facts、写入口阻断）、**instance=None 回填后写操作可通**（已有不同值
      ⇒ unresolved）、hooks.json 合并/幂等/冲突/只删自己
      （test_asset_boundaries.py 同族）。
- [ ] 2.8 回退注入自检（new-session、host 建立优先级各一次）。
- [ ] 2.9 阶段验证：T0 + T1 定向（identity/install 套件）+ validate-wf-design
      + validate-skills。

**阶段 2 审查门**：呈报后确认进入阶段 3。

## 阶段 3：P0-2 upgrade + 回传 + 版本收口

- [ ] 3.1 W4-1 核心：install.py `--upgrade` 模式——三必填参数不变、
      **--source 写死为发行检出根**（其下直接有 install.py/wf-release.json/
      wf-release/）；三方表逐行（偏离落 installation.json assets，字段名按
      MECH §10.4 `{local_fingerprint, upstream_version, upstream_fingerprint,
      decision}`）；**assets 写入侧补齐**（首次安装与 add_platforms 同批写
      upstream_version/可重取来源引用，否则"偏离保持"行无从判定）；预览全字段
      （§10.3）+ **PreviewToken 逐字复制 repair.py 的类实现并入
      --verify-token-parity 比对集**（路径集由 payload/bin/{repair,uninstall}
      扩为含 payload/install.py；install.py 的 --token-parity-check 分支在
      argparse 三必填之前处理）+ 同一交互进程确认；**升级前置机器判据**
      （纯读取函数：task.json {status, paused, **suspended**,
      **handoff.wip（任务记录，非 writer.json——writer 的 handover 无 wip
      字段）**——status==not_started 或 (paused 且非 suspended)；handoff.wip
      存在且 resolved 为空即阻断} / workflow-runs {terminal, paused}，不可读
      即阻断；分支来源/writer 观察复用既有函数；判据字段集登记 MECH §10.4
      升级前置段）；
      maintenance_results；applied_pending_commit；应用后 self_check；
      --export-deviations（O 字节按可重取来源取回，不可取回如实产出）。
- [ ] 3.2 W4-1 入口：`BIN/wf.py` upgrade 同型转交（--release/--release-ref
      透传）；cli.py `COMMANDS["upgrade"]` **保留注册**、桩体改转交报错、
      COMMAND_FLAGS 更新并注明"help 一致性保留"；COMMAND_HELP 真实条目。
- [ ] 3.3 W4-3 文档批：DSGN §7.2 导出句、MECH §10.3 令牌句对齐既实现
      （短指纹口径，消文实分叉）、SK/wf-continue vendor 回源句、
      README(+en) upgrade 通道 + 0.1.5（版本唯一源 = README + builder
      --version；**dev-manifest 维持占位符**）。
- [ ] 3.4 断言批：三方表逐行、三必填缺参报错、--source 子路径即
      WF_PATH_INVALID、预览全字段、令牌（重跑销毁/非 TTY/parity 三方一致且
      --token-parity-check 先于 argparse）、升级前置阻断（含**两步处置出口**：
      暂停后 writer 仍 held ⇒ 出口 task-pause → writer release（WIP 未处置
      时先处置）→ 重跑预览）、applied_pending_commit、
      installation.json assets 写入侧字段
      （首次安装/add_platforms/upgrade 三写者）、export-deviations
      （O 可取回/不可取回/无偏离/**--out 非空拒/符号链接拒/部分失败如实
      报告**）、wf.py 转交、help 注册表 48/48 双向断言不动。
- [ ] 3.5 自举验证：0.1.4 夹具项目 ← 0.1.5 发行 `--upgrade --apply`
      （夹具内不提交）；candidate-clean 评估，不足则 dev-only 登记。
- [ ] 3.6 回退注入自检（upgrade L=O 行、令牌重跑销毁、转交各一次）。
- [ ] 3.7 版本收口：README 双语 + builder 目标版本 → 0.1.5；
      `build-wf-release.py --version 0.1.5` 重建发行树（git status 核对）。

## 收尾（阶段 3 后）

- [ ] C1 backlog-dogfood-round2.md「下一任务待办」逐项处置标注（含维持项理由）。
- [ ] C2 T2 全量：`run_all --full --repro green` + `build-wf-release.py
      --verify --verify-token-parity` + validate-wf-design + check-doc-refs +
      validate-skills。
- [ ] C3 真实宿主手动核验登记（Codex hook 实跑；full README 手动项清单更新）。
- [ ] C4 journal 记录 + 最终复核：git diff --stat 对照三阶段分组 +
      **git status --porcelain（含未跟踪）对照各阶段"新建文件"清单**
      （如 `payload/hooks/codex-session-identity.py`——普通 diff 不含未跟踪
      文件，漏核等于漏交付）。
- [ ] C5 **呈报用户**：结果、未核实项、拟提交分组清单——**等待同意**。
- [ ] C6 用户同意后：分组提交（fix(wf) 主体、chore(wf) 重建发行树 0.1.5、
      docs/chore 收尾）；trellis finish-work 流程。

## 验证命令速查

```bash
# T0
PYTHONPYCACHEPREFIX=/tmp/wf-unit-pycache /softwares/python/bin/python3 -m unittest discover -s scripts/tests -t .
# T1 定向
WF_SUITES="<受影响套件>" bash scripts/tests/wf_runtime/full/run_all.sh
bash scripts/tests/wf_runtime/full/repro/run.sh --group review --mode green --no-build
# 文档闸门
/softwares/python/bin/python3 scripts/validate-wf-design.py
/softwares/python/bin/python3 scripts/check-doc-refs.py
./scripts/validate-skills.sh
# T2
bash scripts/tests/wf_runtime/full/run_all.sh --full --repro green
/softwares/python/bin/python3 scripts/build-wf-release.py --verify --verify-token-parity
```

## 回滚点

- 阶段边界即回滚点（各阶段独立成组、独立 T0 绿）。
- 上位稿改动与实现断言同批；发行树重建独立 chore 提交可单独 revert。
- 用户同意前无任何提交；**中途回退 = 只撤销本任务产生的差异**——按各阶段
  分组文件清单先 `git status`/`git diff` 核对无本任务之外的未提交改动混入，
  再 `git diff -- <本任务文件> | git apply -R`；**本任务新建的未跟踪文件**
  （普通 git diff 不含）按各阶段"新建文件"清单逐一核对 untracked 集只含
  本任务新建文件才删除；发现无关未提交改动混在同一文件 ⇒ 停下交人处置，
  不用 `git checkout --`/`git reset --hard` 类会丢弃未提交工作的操作。
