from pathlib import Path

from auto_patch.patch_handlers import patch_handlers


def test_patch_handlers_copies_lua_file(driver_copy: Path, driver_config: Path) -> None:
    destination = driver_copy / "src" / "lock_patch.lua"
    assert not destination.exists()

    patch_handlers(driver=str(driver_copy), config_path=driver_config, dry_run=False)
    assert destination.exists()


def test_patch_handlers_dry_run_skips_copy(driver_copy: Path, driver_config: Path) -> None:
    destination = driver_copy / "src" / "lock_patch.lua"

    patch_handlers(driver=str(driver_copy), config_path=driver_config, dry_run=True)
    assert not destination.exists()
