# /tmp 黑盒测试报告：Trellis 升级兼容机制

## Environment

- Repo root: `/ops/projects/personal/ai-coding-toolkit`
- Fixture root: `/tmp/trellis-upgrade-mechanism-test`
- Source commands:
  - `docs/workflows/新项目开发工作流/commands/install-workflow.py`
  - `docs/workflows/新项目开发工作流/commands/upgrade-compat.py`
  - `docs/workflows/新项目开发工作流/commands/uninstall-workflow.py`

## Test Matrix

| ID | Scenario | Result |
|----|----------|--------|
| T1 | 首次安装 happy path | Pass |
| T2 | 已安装且版本一致时执行 `upgrade-compat --check` | Pass |
| T3 | 版本一致但 `start.md` 已失去 Phase Router，再执行 `--check` | Fail |
| T4 | 版本变化且 `start.md` 缺失 Phase Router，执行 `--merge` | Pass |
| T5 | 版本变化且 helper script 缺失，执行 `--check` | Fail |
| T6 | 版本变化且 `start.md` 缺失注入锚点，执行 `--force` | Fail |
| T7 | 安装记录损坏时执行 `uninstall` | Fail |
| T8 | 安装记录缺失时执行 `uninstall` | Pass |
| T9 | 卸载后重新安装 | Pass |
| T10 | 安装后命令中 shell 路径是否已替换为 `.trellis/scripts/workflow/` | Pass |

## Confirmed Findings

### F1 `upgrade-compat --check` 在版本一致时直接短路，漏检真实漂移

- Severity: High
- Type: 状态误判 / 漂移漏检
- Repro:
  1. 安装工作流
  2. 保持 `.trellis/.version` 与 `workflow-installed.json` 中版本一致
  3. 用备份原始文件覆盖 `.claude/commands/trellis/start.md`，移除 Phase Router
  4. 执行：
     ```bash
     /ops/softwares/python/bin/python3 docs/workflows/新项目开发工作流/commands/upgrade-compat.py --check --project-root /tmp/trellis-upgrade-mechanism-test
     ```
- Actual:
  - 输出 `版本一致，无需处理`
  - 未执行任何完整性检查
- Expected:
  - 即便版本一致，也应至少检查 `start.md` / 命令 / helper scripts 的完整性，或提供单独的 drift-check 模式
- Impact:
  - 用户可能在“同版本”状态下长期处于损坏部署而不自知

### F2 `upgrade-compat --check` 不检查 helper scripts，导致升级遗留漂移漏报

- Severity: High
- Type: 升级遗留漂移
- Repro:
  1. 安装工作流
  2. 删除 `/tmp/trellis-upgrade-mechanism-test/.trellis/scripts/workflow/plan-validate.py`
  3. 将 `.trellis/.version` 从 `2.1.0` 提升到 `2.2.0`
  4. 执行 `upgrade-compat.py --check`
- Actual:
  - 输出 `start.md: Phase Router 正常`
  - 输出 `所有命令存在`
  - 输出 `无冲突`
  - 实际 helper script 缺失
- Expected:
  - helper scripts 应纳入冲突检测范围
- Impact:
  - 升级后部分命令会引用不存在的脚本，但兼容检查仍显示通过

### F3 `--force` 并不会按文档描述“用备份覆盖”，且在失败时仍返回成功并更新版本记录

- Severity: Critical
- Type: 行为与文档不符 / 假成功
- Repro:
  1. 安装工作流
  2. 把 `.claude/commands/trellis/start.md` 改成一个完全不含 `## Operation Types` 的损坏文件
  3. 将 `.trellis/.version` 提升到 `2.3.0`
  4. 执行：
     ```bash
     /ops/softwares/python/bin/python3 docs/workflows/新项目开发工作流/commands/upgrade-compat.py --force --project-root /tmp/trellis-upgrade-mechanism-test
     ```
