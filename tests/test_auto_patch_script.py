"""End-to-end tests for the auto_patch.sh shell entrypoint.

These exist because the shell entrypoint was previously untested: a `else:`
Python-ism silently stripped the else-branch off the backup guard, so no backup
was ever created on a first run even though `bash -n` reported the file clean.
CI only ever ran pytest and ruff, both Python-only, so nothing caught it.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

DRIVER = "zigbee-lock"
MODEL = "YRD226 TSDB"
MANUFACTURER = "Yale"
ATTRIBUTES = "Language:AutoRelockTime"


@pytest.fixture()
def auto_patch_sandbox(tmp_path: Path, repo_root: Path) -> Path:
    """A throwaway copy of auto_patch/ so the script can `cd` into its own dir."""
    sandbox = tmp_path / "auto_patch"
    shutil.copytree(repo_root / "auto_patch", sandbox)
    return sandbox


@pytest.fixture()
def script_env(tmp_path: Path) -> dict[str, str]:
    """Make the script's bare `python3` resolve to the interpreter running pytest.

    Without this the test depends on whatever `python3` happens to be on PATH
    having PyYAML installed, which is not true inside a virtualenv.
    """
    shim = tmp_path / "shim-bin"
    shim.mkdir()
    (shim / "python3").symlink_to(sys.executable)
    env = dict(os.environ)
    env["PATH"] = f"{shim}{os.pathsep}{env['PATH']}"
    return env


def run_script(sandbox: Path, env: dict[str, str], *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(sandbox / "auto_patch.sh"), *args],
        cwd=sandbox,
        env=env,
        capture_output=True,
        text=True,
    )


def test_backup_is_created_on_first_run(auto_patch_sandbox: Path, script_env: dict[str, str]) -> None:
    """Regression: the documented 'automatic backup' guarantee must actually hold."""
    backup = auto_patch_sandbox / f"{DRIVER}-backup"
    assert not backup.exists(), "precondition: no backup before the run"

    result = run_script(auto_patch_sandbox, script_env, DRIVER, MODEL, MANUFACTURER, ATTRIBUTES)

    assert result.returncode == 0, f"script failed:\n{result.stdout}\n{result.stderr}"
    assert backup.is_dir(), "auto_patch.sh must create a backup before patching"
    # The backup must be a faithful copy of the pre-patch driver, not an empty shell.
    assert (backup / "fingerprints.yml").is_file()
    assert (backup / "profiles").is_dir()
    assert (backup / "src").is_dir()


def test_backup_is_reused_without_aborting(auto_patch_sandbox: Path, script_env: dict[str, str]) -> None:
    """Regression: a pre-existing backup used to abort the run at exit 127."""
    backup = auto_patch_sandbox / f"{DRIVER}-backup"
    shutil.copytree(auto_patch_sandbox / DRIVER, backup)

    result = run_script(auto_patch_sandbox, script_env, DRIVER, MODEL, MANUFACTURER, ATTRIBUTES)

    assert result.returncode == 0, f"script failed:\n{result.stdout}\n{result.stderr}"
    assert "command not found" not in result.stderr
    assert "will be reused" in result.stdout


def test_dry_run_leaves_the_tree_untouched(auto_patch_sandbox: Path, script_env: dict[str, str]) -> None:
    patched_profile = auto_patch_sandbox / DRIVER / "profiles" / "base-lock-patch.yml"

    result = run_script(auto_patch_sandbox, script_env, "--dry-run", DRIVER, MODEL, MANUFACTURER, ATTRIBUTES)

    assert result.returncode == 0, f"script failed:\n{result.stdout}\n{result.stderr}"
    assert not (auto_patch_sandbox / f"{DRIVER}-backup").exists()
    assert not patched_profile.exists()


def test_missing_driver_is_rejected(auto_patch_sandbox: Path, script_env: dict[str, str]) -> None:
    result = run_script(auto_patch_sandbox, script_env, "no-such-driver", MODEL, MANUFACTURER, ATTRIBUTES)

    assert result.returncode != 0
    assert "not found" in result.stderr
    assert not (auto_patch_sandbox / "no-such-driver-backup").exists()


def test_wrong_argument_count_is_rejected(auto_patch_sandbox: Path, script_env: dict[str, str]) -> None:
    result = run_script(auto_patch_sandbox, script_env, DRIVER, MODEL)

    assert result.returncode != 0
    assert "Illegal number of arguments" in result.stdout


def test_script_parses_and_avoids_python_style_else(repo_root: Path) -> None:
    """`bash -n` passes on `else:`, so assert on the token directly."""
    script = repo_root / "auto_patch" / "auto_patch.sh"
    assert "else:" not in script.read_text(), "`else:` is not the bash reserved word `else`"
    assert subprocess.run(["bash", "-n", str(script)]).returncode == 0


def test_script_is_executable(repo_root: Path) -> None:
    """README instructs `./auto_patch.sh`; the mode bit has to back that up."""
    assert os.access(repo_root / "auto_patch" / "auto_patch.sh", os.X_OK)
