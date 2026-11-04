# 执行计划：wf 首轮最小闭环

> 每阶段先跑通再进下一个；每阶段末跑三条机检（validate / check-doc-refs / unittest）。
> **P1–P5 是同一轮内的阶段收口顺序，不代表轮次**；「能力已实现」「环境已验证」「验收结论」三态分别记在
> `validation.md`（用例/回归/未运行项分开列），阶段名不构成验收结论。

## 全局验证命令

```bash
/softwares/python/bin/python3 scripts/validate-wf-design.py     # 期望：输入摘要 4/4 + 七项检查通过
/softwares/python/bin/python3 scripts/check-doc-refs.py         # 期望：0 problem(s)
/softwares/python/bin/python3 -m unittest discover -s scripts/tests -v   # 期望：Ran 19 tests ... OK
```

## P1 底座

- [ ] `payload/lib/wflib/{__init__,codes,records,paths,fingerprint,lock,writer,session,actions,config,templates,assets}.py`
- [ ] `payload/bin/wf.py` 引导层（定位 → repair/uninstall 转交 → confirm-executor → 执行器解析 → execve 移交）
- [ ] `payload/lib/wflib/{module_main,cli}.py`（子命令骨架 + 输出契约 + `status`/`gate`/`version`/`inspect`/`enable`/`bind`/`writer`/`writer-handover`/`stop`/`confirm-executor`）
- [ ] `scripts/wf-dev-deploy.py`（预览/`--confirm` 投放/`installation.json`/`release-manifest.json`/`.gitignore` 托管段/首装契约/自检）
- [ ] `dev-manifest.json` + 源树 `README.md`
- 出口：在 `/tmp` 空项目上 `--confirm` 部署成功，`wf.py --project <abs> status --json` 输出 `{tier, code, ...}`；`WF_EXECUTOR_UNCONFIRMED` 与 `confirm-executor` 往返可用

## P2 单任务闭环

- [ ] `wflib/{tasks,gates,check,curation,spec}.py`
- [ ] `task-new / task-approve / task-start / task-replan / task-pause / task-resume / task-curate / task-check / task-knowledge / task-retrospect / task-attribute / task-abandon / archive / baseline-apply / spec-update`
- [ ] `payload/templates/**`（project-config 骨架、baseline、spec、task、user-workflow）
- [ ] `payload/workflows/{task-flow,session-flow,knowledge-flow}.md` 的 required 步骤与 enforcement 行
- 出口：F1 上真实普通任务 `task-new → approve → start → check（五步） → knowledge → finish 人判 → archive` 全通

## P3 审查适配

- [ ] 先探测 `claude`/`codex`/`dsh` 的非交互 reviewer 能力（不可用按机制稿 §6.4 记录，不降审查）
- [ ] `wflib/review.py`：`review-launch / review-import / review-decide`
- [ ] `skills/wf-review`、`skills/wf-review-action`（协议块、暂存路径、锚点字段）
- [ ] `payload/workflows/review-flow.md`（enforcement 行）
- 出口：V4 链路在 F2 上跑通或如实记「环境不足 + 原因」

## P4 发行与部署

- [ ] `payload/install.py`（release 根单文件安装器：`--target/--release-ref/--source/--skill-root/--confirm`）
- [ ] `scripts/build-wf-release.py`（确定性打包 + `rules_digest` + `--verify` 字节复现 + `--verify-token-parity`）
- [ ] `payload/bin/{repair,uninstall}.py`（自含、令牌同构）+ `payload/workflows/maintenance-flow.md`
- [ ] `wflib/{runs,maintenance}.py` 与二/三轮命令的 blocked 行为
- 出口：F0 从零安装可跑（`install.py` → `wf.py status`）；两次打包字节一致

## P5 夹具与验收

- [ ] F0/F1/F2 建夹具并记录初态/触发/预期/实际/归因
- [ ] V1 宿主身份、V2 归档中断恢复、V3 维护组共存、V4 审查链路、V5 调试计数与复盘
- [ ] 三夹具专属场景：F0 自举/Git 就绪、F1 extracted、F2 共存/Trellis 二分支
- [ ] 实现稿 §7.1 按实际结果更新（属实现稿变更 → 重绑 sha256 + 交人复审）

## 回滚点

- P1 失败：只删 `/tmp` 夹具与源树新文件，不改上位。
- P2–P5 失败：先修实现；若证据表明是机制缺失，停止并出「需人裁决」。

## 评审闸门

- 每个阶段结束：三条机检 + 该阶段出口验证结果写入任务记录。
- 代码评审：`trellis-check`（inline，主会话自查）。
