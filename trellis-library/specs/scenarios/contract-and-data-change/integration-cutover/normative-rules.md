# Normative Rules

* Integration cutover must identify the old path, new path, affected consumers, and transition boundary explicitly.
* Cutover plans should make compatibility assumptions, fallback options, and observation points visible before traffic or usage shifts.
* Consumer migration must not rely on silent behavior drift being "close enough" without evidence.
* Dual-running, staged exposure, or rollback options should be considered when the blast radius or uncertainty is meaningful.
* If cutover evidence is incomplete, the remaining transition risk must be visible rather than absorbed into release optimism.
