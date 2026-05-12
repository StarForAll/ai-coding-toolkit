# Normative Rules

* Type choices must preserve business meaning and operational safety rather than optimizing only for local coding convenience.
* Primitive and wrapper usage should remain intentional, especially where `null` carries domain meaning or absent-state semantics across persistence, RPC, or serialization boundaries.
* Numeric modeling must preserve correctness for the domain, and precision-sensitive values must not rely on floating-point equality or lossy decimal construction.
* Equality and identity semantics must remain explicit enough that value comparison, deduplication, and cache-key behavior are predictable.
* Objects used as map keys, set members, or deduplicated values must keep `equals` and `hashCode` consistent with the identity semantics they claim to represent.
* Mutable objects must not hide unsafe default values or constructor-side business logic that can silently alter persistence or transport state.
* Data-carrier objects should expose state in one predictable way, without competing accessor conventions that make serialization or mapping ambiguous.
* Constants, enums, and bounded value sets should model domain intent explicitly instead of scattering magic values through call sites.
* Constant ownership should remain grouped by responsibility and reuse scope rather than converging into one global constant dump that obscures semantics.
* Constant naming should stay explicit and stable enough that readers can infer purpose without tracing every usage site.
* Unexplained magic literals must not define business meaning directly at call sites where named constants, enums, or dedicated value types would make the rule explicit.
* Literal forms for numeric types should remain unambiguous enough that reviewers can distinguish integral width and precision intent without relying on typography guesses.
* Precision-sensitive decimal values should use construction and comparison paths that preserve domain correctness rather than leaking binary-floating shortcuts into business logic.
* Serializable or persistence-facing object evolution should preserve compatibility expectations explicitly, especially when identity, default values, or serialization metadata influence external behavior.
* Date, time, and format-pattern usage must preserve modern Java time semantics explicitly enough that calendar year, week-based year, timezone, and formatter-thread-safety assumptions are not left to legacy defaults.
