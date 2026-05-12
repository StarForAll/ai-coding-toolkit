# Verification

Check the following:

* tests remain automatic, independent, and repeatable
* assertions are executable rather than delegated to console output or manual inspection
* test sources live in the expected test-only source layout
* test cases intentionally cover correct behavior, boundaries, and error paths
* stronger coverage expectations exist for core or failure-sensitive logic
* tests create their own required fixtures instead of assuming ambient environment state
* hard-to-test design pressure is addressed structurally rather than hidden behind weak tests
* tests preserve automatic, independent, and repeatable AIR-style behavior
* BCDE-style dimensions are covered where the behavior demands them
* baseline versus high-criticality coverage expectations are explicitly distinguished
