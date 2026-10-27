# 收尾验证记录（2026-10-27）

用户人工复核后放行提交与收尾。本文件记录提交前最后一轮验证，与第一批（v43）、第二批（v44）证据分开判读。

## 项目规定检查

| 命令 | 本轮结果 |
|---|---|
| `/softwares/python/bin/python3 trellis-library/cli.py validate --strict-warnings` | PASS，rc0；仅 5 条 stale-related-asset mtime INFO，与 validation.md 记录一致 |
| `./scripts/validate-skills.sh` | PASS；31 skills + spec cross-check |
| `/softwares/python/bin/python3 -m unittest trellis-library/tests/test_cli.py` | PASS；36 tests OK，约 62s |
| `git diff --check` | PASS，rc0 |

## 注册探针复跑

- `.trellis/spec/docs/index.md` 注册的 39 条 `rg -n` 探针全部实际执行；数值预期全部匹配，rc1 仅出现在预期 0 命中的探针。v43 记录的 38 条加 v44 新增 1 条，共 39 条。
- 修复一处注册表自身缺陷：`重新生成后重校验|已落盘的替换指向|原预写标识已被其他身份占用` 探针的预期注释要求覆盖 §7.7 类型 5 引用（主稿"仍按 §7.8 标识占用规则校验目标标识"），但 pattern 缺少能命中该引用句的分支，实际仅 4 hits。已补 `|按 §7.8 标识占用规则` 分支，复跑 5 hits，与注册预期一致；主稿与配套未为此改动。
- v43/v44 三条新探针的命中位置逐条核对：标识占用校验唯一源 1 hit（主稿 §7.8）；移交完成的持久判据 2 hits（§6.4 源 + §7.7 引用）；占用/重生成族 5 hits（§6.5、§6.6、§7.7、§7.8 已落盘指向与类型 4 例外）。

## 提交门禁

- 本仓库 `.git/hooks/pre-commit` 为 sonar secrets 扫描钩子；本轮会话实测 `sonar auth status` rc0 Connected（Source OS Keychain），提交走真实门禁；未禁用 hook、未改配置、未用 `--no-verify`。

## 边界

- 第二批（v44 行为链路）复测仍为 INVALIDATED / 未完成，见 validation-second-batch.md；本次收尾不宣称第二批通过、§10 全量自检通过或"本版可用"。
- 39 条探针为文本一致性检查，不替代第二批行为链路验证；矩阵形状（转移 7 行、组合 11 行、字段矩阵 13 行）沿用 v43 的 structural-checks 事实，v44 diff 未触及矩阵。
