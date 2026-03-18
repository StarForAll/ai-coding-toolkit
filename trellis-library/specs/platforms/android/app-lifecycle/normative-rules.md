# Normative Rules

* Android application behavior must account for screen pause, stop, resume,
  recreation, and process death where those transitions affect correctness.
* Important user state must not depend solely on in-memory assumptions when the
  OS may reclaim resources or recreate the screen.
* Lifecycle-triggered work should remain predictable across repeated resumes,
  interrupted sessions, and background returns.
* Android-specific lifecycle transitions must not silently duplicate, abandon,
  or partially replay meaningful work without explicit handling.
* Remaining uncertainty about lifecycle restoration should stay visible instead
  of being hidden behind framework convenience.
