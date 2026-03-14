# Marketplace

这里存放基于 **trellis 框架** 的个人模板集合，用于在不同场景下快速复用结构化模板（提示词/任务分解/脚手架等）。

## 建议组织方式

```text
marketplace/
  README.md
  <scenario>/
    README.md          # 场景说明、输入输出约定、适用边界
    <template-id>/     # trellis 模板（按实际框架要求组织文件）
```

## 建议约定

- 以“场景”为一级分类：如 `coding/`、`review/`、`debug/`、`docs/` 等。
- 每个模板目录必须有可读的 `README.md`（目的、如何使用、最小示例、注意事项）。
- 若模板依赖特定工具/模型/环境变量，在 `README.md` 明确标注并给出降级方案。

