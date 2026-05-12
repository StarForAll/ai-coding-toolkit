# Verification

Check the following:

* test scope matches the wiring or behavior risk being checked
* framework behavior is not claimed without testing the relevant slice
* integration tests are used where configuration and wiring matter
* business logic and framework wiring verification remain distinguishable
* confidence claims match what tests actually exercised
* isolated tests cover happy path, boundary conditions, failure branches, and dependency-error behavior where relevant
* test names communicate the behavior and scenario being verified
* assertions are automated rather than delegated to console output or manual inspection
* persistence-touching tests create and clean up their own data assumptions
* tests remain independent of execution order and uncontrolled external environments
