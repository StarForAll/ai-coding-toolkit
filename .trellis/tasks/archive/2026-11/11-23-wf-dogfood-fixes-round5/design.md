# 设计：wf 五轮修正

## 0. 总纲：判据句落地映射

| 判据句归类 | 本轮项 | 落点 |
|---|---|---|
| 可计算且同一结论 → 机制 | 路径身份（W1）、hooks.json 条目（W3）、tag↔树↔清单（W4）、旗标消费与"可选"声明（W2） | 代码 + 断言 |
| 可计算但只提供事实/出口 → 机制产出事实，判断留 AI | 多副本歧义的出口文案、升级预览的 hooks 动作、verify 失败逐项事实 | facts/exits |
| 需理解语境 → 指引 | 帮助措辞、采纳建议、回源归属、同轮报告能否重述 | skill/文档，不改机制 |
| 改变授权/承诺 → 人 | tag 创建与推送、真升级实跑、同轮重述的重新裁决 | 人执行/待裁 |

不新增 skill、不新增层级、不新增机制概念（不引入"条件锚点""第二套判定"）。

## 1. W1 人面路径身份

### 问题（已核验）
`three_way_plan` 内部键是 `(base, rel)`（`install.py:1349-1357`），但人面处置与小面输出统一退化为
`rel`（`:1358-1359` 及四处 `rel in keep_rels`；预览 `:1740-1764`；导出 `:1583-1591`；
安装记录 decisions `:1895-1900`）。`claudecode` 是唯一 `reads_shared=False` 的平台
（`:710-742`），因此 claudecode + 任一共享平台即产生"两副本同 rel"。

### 契约
1. **唯一路径 token = 项目相对路径**（POSIX 分隔）。由 `base` 与 `rel` 派生：
   `_asset_token(target, base, rel)`；`base` 在目标内时输出 `relpath(base,target)+"/"+rel`，
   否则输出绝对路径（`registered_root_problems` 已拒绝域外根，此分支只作兜底且不可匹配）。
2. `--keep/--restore` 的取值只接受上述 token：先把计划里所有待决项建成
   `token → (base, rel)` 映射，再按 token 查找。找不到 → 现有
   `WF_USAGE_INVALID`（keep/restore 无对应待决冲突），`exits` 列出可用 token。
   **不保留 `rel` 旧形态别名**：该旗标自 0.1.5 交付起从未在字段上被真实使用（`git tag -l`
   无对应 tag，无 dogfood 实跑），双口径正是本轮要消除的缺陷。
3. 语义不变：`keep` = 保留本地退出托管；`restore` = 写发行内容并恢复托管；
   `required` 资产保留删除仍在写入前 `WF_SEMANTIC_DECISION`。
4. 输出面同批：预览 `selected_paths`、`risks`、`unresolved[].path`（新增 token 字段，
   原 `relative` 保留为内部事实）、导出 `deviations[].target_path` 与
   `not_exported[].target_path`（取代 `path`）、安装记录 `decisions[].path` + `root_ref`。
5. `wf help upgrade` 的 `--keep/--restore` 文案改为"项目相对路径（`<根>/<资产相对路径>`）"。

### 兼容与回退
- 安装记录 schema 只增字段（`root_ref`）不改语义；旧记录缺 `root_ref` 时按 `target` 反查
  `assets[].root_ref`，查不到才用 `project`。
- 若发现未列入计划的新冲突，行为与现状一致（`WF_ASSET_DECISION`）。

## 2. W2 帮助声明与实现一致

### 问题（已核验）
- `task-retrospect`：帮助 `--evidence` 可选 / `--decision` 必填；handler 反着要求；
  `--commit` 从未被读取。
- `task-knowledge`：`--evidence` 从未被读取（`knowledge.evidence` 恒 `[]`）。
- `test_help_domains.py` 的 `RegistryCompletenessTest` 对 `_task_command` 委托型命令
  取不到源码（闭包只含字符串 `name`），断言对 20 余命令为空跑。

### 契约
1. 帮助与行为对齐：`task-retrospect` 的 `--evidence` 标必填、`--decision` 标可选（保留
   `--decision` 作为可选结论文件的既有消费路径）。
2. 幽灵旗标**删除**而非改用：`--commit`（task-retrospect）、`--evidence`
   （task-knowledge）从 `COMMAND_HELP.args`、`COMMAND_FLAGS` 同批移除；记录字段
   `knowledge.evidence` 保留（schema 兼容），值为 `[]` 不变。
