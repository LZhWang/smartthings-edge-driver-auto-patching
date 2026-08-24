"""Safe construction of the Lua fragments the patcher writes into a driver.

`patch_subdriver` edits Lua source that a SmartThings hub executes at driver
load time. Any value interpolated into that source is therefore reaching a code
sink, not a data sink, and the consequence of getting it wrong is worse than a
stray file: attacker-chosen Lua running in a driver that operates the user's
locks.

The values that land there — a device model and manufacturer — are matched
against the driver's own `fingerprints.yml`, so in practice an operator copies
them out of a file authored by whoever published that driver. Treating them as
trusted because they arrived as command-line arguments confuses "the operator
typed it" with "the operator chose it".

Found during the audit that followed the `deviceProfileName` report in
`SECURITY.md`; see also `auto_patch/paths.py` for the filesystem counterpart.
"""

from __future__ import annotations


class UnsafeLuaValueError(ValueError):
    """A value could not be represented safely inside generated Lua."""


def lua_string(value: str, *, field: str) -> str:
    """Return ``value`` as a quoted Lua string literal, escaped.

    Backslash and double quote are escaped so the value cannot terminate its own
    literal. Control characters — newlines included — are rejected outright
    rather than escaped: no legitimate device model contains one, and refusing
    is easier to verify than an escaping table.
    """
    if not isinstance(value, str):
        raise UnsafeLuaValueError(f"{field} must be a string, got {type(value).__name__}")
    for character in value:
        if ord(character) < 0x20 or ord(character) == 0x7F:
            raise UnsafeLuaValueError(
                f"{field} must not contain control characters, got {value!r}",
            )
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'
