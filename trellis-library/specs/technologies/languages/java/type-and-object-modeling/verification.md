# Verification

Check the following:

* type choices preserve business meaning and operational safety rather than local convenience only
* primitive versus wrapper choices match the nullability and boundary semantics the code relies on
* precision-sensitive values are not modeled with unsafe floating-point equality or lossy decimal construction
* equality and identity semantics are reviewable for values used in comparison, deduplication, or keyed collections
* objects used in sets or as map keys keep `equals` and `hashCode` aligned
* POJO defaults and constructors are not silently mutating business state
* object state is exposed through one predictable accessor convention
* bounded values use explicit constants or enums instead of ad hoc magic values
* constants are grouped by responsibility and reuse scope rather than dumped globally
* constant naming remains explicit enough to communicate purpose
* unexplained magic literals are not defining domain rules directly at call sites
* numeric literal forms remain unambiguous for width and precision intent
* decimal construction and comparison preserve precision-sensitive business correctness
* compatibility expectations for serializable or persistence-facing objects are explicit where evolution matters
* date, time, and format-pattern usage does not hide year, timezone, or formatter-safety assumptions behind legacy defaults
