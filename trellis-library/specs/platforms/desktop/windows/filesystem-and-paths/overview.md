# Windows Filesystem And Paths

## Purpose

Define reusable Windows-specific desktop rules for filesystem access, path
handling, install-location assumptions, and file-behavior differences that can
affect correctness on the Windows platform.

## Applicability

Use this concern when desktop software runs on Windows and behavior depends on
path construction, writable locations, install directories, file locking, or
other filesystem semantics that differ from Unix-like environments.
