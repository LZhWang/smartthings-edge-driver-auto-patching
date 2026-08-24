"""Argument types shared by the ``edgeloom`` and ``discover_drivers`` CLIs.

Deliberately dependency-free. ``edgeloom/cli.py`` builds its parser on every
invocation, so it cannot import ``discovery`` to reach a validator there without
pulling ``requests`` and ``yaml`` behind unrelated subcommands.
"""

from __future__ import annotations

import argparse


def non_negative_int(value: str) -> int:
    """Parse a non-negative integer, rejecting negatives at the CLI boundary.

    A negative bound has no meaning for ``--limit``: the two discovery paths
    order their guard differently, so a negative would silently mean "one
    driver" locally and "none" remotely. Refusing it is clearer than agreeing
    on an arbitrary reading.
    """
    try:
        parsed = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected an integer, got {value!r}") from None
    if parsed < 0:
        raise argparse.ArgumentTypeError(f"expected a non-negative integer, got {parsed}")
    return parsed
