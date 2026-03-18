# Verification

Check the following:

* dependency direction is explicit for relevant layers or modules
* volatile implementation details are not pulling stable layers upward
* convenience shortcuts are not bypassing the intended dependency graph
* shared abstractions are purposeful rather than catch-all escape hatches
* any dependency exceptions are narrow and explicit
