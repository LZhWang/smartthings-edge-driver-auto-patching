"""Containment helpers for paths built from driver-supplied data.

A driver's ``fingerprints.yml`` is authored by whoever published the driver,
not by the person running EdgeLoom. Values read out of it therefore reach the
patcher as untrusted input, and ``deviceProfileName`` in particular is used to
build filesystem paths. Two properties are enforced here, deliberately
overlapping:

``safe_identifier`` rejects anything that is not a bare name, so a traversal
never gets as far as path construction. ``contained_path`` re-checks the
resolved destination at the write boundary, so a bug or a symlink upstream of
the join still cannot place a write outside the driver directory.

Reported against 3a30b375 by Marcos Maia Jr. via the process in SECURITY.md.
"""

from __future__ import annotations

import re
from pathlib import Path

# Real SmartThings profile names look like `base-lock` or `lock-without-codes`.
# The grammar is deliberately narrower than "valid filename": it is an
# identifier, and anything richer is a signal rather than a case to support.
_IDENTIFIER = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._-]*\Z")


class UnsafePathError(ValueError):
    """A driver-supplied value would have produced a write outside the driver."""


def safe_identifier(value: str, *, field: str) -> str:
    """Return ``value`` unchanged, or raise if it is not a bare identifier.

    Rejects absolute paths, parent-directory components, path separators, and
    leading dots — none of which can appear in a legitimate profile name.
    """
    if not isinstance(value, str) or not value:
        raise UnsafePathError(f"{field} must be a non-empty string, got {value!r}")
    if not _IDENTIFIER.match(value):
        raise UnsafePathError(
            f"{field} must be a bare name matching [A-Za-z0-9][A-Za-z0-9._-]*, "
            f"got {value!r}. Path separators, parent components and absolute "
            f"paths are not permitted.",
        )
    if ".." in value.split("."):
        raise UnsafePathError(f"{field} must not contain a parent component, got {value!r}")
    return value


def contained_path(root: Path, *parts: str) -> Path:
    """Join ``parts`` onto ``root`` and require the result to stay inside it.

    ``root`` must be a **trusted anchor** — in practice the driver directory the
    operator named on the command line. It is resolved once, and everything
    reached through ``parts`` is judged against that resolved anchor.

    Passing an attacker-influenced directory as ``root`` defeats the check,
    because resolving it follows any symlink it happens to be. An earlier
    revision did exactly that: it took ``driver_dir / "profiles"`` as the root,
    so a driver shipping ``profiles`` as a symlink relocated the anchor itself
    and every write under it was judged "contained". Anchor at the driver.

    Symlinks among the components are refused outright rather than followed and
    then judged. A legitimate Edge driver has no reason to ship ``profiles`` or
    ``src`` as a link, and refusing is easier to verify than reasoning about
    where each link lands — including the case where a link is swapped between
    the check and the write.
    """
    root_resolved = root.resolve()
    candidate = root_resolved

    for part in parts:
        candidate = candidate / part
        if candidate.is_symlink():
            raise UnsafePathError(
                f"refusing to follow a symlink inside the driver: {candidate}",
            )

    resolved = candidate.resolve()
    if resolved != root_resolved and root_resolved not in resolved.parents:
        raise UnsafePathError(
            f"refusing to write outside the driver directory: {resolved} is not under {root_resolved}",
        )
    return resolved
