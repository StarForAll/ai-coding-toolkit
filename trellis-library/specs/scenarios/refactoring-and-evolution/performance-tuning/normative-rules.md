# Normative Rules

* Performance work must start from an identified bottleneck, symptom, or measurable constraint rather than optimization folklore alone.
* Tuning changes should preserve functional behavior unless a deliberate tradeoff is made explicit.
* Optimizations must be verified against relevant measurements or observable behavior, not only code-level intuition.
* Local wins that shift cost to another layer, environment, or user flow must not be treated as clear improvements without broader evidence.
* When measurement quality is weak, the remaining uncertainty must be stated rather than hidden behind confident claims.
