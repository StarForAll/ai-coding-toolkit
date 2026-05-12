# Normative Rules

* Spring Boot services should coordinate use cases, transactions, and cross-repository workflow without becoming an unbounded dumping ground for every helper concern.
* Service-layer boundaries must keep orchestration distinguishable from transport handling, persistence detail, and framework configuration.
* Transaction ownership should be explicit at the service boundary that controls multi-step consistency, rather than scattered across unrelated helpers.
* Service logic should be decomposed when branching, side effects, or dependency count make one service method unreadable to review for correctness.
* Framework proxy behavior such as transaction interception must not be assumed to work through self-invocation or other call paths that bypass the managed boundary.
* Spring-managed asynchronous dispatch such as `@Async` should use an explicit executor policy rather than relying on opaque container defaults whose concurrency behavior is not reviewable.
* Service code must not assume transaction interception, self-invocation behavior, or request-scoped context survive unchanged across an asynchronous dispatch boundary.
* Service methods that trigger asynchronous, integration, or follow-up side effects should make ordering, retry, and failure expectations visible rather than hiding them behind incidental helper calls.
