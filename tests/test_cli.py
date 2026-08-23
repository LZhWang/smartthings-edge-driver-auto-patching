"""Tests for the unified `edgeloom` entrypoint."""

from __future__ import annotations

from pathlib import Path

import pytest

from edgeloom import __version__
from edgeloom.cli import main


def test_version_flag(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_bare_invocation_prints_help(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([]) == 2
    assert "usage: edgeloom" in capsys.readouterr().out


@pytest.mark.parametrize("command", ["patch", "translate", "discover", "validate"])
def test_every_subcommand_is_registered(command: str, capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main([command, "--help"])
    assert exc.value.code == 0
    assert command in capsys.readouterr().out


def test_validate_accepts_verbose_on_either_side(repo_root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    target = str(repo_root / "auto_patch" / "capability-map.yaml")
    assert main(["validate", target, "-v"]) == 0
    after = capsys.readouterr().out
    assert main(["-v", "validate", target]) == 0
    before = capsys.readouterr().out
    assert "capability-map" in after and "capability-map" in before


def test_validate_reports_failures_and_exits_nonzero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text("name: x\ncomponents: []\n", encoding="utf-8")

    assert main(["validate", str(bad)]) == 1
    out = capsys.readouterr().out
    assert "FAIL" in out
    assert "1 failed" in out


def test_validate_errors_when_nothing_was_checked(tmp_path: Path) -> None:
    """An empty run must not be reported as success."""
    (tmp_path / "unrelated.yaml").write_text("hello: world\n", encoding="utf-8")
    assert main(["validate", str(tmp_path)]) == 1


def test_validate_rejects_a_missing_path(tmp_path: Path) -> None:
    assert main(["validate", str(tmp_path / "nope")]) == 1


def test_patch_reports_failure_cleanly(tmp_path: Path) -> None:
    assert main(["patch", str(tmp_path / "absent"), "M", "Mfg"]) == 1


def test_translate_requires_a_token(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("HA_TOKEN", raising=False)
    assert main(["translate", "--ha-url", "http://ha.local", "--output", str(tmp_path)]) == 1


def test_discover_requires_local_dir_for_local_source(tmp_path: Path) -> None:
    assert main(["discover", "--source", "local", "--output", str(tmp_path / "c.json")]) == 1
