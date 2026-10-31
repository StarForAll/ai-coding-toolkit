# Docs

这里用于存放与 AI 编程相关的笔记、规范、决策记录（ADR）、工具使用手册等。

## 建议内容

- workflow 复盘：如何提问、如何拆解、如何验证
- 工具链说明：常用 CLI、脚本、模型选择策略
- 规范/约定：目录约定、命名约定、可复用模板

## 与 workflow 相关的推荐文档

**独立框架（现行）**

- `docs/workflows/wf-framework-charter.md`：基调与边界（要不要做、边界在哪、何时停止；与设计稿冲突时以此为上位判据）
- `docs/workflows/wf-framework-design.md`：设计契约（状态、门禁、记录、spec、资产与验收）

**较早的 Trellis 内嵌 wf 模块（其“唯一权威”声明仅限该模块，不延伸到独立框架）**

- `docs/workflows/workflow-design.md`：该模块的整体设计（判定与流转权威，仅限该模块）
- `docs/workflows/依赖机制设计说明.md`：该模块的依赖机制细节
- `docs/workflows/workflow-implementation.md`：该模块的实现方案（模块源、写入面与工程契约）
- `docs/workflows/wf-variant.md`：流程变体正文（待迁入模块源模板）

**模块源路径**

- `docs/workflows/新项目开发工作流/`：模块源（旧模块已退役，路径重建中）

> 旧工作流产品的制作规范与演练模板已随旧模块退役（2026-10-28）；需要时按新模块结构重写。

## 其他可复用运行时修复指南

- `docs/Trellis元数据自动提交失败恢复指南.md`：当 Trellis 的 archive / finish-work 自动提交因只读环境失败时，如何修改脚本链路与命令入口，让项目支持恢复命令与提权重试
