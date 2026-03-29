# Normative Rules

* Parallel work should be split along boundaries that minimize overlapping write scope and hidden coupling.
* Shared assumptions that affect multiple parallel tracks must be made explicit before concurrent execution begins.
* Concurrent work must not rely on silent reversion of another contributor's changes.
* Integration risk should be assessed before declaring parallel streams independently complete.
* When write-scope isolation cannot be maintained, coordination must increase rather than pretending the work is independent.
