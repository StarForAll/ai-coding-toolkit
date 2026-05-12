# Verification

Check the following:

* persistence concerns are clearly separated from domain and orchestration logic
* repositories are not absorbing misplaced workflow logic
* query and transactional assumptions are understandable
* framework convenience is not hiding cross-layer reach-through
* data-access conventions remain consistent across modules
* query composition uses safe parameter binding rather than injection-prone string assembly
* complex query behavior is reviewable in the persistence boundary
* batch size, pagination, and related-data fetch strategy are explicit for large datasets
* persistence-local transaction assumptions stay reviewable where mixed data sources or hidden write coupling would break atomic expectations
* queries and mappings use explicit selected fields where wildcard fetching would create coupling or waste
* field-to-property mapping remains explicit enough for boolean fields and partial updates to stay correct
* updates do not rewrite unrelated fields or issue risky correction SQL without explicit review
* convenience ORM or database features are not hiding portability, performance, or correctness risk
* join shape, aggregate strategy, and index assumptions remain reviewable for cost and correctness
* index naming and uniqueness intent stay consistent enough to infer lookup purpose
* `count`, `NULL`, pagination, and correction-write semantics remain explicit enough to review aggregate accuracy and cost
* join usage remains bounded and supported by appropriate indexing assumptions
* ORM parameter binding and result mapping preserve explicit, safe field-to-type correspondence
* transaction boundaries are not widened by default beyond the actual consistency need
