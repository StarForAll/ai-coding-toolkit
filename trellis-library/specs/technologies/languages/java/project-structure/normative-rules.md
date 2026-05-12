# Normative Rules

* Java packages should express stable ownership and responsibility boundaries rather than mirroring temporary implementation noise.
* Public package structure must help readers locate domain concepts, entry points, and integration boundaries without hidden tribal knowledge.
* Package boundaries should discourage cyclical dependency and uncontrolled reach-through across unrelated modules.
* Utility and shared packages must not become dumping grounds for bypassing clearer ownership.
* Structural conventions should remain consistent enough that new code is placed predictably.
* Type, method, field, constant, and package naming should follow one consistent convention so intent is recognizable without local exceptions.
* Import organization and source-file dependencies should prefer clarity and explicitness over stylistic churn or hidden wildcard coupling.
* Data-transfer shapes and domain entities should remain distinguishable in naming and placement so boundary crossings stay visible.
