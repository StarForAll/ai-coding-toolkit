# 执行计划：wf 五轮修正

顺序按"最小独立 → 组合面"。每步末尾都给验证命令；未过不进下一步。
提交收尾（Phase 3.4 / finish-work）与 tag 创建只在用户同意后执行。

## S1 W2 帮助声明与实现一致（独立，先做）

1. `payload/lib/wflib/cli.py`
   - `COMMAND_HELP["task-retrospect"].args`：`--evidence` 改"必填：复盘证据文件"；
     `--decision` 改"可选：结论文件（给了就并入库）"；删 `--commit`。
   - `COMMAND_HELP["task-knowledge"].args`：删 `--evidence`；`--changes` 文案补一句
     "（字段为 action/path/reason/summary；与 `spec-update --changes` 形状不同）"。
   - `COMMAND_HELP["spec-update"].args["--changes"]` 补镜像提示。
   - `COMMAND_FLAGS`：同步删 `task-retrospect --commit`、`task-knowledge --evidence`。
   - `_task_command` / `_runs_command`：给 handler 加 `__wf_target__ = "<module>:<func>"`。
2. 新增 `scripts/tests/wf_runtime/test_help_contract.py`
   - `ConsumptionTest`：帮助登记的每个旗标必须被真实实现读取（动态旗标 allowlist 写明理由）。
   - `ClaimTest`：`example` 基线逐旗标删除后 dispatch；"可选"删除不得出现点名该旗标的
     `WF_USAGE_INVALID`；"必填"删除不得 `WF_OK`。
   - 临时项目根 + `--out` 重写临时目录；断言不写真实 /tmp。
3. 修 `test_help_domains.py::RegistryCompletenessTest`：改用 `__wf_target__` 解析真实源码，
   回退注入一次确认变红。
4. 验证：`python3 -m unittest scripts.tests.wf_runtime.test_help_contract scripts.tests.wf_runtime.test_help_domains -v`

## S2 W1 人面路径身份（install.py）

1. `payload/install.py`
   - 新增 `_asset_token(target, base, rel)`。
   - `three_way_plan`：所有 `unresolved/unmanaged/deletes/actions` 条目增 `path`（token）；
     `keep_rels/restore_rels` 改为 token 集合；四处匹配改按 `key=(base,rel)` 反查。
   - `run_upgrade`：`selected`/`before_states`/`risks`/`unknown_keep|restore` 全部用 token；
     未匹配时的 `exits` 列出可用 token。
   - `export_deviations`：`deviations[]`/`not_exported[]` 用 `target_path`（取代 `path`）。
   - 安装记录 `decisions[]`：写 `path`(token) + `root_ref`。
   - `COMMAND_HELP`（`lib/wflib/cli.py` 的 upgrade 条目）与 `install.py` argparse help：
     `--keep/--restore` 文案改"项目相对路径"。
2. 新增 `scripts/tests/wf_runtime/test_w1_upgrade_path_identity.py`
   - 两副本（`.agents/skills` + `.claude/skills`）同 rel 各自偏离 ⇒ 只给一个 token 时
     另一副本仍按三方结果处理；只给 `rel` 形态 ⇒ `WF_USAGE_INVALID` + exits 含 token。
   - 导出清单含 `target_path`；`decisions` 含 `root_ref`。
3. 验证：`python3 -m unittest scripts.tests.wf_runtime.test_w1_upgrade_path_identity scripts.tests.wf_runtime.test_w4_upgrade -v`

## S3 W3 升级维护 hooks.json

1. `payload/install.py`
   - 抽出唯一实现 `sync_hooks_json(target, script_relative, command, previous_command=None)`；
     `merge_hooks_json` 转为调用它（首装/add_platforms 路径不改语义）。
   - 首装（`:2217`）与 `add_platforms`（`:1066`）写安装记录 `host_hook_entries`。
   - `run_upgrade` 应用段：对每个已投放 host_hook 资产执行 sync；`conflict` ⇒
     `WF_ASSET_DECISION`（含 hooks.json 路径、旧命令串、当前命令串、出口）；
     `appended|updated` ⇒ 进 `changes` 与维护变更登记（`.codex/hooks.json`）。
   - 预览增 `hooks_json` 段（路径/动作/旧值/当前值）。
   - `self_check` 增条目核对（缺失/漂移进 problems）。
