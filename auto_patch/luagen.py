"""Safe construction of the Lua fragments the patcher writes into a driver.

`patch_subdriver` edits Lua source, and interpolating a raw string into it means
any value containing a double quote or backslash silently produces broken Lua
while the patch reports success. That is the bug this module exists to prevent:
a correctness one.

It is deliberately *not* framed as a security boundary. This was investigated as
a possible injection vulnerability and the threat model does not hold: the only
party who can get a crafted value this far is the driver publisher, and they
already ship every `src/*.lua` in the driver — EdgeLoom copies those through
byte-identical, with no vetting, and the hub executes them at the driver's main
entry point. An injected subdriver line is a strictly less privileged, strictly
more expensive route to something the publisher already has. The operator's own
`--model` argument is documented as coming from the SmartThings Advanced Web App
(`docs/patching.md`), not from driver files.

Escaping is still correct to do, and cheap. See `auto_patch/paths.py` for the
filesystem counterpart, which *is* a security boundary.
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
