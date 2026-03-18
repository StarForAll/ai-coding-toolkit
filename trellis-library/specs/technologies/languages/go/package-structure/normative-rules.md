# Normative Rules

* Go packages should be small enough to communicate a clear purpose and stable enough to justify their exported surface.
* Exported identifiers must represent intentional package contracts rather than incidental implementation details.
* Package boundaries should preserve simple import relationships and avoid artificial layering complexity.
* Internal helpers should remain internal unless a genuine reuse boundary exists.
* Structural simplicity must not be confused with collapsing unrelated responsibilities into one package.
