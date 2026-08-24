"""Regression tests for the driver-supplied path containment guards.

Reported against 3a30b375 by Marcos Maia Jr. through SECURITY.md: a
`deviceProfileName` carrying parent components or an absolute path caused
patch_profiles to write a generated profile outside the driver directory.

Two layers are tested separately on purpose. `safe_identifier` rejects the
input before path construction, so an end-to-end test alone would never
execute `contained_path` and the write-boundary guard would go unverified.
"""

from __future__ import annotations

import pytest
import yaml

from auto_patch.patch_profiles import patch_profiles
from auto_patch.paths import UnsafePathError, contained_path, safe_identifier

ESCAPES = [
    "../../../outside",
    "..",
    "a/b",
    "/tmp/absolute",
    "profiles/../../escape",
]


# --- layer 1: the value never becomes a path -------------------------------


@pytest.mark.parametrize("value", ESCAPES)
def test_safe_identifier_rejects_path_like_names(value: str) -> None:
    with pytest.raises(UnsafePathError):
        safe_identifier(value, field="deviceProfileName")


@pytest.mark.parametrize("value", ["base-lock", "lock-battery", "lock-without-codes", "P1.2_x"])
def test_safe_identifier_accepts_real_profile_names(value: str) -> None:
    assert safe_identifier(value, field="deviceProfileName") == value


@pytest.mark.parametrize("value", ["", ".hidden", "-lead"])
def test_safe_identifier_rejects_degenerate_names(value: str) -> None:
    with pytest.raises(UnsafePathError):
        safe_identifier(value, field="deviceProfileName")


# --- layer 2: the write boundary, exercised on its own ---------------------


def test_contained_path_allows_a_child(tmp_path) -> None:
    profiles = tmp_path / "profiles"
    profiles.mkdir()
    assert contained_path(profiles, "ok.yml") == profiles / "ok.yml"


@pytest.mark.parametrize("part", ["../escape.yml", "/tmp/absolute.yml"])
def test_contained_path_rejects_an_escape(tmp_path, part: str) -> None:
    profiles = tmp_path / "profiles"
    profiles.mkdir()
    with pytest.raises(UnsafePathError):
        contained_path(profiles, part)


def test_contained_path_follows_symlinks_before_judging(tmp_path) -> None:
    """A symlinked profiles/ pointing outside the driver must not pass."""
    driver = tmp_path / "driver"
    driver.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (driver / "profiles").symlink_to(outside, target_is_directory=True)

    with pytest.raises(UnsafePathError):
        contained_path(driver, "profiles", "x.yml")


def test_contained_path_rejects_climbing_out_of_profiles(tmp_path) -> None:
    """Inside the driver but outside profiles/ is still not a profile path."""
    profiles = tmp_path / "profiles"
    profiles.mkdir()
    with pytest.raises(UnsafePathError):
        contained_path(profiles, "../sneaky.yml")


# --- end to end: the reported reproduction ---------------------------------


def _write_fingerprints(driver_dir, profile_name: str) -> None:
    (driver_dir / "fingerprints.yml").write_text(
        yaml.safe_dump(
            {
                "zigbeeManufacturer": [
                    {
                        "id": "Yale/YRD226",
                        "deviceLabel": "Yale Lock",
                        "manufacturer": "Yale",
                        "model": "YRD226 TSDB",
                        "deviceProfileName": profile_name,
                    },
                ],
            },
        ),
    )


@pytest.mark.parametrize("hostile", ["../../../escaped", "/tmp/edgeloom-escape-probe"])
def test_patch_profiles_refuses_to_escape_the_driver(driver_copy, capability_config, hostile, tmp_path):
    """The reported reproduction: a hostile driver must not write outside itself."""
    _write_fingerprints(driver_copy, hostile)
    before = {p for p in tmp_path.rglob("*") if p.is_file()}

    with pytest.raises(UnsafePathError):
        patch_profiles(
            str(driver_copy),
            "YRD226 TSDB",
            "Yale",
            "ALL",
            config_path=capability_config,
        )

    after = {p for p in tmp_path.rglob("*") if p.is_file()}
    escaped = {p for p in after - before if "escape" in p.name}
    assert not escaped, f"files written outside the driver: {escaped}"


def test_patch_profiles_still_patches_a_legitimate_driver(driver_copy, capability_config):
    """The guard must not break the normal path."""
    assert (
        patch_profiles(str(driver_copy), "YRD226 TSDB", "Yale", "ALL", config_path=capability_config)
        == "base-lock"
    )
    assert (driver_copy / "profiles" / "base-lock-patch.yml").is_file()
