# DDD

## 核心领域对象

- `InspectionRecord`: 单次巡检记录
- `IssueSummary`: 汇总后的异常问题视图
- `AuthorizationState`: 试运行 / 已到期 / 永久授权

## 领域规则

- 试运行到期后禁止新增和编辑，但保留历史查看与导出
- 永久授权切换后不需要迁移历史数据
