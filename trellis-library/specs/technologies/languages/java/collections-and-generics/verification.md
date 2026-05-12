# Verification

Check the following:

* collection mutability expectations are explicit for views, singleton helpers, and adapter-backed collections
* subviews or slices are not treated as independent copies when they remain coupled to the source collection
* iteration and mutation behavior is safe for the chosen access pattern
* wildcard and generic-bound choices communicate producer versus consumer intent clearly enough for callers
* raw collections or unchecked assignments do not hide later cast failures
* collection and array conversions preserve the intended runtime type and mutability semantics
* collection sizing and lookup choices reflect expected scale and access patterns
* custom comparators satisfy ordering requirements for sorting and ordered containers
* stable regular-expression or parsing helpers do not pay avoidable recompilation cost on ordinary hot paths