3. 委托型命令可自省：`_task_command`/`_runs_command` 生成的 handler 带
   `__wf_target__ = "<module>:<func>"`；测试据此 `inspect.getsource` 真实实现。
4. 两个断言（`scripts/tests/wf_runtime/`）：
   - **消费断言**：帮助里登记的每个旗标，必须被该命令的真实实现读取
     （`args.value/flag` 静态提取；动态名走 allowlist 并写明理由）。
   - **声明断言（行为）**：以帮助 `example` 为基准，逐条删除旗标后 dispatch：
     ① 文本以"可选"开头的旗标被删 ⇒ 结果不得是"点名该旗标的 `WF_USAGE_INVALID`"；
     ② 文本以"必填"开头的旗标被删 ⇒ 结果不得是 `WF_OK`。
     条件式必填（"record 必填"/"pause："等）不在 ① ② 的自动声明集内，由目标断言覆盖。
5. 不引入"必填声明表"这种新结构：帮助措辞仍是人读的唯一形态，断言从行为侧对照。

### 风险
例子里可能有副作用路径（`--out /tmp/...`）：测试把 `/tmp` 前缀的 `--out` 改写为临时目录，
并在临时项目根内 dispatch。`upgrade` 的 example 指向不存在路径 ⇒ 只验证"不是 WF_OK"。

## 3. W3 升级维护 hooks.json

### 问题（已核验）
`merge_hooks_json` 只在首装（`install.py:2217`）与 `add_platforms`（`:1066`）调用；
`run_upgrade` 的 apply 段与 `self_check` 都不碰 hooks.json ⇒ 改 hook 落点/命令串的发行
会把已升级项目留在失效条目上，自检仍绿（退化方向＝会话身份错配）。

### 契约
1. 唯一实现：升级复用 `merge_hooks_json` 的所有权判定（命令串引用本脚本文件名），
   为它加"上一版命令串"入参：
   `sync_hooks_json(target, script_relative, command, previous_command=None)` →
   `{action: created|unchanged|appended|updated|conflict, entry, previous_command}`。
   - 无条目 → `appended`（等价于首装合并）；
   - 有条目且命令串 == 当前 → `unchanged`；
   - 有条目且命令串 == `previous_command` → `updated`（我们的旧条目，替换命令串）；
   - 有条目且命令串既非当前也非上一版 → `conflict`（用户改过）⇒ 升级
     `WF_ASSET_DECISION`，不覆盖、不擅自"修好"。
2. `previous_command` 来源：安装记录顶层 `host_hook_entries`
   （`[{platform, script_relative, command, updated_at}]`），首装与 `add_platforms` 写入；
   升级在应用段读旧值、写新值；旧安装记录无该字段 ⇒ `previous_command=None`，
   此时条目命令串不等于当前即 `conflict`（交人），不靠猜。
3. `self_check` 增条目核对：清单声明平台内 `host_hook` 已投放 ⇒ `.codex/hooks.json`
   存在且有条目命令串引用该脚本名并等于当前命令串；否则 problem
   `{"target": .../.codex/hooks.json, "reason": "host hook entry missing|command drift"}`。
4. 升级预览增 `hooks_json` 段：`{path, action, previous_command, command}`；`--apply`
   后按同一函数执行并在 facts 报动作。`.codex/hooks.json` 不是发行资产、不进 `selected_paths`
   （它不是托管路径），但写入属维护变更，需按 §4.4 维护变更持久化登记（相对路径
   `.codex/hooks.json`）。
5. 对称性不变：`uninstall.py` 的 `remove_hooks_json_entry` 不动。

### 兼容
- 已装项目缺 `host_hook_entries`：不阻断升级，按第 2 条交人；升级后补登当前值。
- 非 codex 平台或无 host_hook 资产：整段跳过（不读不写 hooks.json）。

## 4. W4 发行身份机械闭环

### 问题（已核验）
`git tag -l` 仅 `wf-v0.1.0`；`build-wf-release.py:77-84` 只"已存在则拒绝重建"；
`install.py:24 REF_RE` + `rev-parse` 使无 tag 即不可安装/升级；README 却记载
0.1.5→0.1.6 可用 upgrade 升级 ⇒ 文档承诺的通道在字段上不可执行。

