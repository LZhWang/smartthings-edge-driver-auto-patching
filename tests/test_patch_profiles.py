from pathlib import Path

import yaml

from auto_patch.patch_profiles import patch_profiles


def _load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def test_patch_profiles_creates_backup_and_new_profile(driver_copy: Path, capability_config: Path) -> None:
    fingerprints_path = driver_copy / "fingerprints.yml"
    backup_path = driver_copy / "fingerprints-old.yml"

    patch_profiles(
        driver=str(driver_copy),
        model="YRD226 TSDB",
        manufacturer="Yale",
        attributes="Language:AutoRelockTime",
        config_path=capability_config,
        dry_run=False,
    )

    assert backup_path.exists()

    fingerprints = _load_yaml(fingerprints_path)
    patched_entries = [d for d in fingerprints["zigbeeManufacturer"] if d["model"] == "YRD226 TSDB"]
    assert patched_entries, "Expected matching fingerprint entry"
    assert patched_entries[0]["deviceProfileName"].endswith("-patch")

    patched_profile = driver_copy / "profiles" / "base-lock-patch.yml"
    assert patched_profile.exists()
    profile_content = _load_yaml(patched_profile)
    capability_ids = [cap["id"] for cap in profile_content["components"][0]["capabilities"]]
    assert "adminmusic34435.language" in capability_ids
    assert "adminmusic34435.autoRelockTime" in capability_ids


def test_patch_profiles_dry_run_does_not_modify_files(driver_copy: Path, capability_config: Path) -> None:
    patch_profiles(
        driver=str(driver_copy),
        model="YRD226 TSDB",
        manufacturer="Yale",
        attributes="Language",
        config_path=capability_config,
        dry_run=True,
    )

    backup_path = driver_copy / "fingerprints-old.yml"
    patched_profile = driver_copy / "profiles" / "base-lock-patch.yml"
    assert not backup_path.exists()
    assert not patched_profile.exists()
