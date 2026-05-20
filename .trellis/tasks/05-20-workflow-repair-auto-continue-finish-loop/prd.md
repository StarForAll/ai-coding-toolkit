# 修复 workflow-repair `--auto` 的 continue / finish-work 闭环

## 背景

当前 `skills/workflow-repair/SKILL.md` 对 `--auto` 的合同只描述了修复成功后进入提交确认与 `finish-work`，但没有把 Trellis 正常任务流里的 `continue` 重入链路定义完整。

实际问题包括：

- `--auto` 没有明确要求先回到当前任务的 `trellis-continue` / `/trellis:continue` 正常流转面
- 任务完成后可能反复继续执行 `trellis-continue`，没有“已 close / 已完成”识别规则
- 当命令面不存在但仓库里有同名 skill surface 时，合同仍可能错误地以“没有 finish-work 命令面”为由停下
- 自动提交流程只覆盖了单次确认，没有定义“提交后再次 continue，直到推荐 finish-work 或任务关闭”的闭环

## 目标

修复 `skills/workflow-repair` 的 `--auto` 行为合同与配套场景测试，使其在修复成功后：

1. 先回到当前 repair task 的正常 Trellis `continue` 流程
2. 遇到当前任务的一次性提交确认时自动回复 `ok`
3. 提交后再次通过 `continue` 继续推进，直到：
   - 推荐执行 `trellis-finish-work` / `/trellis:finish-work`，或
   - 当前任务已经在 `continue` 流程里被正常关闭
4. 检测 `continue` / `finish-work` surface 时，优先使用当前平台可调用命令；若命令面不存在，再回退到当前项目内对应 skill surface；只有两者都不存在时才可作为 blocker 停止

## 范围

- `skills/workflow-repair/SKILL.md`
- `skills/workflow-repair/tests/*.md` 中与 `--auto` 相关的场景文件
- `.trellis/spec/skills/workflow-repair.md`
- 必要时补充 `skills/workflow-scan/SKILL.md` 的配对兼容说明

## 非目标

- 不新增 `workflow-repair` 的独立可执行脚本
- 不修改 `WORKFLOW_QUESTIONS.md` 协议字段或 schema
- 不改动 Trellis baseline `trellis-continue` / `trellis-finish-work` 的实现内容

## 需求

- `--auto` 必须把“修复后自动收尾”定义为当前 repair task 的正常 Trellis close-out 重入流程，而不是一次性的 finish-work 直跳
- `--auto` 必须识别 `trellis-continue` 与 `trellis-finish-work` 在不同 CLI 中可能是命令也可能是 skill
- 对于 `finish-work`，当命令面不可用但仓库内存在同名 skill surface 时，不得错误判定为 blocker
- `continue` 可能在某次重入后直接把任务推进到完成/关闭态，`--auto` 必须识别该终止条件，不能无限循环 `continue`
- 现有 `pending -> final outcome` repair log 规则仍需成立

## 验收标准

- [ ] `skills/workflow-repair/SKILL.md` 明确要求 `--auto` 通过当前任务的 `continue` surface 驱动后续收尾
- [ ] 合同明确 `continue` / `finish-work` 的“命令优先，缺失时回退 skill surface，双缺失才阻断”规则
- [ ] 合同明确提交后再次 `continue` 直到推荐 `finish-work` 或任务关闭的循环终止规则
- [ ] 至少新增或更新覆盖以下场景的压力测试：
  - 命令面缺失但 skill surface 存在
  - `continue` 推进到提交确认再继续
  - `continue` 自身把任务关闭
- [ ] `./scripts/validate-skills.sh` 通过

## 验证计划

- 运行 `./scripts/validate-skills.sh`
- 视改动范围补跑针对性文本/contract 校验
