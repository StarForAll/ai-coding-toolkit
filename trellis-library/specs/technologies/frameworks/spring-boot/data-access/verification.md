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
