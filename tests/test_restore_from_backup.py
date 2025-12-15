from pathlib import Path

import pytest

from auto_patch import restore_from_backup


def test_successful_restore(monkeypatch, tmp_path: Path) -> None:
    tmp_root = tmp_path / "auto_patch"
    tmp_root.mkdir()

    active = tmp_root / "zigbee-lock"
    backup = tmp_root / "zigbee-lock-backup"
    active.mkdir()
    backup.mkdir()

    (active / "fingerprints.yml").write_text("patched\n", encoding="utf-8")
    (backup / "fingerprints.yml").write_text("original\n", encoding="utf-8")

    monkeypatch.setattr(restore_from_backup, "SCRIPT_ROOT", tmp_root)

    patched_dir = restore_from_backup.restore_driver("zigbee-lock", dry_run=False)

    restored_file = tmp_root / "zigbee-lock" / "fingerprints.yml"
    assert restored_file.read_text(encoding="utf-8") == "original\n"
    assert not backup.exists()

    assert patched_dir is not None
    assert patched_dir.exists()
    assert patched_dir.name.startswith("zigbee-lock-patched-")
    assert (patched_dir / "fingerprints.yml").read_text(encoding="utf-8") == "patched\n"


def test_missing_backup_raises(monkeypatch, tmp_path: Path) -> None:
    tmp_root = tmp_path / "auto_patch"
    tmp_root.mkdir()

    active = tmp_root / "zigbee-lock"
    active.mkdir()
    (active / "fingerprints.yml").write_text("patched\n", encoding="utf-8")

    monkeypatch.setattr(restore_from_backup, "SCRIPT_ROOT", tmp_root)

    with pytest.raises(FileNotFoundError):
        restore_from_backup.restore_driver("zigbee-lock", dry_run=False)


def test_dry_run_no_changes(monkeypatch, tmp_path: Path) -> None:
    tmp_root = tmp_path / "auto_patch"
    tmp_root.mkdir()

    active = tmp_root / "zigbee-lock"
    backup = tmp_root / "zigbee-lock-backup"
    active.mkdir()
    backup.mkdir()

    (active / "fingerprints.yml").write_text("patched\n", encoding="utf-8")
    (backup / "fingerprints.yml").write_text("original\n", encoding="utf-8")

    monkeypatch.setattr(restore_from_backup, "SCRIPT_ROOT", tmp_root)

    patched_dir = restore_from_backup.restore_driver("zigbee-lock", dry_run=True)

    assert patched_dir is not None
    assert not patched_dir.exists()
    assert (active / "fingerprints.yml").read_text(encoding="utf-8") == "patched\n"
    assert (backup / "fingerprints.yml").read_text(encoding="utf-8") == "original\n"
    patched_dirs = [path for path in tmp_root.iterdir() if path.name.startswith("zigbee-lock-patched-")]
    assert not patched_dirs
