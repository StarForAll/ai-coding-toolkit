# 实施计划

当前为 `planning`。用户批准最新版方案后，按实际实施平台选择激活方式。当前会话是 Codex inline。若在此模式实施，两个 JSONL 有意留空，使用下列命令，进入实施后由主会话按 `trellis-before-dev` 加载脚本规范、[wf 交付纪律](../../spec/docs/wf-delivery-discipline.md)及本任务工件。

```bash
/softwares/python/bin/python3 ./.trellis/scripts/task.py start \
  .trellis/tasks/11-18-fix-wf-script-validation --allow-empty-context
```

若交接给 ZCode 等采用子代理派发的平台，在激活前按 [Trellis 工作流 1.3](../../workflow.md) 为 `implement.jsonl` 和 `check.jsonl` 各登记真实的规范或研究条目。先验证清单，通过后再用普通启动命令。主会话读取规范不能代替派发清单。

```bash
/softwares/python/bin/python3 ./.trellis/scripts/task.py validate \
  .trellis/tasks/11-18-fix-wf-script-validation
/softwares/python/bin/python3 ./.trellis/scripts/task.py start \
  .trellis/tasks/11-18-fix-wf-script-validation
```

1. 用下方资源验收命令记录修改前的结果。确认作者侧命令和 T0 本身退出为 0 时，未关闭文件警告仍能使外层退出为 1。按文件、行号和调用归因，与 R2 清单逐项对应。
2. 新增 `scripts/tests/test_check_wf_analysis.py`，按设计的隔离副本方案编写回归用例。先用旧实现确认缺失一级、带字母的二级和历史后正文的用例因目标断言失败，并记录撤回词及矩阵标签的旧边界行为。快速验证使用 `PYTHONPYCACHEPREFIX=/tmp/wf-unit-pycache /softwares/python/bin/python3 -m unittest scripts.tests.test_check_wf_analysis`。
3. 替换引用检查段，同批订正两处 D3 指向。重跑上一步命令，核对引用正负例与两项旧规则的边界断言，再按下方步骤核对 D3。
4. 按 R2 清单收口文件读写。重跑下方资源验收，随后执行设计文档检查和适用的 T2 检查。T0 已包含新增回归和四个目标测试文件。
5. 核对 `git diff --check`、`git diff`、`git diff --cached`、`git status --short --untracked-files=all` 和新增测试文件内容。逐项记录 AC1–AC4 的实际退出码、结果和例外。资源验收只在命令退出码与 stderr 都满足要求时通过。收口前保留预期改动，清理由本次验证创建的临时副本。

## D3 指向（AC4）

在仓库根目录定位两条 D3、方案的第 4 节标题、C2 行及 A8 的交叉指向。

```bash
rg -n -F -e 'D3（已定：选 A）' -e 'D3（⑥ 内）' \
  -e '## 4. 完成条件与清除动作' -e '| **C2** 无未关闭' -e 'light 关闭 C2 的入口成本' \
  docs/workflows/wf/analysis/proposal-repairing-state.md \
  docs/workflows/wf/analysis/backlog-excluded-from-item6.md
```

逐条确认两份文档的 D3 都明确指向方案的 §4 C2 行，该行确实是 A8 所指的现行关闭条件，同时核对两处差异只订正指向。记录两个来源和一个目标的位置。仅命中 `§4` 字符串不足以通过。

## 资源验收（AC2、AC3、AC4）

在仓库根目录运行。保留三个命令的 stderr 和退出码，最后按其中任一失败返回 1。基线和修复后用同一条命令，比较是否出现未关闭文件告警，避免把 `-W error` 在析构环节打印的未捕获异常误当成测试失败。

```bash
PYTHONPYCACHEPREFIX=/tmp/wf-unit-pycache /softwares/python/bin/python3 - <<'PY'
import re
import subprocess
import sys

checks = (
    ("scripts/check-wf-analysis.py",),
    ("scripts/check-doc-refs.py",),
    ("-m", "unittest", "discover", "-s", "scripts/tests", "-t", "."),
)
unclosed_file = re.compile(rb"ResourceWarning:[ \t]+unclosed file\b")
failed = False
for args in checks:
    result = subprocess.run(
        [sys.executable, "-W", "always::ResourceWarning", *args],
        stderr=subprocess.PIPE,
        check=False,
    )
    sys.stderr.buffer.write(result.stderr)
    sys.stderr.buffer.flush()
    warned = unclosed_file.search(result.stderr) is not None
    print(f"{' '.join(args)}: exit={result.returncode}, unclosed_file={warned}",
          file=sys.stderr, flush=True)
    failed |= result.returncode != 0 or warned
raise SystemExit(1 if failed else 0)
PY
```

如果 T0 碰到宿主 `/proc` 会话 leader 不可见，按交付纪律在上述验收外层 Python 前加 `setsid --wait`，保留所有告警和退出码断言。验收覆盖三个被观测进程输出的未关闭文件警告。本任务七处测试调用都在 unittest 主进程执行。独立子进程吞掉的诊断和其他类型的 `ResourceWarning` 不在该门槛的证明范围。

T0 的观察范围大于 R2 的修改清单，基线仍可能发现清单外告警。按来源记录为已有问题或本次引入的问题。本次引入的告警须在当前修改中消除。清单外的已有问题单列，预跑本身不扩大修改范围。如果它在最终验收仍出现，AC3 记为失败并报告来源，保留原过滤条件。

## 其余收口检查（AC2、AC4）

以下是 [wf 交付纪律 §8](../../spec/docs/wf-delivery-discipline.md#8-收口前的最小证据集四层) 中其余的 T2 检查。`check-doc-refs.py` 和 T0 已在资源验收中执行。

```bash
/softwares/python/bin/python3 -B scripts/validate-wf-design.py
./scripts/validate-skills.sh
/softwares/python/bin/python3 -B scripts/build-wf-release.py --verify --verify-token-parity
bash scripts/tests/wf_runtime/full/run_all.sh --full --repro green
```

full 使用测试发行副本，按 runner 规范隔离结果、夹具与缓存，并避免和其他 full 并发。发行验证使用 `--verify`，已有产物不通过时只记录实际原因和影响。T2 失败或因宿主能力未运行时单列状态及下一步，不能从 T0 成功推定。
