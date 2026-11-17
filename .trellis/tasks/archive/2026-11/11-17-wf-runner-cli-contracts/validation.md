# C1 验证记录：repro 公开 CLI 参数终止性与兼容

> 基线 c0c3a167；实施会话 2026-11-17；解释器 `/softwares/python/bin/python3 -B`。
> 证据按“反例 / 正常对照 / 命令 / 观察 / 限制”记录；未运行项如实标注。

## 激活记录（2026-11-17）

- 实际会话：DSH **inline**（`dsh.dispatch_mode: inline`，`in_progress-inline` 横幅；主会话直接
  实现/检查，不派发 implement/check 子agent）。本任务 `implement.jsonl`/`check.jsonl` 有意为空，
  按 activation.md 的 inline 分支以 `task.py start --allow-empty-context` 激活；分支 `main`。
- 未使用 ZCode/其他 dispatch 分支；若未来切到 `dispatch_mode: auto`，必须先为该子任务填写
  真实 spec/research 清单并 `task.py validate`，不能沿用本次 inline 记录。

## AC11–12 公开解析分片

| 项 | 反例（旧实现可复现） | 正常对照 | 命令与观察 |
|---|---|---|---|
| 缺值终止 | 从 HEAD 归档复制旧树，`timeout 3 bash .../repro/run.sh --mode` 与 `--only` 均返回 **124**（shift 2 不前进的死循环） | 新实现 rc=2 且零写入 | `scripts/tests/wf_runtime/test_repro_cli.py`（16 tests）逐选项覆盖 missing/empty/next-option/`--opt=` |
| 零副作用 | 非法调用前后 `TMPDIR`/HOME 隔离根保持空 | 每个拒绝用例断言 `os.listdir(root)==[]` | 同上 RejectionTest（10 个选项 × 3 形态 + candidate/unknown/list 组合） |
| 兼容保真 | 旧 shell `while/case` 无重复 group 保序断言 | 重复 group 保序、标量最后值、含空格/引号路径原样 | CompatibilityTest；`eval` 回读 shlex 输出 |
| `--list` 纯面 | 旧实现“后出现的 `--mode` 覆盖 `--list`”会误跑整轮 | `--list` 与 `--mode` 同时出现 rc=2；`--list` 仍零写 | test_repro_cli + 既有 `test_repro_list` |
| frame 保留参数 | 未改内部 frame | `--_wf-*` 先被 `runner_protocol` 拒绝；公开 parser 不再见 | RejectionTest.test_internal_frame_options_never_reach_the_public_parser |
| helper 登记 | — | `cli.py` 同时进入 `repro_select.HELPERS`/`RUNNER_FILES` 与 `plan.FAKE_TREE_COPY` | `test_repro_cli.HelperRegistrationTest`、`test_repro_selection` |

## 命令

```bash
bash -n scripts/tests/wf_runtime/full/repro/run.sh
/softwares/python/bin/python3 -B -m unittest scripts.tests.wf_runtime.test_repro_cli \
  scripts.tests.wf_runtime.test_repro_list scripts.tests.wf_runtime.test_repro_selection \
  scripts.tests.wf_runtime.test_repro_case_helpers scripts.tests.wf_runtime.test_runner_hygiene   # 62 OK
/softwares/python/bin/python3 -B -m unittest discover -s scripts/tests -t .                      # 1223 OK, 32 skipped
```

## 限制

- `--max` 等未来选项不在本轮；公开选项集合以 `repro/cli.py` 为唯一来源，新增必须同批进入 HELPERS/FAKE_TREE。
- “零写入”由隔离根目录枚举证明，不覆盖宿主内核级临时对象。
