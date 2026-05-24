# finish-work-checklist 模板

> 用于当前 task 在进入 Trellis 原生 `finish-work` 前冻结收尾证据。
> 必须按真实状态填写；没有证据时写 `not run` / `not applicable`，不要伪造通过。

## 冻结验证矩阵

| Check | Command or Method | Result |
| --- | --- | --- |
| 示例：lint | `<真实命令>` | `pass` / `fail` / `not run` |
| 示例：type-check | `<真实命令>` | `pass` / `fail` / `not run` |
| 示例：tests | `<真实命令>` | `pass` / `fail` / `not run` |

## 人工验证

- 当前状态：`pass` / `fail` / `not run`
- 证据缺口：`none` / `<缺口说明>`
- 人工验证说明：

## 同步结论

- spec / 文档同步：`done` / `not needed` / `pending`
- 隐藏目录联动同步：`done` / `not needed` / `pending`
- child-task parent record sync：`not applicable` / `done` / `pending`
