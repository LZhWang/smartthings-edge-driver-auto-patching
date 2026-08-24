"""Regression tests for the driver-supplied path containment guards.

Reported against 3a30b375 by Marcos Maia Jr. through SECURITY.md: a
`deviceProfileName` carrying parent components or an absolute path caused
patch_profiles to write a generated profile outside the driver directory.

Two layers are tested separately on purpose. `safe_identifier` rejects the
input before path construction, so an end-to-end test alone would never
execute `contained_path` and the write-boundary guard would go unverified.
"""

from __future__ import annotations

import shutil

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
    (tmp_path / "profiles").mkdir()
    assert contained_path(tmp_path, "profiles", "ok.yml") == tmp_path / "profiles" / "ok.yml"


@pytest.mark.parametrize("part", ["../../escape.yml", "/tmp/absolute.yml"])
def test_contained_path_rejects_an_escape(tmp_path, part: str) -> None:
    (tmp_path / "profiles").mkdir()
    with pytest.raises(UnsafePathError):
        contained_path(tmp_path, "profiles", part)


def test_contained_path_allows_a_parent_hop_that_stays_inside(tmp_path) -> None:
    """Documents the layering rather than asserting a security property.

    ``profiles/../x.yml`` lands inside the driver, so this layer — whose job is
    "do not leave the driver" — permits it. Names like that never reach here in
    practice: ``safe_identifier`` rejects parent components and separators
    before a path is built. Anchoring tighter, on ``profiles/`` itself, is what
    made a symlinked ``profiles`` relocate the anchor.
    """
    (tmp_path / "profiles").mkdir()
    assert contained_path(tmp_path, "profiles", "../x.yml") == tmp_path / "x.yml"


@pytest.mark.parametrize("linked", ["profiles", "src"])
def test_contained_path_refuses_a_symlinked_component(tmp_path, linked: str) -> None:
    """The bypass that defeated the first version of this guard.

    Anchoring on ``driver/profiles`` resolved that symlink and made the outside
    directory the containment base, so every write under it passed. The call
    shape here is the one the patcher actually uses: anchor on the driver, pass
    the subdirectory as a component.
    """
    driver = tmp_path / "driver"
    driver.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (driver / linked).symlink_to(outside, target_is_directory=True)

    with pytest.raises(UnsafePathError):
        contained_path(driver, linked, "x.yml")


def test_contained_path_refuses_a_symlinked_leaf(tmp_path) -> None:
    """A single linked file is the realistic shape: the tree looks normal."""
    driver = tmp_path / "driver"
    (driver / "src").mkdir(parents=True)
    outside = tmp_path / "outside.lua"
    outside.write_text("original", encoding="utf-8")
    (driver / "src" / "init.lua").symlink_to(outside)

    with pytest.raises(UnsafePathError):
        contained_path(driver, "src", "init.lua")


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


def test_patch_refuses_a_driver_with_a_symlinked_profiles(driver_copy, capability_config, tmp_path):
    """End to end: the bypass reproduced through the real patch entry point.

    A unit test alone would not have caught this. The first version of the guard
    passed its own symlink test while the patcher, which called it differently,
    was wide open.
    """
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "base-lock.yml").write_text(
        (driver_copy / "profiles" / "base-lock.yml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    shutil.rmtree(driver_copy / "profiles")
    (driver_copy / "profiles").symlink_to(outside, target_is_directory=True)

    with pytest.raises(UnsafePathError):
        patch_profiles(str(driver_copy), "YRD226 TSDB", "Yale", "ALL", config_path=capability_config)

    assert not (outside / "base-lock-patch.yml").exists()
