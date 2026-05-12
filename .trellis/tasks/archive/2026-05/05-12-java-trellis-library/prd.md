# 提炼 Java 开发手册技术内容到 trellis-library

## Goal

将 `./tmp/Java开发手册.md` 中仍具复用价值的技术规则提炼到 `trellis-library/` 的合适子目录中，优先补充现有 Java / Spring / universal concern，只有在现有结构无法承载时才新增最小必要 concern，并忽略前言、版本历史等非技术性内容。

## What I already know

* 源文档是中文版《Java 开发手册》，内容覆盖编程规约、异常日志、单元测试、安全规约、MySQL 数据库、工程结构、设计规约。
* `trellis-library/` 的默认语言是 English，规范资产需要遵守 4 文件 concern 结构和 `manifest.yaml` 注册规则。
* 仓库在 2026-05-12 已做过一轮 `java-spring.md` 提炼，当前 `trellis-library` 已存在 Java / Spring Boot / backend-service / universal-domains 相关 concern，不能简单重复迁移。
* 本次源文档覆盖范围比之前的 `java-spring.md` 更宽，包含 Java 语言层编码约定、常量/对象建模、集合/并发、MySQL 与工程结构等主题。

## Assumptions (temporary)

* 用户要的是“沉淀可复用技术规则”，不是保留一本新的 Java 手册副本。
* 源文档中的示例、前言、历史说明、规约等级说明等内容，若不构成可复用技术规范，可直接忽略。
* 能映射到已有 concern 的内容优先补充既有 `normative-rules.md` / `verification.md`，避免新增碎片化资产。

## Open Questions

* 无阻塞问题。是否新增 concern 可通过现有资产覆盖度直接判断。

## Requirements

* 仅提炼 `./tmp/Java开发手册.md` 中的技术内容。
* 非技术性内容不迁移到 `trellis-library/`。
* 新增或更新的 `trellis-library` 资产必须使用 English。
* 优先复用现有 concern；只有存在结构性缺口时才新增 concern 并更新 `manifest.yaml`。
* 如 pack / example 需要显式纳入新增 concern，应同步更新。

## Acceptance Criteria

* [ ] `./tmp/Java开发手册.md` 中主要可复用技术规则已映射到 `trellis-library/` 的合适资产
* [ ] 未将前言、版本历史等非技术性内容写入 `trellis-library/`
* [ ] 若新增资产，目录结构与 `manifest.yaml` 注册保持一致
* [ ] `python3 trellis-library/cli.py validate --strict-warnings` 通过

## Definition of Done

* Relevant library assets updated or created
* Manifest updated if asset set changes
* Validation run and result reported truthfully
* No unrelated files reverted

## Out of Scope

* 逐字翻译或镜像整篇《Java 开发手册》
* 引入与源文档无关的新技术主题
* 修改与本次提炼无关的其他资产

## Technical Notes

* Source document: `tmp/Java开发手册.md`
* Relevant authoring guidance:
  * `.trellis/spec/library-assets/spec-authoring.md`
  * `.trellis/spec/library-assets/manifest-maintenance.md`
  * `.trellis/spec/guides/code-reuse-thinking-guide.md`
  * `.trellis/spec/guides/cross-layer-thinking-guide.md`
