"""Tests for the cross-platform patch orchestration."""

from __future__ import annotations

from pathlib import Path

import pytest

from edgeloom import patching
from edgeloom.patching import PatchError, run_patch

MODEL = "YRD226 TSDB"
MANUFACTURER = "Yale"
ATTRIBUTES = "Language:AutoRelockTime"


def test_patch_creates_backup_and_patched_profile(driver_copy: Path) -> None:
    result = run_patch(driver_copy, MODEL, MANUFACTURER, ATTRIBUTES)

    assert result.backup is not None and result.backup.is_dir()
    assert result.profile_name == "base-lock"
    assert (driver_copy / "profiles" / "base-lock-patch.yml").is_file()
    # The backup must hold the pre-patch state, not the patched one.
    assert not (result.backup / "profiles" / "base-lock-patch.yml").exists()


def test_dry_run_writes_nothing(driver_copy: Path) -> None:
    result = run_patch(driver_copy, MODEL, MANUFACTURER, ATTRIBUTES, dry_run=True)

    assert result.backup is None
    assert not (driver_copy / "profiles" / "base-lock-patch.yml").exists()
    assert not driver_copy.with_name(f"{driver_copy.name}-backup").exists()


def test_missing_driver_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(PatchError, match="not found"):
        run_patch(tmp_path / "absent", MODEL, MANUFACTURER, ATTRIBUTES)


def test_failure_rolls_the_driver_back(driver_copy: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A failure in a later step must leave the driver exactly as it was found."""
    before = sorted(p.name for p in (driver_copy / "profiles").iterdir())

    def boom(*args: object, **kwargs: object) -> None:
        raise RuntimeError("step 2 exploded")

    monkeypatch.setattr(patching, "patch_handlers", boom)

    with pytest.raises(PatchError, match="step 2 exploded"):
        run_patch(driver_copy, MODEL, MANUFACTURER, ATTRIBUTES)

    assert driver_copy.is_dir(), "the driver must survive a failed run"
    assert sorted(p.name for p in (driver_copy / "profiles").iterdir()) == before
    assert not driver_copy.with_name(f"{driver_copy.name}-backup").exists()


def test_restore_refuses_to_delete_without_a_backup(driver_copy: Path) -> None:
    """Guards the data-loss path: no backup means the driver is left alone."""
    patching.restore_backup(driver_copy, None)

    assert driver_copy.is_dir()
    assert (driver_copy / "fingerprints.yml").is_file()


def test_existing_backup_is_reused(driver_copy: Path) -> None:
    backup = driver_copy.with_name(f"{driver_copy.name}-backup")
    backup.mkdir()
    (backup / "marker.txt").write_text("pre-existing", encoding="utf-8")

    result = run_patch(driver_copy, MODEL, MANUFACTURER, ATTRIBUTES)

    assert result.backup == backup
    assert (backup / "marker.txt").is_file(), "an existing backup must not be clobbered"
