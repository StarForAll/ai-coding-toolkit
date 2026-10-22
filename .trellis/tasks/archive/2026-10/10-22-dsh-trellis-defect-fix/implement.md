# Implement：dsh-trellis 缺陷修复

## 步骤

1. **新增 `lib/subagent-identity.js`**
   - 投影定义（key / stateVersion / stateSchema / init / apply）+ 注册/读取封装。
   - 兼容 legacy registry（`schema` + `view`）。
2. **`lib/dispatch-guard.js`**
   - `parseDispatchRequest(prompt, description)`：prompt 优先，description 用整段角色名
     兜底（`roleFromLabel`）。
   - `exec.arguments.description` 传入；`Active task:` 解析不变。
   - `inlineDenyReason`：改为“用户决定 + 禁止自行改配置”的表述。
3. **`lib/subagent-context.js`**
   - `parseDispatchPrompt(messages, label)`：label 用整段角色名兜底。
   - `registerSubagentContext` 注册 identity 投影并读取 `labelOf(agent.session)`；disposer 释放投影。
   - `subagentContextMessage`：前导唯一权威说明；skill 已推送/缺失两种分支。
   - `roleInstructionsFallback`：只保留加载提示。
4. **`lib/role-contract.js`**
   - `TASK_CONTEXT_SECTION` 去掉重复的 prepared 段落，改为指向 `## Curated Context`。
   - 新增 `roleFromLabel`：label 以角色名开头（可带括号/冒号/破折号标注）才生效，
     话题型描述与“角色名后接普通词语”保持 generic。
5. **`lib/index.js`**
   - 在 `subagentContext` 启用时把 identity 投影的生命周期挂到 `registerSubagentContext`（由它返回的 disposer 统一释放），避免新增独立注册点。
6. **测试**
   - `dispatch-guard.test.js`：description 兜底、inline 拒绝 description-only、拒绝文案约束。
   - `subagent-context.test.js`：label 兜底、文本唯一性、skill 已推送/缺失分支。
   - 新增 `subagent-identity.test.js`：真实 `SessionProjectionRegistry` 折叠 descriptor、
     legacy 注册路径、注册表缺失降级。
   - 新增 `role-contract.test.js`：整段角色匹配与话题型反例。
   - 新增/扩展真实运行时集成用例（`native-subagent-push.test.js`）：真实 AgentLoop +
     Session + `subagent/descriptor`，label-only 角色收到 push、话题型 label 静默。
7. **版本与文档**
   - `package.json` → 0.1.2；`pnpm run build:client`。
   - README：删除上游章节、修正守卫表述、补 0.1.2 记录。
   - `LOCAL_CHANGES.md` / `docs/validation-0.1.2-local.md`：0.1.2 簿记与验证记录。
8. **验证**
   - `pnpm test`；`node --test test/client-bundle.test.js`；
   - 隔离 profile 真实 headless 会话（临时 Trellis 项目）派发验证；
   - 复核 `git diff`，确认未触碰用户未提交文件。

## 验收命令

```bash
cd dsh-plugins/dsh-trellis
node --test test/*.test.js
pnpm run build:client
node --test test/client-bundle.test.js
```

## 依赖顺序

1 → 2/3/4 并行 → 5 → 6 → 7 → 8。第 3、5 步共用 identity 投影，先落地 1。
