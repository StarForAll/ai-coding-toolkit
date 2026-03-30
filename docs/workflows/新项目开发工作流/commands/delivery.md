---
name: delivery
description: 开发完成？准备交付 — 验收测试、交付物生成、变更日志、经验沉淀。触发词：准备交付、跑验收、整理交付物、项目收尾
---

# /trellis:delivery — 项目测试、交付与沉淀

> **Workflow Position**: §6+§7 → 前: `/trellis:finish-work` → 后: `/trellis:record-session`
> **Cross-CLI**: ✅ Claude Code · ✅ Cursor (命令名: delivery) · ⚠️ OpenCode · ⚠️ Codex/Gemini

---

## When to Use (自然触发)

- "准备交付了"
- "跑一下验收测试"
- "整理一下交付物"
- "项目收尾"
- "生成 changelog"
- "做个项目复盘"

---

## 流程

### Step 1: 自动化测试

**Skill**: `verification-before-completion`

```bash
pnpm test && pnpm type-check && pnpm lint
```

### Step 2: 可用性与性能验证

按 PRD 验收标准逐项检查

### Step 3: 验收门禁

- [ ] 核心场景 100% 通过
- [ ] P0/P1 缺陷为 0
- [ ] 安全扫描无高危

### Step 4: 外部项目交付控制门禁（如适用）

若项目属于外包、定制开发或新客户项目，进入正式交付前先检查 `assessment.md` / 合同中约定的交付控制轨道：

- **首选轨：托管部署**
  - 尾款未到账：只交付演示地址、试运行环境访问、验收材料、用户手册、运维说明
  - 尾款未到账：不交付源码仓库权限、生产环境密钥、管理员账号、最终部署权限
- **备选轨：试运行授权**
  - 必须已明确披露：授权有效期、续期方式、到期行为、永久授权触发条件
  - 到期行为应限制为“演示模式”或“只读模式”，不得破坏已有数据
  - 尾款未到账：不交付永久授权、不交付完整源码与最终控制权

禁止项：

- 未披露的授权失效机制
- 远程关停、隐藏后门、不可恢复锁定
- 用不可解码文件伪装源码交付

### Step 5: 交付物生成

**Skill**: `doc-coauthoring` — 协同撰写交付文档

客户交付物：代码 + PRD + 用户手册 + 运维文档
开发交付物：代码 + 技术文档 + 评估集

### Step 6: 尾款到账后的最终移交（如适用）

仅在开发者明确确认尾款到账后，才执行最终移交 checklist：

- [ ] 源码仓库权限或源码包
- [ ] 永久授权文件，或移除试运行限制的正式版本
- [ ] 构建脚本、部署脚本、CI/CD 配置
- [ ] 生产环境变量、密钥、证书、第三方平台配置
- [ ] 服务器、域名、数据库、对象存储等管理员权限
- [ ] 最终运维文档、回滚说明、交接记录

若尾款尚未到账，上述条目不得在交付清单中标记为“已完成移交”。

### Step 7: 变更日志

**Skill**: `changelog-generator` — 从 git commits 自动生成

### Step 8: 代码审查

**Skill**: `requesting-code-review` — PR 前审查清单

### Step 9: 经验沉淀

项目复盘：效率指标 + Bug 知识沉淀 + 改进项

### Step 10: 收尾记录校验

进入 `/trellis:record-session` 前，先确认：

- 已完成内容已由人工测试并提交
- 已完成任务先归档，未完成任务不要误归档
- `task.py archive` 与 `add_session.py` 一旦修改 `.trellis/tasks` 或 `.trellis/workspace`，必须真实自动提交，不接受“脚本提示成功但 git 仍脏”的状态

```bash
git status --short .trellis/tasks
git status --short .trellis/workspace .trellis/tasks
```

判定规则：

- 输出为空：可以视为归档/记录闭环完成
- 仍有 `.trellis/tasks` 或 `.trellis/workspace` 变更：`/trellis:record-session` 不算完成，先处理自动提交失败原因

---

## 输出

```
$TASK_DIR/delivery/
├── test-report.md
├── acceptance.md
├── deliverables.md
├── transfer-checklist.md
└── retrospective.md
```

## 下一步推荐

**当前状态**: 验收测试完成，交付物已生成。

根据验收结果：

| 验收结果 | 推荐命令 | 说明 |
|---------|---------|------|
| 全部通过，准备收尾 | `/trellis:record-session` | **默认推荐**。记录会话，并确认 `.trellis` 元数据已自动提交 |
| 有 P0/P1 缺陷 | `/trellis:break-loop` | 深度分析 Bug 根因 |
| 有 P2/P3 缺陷 | `/trellis:start` | 回到实施阶段修复 |
| 需要更新规范文档 | `/trellis:update-spec` | 沉淀新发现的模式到 spec |
| 需要请求代码审查 | Skill: `requesting-code-review` | PR 前外部审查 |
| 需要归档任务 | `python3 ./.trellis/scripts/task.py archive <name>` | 项目完成归档，并检查 `.trellis/tasks` 已自动提交 |
| 不确定下一步 | `/trellis:record-session` | 先记录会话，但只有 `.trellis` 元数据自动提交成功后才算完成 |
