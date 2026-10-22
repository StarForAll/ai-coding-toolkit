# Implement: dsh-trellis 0.1.3 Codex parity 全量复核与缺口验证

> 执行前闸门：design.md 与本清单经用户确认后才 `task.py start`。
> 修复闸门：G1–G4 全部完成、报告交付、用户确认问题清单与方案后才允许修复。

## 阶段 0：环境准备
- [ ] 0.1 创建 /tmp/dsh-parity-reverify/{proj-basic,proj-nogit,proj-plain}
  （proj-basic/proj-nogit 跑 `trellis init --dsh`，proj-basic 额外 git init）
- [ ] 0.2 新建 `trellis-headless` profile（dsh-base + dsh-headless + dsh-trellis，
  安装来源与 web profile 同一 git 快照）；确认插件版本为 0.1.3
- [ ] 0.3 确认 deepseek API 可用（一条最小 headless 会话）；不可用则按 design 降级

## 阶段 1：G1 修复回归（真实会话，trellis-headless + proj-basic）
- [ ] 1.1 G1.1 无任务时 description-only implement 派发 → 守卫 deny（事件日志取证）
- [ ] 1.2 G1.2 任务 in_progress 后 description-only 派发 → 子代理首步 push 取证
  （角色契约、curated context、`was prepared` 恰好一次、不要再次加载说明）
- [ ] 1.3 G1.3 话题型 description → generic 静默（无 push 无 deny）
- [ ] 1.4 G1.4 skill 缺失退化路径（临时移文件，验证后恢复）

## 阶段 2：G2 主链路复核（C1–C10 重跑）
- [ ] 2.1 C1 面包屑（no_task/planning/in_progress/task_error/completed + 去重 + no-trellis）
- [ ] 2.2 C2 会话身份隔离（两个 dsh 会话 + pi 会话指针并存）
- [ ] 2.3 C3 trellis_wait（成功路径真实调用；失败映射看单元）
- [ ] 2.4 C4 子代理 push 内容完整性
- [ ] 2.5 C5 /trellis-status、/trellis-finish、/trellis-doctor（真实代码执行）
- [ ] 2.6 C6 dispatch_mode 引导（proj-nogit 自动补 inline；显式 auto 不覆盖）
- [ ] 2.7 C7 spec 注入（deny-once、read ticket、持久化分片、compaction 重置）
- [ ] 2.8 C8 bootstrap 一次性（含子代理永不注入）
- [ ] 2.9 C9 proj-plain 零干扰
- [ ] 2.10 C10 init 产物 ↔ 插件读取路径双向一致 + Trellis 源码契约比对
- [ ] 2.11 Codex 逐点对照（.codex/hooks、agents toml、Trellis 源码 codex 平台）→ 三档表

## 阶段 3：G3 补足评估
- [ ] 3.1 无插件 headless profile 在 proj-basic 跑同流程 → 缺失清单
- [ ] 3.2 插件版补足对照 → 三段式结论（缺失 → 已补足 → 残余不足+可改进性）

## 阶段 4：G4 缺漏扫描
- [ ] 4.1 多会话并发隔离
- [ ] 4.2 异常路径 fail-closed（task.json 损坏 / config.yaml 损坏、只读 / .trellis 中途删除）
- [ ] 4.3 长会话（compaction 重注入、--session-id resume 声明复核）
- [ ] 4.4 research 角色链路
- [ ] 4.5 冲突检测 / 版本监控（可实测部分实测，其余标注证据等级与原因）
- [ ] 4.6 workflow.md 派发协议一致性（trellis_wait vs run_in_background:false）
- [ ] 4.7 Trellis 0.7.0-beta.4 契约（task.py --json、DSH_TRELLIS_CONTEXT_ID 优先级）

## 阶段 5：报告与修复闸门
- [ ] 5.1 写 verification-report.md（逐项结论 + 证据等级 + 取证位置 + 三档对照表）
- [ ] 5.2 问题清单（定性 / 影响面 / 可选方案 / 推荐项）
- [ ] 5.3 **停下，交付用户确认；确认后才进入修复迭代**
- [ ] 5.4（确认后）修复 → 回归验证 → 更新报告

## 验证命令
- 会话取证：`~/.dsh/sessions/` 下按 session id 解压 session.v4.jsonl.zstd 检索
  `dsh-trellis` / `subagent-context` / deny 事件
- 插件测试（补充）：`cd dsh-plugins/dsh-trellis && pnpm test`
- Trellis 契约：`python3 .trellis/scripts/task.py current --json`（临时项目内）

## 回滚点
- 临时项目与新建 profile 均在 /tmp 与 ~/.dsh/profiles/trellis-headless，删除即回滚
- G1.4 的 skill 文件移动立即恢复
- 修复迭代前 git 提交插件现状（如已有未提交改动则先确认归属）
