# wf 轮次叙述（2026-11-25 自 README「目标版本」单元迁出）

> 本文件只保存历轮变化的叙述，便于 README 保持"当前版本 + 操作口径"的可读长度。
> 产品规则、命令契约与判定字段仍以 [README](../README.md)、[机制稿](../../wf-framework-mechanism.md)、
> [设计稿](../../wf-framework-design.md) 为准；任务级证据与裁定见 Git 与 `.trellis/tasks/` 记录。
> 追加新轮次时在本文件末尾按时间顺序补一段，不把流水账堆回 README 单元。

本轮内容（dogfood 六~八轮 + 复核轮）：在途审查轮不再被旧结论挤掉——`check_next_hint` 按「轮次＋锚点」判在途，旧 fail/pass 留作历史，不再误导重新 `review-launch`；审查材料 `status.json` 汇总后一次写出，日志问题并入后不再丢 `redacted`/`redaction` 脱敏说明；wf-review 材料指引与实现对齐（`logs[]` 只含通过证据身份核对的日志，不符/缺失改在 `status.json.problems`）；升级帮助示例只引用已打 tag 的发行版本并加机械护栏测试；会话轮换出口修正（暂停不解除在途绑定，移除"暂停后重试"无效出口）；重复调试裁定（debug-ruling）归还主会话授权内——机制保留计数、证据、留痕与归档门禁，诊断语义不再逐倍数人签（机制稿 §1.3/§8.1/§11.2 同步；finish 草稿投影已裁「不同问题」倍数，复核面闭合）；wf-review-action 外发确认口径与 wf-continue 对齐（同任务同材料类持续有效）；**七轮**：轮次材料一经物化即固定（manifest，同轮重入只校验不重写），pass 判定要求全部轮次已知 blocking 已关闭，`check_next_hint` 判据统一走 `latest_decision`，`task-approve --draft` 前移 PRD 结构预检，`review-context` 续写补授权事实；**八轮**：判定侧消费材料身份（drift 拒、采纳记弱身份、不重写 manifest）、Check 下一跳在有 blocking 时不再指向 finish、PRD 摘要单读数（草稿/正式批准/机械修订/replan 同源，**0.1.7 上手写或照旧报错抄的 `object_digest` 需按新草稿重出**）、会话轮换与 `enable` 共用终态判据（记录缺失按 unknown 拒绝并给 status/repair 出口）、`judgments` 的 `kind` 增 `框架改动` 并修 help 指针。

**第四轮独立复审（2026-11-25）**：`task-approve --draft` 输出 `complexity_proposal`（四项条件与提议）与生效 `tdd`，并把两值写进 approve 条目的 `plan` 骨架；正式批准在决定与 inputs 都未给 complexity 时把 `confirmed_source` 记 `proposed` 并给出可见提示（不再冒充 `inputs`）；`review-status` 按「对象终态 / 外部审查是否必需」投影 `entry_gate`，已归档对象不再被劝去 `review-launch`，`review-launch` 对归档对象报终态事实（此前误报「规划批准已失效」）；pass 结果的 `exit` 置 null（与机制稿 §11.1「exit 是失败/待决出口」一致）；草稿在项目配置/请求 TDD 取值非法时只报事实、不阻断骨架；轻量任务不再被给"临时加审查轮"的出口（与 wf-review 同口径）；`.wf/spec/` 顶层`index.md` 与两份 checklist 不再被当作规则加载（出厂模板不再自带 3 条 frontmatter 问题）；`review-context` 首次物化后按真实状态回显 `materials_check`；

**0.0.2**：复杂分级没有人的批准决定承载时，`task-approve` 直接以 `WF_SEMANTIC_DECISION` 拒绝（出口：`--draft` 骨架已预填 `plan.complexity`，或手写决定补该键；请求 inputs 只作提议）；TDD 未写入决定仍按项目默认/发行缺省并给出「未由人确认」提示。

**0.0.3**：复杂分级的人签判据/文案收敛为 `tasks.complex_needs_human_decision()` 单一实现（批准入口与归档门禁共用）；TDD 只由决定 `plan.tdd` 或项目/发行缺省取值，`inputs.tdd` 不再生效（模型不得自行开启 TDD）；轻量任务的外部审查改为可选工具（`wf-review` 与 `review-status` 同口径）；`AGENTS.md` 不再复述版本号，以 README 目标版本行为唯一事实；README 目标版本单元收敛并由 `test_readme_version_cell` 锁上限。

**0.0.4**：TDD 缺省值按 `tdd_source` 记录、不要求额外人签（设计稿 TDD 段同步：要记成人的选择就写 `plan.tdd`）；轻量任务自愿外部审查的后果写全——一轮发起后未关闭 blocking 进归档门禁，fail 须逐条关闭；`task-approve` 帮助的 `plan` 说明与示例不再鼓励照抄 `tdd`。

**0.0.5**：`install.py` 的 tag 校验把 source 相对仓库根的前缀拼入 `git show <commit>:<path>`，发行树位于仓库子目录（作者仓库 `docs/workflows/wf-release/`）时可直接安装/升级；根级候选仓库布局继续可用。新增 `test_install_source_layout` 锁定两种布局。

**0.0.6**：安装命令自带解释器选择与确认——`--python` 缺省系统 `python3`（没有则拒绝安装），安装成功后由同一条命令转交 `confirm-executor`（人输入 yes），`--python` 写入本机用户级配置并按 global 确认；安装/升级 tag 校验支持 source 在仓库子目录（0.0.5 已改，0.0.6 起文档与示例直接使用）。

**0.0.7**：`wf help` 的 48 个命令示例与安装/升级示例统一给取值加引号（单/双均可）；`wf help` 无参输出增 `quoting` 约定；`session-flow` 运行约定第 7 条把「命令取值一律加引号」写成唯一论述位，skills 以指针继承；测试的示例解析改用 `shlex.split` 与 shell 语义一致。

**0.0.8**：wf 改为系统级命令分发——`docs/workflows/wf-cli/` 以登记 Forgejo 发行 tag 安装为 `wf`，`wf install` 按命令自身版本、`wf upgrade` 取默认分支按 tag 创建时间最新的发行，`wf uninstall`/`wf repair` 转交已安装独立入口，运行期命令由 `wf` 定位并转交 `.wf/bin/wf.py`；用户面移除 `--release`/`--release-ref`/`--source`，发行安装器自定位发行根并按清单版本推导 tag，项目内 `wf.py upgrade` 只给系统命令出口。系统命令安装改为无版本 bootstrap（取 Forgejo 最新正式 release 的稳定 `install.py` 附件，再由它取同一 release 的 `wf_cli-<version>-py3-none-any.whl`），新增 `wf self-upgrade` 升级系统命令本身（与项目 `wf upgrade` 分离），release 必须保存该 wheel 附件。