2. 新增 `scripts/tests/wf_runtime/test_w3_hooks_sync.py`
   - 无条目 ⇒ appended；当前值 ⇒ unchanged；旧值 ⇒ updated 且记录换新；
     用户改过 ⇒ conflict/`WF_ASSET_DECISION` 且文件未变；self_check 对缺失/漂移报 problem；
     `--platform dsh` 项目不读不写 hooks.json；卸载对称移除不回退。
3. 验证：`python3 -m unittest scripts.tests.wf_runtime.test_w3_hooks_sync scripts.tests.wf_runtime.test_w4_upgrade scripts.tests.wf_runtime.test_asset_boundaries -v`

## S4 W4 发行身份机械闭环

1. 新增 `scripts/verify-wf-release.py`（六项 check，见 design §4；只读）。
2. `scripts/git-hooks/pre-push`：对 `refs/tags/wf-v*` 推送行调用该脚本，失败即拒。
3. `payload/../README.md`（`docs/workflows/wf/README.md`）：
   - 「目标版本」→ `0.1.7`；§3 版本义务补机械核对句；§1 升级通道改成
     "已打 tag 的版本"事实 + 现有 tag 清单（仅 `wf-v0.1.0`）；§5 收口步骤补
     `verify-wf-release.py`。
4. 新增 `scripts/tests/test_verify_wf_release.py`：假 tag / 树不一致 / 版本不一致 /
   README 不一致逐项红；合规模拟通过；pre-push 只对 tag 行生效（用桩 git 调用）。
5. 验证：`python3 -m unittest scripts.tests.test_verify_wf_release -v`；
   `python3 scripts/verify-wf-release.py --version 0.1.7 --ref refs/tags/wf-v0.1.7`
   在未建 tag 时给"tag 缺失 + 出口"（预期失败输出，作为负例留档）。

## S5 W5 §1.1 与部署表声明

1. `docs/workflows/wf-framework-design.md` §1.1 四处（design §5 逐条）。
2. `payload/install.py` PLATFORMS 注释补"env: 声明 ≠ 已实现"句。
3. `docs/workflows/wf-framework-design.index.md` 反扫；必要时同步
   `wf-framework-implementation.md` 的登记段（W1/W3 新字段与入口）。
4. 验证：`python3 scripts/validate-wf-design.py`、`python3 scripts/check-doc-refs.py`。

## S6 发行与收口

1. `python3 scripts/build-wf-release.py --version 0.1.7`（重建发行树）。
2. `python3 scripts/build-wf-release.py --verify --verify-token-parity`。
3. `python3 -m unittest discover -s scripts/tests -t . -v`（T0/T1）；
   `bash scripts/tests/wf_runtime/full/run_all.sh --full`（T2）。
4. `./scripts/validate-skills.sh`。
5. `git status` / `git diff` 复核：只含本任务授权路径；`.wf/` 运行态未入库。
6. **停在这里报结果**：提交、tag 创建、finish-work 归档均等用户同意。
7. 用户同意后：按精确路径暂存提交 → 人建 `wf-v0.1.7` tag → `verify-wf-release.py` 复核 →
   `finish-work` 归档并在 `analysis/` 留 W6 证据与默认裁决。

## 检查闸门（每步末）

- 新增断言必须能"回退注入变红"；只写绿不写红的断言视为未完成。
- 不改已发行原因码语义；不新增 skill；不在升级路径另写第二套 hooks.json 判定。
- 每步结束复核 `git diff --stat`，确认没有越界文件（尤其 `.trellis/tasks/**` 与运行态）。

## 执行实况（2026-11-23，收尾前记录）

