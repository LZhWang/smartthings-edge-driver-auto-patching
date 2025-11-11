import shutil
from pathlib import Path

import pytest


@pytest.fixture()
def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture()
def driver_copy(tmp_path, repo_root: Path) -> Path:
    source = repo_root / "auto_patch" / "zigbee-lock"
    destination = tmp_path / "zigbee-lock"
    shutil.copytree(source, destination)
    return destination


@pytest.fixture()
def capability_config(repo_root: Path) -> Path:
    return repo_root / "auto_patch" / "custom_capability_list.config"


@pytest.fixture()
def driver_config(repo_root: Path) -> Path:
    return repo_root / "auto_patch" / "driver2patch.config"
