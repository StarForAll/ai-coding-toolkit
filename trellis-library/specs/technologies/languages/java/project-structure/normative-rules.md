# Normative Rules

* Java packages should express stable ownership and responsibility boundaries rather than mirroring temporary implementation noise.
* Public package structure must help readers locate domain concepts, entry points, and integration boundaries without hidden tribal knowledge.
* Package boundaries should discourage cyclical dependency and uncontrolled reach-through across unrelated modules.
* Utility and shared packages must not become dumping grounds for bypassing clearer ownership.
* Structural conventions should remain consistent enough that new code is placed predictably.
* Type, method, field, constant, and package naming should follow one consistent convention so intent is recognizable without local exceptions.
* Import organization and source-file dependencies should prefer clarity and explicitness over stylistic churn or hidden wildcard coupling.
* Data-transfer shapes and domain entities should remain distinguishable in naming and placement so boundary crossings stay visible.
* Access modifiers should remain as narrow as practical so constructors, fields, and helpers do not expose wider mutation or instantiation surfaces than the design intends.
* Static access should stay explicit, and utility-style code must not rely on instance references, broad visibility, or catch-all constant holders that blur ownership.
* Comments and API-facing documentation should stay synchronized with structural contracts where naming or boundary semantics would otherwise be ambiguous.
* Naming conventions for interfaces, implementations, enums, and boundary-crossing model types should make role and responsibility visible without local folklore.
* Layer-facing method names should follow a durable action vocabulary so read, write, list, count, create, delete, and update behavior are distinguishable at call sites.
* API-facing types, abstract methods, and extension contracts should carry documentation strong enough for implementers and callers to understand obligations without reading the implementation first.
* Modern Java constructs such as `record` and `sealed` types should be used intentionally where they clarify ownership, immutability, or closed hierarchies rather than preserving boilerplate class patterns by habit.
* Naming suffixes and prefixes for abstractions, implementations, exceptions, enums, and boundary-crossing models should stay consistent enough that `Service`, `Repository`/`DAO`, `DTO`, `VO`, `BO`, `AO`, `Query`, `Abstract`/`Base`, `Exception`, and `Enum` semantics are recognizable without local legend.
* Interface naming should preserve whether the type represents a capability, role contract, or concrete boundary, instead of mixing marker-style and implementation-style names arbitrarily.
* Package and type conventions should leave room for framework-neutral interfaces and modern Java constructs rather than forcing one legacy naming pattern onto all abstractions.
* Javadoc and equivalent contract documentation should exist for abstract methods, interface methods, enums whose values need semantic explanation, and other API surfaces where signatures alone do not communicate obligations.
