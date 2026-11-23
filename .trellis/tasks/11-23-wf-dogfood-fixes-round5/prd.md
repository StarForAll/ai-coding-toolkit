# wf 五轮修正——dogfood 报告核验与机制/指引分层收口

## Goal

以质疑角度核验两份 dogfood 分析报告（`/tmp/wf-find-a.md`、`/tmp/wf-find-b.md`）与四份
traffic_monitor 实测会话，**只修经源码核验成立的问题**，并把「能由明确输入稳定计算」的部分
收进机制、其余留在指引——不新增 skill、不新增层级、不以复杂逻辑限定 AI 的自主判断。

核验台账见 `research/verification-ledger.md`：a-1、a-2、b-P0、b-P1 成立；b-P2#1 表述不准确
（实质成立）；b-P2#2 属已声明边界；b-P2#3 驳回；b-P3 成立但只做指引级收口；b 的 F13/F18 与
c/d 多项已被 0.1.5/0.1.6 收口，不得据其重复修。

## 输入与证据边界

- 会话证据：`traffic_monitor_1..4`（会话 2「禁改 `.wf/` 导致整体绕过」、会话 4「8 轮审查、
  两轮上限死路、现场发明 review-restart/reauthorize、材料不含未跟踪文件、摘要锁定、
  「只登记不修复」停点」）。
- 结构证据：`git tag -l`（仅 `wf-v0.1.0`）、`install.py`/`cli.py`/`tasks.py` 具体行号、
  `scripts/tests/wf_runtime/test_help_domains.py` 的覆盖盲区。
- 前轮裁决不得推翻：同轮报告修订（11-21 裁决"导入后不可覆盖"）、单 reviewer 留痕降级、
  control_plane_digest 常开键、K6 submit 通道统一、repo_rules 逐文件确认。

## Requirements

### W1 人面路径身份统一（a-1，机制）

`--keep/--restore`、升级预览、`--export-deviations` 清单、安装记录 decisions 的**人面路径
一律是项目相对路径**（`root_ref` + `target` 复合而来的唯一字符串）；内部仍按 `(base, rel)`
匹配。同名副本因此可分别处置，帮助文案与真实匹配口径一致。

- 匹配口径：`--keep <项目相对路径>` 解析回 `(base, rel)`；无法解析到待决冲突时仍按
  "keep/restore 指定路径没有对应待决冲突"报错（既有出口不变）。
- 多根同时冲突且人只给 `rel` 形态（旧写法）时**不再静默套用到所有副本**：给
  `WF_USAGE_INVALID` + 出口"用 preview 列出的项目相对路径逐项指定"。
- 预览 `selected_paths`、导出 `deviations[].target_path`、安装记录 decisions 记录
  `path` + `root_ref`；导出同时保留 `source_path`（源树相对）。

### W2 帮助声明与实现一致（a-2 + D-1/D-2，机制+断言）

- 修 `task-retrospect`：`--evidence` 标注为必填、`--decision` 标注为可选；按真实消费
  去掉幽灵旗标 `--commit`（handler 从未读取）。
- 修 `task-knowledge`：去掉幽灵旗标 `--evidence`（handler 硬编码 `evidence=[]`），
  保留记录字段 `knowledge.evidence` 供 schema 兼容。
- 让"帮助 ↔ 注册表 ↔ handler 消费"三向断言对**委托型命令**（`_task_command` /
  `_review_command` / `_runs_command`）真实生效（现为空跑）。
- 新增"必填/可选声明与实际用法校验一致"的行为断言：帮助标"必填"的旗标缺省必得
  `WF_USAGE_INVALID`；标"可选"的旗标缺省不得产出点名该旗标的用法错误。

### W3 升级维护 hooks.json（b-P1，机制）

`host_hook` 类资产的部署面包含宿主 `hooks.json` 条目。升级应用后必须与脚本字节同批维护：

- 已投放 codex hook 时，升级后核对 `.codex/hooks.json`：条目缺失 → 补写（幂等）；
  条目命令串等于**上一版登记的命令串** → 视为本框架旧条目，更新为当前命令串并登记；
  命令串引用本脚本文件名但既非当前也非上一版 → `WF_ASSET_DECISION`（用户改过，交人）。
- 上一版命令串写入安装记录（`host_hook_entries`，字段：`script_relative`、`command`、
  `platform`），不依赖猜。
- `self_check` 增条目核对：声明平台内 host_hook 已投放 ⇒ 条目存在且命令串为当前值；
  缺失/漂移按 problem 报出（不再"脚本字节对就绿"）。
- 升级预览列出将发生的 hooks.json 动作（新增/更新/冲突），与资产动作同屏。
- 与既有 `merge_hooks_json`/`remove_hooks_json_entry` 同一实现（不为升级另写一套判定）。

### W4 发行身份机械闭环（b-P0，机制）

- 新增 `scripts/verify-wf-release.py`：给定 `--version X.Y.Z --ref refs/tags/wf-vX.Y.Z`，
  无歧义核对 ① tag 存在且解析到提交；② 该提交内 `docs/workflows/wf-release/**` 与当前
  源码树 `--verify` 字节一致；③ 清单 `version` 与 tag 版本一致；④ README「目标版本」
  一致；⑤ 重算 `rules_digest` 与清单一致。失败逐项报事实与出口（不创建/不改 tag）。
