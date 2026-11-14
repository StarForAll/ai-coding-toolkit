# Step 3 验证记录（2026-11-14 20:2x）

## 3.1 字节码缓存（PYTHONPYCACHEPREFIX）

- run_all / run_one / repro/run.sh 统一下发 `PYTHONPYCACHEPREFIX`；计划前用 bootstrap 前缀
  （结果目录尚未 claim），`prepare-results` 后改指 `$RESULTS_DIR/pycache`（可经 `WF_PYCACHE` 注入），
  彻底移除 `PYTHONDONTWRITEBYTECODE`。
- summary 记录 `pycache_root`。
- 抽样（pyc 落点）：
  - `cp2_tests` 普通并行：`/tmp/wf-step3-r2/pycache` 152 个 pyc；源树 0。
  - `cp3_tests`（isolated-user，合成 HOME）：`/tmp/wf-step3-cp3/pycache` 174 个 pyc；合成 HOME 内无 pyc；源树 0。
  - `--serial cp2_tests`：`/tmp/wf-step3-serial/pycache` 151 个 pyc；源树 0。
- “改源码立即生效”（pyc 不提供陈旧答案）：夹具 `.wf/lib/wflib/cli.py` 追加
  `raise RuntimeError("NEW-CODE-ACTIVE")` → 下一次 `wf.py status` 立即抛出该错误；删除该行后恢复 WF_OK。
- 全量：`--full --repro green` 61.9s（基线 90.3/88.8s，−31%），149 单元 0 失败；模板命中 0s；
  `HYGIENE-OK`；`find docs/workflows/wf scripts/tests \( -name '*.pyc' -o -name '__pycache__' \)` = 0。
- 可证伪性（策略级）：临时注释掉两处 `PYTHONPYCACHEPREFIX` 导出与 mkdir，跑 full →
  `SOURCE-TREE-POLLUTED`（18 个新增路径，含 payload/lib/wflib 与 full/__pycache__）且退出非零；
  恢复后清存量并重跑 → 绿。

## 3.2 模板跨 run 缓存

- key = `<digest12>-<pyver>-<deploy>[-<version>-<ref>]`；digest 取
  `wf_release_common.tree_digest(docs/workflows/wf/payload)` 前 12 位（内容摘要）。
  实测 dev key：`5424b96643be-3.14-dev`。
- 单套件：首次发布 8s（模板 2s + 套件 5s），第二次命中 6.11s（模板 0s，`template_cache_hit=true`，
  `template_source=cache`，`template_reused=true`）；基线 11.5s。
- 发布序列：`<key>.build` 构建 → template_check → 挪旧条目 → move 到 `<key>` →
  `template_check <key> --repoint-from <key>.build --expect-repoint-min 1` → 最后写 `<key>.meta.json`
  （`root=realpath(<key>)`）。命中序列：meta.root 比对 → template_check → `source_hygiene --strict` →
  克隆后 `--repoint-from <meta.root> --expect-repoint-min 1`（0 改写 → 该单元失败）。
- 七条失效实证（全部演示）：
  1. 改 payload 内容（spec.py 追加一行）→ key `5424b9…` → `0c167a…`，重建；反向：只 `touch` → 仍命中（模板 0s）。
  2. 解释器版本：同一段 key 计算代码在 3.14.7 与 3.13.5 下分别为 `5424b96643be-3.14-dev` / `5424b96643be-3.13-dev`。
  3. candidate 身份：`5424b96643be-3.14-candidate-0.1.2-refs-tags-wf-v0.1.2` 与
     `...-0.1.3-refs-tags-wf-v0.1.3` 不同。
  4. 删 `<key>.meta.json` → `TEMPLATE-CACHE-INVALID: 缺少 meta` → 重建（hit=false）。
  5. 整份 `template/` 复制到另一个 cache 根 → `TEMPLATE-CACHE-MOVED: meta.root 与条目 realpath 不一致` → 挪陈旧 + 重建。
  6. 把条目内 recovery.md 的自指记录改成 `/tmp/another-root`（meta.root 不变）→ 克隆时
     `TEMPLATE-REPOINT-COUNT=0` → `TEMPLATE-REPOINT-MISMATCH`，该单元结果为 5 列 bad 行，整次 GATE-FAIL。
  7. 往条目塞 `__pycache__/x.pyc` → `TEMPLATE-CACHE-DIRTY` / `TEMPLATE-CACHE-INVALID` → 重建。
- r67 假环境显式钉 `WF_NO_TEMPLATE=1` + `WF_NO_TEMPLATE_CACHE=1`，模板机制整套关闭。
- 开关：`--no-template`（含缓存）与 `--no-template-cache`（仅跨 run 缓存）由 plan 归一为
  PLAN_NO_TEMPLATE / PLAN_NO_TEMPLATE_CACHE。

## 其他

- T0：873 tests OK（skipped=10）。
- r67 冒烟：saved 16 / 16，GATE-OK。
