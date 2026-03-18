# Normative Rules

* Web rendering behavior should account for main-thread pressure, layout cost, visual update timing, and user-perceived responsiveness.
* Performance-sensitive rendering work must not assume that browser scheduling or device capability will hide inefficient behavior.
* Loading, placeholder, and incremental rendering strategies should preserve understandable user feedback under slow or partial conditions.
* Rendering optimizations must not silently degrade accessibility, correctness, or interaction stability.
* When rendering-performance evidence is incomplete, the remaining user-experience risk must remain visible.