- 仓库预推送钩子对 `refs/tags/wf-v*` 增一道机械守卫：`verify-wf-release.py` 不通过则拒绝
  推送该 tag（只对 tag 推送生效，不影响普通分支推送与"先提交后打 tag"的顺序）。
- README 版本义务诚实化：明确"已发行 tag 仅 `wf-v0.1.0`；0.1.1–0.1.6 是未打 tag 的开发版，
  不作为升级来源"；升级只能自**已打 tag** 的版本起。
- 版本升 `0.1.7`（源树 README 目标版本 + builder `--version`；dev-manifest 维持占位符）；
  发行树重建并 `--verify` 一致。**tag 由人执行**，本轮不建 tag。

### W5 §1.1 与部署表声明诚实化（指引）

- `wf-framework-design.md §1.1`「固定流转程序化」清单：三方升级匹配的交付状态改为"已交付"，
  删除"未交付期间该条为登记缺口"的陈旧括注。
- §1.1 人签封闭清单补"机械修订的等价性签认（`task-approve` choice=机械修订）"。
- §1.1"机制侧只提供它需要的事实（`facts`/`next`）"补 `exits` 令牌表与 `--draft` 骨架
  （两者仍是机制产物，不是新层级）。
- 部署表 `session_identity` 注释补一句：`env:` 前缀只表示该值在适配层/显式信封可见；
  未交付适配层的宿主在运行期等同 `unknown`（可区分性由 `enable --new-session` 覆盖）。
- 索引/机检同步：`wf-framework-design.index.md` 与 `scripts/validate-wf-design.py` 绿。

### W6 需人裁（本任务不自行推进，只登记）

- 同轮报告"判定前可重述"：11-21 已裁维持"导入后不可覆盖"。本轮把 dogfood 第 1→2 轮
  （纯格式修正即被迫整轮重审）的成本证据补进 `analysis/`，**默认维持原裁决**；
  只有人重新裁决才实施。
- 审批决定代笔的防伪强化：§1.5 已声明"不建立验证证据链"，维持；不新增字段。

## Constraints

- 判据句分工：路径身份、必填声明、hooks.json 条目、tag↔树↔清单全部进机制；
  帮助文案措辞、"该不该采纳建议"、"回源归属"仍是 AI/人判断。
- 单实现纪律：不在升级路径另写一套 hooks.json 判定；不复制既有 `--keep/--restore` 语义。
- schema 演进：任务/安装记录只增字段不改语义；旧记录缺字段按既有缺省解释。
- 不新增 skill、不改 skill 数量、不新增机制层级；指引只落既有 skill 判据位。
- 已发行帮助面的取值域与原因码语义只增不改义（`WF_USAGE_INVALID` 用于用法类错误）。
- **提交收尾只在用户同意后执行**；tag 创建与推送同样只在人执行/同意后。

## Acceptance Criteria

- [ ] W1：claudecode + 共享根两副本同 rel，各自独立偏离时 `--keep <项目相对路径>` 只处置
      指定副本；另一副本仍按其三方结果处理（回归断言入库）；旧形态 `rel` 在有多副本冲突时
      被拒并给出口；导出清单含 `target_path`，安装记录 decisions 含 `root_ref`；
      `wf help upgrade` 的路径基准与真实匹配一致。
- [ ] W2：`task-retrospect` 只给 `--task --decision` 可执行且 `--evidence` 标注必填口径一致；
      `--commit`/`task-knowledge --evidence` 不再出现在帮助与注册表；委托型命令的
      "帮助↔注册表↔消费"断言真实覆盖（回退注入变红）；必填/可选行为断言对全部命令生效。
- [ ] W3：升级把旧命令串的 hooks.json 条目更新为当前命令串并登记上一版；条目缺失时补写；
      用户改过的命令串报 `WF_ASSET_DECISION` 不覆盖；`self_check` 对条目缺失/漂移产出 problem；
      预览列出 hooks.json 动作；卸载仍对称移除（既有断言不回退）。
- [ ] W4：`verify-wf-release.py` 对"tag 缺失/树不一致/版本不一致/README 不一致/
      rules_digest 不一致"逐项拒绝并给事实；对合规 tag 通过；pre-push 守卫只在推送
      `refs/tags/wf-v*` 时生效（普通推送不受影响，回退注入变红）；README 的 tag 事实与
      `git tag -l` 一致；发行树 0.1.7 与源树字节复现。
- [ ] W5：`validate-wf-design.py` 绿；索引无悬空；§1.1 四处偏差已改且被新断言覆盖。
- [ ] W6：证据与默认裁决写入 `analysis/`，未实施。
- [ ] 分层验证：定向套件（upgrade/identity/review/help）绿；`run_all --full` 绿；
      `build-wf-release --verify --verify-token-parity` 绿；`check-doc-refs.py`、
      `validate-skills.sh` 绿；最终 diff 复核无授权外路径。

## Out of Scope（防范围漂移）

- 同轮报告修订、审批防伪强化（W6，需人裁）。
- traffic_monitor 目标项目的真实升级操作（下一轮 dogfood 输入）。
- zcode/pi/dsh 会话标识适配层新建（实现稿已声明边界）。
- `task-knowledge` / `spec-update` 的 `--changes` schema 合并（只加双向提示）。
- 帮助/实现一致性中属"条件性必填"的既有复杂分支重构（保留 handler 内判断）。