"""Regression tests for values interpolated into hub-executed Lua.

`patch_subdriver` rewrites Lua that a SmartThings hub runs at driver load time.
A device model carrying a double quote used to terminate its own string literal
and land arbitrary Lua in that module — a code sink, not a data sink.

The model is matched against the driver's own `fingerprints.yml`, so an operator
copies it out of a file authored by whoever published the driver. Arriving as a
command-line argument does not make it operator-chosen.

Found during the audit that followed the `deviceProfileName` report.
"""

from __future__ import annotations

import pytest

from auto_patch.luagen import UnsafeLuaValueError, lua_string
from auto_patch.patch_subdriver import add_device_model

BREAKOUT = 'X", evil=os.execute("id > /tmp/pwn"), z="'


# --- the escaper on its own -------------------------------------------------


def test_lua_string_escapes_a_quote_so_it_cannot_close_the_literal() -> None:
    assert lua_string('a"b', field="model") == '"a\\"b"'


def test_lua_string_escapes_backslash_before_quote() -> None:
    # A naive quote-only escaper turns `\` + `"` into `\\"`, which closes the
    # literal anyway. Backslash must be doubled first.
    assert lua_string('a\\"b', field="model") == '"a\\\\\\"b"'


@pytest.mark.parametrize("value", ["a\nb", "a\tb", "a\rb", "a\x00b", "a\x7fb"])
def test_lua_string_rejects_control_characters(value: str) -> None:
    with pytest.raises(UnsafeLuaValueError):
        lua_string(value, field="model")


def test_lua_string_passes_a_real_model_through() -> None:
    assert lua_string("YRD226 TSDB", field="model") == '"YRD226 TSDB"'


# --- end to end through the subdriver rewrite -------------------------------


def _subdriver_with_model(tmp_path, model: str, manufacturer: str = "Yale"):
    subdriver = tmp_path / "lock-patch"
    subdriver.mkdir()
    init = subdriver / "init.lua"
    init.write_text(
        'local PATCHED_DEVICE_MODELS = {\n  { mfr = "Yale", model = "YRD226 TSDB" }\n}\n',
        encoding="utf-8",
    )
    add_device_model(subdriver, manufacturer, model, dry_run=False)
    return init.read_text(encoding="utf-8")


def test_breakout_payload_stays_inside_its_string_literal(tmp_path) -> None:
    code = _subdriver_with_model(tmp_path, BREAKOUT)

    line = next(ln for ln in code.splitlines() if "os.execute" in ln)
    # Every quote in the payload must arrive escaped, so the literal that opened
    # after `model = ` is still open when os.execute appears.
    assert 'model = "X\\", evil=os.execute(\\"id > /tmp/pwn\\"), z=\\"" }' in line
    # And the bare, unescaped form that would have executed must be absent.
    assert 'evil=os.execute("id' not in code


def test_a_legitimate_model_is_unchanged(tmp_path) -> None:
    code = _subdriver_with_model(tmp_path, "YRD226 TSDB", "Yale")
    assert '{ mfr = "Yale", model = "YRD226 TSDB" },' in code


def test_a_model_with_a_newline_is_refused(tmp_path) -> None:
    with pytest.raises(UnsafeLuaValueError):
        _subdriver_with_model(tmp_path, "X\nrogue = 1")
