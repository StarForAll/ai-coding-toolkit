# Normative Rules

* Test doubles should isolate meaningful boundaries, not hide the behavior actually under risk.
* Mocking should preserve confidence in contract behavior rather than merely making tests easier to write.
* Mocks, fakes, and stubs must remain explicit about what real behavior they are standing in for.
* A test suite must not rely so heavily on mocked behavior that integration drift becomes invisible.
* When mocking creates blind spots, those gaps should be balanced by stronger higher-level verification.
