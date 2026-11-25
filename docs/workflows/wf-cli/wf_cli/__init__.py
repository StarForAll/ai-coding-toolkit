"""System-level wf command (distribution package, not a target-project asset)."""

__all__ = ["__version__"]

from .version import cli_version

__version__ = cli_version()