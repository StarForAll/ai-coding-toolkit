# E：独立复审的执行包

> 用途：把「未参与修订的会话/CLI 复审」变成可执行、可核对的动作。
> 本文件只准备材料与判据，**不代替复审结论**；复审结论由复审者给出，由人确认后回填。

## 1. 前置约束（缺一不可）

| 约束 | 说明 |
|---|---|
| 复审者未参与修订 | 本会话（DSH，2026-11-03～11-04 的全部 R1–R78 修订）不能担任复审者 |
| 外发授权 | `codex`/`pi` 都是云端 CLI，送审等于把仓库内容发到外部服务；须由人明确授权**送审材料范围** |
| 只读 | 复审者不改仓库；发现的问题以报告形式交回，由主会话处置 |
| 材料边界 | 只送 §2 列出的文件；不送 `.env`、凭据、`~/.claude`、`dsh-plugins/` 等无关资产 |

## 2. 送审材料（当前版本，2026-11-04）

| 文件 | 行数 | sha256（前 16 位） |
|---|---|---|
| `docs/workflows/wf-framework-charter.md` | 128 | `8b816ee4cb1fad03` |
| `docs/workflows/wf-framework-design.md` | 719 | `f41173d9c174ab78` |
| `docs/workflows/wf-framework-mechanism.md` | 1141 | `7cef366cddd87c4e` |
| `docs/workflows/wf-framework-implementation.md` | 858 | `0d3151b909c8afa9` |
| `docs/workflows/新项目开发工作流/`（源树：payload + skills + README + dev-manifest） | — | 目录，按需整体送审 |
| `.trellis/tasks/11-03-wf-round1-min-loop/validation.md` | — | 实跑记录（可只送 §1–§20 摘要 + §65–§69） |
| 本目录的 `round1-closure-plan.md`、`pending-decisions.md` | — | 收口状态与已裁定项 |

## 3. 复现命令（复审者可自行验证）

```bash
cd /home/xzc/projects/personal/ai-coding-toolkit

# 全局机检（七项 + 覆盖率）
/softwares/python/bin/python3 scripts/validate-wf-design.py

# 引用检查
/softwares/python/bin/python3 scripts/check-doc-refs.py

# 单元测试（锁契约、归档持久化、rules_digest 一致性）
/softwares/python/bin/python3 -m unittest discover -s scripts/tests
/softwares/python/bin/python3 -m unittest discover -s scripts/tests/wf_runtime

# 发行包可复现（字节级）与令牌一致
/softwares/python/bin/python3 scripts/build-wf-release.py --verify
/softwares/python/bin/python3 scripts/build-wf-release.py --verify-token-parity

# 全量功能回归：45 项套件 + 三夹具 + F0，从零重建发行仓库，失败即 exit≠0
bash scripts/tests/wf_runtime/full/run_all.sh
```

## 4. 复审判据（逐条给结论，不接受"看起来没问题"）

1. **上位文件遵守**：charter T1–T7 未被违反；设计稿/机制稿未被"实现反推"改写（四份受保护文件与机制稿是否只在允许范围内变动）。
2. **不新增判定**：状态值、原因码、记录字段、哈希域、门禁顺序是否严格来自机制稿（对照 §2–§3 的码表与 §11.2 的步骤集合）。
3. **门禁与记录自洽**：报告里声称的每条门禁，代码里是否有对应核验；`inspect`/`gate`/`archive` 的事实是否与记录一致。
4. **防伪边界**：脚本只核结构与取值、不判语义；不存在"存在即通过"的路径（尤其 `approval.choice`、`review` 结论、维护回执）。
5. **未知不当零**：配置非法、记录不完整、数据缺失时是否阻断而非放行（§2.3.3、§2.3.11）。
6. **可复现**：§3 的命令全部可跑通；`--verify` 字节复现；`run_all.sh` 有失败即非零退出。
7. **文档与代码一致**：§6.2 每条能力登记的函数名在代码中存在；不存在的命令/函数/能力不得宣称（§2.3.11 纪律）。
8. **未运行项诚实**：未运行的能力是否明确标注原因；不得把未运行写成已通过。
9. **安全与凭据**：日志/facts 是否脱敏；凭据不出现在记录、命令行或提交里。
10. **可维护性**：同一判定是否只有一处实现（不各写判据）；重复/死代码是否清理。

## 5. 已知未完成项（复审时不应算作缺陷，但须核对"是否诚实登记")

| 项 | 状态 |
|---|---|
| 真实会话压缩事件 | **身份轴已运行**（2026-11-04 两次真实压缩后 `$DSH_SESSION_ID` 未变，`validation.md` §71）；绑定轴待下一次压缩，判据见 `d1-compaction-checkpoint.md` §1 |
| 实例（run）编排、`upgrade`、`uninstall --purge` | 属第二/三轮，首轮明确不做 |
| 机制稿 §0.2 的四项机检扩展 | 已裁定排到首轮收口之后 |
| 独立的「E 复审」 | 已执行（`codex exec`，`review-round44-reconciliation.md`）；未覆盖轴见实现稿 frontmatter |

## 6. 复审结论的回填方式

复审者按 `<!-- wf-review-report:v1 -->` 协议或在正文列出缺陷（编号 + 事实 + 契约依据 + 建议）。主会话收到后：

1. 逐条复核（成立/部分成立/不成立，给证据）；
2. 成立的按"改实现 → 补用例 → 全量回归 → 改文档 → 重绑 sha256 → 记 `validation.md`"闭环；
3. 全部处置后，把实现稿 frontmatter 的 `status` 从「首轮实现候选（未经独立复审）」改为「定稿（按已覆盖轴）」，并登记复审主体、覆盖轴与结论；
4. 若复审覆盖不到的轴，写明"未覆盖"，不整体称定稿。
