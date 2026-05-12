# Scope Boundary

This concern covers Spring Boot service-layer responsibility, orchestration boundaries, transaction ownership, framework proxy semantics, and service-triggered asynchronous dispatch assumptions that affect business coordination.

It does not replace domain modeling, low-level repository query rules, or generic backend runtime policy. Persistence-local query shape and repository-facing transaction behavior belong to the Spring Boot Data Access concern, while generic job ownership, retry, and failure visibility remain in the backend-service async concern.