| 步骤 | 结果 |
|---|---|
| S1 W2 帮助/实现一致 | 完成。`task-retrospect` 必填对齐；删 2+5 个幽灵旗标；`__wf_target__`/`__wf_target_map__` + `command_introspection` 让 20 余委托命令的断言真实生效并加覆盖下限；新增 `test_help_contract.py`（7 断言，含两条回归注入）。顺带：删掉只被测试引用的 `merge_hooks_json` 与 `HOOK_COMMAND`（升级/首装/追加平台共用 `plan_hooks_json`+`apply_hooks_json`），对应断言改锚真实路径 |
| S2 W1 路径身份 | 完成。`_asset_token` + 全链 token 化（匹配/预览/导出/留痕/帮助）。新增 `test_w1_upgrade_path_identity.py`（11 断言）。破坏性口径已在 README 与台账写明 |
| S3 W3 hooks.json | 完成。`plan_hooks_json`/`apply_hooks_json`/`host_hook_command` + 安装记录 `host_hook_entries` + 写入前拒冲突 + `self_check` 核条目。新增 `test_w3_hooks_sync.py`（17 断言）；`test_w3_session_identity` 的两条断言改锚新路径 |
| S4 W4 tag 闭环 | 完成。`scripts/verify-wf-release.py`（六项只读核对）+ pre-push 仅对 `refs/tags/wf-v*` 守卫 + README 版本义务/现有 tag 事实 + 版本 0.1.7。新增 `test_verify_wf_release.py`（15 断言） |
| S5 W5 §1.1 与声明 | 完成。§1.1 四处（陈旧交付状态、人签清单、facts 措辞、部署表 `env:` 口径）；机制稿登记 `host_hook_entries` 与本次修订；索引反扫 +1 行；设计稿/索引输入摘要刷新 |
| S6 发行与收口 | 发行树 0.1.7 重建（74 资产）并 `--verify --verify-token-parity` 绿；`validate-wf-design.py`（100%/100%，92/92，14/14，4/4）、`check-doc-refs.py`、`validate-skills.sh` 绿；`wf_runtime` 单元 1074 例仅存量红（干净 worktree 复核同红）；全量 runner 149 单元 148 绿 + 1 处存量红（`r89_tests`，见台账 §5） |

**待用户决定的收尾动作**：按精确路径暂存提交（本任务全部改动）、人创建并推送
`wf-v0.1.7` tag（随后 `verify-wf-release.py` 复核）、`/trellis-finish-work` 归档。

## 第二份审查输入（同日）的追加处置

- **P1 半安装态**：hooks.json 判定从"写资产之后"移到**任何写入之前**；写入后才可能失败的三处
  （投放写冲突 / hooks 落地失败 / 维护应用失败）统一走 `maintenance_abort`（recovering 检查点 +
  代次递增 + 两个出口，不留 `held`）；`add_platforms` 的幂等条件并入"待落地 hook 动作"，
  使"安装后 hooks.json 丢条目"可用重跑同一条安装命令补齐。回归 `HalfInstallStateTest`（3 断言）
  + 回退注入（判定挪回写后 ⇒ `.wf/` 已建 / 资产已写 / writer=held 全部现形）。
- **README tag 口径**：0.1.6→0.1.7 句加"前提：人已建 tag"；§3 补"忘记打 tag 也有提醒"。
- **pre-push 忘记打 tag 提醒**：改动发行树且清单版本无对应 `wf-v*` tag ⇒ 非阻断 WARN + 两条修复命令。
- **机制稿 §0.1 顺序**：五轮句移到四轮句之后（同日先四轮提交）。
- **b-P1（dev-deploy 形态走 upgrade 未端到端实跑）**：机制不矛盾，登记为下一轮 dogfood 必测项，
  本轮不宣称已实跑。

## 第五份审查输入（同日）的追加处置

- **a-1 幽灵旗标复发**：删 `task-retrospect --decision`（帮助/注册表/handler/技能命令行）；新增
  `DeadValueTest`（命令实现内"赋值后从未使用"扫描）并清掉 4 处同类死值。
- **b-1 预览内容绑定**：锁内重核改为逐路径动作 + 三端摘要指纹；行为测试 + 回退注入均通过。
- **b-2 首装中断接续**：路由改按安装记录判定；重试沿用既有 writer（代次/修订递增、回执追加）。
- **b-3 manual 开工验证**：不执行、只记 `human_required`；人判证据仍由 Check 强制；机制稿同批登记。
- **b-4 hook 事件**：`plan_hooks_json` 增 `event`（默认 `SessionStart`），错位即 `conflict`；自检同判。
- a-2（指引测试锁措辞）：确认为刻意取舍，只在测试头注明适用范围。

## 第六份审查输入（同日）的追加处置

- **a-1 首装重入越过持有边界**：新增 `_first_install_takeover()`——只接管"无持有者"或
  "本框架安装维护检查点"；会话持有/交接态/其它维护阶段一律 `WF_WRITER_BUSY` 且原样保留 writer。
  回归 4 条 + 回退注入（去掉守卫 ⇒ 3 条同时红）。
- **a-2 开工验证失败输出未脱敏**：改走 `check.redact_text`（同一实现）；改前实测带出明文
  `Bearer …`，改后为 `***`。回归 1 条。
