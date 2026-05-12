# Verification

Check the following:

* packages communicate stable ownership and responsibility
* important entry points and domain concepts are discoverable
* package layout does not encourage cyclical or reach-through coupling
* shared code is not a catch-all escape hatch
* placement of new code remains predictable and consistent
* naming conventions are consistent across types, methods, fields, constants, and packages
* import structure does not hide dependency ambiguity through wildcard or disorderly usage
* DTOs, request models, response models, and entities are distinguishable by name or placement
* access modifiers and construction paths do not expose broader surfaces than intended
* static members, utility code, and constant ownership stay explicit rather than blurred across instance boundaries
* comments and API-facing docs still match the structural contracts they describe
* interface, implementation, enum, and model-type naming makes role boundaries visible
* layer-facing method names communicate durable action semantics
* abstract or API-facing contracts have enough documentation for callers and implementers
* `record` and `sealed` usage is intentional where it materially clarifies the model
* suffix and prefix conventions for abstractions, exceptions, enums, and model types remain consistent enough to infer role
* interface naming reflects capability, role contract, or boundary intent instead of arbitrary style mixing
* package and type conventions still leave room for framework-neutral interfaces and modern Java constructs
* abstract methods, interface methods, and semantically significant enum values carry enough documentation to explain obligations
