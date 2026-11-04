# 第二十一轮外部评审的复核与修正（2 项）

- 复核对象：外部评审第 21 轮 2 条（含定向与隔离探针）
- 处置编号 R58；实施与实跑见 `validation.md` §44

## 0. 结论

| # | 原判 | 复核 | 契约依据 | 处置 |
|---|---|---|---|---|
| 1 | 调试阈值消费者丢弃 problem，非法值仍回退 3 | **成立** | 设计稿 §3 | R58-a |
| 2 | `value_of` 的结构/字段分类错误，两个方向都会错 | **成立** | 设计稿 §3「无关配置按局部阻断」 | R58-b |

## 1. 复核

**① 阈值**：`debug_threshold()` 虽然调了统一取值器，却把 `problem` 丢掉、回退 3。探针：一次失败未裁定时，阈值 `1` 正确要求裁定，`"bad"` 静默放行。

**② 分类**：`value_of` 用「错误串是否包含当前键名」来猜结构问题，而且只在键缺失分支消费它，于是两头都错：
- `tdd_default` 非法 + `spec_verify_days` 缺失 → 把无关字段错当成结构问题，误阻断周期判断（扩散）；
- `schema_version: 999` + 周期合法 → 键存在分支不看结构问题，Check 直接 pass（漏阻）。

## 2. 处置（R58）

- `load_project_config` 的 problems 改为结构化 `{level, key, message}`；`level` 取 `structure`（schema_version 不受支持、配置整体不可读）或 `field`（具体键非法）。`project_id`/`python_executable` 归为 field。
- `value_of` 按 `level` 分类：`structure` 约束所有相关键；`field` 只影响它自己；无关键的 field 错误不扩散。键缺失且配置缺失（允许缺失）时取缺省。
- `debug_threshold()`: 有 problem 即抛 `WF_CAPABILITY_UNAVAILABLE`（facts 带键名），不再回退。
- Check 侧把 `config_problems` 格式化为消息串（facts 保持可读），周期问题照旧阻断。

## 3. 边界

- 不新增原因码：配置不可用走 `WF_CAPABILITY_UNAVAILABLE`。
- 不整体阻断：只有结构级问题才约束全部键，字段级仍局部。
- 不把「配置文件缺失且允许缺失」误判为非法（初始化任务必经）。

## 4. 对收口状态的影响

属「统一入口只接了一半 + 分类错」：修了函数名不等于修了行为。落地后需重跑 Check/门禁相关（CP1/CP3/CP5、R13/R18/R21/R34/R43/R56/R57）与三夹具全流程、F0。