- **b 的口径张力**：设计稿 §1.1「随 0.1.5/0.1.6 发行」→「随 0.1.5/0.1.6 的源码树交付」并点明
  0.1.1–0.1.6 未打 tag；机制稿修订说明与设计稿输入摘要同批更新。

## 第七份审查输入（同日）的追加处置

- **a-1 长凭据泄露**：`redact_text` 增 `_value_extent()`（窗口覆盖整个值而非固定半宽）；
  `_run_start_verifications` 改为"先遮罩、后截断"。回归 `LongCredentialMaskTest`。
- **a-2 并发安装覆盖**：首装锁内第一步重判安装记录，存在即释放锁并交回 `add_platforms`
  （不重建安装身份、不覆盖平台/根）。回归 `ConcurrentInstallTest` + 回退注入。
- **b-P1/P2 维持**（摘要锁待人裁；tag 待建、dev-deploy 升级待实测）。
- **b-P3 登记为下一轮测量项**（安装/升级的实际轮次与重试次数），本轮不做为凑减法的结构删减。

## 第八份审查输入（同日）的追加处置

- **b-1 键名后缀 / URL userinfo**：新增 `_value_start()`（跳过键名剩余与收尾引号，按分隔符取值）；
  新增 `STANDALONE_PATTERNS`（URL userinfo 无触发词，全文线性一遍，只遮 password 保留 user/host）；
  无触发词文本也跑独立规则。
- **b-2 自检失败恢复链**：幂等分支现在跑同一 `self_check` 并把结论摆进 facts/输出
  （`clean|problems` + 逐条问题）；仍按"无变化"返回、不取写权（硬阻断版被 `r83_tests` 的幂等用例
  证明会误伤合成夹具）。
- **b-3 重复扫描平方**：已落在当前窗口内的触发词跳过，1MB 对抗输入 0.13s（旧行为 100KB 即 43s）。
- **批次纪律**：`.trellis/spec/docs/wf-delivery-discipline.md` §8 增第 5 条——安全路径改动同批必须
  带对抗性用例（超长值/前缀切断/引号跨行/键名变体/无关键词形态/成本上界）。

## 第九份审查输入（同日）的追加处置

- **脱敏按协议一次性规格化**：删除窗口机制（`TRIGGER`/`MASK_WINDOW`/`_value_extent`/`_value_start`/
  `_standalone_masked`），改为有序规则表 + 字面预筛；覆盖引号值、厂商令牌、PEM、URL userinfo、
  中文键名。256KB 最坏 31ms（旧窗口实现 1.3s；旧实现 100KB 对抗 43s）。
- **审查材料脱敏**（`diff.patch`/`prd.md` + `status.json.redacted`），`wf-review` 同步告知。
- **卸载只摘本脚本成员**；**hook 判定纳入 matcher**。
- **`wf-continue` 证据纪律改按"谁生成"分类**（不再用会漏项的"五类白名单"）。
- **发行核对提示** `git tag wf-v0.1.7`（此前多一层 `refs/tags/`）。
- **§1.1 人签清单补**手工验证结论与工作流 `human_points`，并写明机械修订的前提与边界。
- **证据边界**：本轮只证明机制与指引落点；"AI 是否真的不再反复提醒/换轮"需下一轮新版会话实测。

## 第十份审查输入（同日）的追加处置

- **脱敏回归（a-P0）**：规则顺序（具体形态先）、值不得以 `=`/`:` 起始、`_QUOTED` 整体分组、
  预筛不掺空白形态；新增**性质矩阵**测试（形态×分隔符×长度×引号）。
- **遮罩分两级**：`redact_text`（日志/回显，全量）与 `redact_material`（材料，只遮字面凭据，
  保持代码可审）；调用不被误遮。
- **材料日志**：先核身份再物化（未引用/失配的不进材料包，只进 problems）。
- **人签绑定**：手工验证决定加 `content_digest`（`status` 暴露 `delivery.content_digest`）；
  机械修订核对 `object_digest` 与当前 PRD 摘要。
- **审查绑定**：同锚点不同 Check id 不再判 `WF_REVIEW_INVALID`。
- **净减**：删除窗口机制与 4 个辅助函数；256KB 遮罩 31ms（原 1.3s）。
- **验证口径**：run 目录要按 runner-control 的 run_id 取（字典序会读到旧 run）；全量套件用已提交的
  harness，改 harness 需提交后才生效——本轮据此修正了 cp1/cp2/r7r15 三处夹具与 `units.json` 期望数。

## 第十一份审查输入（同日）的追加处置

