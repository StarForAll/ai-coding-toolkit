# 本轮验证与门禁记录

执行日期：2026-10-26。作者仓库初始为 clean，分支 main，HEAD=98ee2b7；本轮不提交 / 不收尾。

## 项目规定检查

| 命令 | 本轮观察结果 | 说明 |
|---|---|---|
| `/softwares/python/bin/python3 trellis-library/cli.py validate --strict-warnings` | PASS，rc0 | 5条 stale-related-asset INFO（mtime-only），没有 warning/error；不据此做无关同步 |
| `./scripts/validate-skills.sh` | PASS，rc0 | 31 skills，spec cross-check passed |
| `/softwares/python/bin/python3 -m unittest trellis-library/tests/test_cli.py` | PASS，rc0 | 36 tests，62.289s，OK |
| `git diff --check` | PASS，rc0 | 对最终产品三文件变更运行；任务新文件另逐个检查 |
| 注册表38个 `rg -n` 命令 | 全部执行，数字预期匹配 | rc1在预期0匹配时为正常结果；全文输出见probes.md / evidence/probe-results.json |
| `evidence/replay_chain.py` | 最终run3 PASS | S1–S10 10/10；原生调用 / 扮演机制 / 推演分层见chain-report.md |
| `evidence/verify_revision.py` | PASS，rc0 | 25项限定检查；38文本探针；304格字段推演；§7.4/恢复边界/配套§9不变 |
| 状态 / 矩阵形状核对 | PASS | 转移7行、组合11行、字段矩阵13行，双方转移与组合的形状一致；evidence/structural-checks.json |

上述检查完成后只补任务报告，不改变已验证的产品三文件；未因一般报告更新盲目重跑已完成的链路或项目测试。

## 本轮实际失败与处理

1. 规划阶段一次 `nl ... | sed -n '...;0,101p'`：rc1，`invalid usage of line address 0`。这是读取命令区间错误，未修改文件；后续以合法行段直接读取补全。
2. 读取基底初始提交的 `.trellis/.developer`：rc128，文件不在该提交（被忽略的本地开发者记录）。没有凭空从版本库生成该记录；新夹具按本地测试身份配置。
3. 链路run1，原生归档P：rc1，`branch and base_branch are both 'fixture'`。原生操作拒绝且未归档；日志保存在evidence/chain-commands-failed-run1.json。修正的是测试夹具的真实分支元数据，建立main基线引用并在create时明确`--base-branch main`；没有使用`--skip-branch-validation`或改写校验代码。作者仓库不创建分支。
4. 链路run2：Python `FileNotFoundError`，新Git仓库未自带`.git/info/`。补创建该测试目录后使用全新run3夹具，保留失败命令日志evidence/chain-commands-failed-run2.json；不覆盖失败夹具。
5. 原夹具`/tmp/dep-mech-chain-20261026`修正尝试本地提交：`git commit -m "v43 fixture: restore R2 identity106 and unique successor107"`，rc1，`SonarQube code scanning is inactive: not authenticated. Run 'sonar auth login'.` 没有创建提交，HEAD仍为`8d4dedd7b262a066e0d1946001708b6b578f6aed`。未重试、未跳过hook、未改配置、未经另一条路径实现该被拒提交；仅撤销本轮两个文件的暂存，保留工作区修正。继续允许的只读审计与已授权报告工作。此前run3的独立复测和提交已经完成，不能把它冒称为原夹具提交成功。

第5项的下一安全步骤是由有权限的人恢复该原夹具的Sonar认证，再人工审阅并决定是否持久化；本轮不自动认证，不请求或搬运凭据。该限制不影响作者仓库设计文档修改和此前已完成的独立链路证据，但原夹具HEAD仍不能作为“已修复”的提交事实源。

交付前证据格式检查另遇一次CSV换行提示：`CRLF will be replaced by LF`，检查器因此拒绝宣称全通过。两份CSV及其生成器已统一LF；探针报告中继承的命令对齐尾空格亦已去除，原始JSON证据未改；静态处分表同时补齐每条适用路径的一般/P/R角色，共304格，并同步报告。这里只重新生成变动的静态表，未重复原生链路或P2提交探针。一次客户端原始帧调用在进入脚本前返回`SyntaxError: Invalid or unexpected token`，没有执行读写；由已验证可用的客户端转发格式完成后续检查。

## 交付前范围复核

- 产品变更仅主稿、配套、docs spec注册表；其余新增均位于本任务目录。未改§10结构、§7.4终态或类型4恢复边界，未改运行时实现。
- 任务保持`in_progress`供人工复核；没有finish/archive/journal、作者仓库git提交、push或PR。
- 新任务证据文件已落盘，依用户“不提交”限制尚未进入提交；不宣称口径11的版本库发布条件已达成。
