from pathlib import Path

from discovery.discover_drivers import (
    build_driver_catalog,
    detect_unsupported_drivers,
    summarize_fingerprints,
)


def test_local_discovery(driver_copy: Path) -> None:
    fingerprints = build_driver_catalog(
        source="local",
        repo="",
        branch="",
        local_dir=driver_copy.parent,
        driver_subpath=".",
        token=None,
        limit=None,
        timeout=1,
    )

    drivers, stats = summarize_fingerprints(fingerprints)
    assert stats["driver_count"] == 1
    assert stats["fingerprint_count"] > 0
    assert drivers[0]["driver"] == "zigbee-lock"


def test_detects_unsupported_driver(driver_copy: Path, tmp_path) -> None:
    fingerprints = build_driver_catalog(
        source="local",
        repo="",
        branch="",
        local_dir=driver_copy.parent,
        driver_subpath=".",
        token=None,
        limit=None,
        timeout=1,
    )
    drivers, _ = summarize_fingerprints(fingerprints)

    fake_config = tmp_path / "caps.config"
    fake_config.write_text("[other-driver]\nattr=value\n", encoding="utf-8")

    unsupported = detect_unsupported_drivers(drivers, fake_config)
    assert "zigbee-lock" in unsupported