- **材料遮罩接线**：`write_materials` 改用 `redact_material`；材料值域改为「引号值或不含`.`/括号/下标的裸串」，
  `.env` 字面量遮、调用/属性保留；加接线断言与矩阵用例。
- **直接人判验收**：无 `verification_ids` 的验收项同样核 `content_digest`。
- **材料命令记录脱敏** + **重生成材料时清空旧日志副本**。
- **审查绑定读真实嵌套锚点**（`check.anchor.check_anchor`），夹具改真实形状。
- **纯人判验收不再被"commands 空"拒**；第一版实现因同名变量遮蔽导致 `unknown verification_id`
  使模板夹具与运行器整轮失败，已修正并写进注释。

## 第十二份审查输入（同日）的追加处置

- **材料级判据重定**：字面量 = 引号值，或"含数字、无调用/下标语法、长度≥4"的裸串；中文键与
  `Bearer =`/`Basic =` 赋值同口径（各补 `_LITERAL`+`code_safe` 一条，全量档保留 `_VALUE`）。
- **矩阵派生**：材料档断言不再手挑子集，改按形态与规则档位派生，白名单显式（仅调用/常量引用）。
- **材料一次性写脱敏结果**：新增 `redact_object()`；`tests.json` 不再"先写原文后覆写"。
- **轮次身份/下一跳锚点感知**：同锚点重跑 Check 不再要求重开一轮（身份核验 + `check_next_hint`）。
- **空命令判据**：按必须执行的验证项（required 或被引用）计算，可选验证项缺失不阻断。
- **诊断字段**：`check_id_changed` 阻断事实里的 `current_check_anchor` 改读嵌套锚点。

## 第十三份审查输入（同日）的追加处置

- **tests.json 只写一次**：删掉原文首写（回归用 write_json 监视器断言次数=1 且无明文）。
- **结构化脱敏按字段名**：`redact_object` + `_structured_secret_key`（`{"password": "纯字母"}` 也遮；
  `token_count`/`*_version`/`*_name` 保留）。
- **材料档残余风险登记**：`protocol/redaction.json` 增 `material-literal-heuristic`（纯字母无数字裸值
  不遮），边界测试固定两档行为。
- **材料范围校验 / Check 下一跳锚点感知**：同锚点重验不再要求重开一轮；`check_next_hint` 先问
  `gates.review_binding`，摘要失配时改说"重新导入或换一轮"。
- **断言卫生扫描**：新增 `test_assertion_hygiene.py`（AST 查恒真断言，扫描器自带反例测试），
  修掉上一轮派生矩阵里的空转断言与死条目。

## 第十四份审查输入（同日）的追加处置

- **材料遮罩按文件分片**：`redact_patch` 按 `diff --git` 选档（配置类全量 / 代码类字面量），
  PRD 走全量，`status.json.redaction` 写明策略；新增 `is_config_path`/`redact_for_path`。
- **默认请求带 `check_anchor`**（同锚点复用在真实路径闭环）。
- **开工验证超时**：抽出 `check.verification_timeout`（Check 与开工验证共用），
  `TimeoutExpired` 归 `WF_CHECK_FAILED` + `timed out after Ns`。
- **恒真断言扫描扩到整个 `scripts/tests/`**（含发行链/构建链与 `wf_review/`）。
- **删掉 `_VALUE` 重复定义**。

## 第十五份审查输入（同日）的追加处置

- **命令记录 argv 语义**：新增 `redact_commands()`（argv 位置语义 + 其余字段全量），`tests.json` 改用它。
- **开工验证不再吞配置错误**：非法 `verification_timeout_seconds` 按 `WF_RECORD_INVALID` 抛出且不执行命令。
- **材料日志**：每次生成前无条件清空 `materials/check-logs/`（源目录缺失也清）。
- **协议登记**：`material-literal-heuristic` 增 `surfaces` 表（diff per-file / prd full / tests argv-aware+full）
  并改写 `residual_risk` 为"仅代码类文件的纯字母裸值"。

## 2026-11-23 人裁：安装不再区分平台（一次装齐全部支持平台）

- **单一来源**：`PLATFORMS` 表即"装哪些平台"，`all_platforms()`/`resolve_skill_roots(target)`
  覆盖全部；新增平台只改表，重跑安装/升级即补齐。`--platform` 从 install/升级/开发态部署三处移除，
  `PLATFORM_ALIASES`/`_flatten_platforms` 随之删除。
