# Verification

Check the following:

* freshness and invalidation expectations are explicit
* strong-consistency assumptions are not silently overstated
* invalidation ownership is clear
* read optimization does not hide correctness risk
* delayed or probabilistic consistency is visible at affected boundaries
* cached entries have a bounded lifetime or explicit refresh discipline
* miss handling and null-result strategy do not create avoidable penetration risk
* source-of-truth write and cache invalidation ordering is explicit
