# 提炼 java-spring 文档到 trellis-library

## Goal

将项目根目录的 `java-spring.md` 从单篇混合规范文档提炼为 `trellis-library/` 中可复用、可注册、可组合的规范资产。结果应符合现有 taxonomy 和 manifest 约定，优先复用或增强已有 Java / Spring Boot / backend-service / universal-domains concerns，避免把跨技术栈规则错误固化为 Spring 专属规范。

## What I already know

* 源文档 `java-spring.md` 是一份中文混合规范，覆盖命名、日志、异常、Controller/Service/Mapper、参数校验、幂等、并发控制、缓存、对象转换、配置安全、数据库设计、事务、异步、分布式事务、安全、性能、测试、代码评审等主题。
* `trellis-library/` 的默认语言为 English，规范资产需要遵守 4 文件 complex concern 结构和 `manifest.yaml` 注册规则。
* 现有 Java / Spring Boot 相关 concern 只有：
  * `spec.technologies.languages.java-project-structure`
  * `spec.technologies.languages.java-error-handling`
  * `spec.technologies.frameworks.spring-boot-application-structure`
  * `spec.technologies.frameworks.spring-boot-web-layer`
  * `spec.technologies.frameworks.spring-boot-data-access`
  * `spec.technologies.frameworks.spring-boot-security`
  * `spec.technologies.frameworks.spring-boot-testing`
* 现有跨栈 concern 还覆盖：
  * `spec.universal-domains.data.caching-and-consistency`
  * `spec.universal-domains.data.data-integrity`
  * `spec.universal-domains.data.database-schema`
  * `spec.universal-domains.security.input-validation`
  * `spec.universal-domains.security.secrets-and-config`
  * `spec.platforms.backend-service.api-serving`
  * `spec.platforms.backend-service.service-runtime`
  * `spec.platforms.backend-service.async-jobs-and-schedulers`
  * `spec.platforms.backend-service.observability-and-operations`
* `examples/assembled-packs/java-spring-service-foundation.md` 和 `pack.java-spring-service-foundation` 已经存在，当前选择了一组 Java/Spring/Backend 基础资产。

## Assumptions (temporary)

* 用户的“提炼”目标是把可复用知识沉淀到 `trellis-library`，而不是保留一份单独的 `java-spring.md` 镜像版本。
* 对于明显带有项目工具偏好的内容，例如 Apifox / Nacos / RocketMQ 事务消息，如果不能抽象成跨项目可复用规则，应避免强行入库。
* 本次任务可以对已有 concern 进行补充，并在确有缺口时新增少量 concern；不要求完整覆盖 `java-spring.md` 的每一条原文。

## Open Questions

* 无阻塞问题。目录归类和资产边界可通过现有库结构与源文档内容直接判断。

## Requirements (evolving)

* 将 `java-spring.md` 中可复用的内容映射到 `trellis-library/` 的合适 concern，而不是简单复制整篇文档。
* 对已存在 concern 的重叠主题，优先补充 `normative-rules.md` 与 `verification.md`。
* 对确有结构性缺口且具备复用价值的主题，可新增规范 concern，并按 4 文件结构注册到 `manifest.yaml`。
* 新增或更新的内容必须用 English 编写。
* 不把明显的供应商/项目绑定内容直接写成通用规范。
* 如新增 concern 对 Java Spring 基础包具有普适价值，应同步更新 `examples/assembled-packs/java-spring-service-foundation.md` 与 `pack.java-spring-service-foundation`。

## Content Mapping

### Update Existing Concerns

* `spec.technologies.languages.java-project-structure`
  * 吸收命名约定、import 规则、依赖注入和对象转换中与 Java 代码组织相关的内容
* `spec.technologies.languages.java-error-handling`
  * 吸收统一异常处理、异常分类、避免吞异常/重复日志等内容
* `spec.technologies.frameworks.spring-boot-web-layer`
  * 吸收 Controller 职责、HTTP 方法约定、统一返回、参数校验边界、接口文档的一般化约束
* `spec.technologies.frameworks.spring-boot-data-access`
  * 吸收 Mapper 层规则、SQL 安全、批量处理、事务边界、N+1 查询、深度分页等内容
* `spec.technologies.frameworks.spring-boot-security`
  * 吸收 XSS、防越权、敏感操作审计等 Spring Web / Security 相关内容
* `spec.technologies.frameworks.spring-boot-testing`
  * 吸收 Spring 相关测试边界、Mock 覆盖、测试命名等内容

### Update Existing Cross-Stack Concerns

* `spec.universal-domains.data.caching-and-consistency`
  * 吸收缓存 TTL、空值缓存、防穿透、更新策略等可复用规则
* `spec.universal-domains.data.data-integrity`
  * 吸收幂等性、乐观锁、分布式锁适用边界等完整性约束
* `spec.universal-domains.data.database-schema`
  * 吸收表设计、通用字段、命名、索引等数据库建模规范
* `spec.universal-domains.security.input-validation`
  * 吸收参数校验边界、嵌套校验、业务校验与 shape 校验分离等规则
* `spec.universal-domains.security.secrets-and-config`
  * 吸收敏感配置不得硬编码、不得写日志等内容
* `spec.platforms.backend-service.api-serving`
  * 吸收接口幂等、导出/分页负载与服务 API 行为相关的规则
* `spec.platforms.backend-service.async-jobs-and-schedulers`
  * 吸收异步处理的重试、幂等、可观测性约束
* `spec.platforms.backend-service.observability-and-operations`
  * 吸收结构化日志、关键节点日志、敏感信息脱敏等通用可观测性要求

### Likely New Concerns

* `spec.technologies.frameworks.spring-boot.service-layer`
  * 处理 Service 职责、复杂度控制、事务编排边界、自调用代理失效等 Spring service 语义

### Explicitly Out of Scope

* Apifox、Nacos、RocketMQ 等具体产品名绑定的工具使用说明，除非能抽象成可复用且不依赖厂商名的规则
* 逐字保留中文原文
* 生成编译后的“Java/Spring 总规范”汇总文档

## Acceptance Criteria (evolving)

* [ ] `java-spring.md` 中的主要可复用主题已经被映射到 `trellis-library` 中的合适资产，而不是停留在单独源文档
* [ ] 如有新增 concern，目录结构与 `manifest.yaml` 注册完整且一致
* [ ] Java Spring foundation example/pack 在需要时纳入新 concern
* [ ] `python3 trellis-library/cli.py validate --strict-warnings` 通过

## Definition of Done (team quality bar)

* Relevant spec assets updated or created
* `manifest.yaml` updated if asset set changes
* Validation run with truthful result reported
* No unrelated files reverted

## Out of Scope (explicit)

* 删除或重写用户未要求的其他技术栈规范
* 引入新的脚本、schema 或 checklist，除非实施过程中发现它们是验证所必需

## Technical Notes

* 源文档：`java-spring.md`
* 关键结构参考：
  * `trellis-library/README.md`
  * `trellis-library/taxonomy.md`
  * `.trellis/spec/library-assets/spec-authoring.md`
  * `.trellis/spec/library-assets/manifest-maintenance.md`
* 当前 Java Spring 示例包：
  * `trellis-library/examples/assembled-packs/java-spring-service-foundation.md`
  * `trellis-library/manifest.yaml` 中 `pack.java-spring-service-foundation`