- **重复执行同一条安装命令**：`add_platforms`（追加平台）删除 → `verify_installed`：
  缺的落点/hook 条目**只补不改**（取写权、产回执、登记资产、提升 roots/platforms）；
  内容被本地改过 ⇒ 指向上级三方升级；完全一致 ⇒ 只读核对 + 自检，不取写权。
- **升级**：技能根按全部平台规划，写回记录的 roots/platforms 提升为全集。
- **分类**：`installed_asset_paths` 纳入 `host_hook_entries[].hooks_json_path`（hooks.json 恒存在，
  不再每次落进 c 档）。
- **维护回执契约**：补齐回执带 `head_before` + 账本登记；无下界提交（部署早于首个提交）时
  探针按 HEAD 树内容核对，而不是永远 pending。
- **测试**：r89 改写为"无参数即装齐/all-platforms/幂等/漂移不覆盖"；r83 改写为 verify/补齐语义；
  r90 改写为重复部署幂等；删除 5 个 add_platforms 专用 repro（其不变量已由 r83/r90 承接），
  改写 `identity-platform-fact` 与 `reinstall-preserves-data`；`units.json` 期望数同步。

### 收尾验证（本次人裁改动）

- 全量 `run_all.sh`：`run_id=1795445301637…` **144 项 0 失败**（59 套件 + 5 专项 + 80 repro，green 模式）。
- 单测 1798 项：仅余 3 类既有/建档失败——`test_w1_to_w5_and_f1_real_publisher_windows`(6)、
  `test_wfdrive_constants`(2)（均在干净 HEAD 同红）；`test_source_coverage`(5) 属
  **提交后可再生**的候选审计/基线（读 `candidate-audit.json` 的脚本字节与 `coverage-baseline.json`
  的计数），提交后由人/CI 跑一次 `source_coverage.py --baseline-out …` 与候选审计重生成即恢复。

## 第十七份审查（平台改造后复查）的处置

| 编号 | 判定 | 处置 |
|---|---|---|
| a-P0「README/注释仍写"追加平台"」 | **成立** | README 重跑语义改为"补齐/核对、没有追加平台这一步"；`install.py` 三处注释（锁判据、已安装分支、锁内哨兵）与 `wf-dev-deploy.py` 两处注释同步 |
| a-P1「一次装齐零真实安装验证」 | **成立（已做部分）** | 本轮用真实临时 Git 项目跑了 dev-deploy 首装 + 重跑（含陈旧记录刷新）、用 `three_way_plan` 对真实 dev 记录做升级匹配（86 noop / 0 unresolved）；**tag 化发行升级仍需人建 tag 后实测**（登记为下一轮必测） |
| a-P4「dsh 的 `env:` 声明缺"等同 unknown"限定」 | **成立** | 平台表注释补齐：装齐 ≠ 会话标识可用，入口不读该变量，可区分性由 `enable --new-session` 覆盖 |
| b-1「开发态部署漏装 host_hook」 | **成立（实锤：`.codex/hooks*` 从不落地）** | `plan_deployment` 补 `host_hook` 类（与发行安装同类别覆盖），部署段用同一 `plan_host_hooks`/`apply_hooks_json`，记录写 `host_hook_entries`；实测 `.codex/hooks/wf-session-identity.py` 与 `hooks.json` 都生成 |
| b-2「技能副本 target 重复带根 → 升级当成 26 处撞用户文件」 | **成立** | 记录改存**资产相对路径**（根由 `root_ref` 表达，与 `install.py` 同形状）；实测升级匹配 86 noop / 0 unresolved |
| b-3「登记一个 hook 就把整份 hooks.json 当控制记录」 | **成立（我上一轮的过度收口）** | `scope` 新增 `host_hook_shared_paths` + `_hooks_json_is_framework_only`：**只有框架独占**才算控制面，用户加过命令则按普通路径归桶（进交付/审查范围） |
| b-4「重跑结论与运行期状态矛盾；保留偏离被当冲突」 | **成立（两处）** | ① 已接受偏离（`local_fingerprint`）不再算 drift，判据抽成 `accepted_local_digests` 供自检/核对共用；② 记录 `platforms`/`roots` 陈旧时补齐并写回执（含 `installation.json` 的 before/after）；③ 开发态重跑**委托** `install.py::verify_installed`，不再维护第二套实现 |
| b-5「累计失败计数」 | 维持·第九次登记待人裁 | 属 §11.2 既有语义 |