### 契约
1. `scripts/verify-wf-release.py`（仅标准库、authoring 侧、不进发行清单）：
   `--version X.Y.Z --ref refs/tags/wf-vX.Y.Z [--json]`，逐项核对并输出
   `checks: [{name, ok, facts, exits}]`，任一不过 ⇒ 非零退出：
   - `tag_exists`：`git rev-parse --verify <ref>^{commit}` 成功且 `git tag -l` 含该 ref；
   - `release_tree_matches_source`：`build-wf-release.py --version X --verify` 通过
     （源码 → 临时重建 == 工作树发行树）；
   - `tag_tree_matches_worktree`：tag 提交内 `docs/workflows/wf-release/**` 的 blob 与
     工作树同路径字节逐一相同（`git cat-file blob`）；
   - `manifest_version`：tag 提交内 `wf-release.json.version == X`；
   - `readme_version`：tag 提交内 `docs/workflows/wf/README.md` 的目标版本 == X；
   - `rules_digest`：按 `wf_release_common` 同一算法重算并与清单声明值相同。
   脚本**不创建、不修改、不删除 tag**，只报事实与出口。
2. 预推送守卫：`scripts/git-hooks/pre-push` 对每条目标为 `refs/tags/wf-v*` 的推送运行上述
   脚本；失败 ⇒ 拒绝该次推送并打印失败项。普通分支推送、提交后尚未打 tag 的推送不受影响
   （只匹配 tag 推送行）。
3. README 版本义务诚实化：`§1`/`§3` 明确"已发行 tag 仅 `wf-v0.1.0`；0.1.1–0.1.6 是未打 tag
   的开发版，不能作为升级目标或来源"；升级只能自**已打 tag** 的版本起；发行收口步骤里
   "建 tag"后跟一句"用 `scripts/verify-wf-release.py` 复核，不通过则该 tag 不是有效发行"。
4. 版本升 `0.1.7`：README「目标版本」+ `build-wf-release.py --version 0.1.7`；发行树重建、
   `--verify` 与 `--verify-token-parity` 绿。**tag 由人创建**（本轮不建、不推）。

### 回退
脚本与钩子都是 authoring 侧只读工具：删掉不影响目标项目运行时；版本号回退需重建发行树。

## 5. W5 §1.1 与部署表声明

- `wf-framework-design.md:58`：三方升级匹配的"未交付期间该条为登记缺口"括注删除，
  改为"已交付（0.1.5/0.1.6 升级通道）"。
- `:44` 人签封闭清单补"机械修订的等价性签认（`task-approve` choice=机械修订）"。
- `:44`"机制侧只提供它需要的事实（`facts`/`next`）"→"（`facts`/`next`/`exits` 与
  `--draft` 骨架）"，并补一句"两者仍是机制产物，不构成新层级"。
- `install.py` 部署表注释：`env:` 前缀只表示该值在适配层/显式信封可见；未交付适配层的
  宿主运行期等同 `unknown`（可区分性由 `enable --new-session` 覆盖）。
- 同批：`wf-framework-design.index.md` 反扫；`scripts/validate-wf-design.py` 绿；
  `check-doc-refs.py` 绿。

## 6. 验证设计

| 层 | 命令 | 覆盖 |
|---|---|---|
| T0 定向 | `python3 -m unittest scripts.tests.wf_runtime.test_w1_upgrade_path_identity scripts.tests.wf_runtime.test_w3_hooks_sync scripts.tests.wf_runtime.test_help_contract scripts.tests.test_verify_wf_release` | 新增断言 |
| T1 既有 | `test_w4_upgrade.py`、`test_help_domains.py`、`test_decision_domains.py`、`wf_identity/*`、`wf_review/*` | 不回退 |
| T2 全量 | `scripts/tests/wf_runtime/full/run_all.sh --full` | 全链 |
| 发行 | `build-wf-release.py --verify --verify-token-parity`、`validate-wf-design.py`、`check-doc-refs.py`、`validate-skills.sh` | 发行树/上位稿一致 |

回退注入（每项至少一次）：W1 把 token 改回 `rel` ⇒ 多副本断言变红；W2 恢复 `--commit`
⇒ 消费断言变红；W3 去掉 `previous_command` 分支 ⇒ 漂移断言变红；W4 用假 tag ⇒
`tag_exists`/`tag_tree_matches_worktree` 变红。

## 7. 交付顺序与回滚点

1. W2（最小、独立）→ 2. W1（install.py 面）→ 3. W3（install.py 面，依赖 W1 的路径输出）
→ 4. W4（scripts 面 + 版本）→ 5. W5（文档 + 索引）→ 6. 发行树重建与全量验证。
每步可单独回滚：W1/W3 只碰 `install.py` 与安装记录字段；W2 只碰 help/注册表/测试；
W4 只碰 `scripts/**` 与 README；W5 只碰上位稿与索引。