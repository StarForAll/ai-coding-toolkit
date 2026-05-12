# Verification

Check the following:

* transport, validation, authorization, orchestration, and domain execution boundaries are clear
* framework defaults are not hiding contract drift
* failure translation and client-visible behavior are predictable
* controllers are not absorbing domain logic
* request-flow conventions are consistent across endpoints
* HTTP method and route choices align with read versus mutation intent
* malformed-input validation is enforced at the boundary while deeper business validation remains explicit
* request and response contracts do not expose persistence entities directly
* mapping boundaries are explicit enough that shallow-copy helpers do not hide nested-field leakage
* client-facing endpoint behavior is documented or otherwise reviewable at the boundary
* controller branching remains shallow enough that orchestration is still reviewable
* request parameters that can amplify load are validated against explicit operational limits