- Actual:
  - 输出 `start.md 中未找到 '## Operation Types'，无法自动注入 Phase Router`
  - 仍然输出 `升级兼容处理完成`
  - 仍然更新 `workflow-installed.json` 版本记录
  - `start.md` 保持损坏状态
- Expected:
  - `--force` 应真正从备份恢复或直接用可用源内容重建 `start.md`
  - 若恢复失败，应非 0 退出，不应写入“已完成/已更新版本”的状态
- Impact:
  - 会制造“已升级兼容”的假象，后续所有基于版本记录的判断都会被污染

### F4 `uninstall-workflow.py` 对损坏的安装记录没有容错，直接崩溃

- Severity: High
- Type: 执行错误
- Repro:
  1. 安装工作流
  2. 将 `.trellis/workflow-installed.json` 写成非法 JSON
  3. 执行：
     ```bash
     /ops/softwares/python/bin/python3 docs/workflows/新项目开发工作流/commands/uninstall-workflow.py --project-root /tmp/trellis-upgrade-mechanism-test
     ```
- Actual:
  - `json.decoder.JSONDecodeError`
  - 未进入清理逻辑
- Expected:
  - 应像 `upgrade-compat.py` 一样容错读取，降级到默认命令列表或提示后继续清理
- Impact:
  - 安装记录一旦损坏，用户无法正常卸载，残留文件和状态会继续堆积

## Additional Notes

### A1 `upgrade-compat --merge` 在“版本变化但无冲突”时会重新部署并更新记录

- 这是当前实现的实际行为。
- 但 `命令映射.md` 的流程图写的是：
  - `upgrade-compat.py --check`
  - `版本不一致 + 无冲突 → 自动重新部署`
- 当前 `--check` 并不会自动重新部署，只会输出 `无冲突` 并退出。
- 这更像文档口径偏差，而不是脚本崩溃型 bug。

### A2 `uninstall` 在安装记录缺失时可正常降级清理

- 顺序复测确认：
  - `workflow-installed.json` 缺失时，`uninstall-workflow.py` 会使用默认命令列表并成功恢复 `start.md`
  - `.trellis/scripts/workflow/` 也会被删除

## Evidence Snippets

### `--check` 同版本短路

```text
当前版本: 2.0.0  |  安装时版本: 2.0.0
✅ 版本一致，无需处理
```

### helper script 缺失但仍无冲突

```text
当前版本: 2.2.0  |  安装时版本: 2.1.0
✅ start.md: Phase Router 正常
✅ 所有命令存在
冲突: 0
✅ 无冲突
```

### `--force` 失败但仍报告完成

```text
⚠️  start.md 中未找到 '## Operation Types'，无法自动注入 Phase Router
✅ 版本标记已更新: 2.3.0
✅ 升级兼容处理完成
```

### `uninstall` 读取损坏记录直接崩

```text
json.decoder.JSONDecodeError: Expecting property name enclosed in double quotes
```

## Commands Executed

```bash
/ops/softwares/python/bin/python3 docs/workflows/新项目开发工作流/commands/install-workflow.py --project-root /tmp/trellis-upgrade-mechanism-test
/ops/softwares/python/bin/python3 docs/workflows/新项目开发工作流/commands/upgrade-compat.py --check --project-root /tmp/trellis-upgrade-mechanism-test
/ops/softwares/python/bin/python3 docs/workflows/新项目开发工作流/commands/upgrade-compat.py --merge --project-root /tmp/trellis-upgrade-mechanism-test
/ops/softwares/python/bin/python3 docs/workflows/新项目开发工作流/commands/upgrade-compat.py --force --project-root /tmp/trellis-upgrade-mechanism-test
/ops/softwares/python/bin/python3 docs/workflows/新项目开发工作流/commands/uninstall-workflow.py --project-root /tmp/trellis-upgrade-mechanism-test
```

## Verification Status

- 实际执行: yes
- 发现问题: yes
- 正式修复: not started
