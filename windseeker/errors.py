from __future__ import annotations


class ImportCycleError(RuntimeError):
    """Raised when the import graph contains one or more cycles."""


class MissingPackageError(RuntimeError):
    """
    Raised when an import references a package we did not find/parse.

    NOTE: Windseeker currently does NOT raise this by default because SysML standard
    libraries may be valid imports but not present in the scanned directory.
    """
