# Verification

Check the following:

* network behavior accounts for latency, interruption, and partial connectivity
* loading, cancellation, timeout, and stale-response handling are explicit
* network-driven states are meaningfully distinguished
* retry and refresh behavior do not create uncontrolled amplification
* degraded or reordered responses remain understandable
