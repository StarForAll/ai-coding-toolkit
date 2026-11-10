# 裁定记录：`broken-reference` 豁免口径（B）

裁定人：用户（2026-11-09 14:24）。原文：**"B：接受"豁免 = 声明 + 人复核""**。

## 为什么需要裁定

v42 K4c 要求「本任务内新增/修改的 spec 规则不得当判据」，同时给一条纠错豁免：若修改只涉及 `check` 的机械纠错
（旧 check 引用的路径/命令在当前环境不存在，机械可判）且声明 `check_fix_kind=broken-reference`，不触发禁令。
但**旧规则的 `check` 原文没有落盘**（策展只存摘要），"旧 check 指向的路径/命令不存在"无法机械判定。

## 裁定落地（B 语义）

1. **import**：`assertion_ref` 指向本任务改过的规则时，若报告声明 `check_fix_kind=broken-reference`，放行并记录
   `imported[].broken_reference = {declared: true, lifted: [{finding, assertion_ref, rule}]}`。
2. **decide**：`lifted` 里每条 finding 必须有一条 `recheck_by=human:<来源>` 的 disposition，否则拒绝并给两条出口
   （补人复核 / 撤回豁免改用未被修改的判据）。
3. **文档**：机制稿 §9.2 增「规则不得自证」与「豁免 = 声明 + 人复核」，并把"框架不验证声明真伪"写在正文。
4. **测试**：`broken_reference_problems` 三条（无声明不需人、有声明缺人复核被拒、人复核后通过）。

## 代价与对价

- 代价：豁免的质量依赖人真的看了这条声明（与 v42 §0.2「人的声明不机械检测」同一条取舍）。
- 对价：声明一旦做了就进入 `imported` 记录与判定前置，**不会静默通过**；预览里可单列。
