from pathlib import Path

from auto_patch.patch_subdriver import patch_subdriver


def test_patch_subdriver_adds_template_and_model(driver_copy: Path, driver_config: Path) -> None:
    subdriver_dir = driver_copy / "src" / "lock-patch"
    parent_init = driver_copy / "src" / "init.lua"

    patch_subdriver(
        driver=str(driver_copy),
        manufacturer="Yale",
        model="YRD226 TSDB",
        config_path=driver_config,
        dry_run=False,
    )

    assert subdriver_dir.exists()
    init_path = subdriver_dir / "init.lua"
    assert init_path.exists()
    init_content = init_path.read_text(encoding="utf-8")
    assert 'model = "YRD226 TSDB"' in init_content

    parent_content = parent_init.read_text(encoding="utf-8")
    assert 'require("lock-patch")' in parent_content


def test_patch_subdriver_dry_run(driver_copy: Path, driver_config: Path) -> None:
    subdriver_dir = driver_copy / "src" / "lock-patch"

    patch_subdriver(
        driver=str(driver_copy),
        manufacturer="Yale",
        model="YRD226 TSDB",
        config_path=driver_config,
        dry_run=True,
    )

    assert not subdriver_dir.exists()
