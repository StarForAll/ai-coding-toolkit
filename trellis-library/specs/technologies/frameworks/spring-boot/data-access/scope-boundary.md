# Scope Boundary

This concern covers Spring Boot data-access boundaries, persistence responsibilities, repository-facing structure, and persistence-local transaction assumptions.

It does not replace database-schema rules or vendor-specific query tuning. Transaction orchestration ownership, self-invocation behavior, and other service-boundary proxy assumptions belong to the Spring Boot Service Layer concern rather than this persistence concern.
