# Normative Rules

* Extension points must be intentional and bounded, not accidental leakage of internal implementation details.
* Core behavior and extension behavior must be distinguishable so failures can be traced and contained.
* Extension contracts must define what may vary and what must remain stable.
* New extension points must not be introduced only to avoid making a concrete design decision.
* Extension mechanisms should minimize blast radius when custom logic fails or is misused.
