# Normative Rules

* Spring Boot tests should choose the narrowest framework slice that still verifies the behavior or wiring risk in question.
* Framework-managed behavior must not be treated as proven when tests bypass the actual slice where that behavior lives.
* Integration-style tests should be used where configuration, web boundaries, security, or persistence wiring materially affect correctness.
* Test structure must not blur the difference between business-logic verification and framework wiring verification.
* Testing conventions should remain consistent enough that confidence claims can be mapped to what was actually exercised.
