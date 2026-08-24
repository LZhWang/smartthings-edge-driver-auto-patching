"""Offline coverage for remote discovery, parsing, and catalog output."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from discovery import discover_drivers


class FakeResponse:
    def __init__(self, status_code: int, *, text: str = "", payload: object = None) -> None:
        self.status_code = status_code
        self.text = text
        self._payload = payload

    def json(self) -> object:
        return self._payload


def _install_fake_get(
    monkeypatch: pytest.MonkeyPatch, routes: dict[str, FakeResponse]
) -> list[tuple[str, dict]]:
    calls: list[tuple[str, dict]] = []

    def fake_get(url: str, **kwargs: object) -> FakeResponse:
        if url not in routes:
            raise AssertionError(f"unexpected network request: {url}")
        calls.append((url, kwargs))
        return routes[url]

    monkeypatch.setattr(discover_drivers.requests, "get", fake_get)
    return calls


def _fingerprint_document(model: str) -> str:
    return yaml.safe_dump(
        {
            "zigbeeManufacturer": [
                {
                    "id": f"Yale/{model}",
                    "deviceLabel": "Yale Door Lock",
                    "manufacturer": "Yale",
                    "model": model,
                    "deviceProfileName": "base-lock",
                }
            ]
        }
    )


def _matter_document(model: str) -> str:
    """A fingerprints.yml with no ``zigbeeManufacturer`` key: fetchable, but it
    yields zero Zigbee fingerprints, so it must not count against ``--limit``."""
    return yaml.safe_dump({"matterGeneric": [{"model": model}]})


@pytest.mark.parametrize("token", [None, "test-token"])
def test_fetch_remote_directory_filters_and_sends_expected_request(
    monkeypatch: pytest.MonkeyPatch, token: str | None
) -> None:
    url = "https://api.github.com/repos/acme/drivers/contents/drivers"
    calls = _install_fake_get(
        monkeypatch,
        {
            url: FakeResponse(
                200,
                payload=[
                    {"name": "zigbee-lock", "type": "dir"},
                    {"name": "README.md", "type": "file"},
                    {"name": "zigbee-switch", "type": "dir"},
                ],
            )
        },
    )

    result = discover_drivers.fetch_remote_directory("acme/drivers", "release", "/drivers/", token, 4.5)

    assert result == ["zigbee-lock", "zigbee-switch"]
    assert len(calls) == 1
    _, kwargs = calls[0]
    expected_headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "edge-driver-auto-patching",
    }
    if token is not None:
        expected_headers["Authorization"] = f"Bearer {token}"
    assert kwargs == {"headers": expected_headers, "params": {"ref": "release"}, "timeout": 4.5}


def test_fetch_remote_directory_reports_non_200(monkeypatch: pytest.MonkeyPatch) -> None:
    url = "https://api.github.com/repos/acme/drivers/contents/drivers"
    _install_fake_get(monkeypatch, {url: FakeResponse(503, text="unavailable")})

    with pytest.raises(RuntimeError, match="503"):
        discover_drivers.fetch_remote_directory("acme/drivers", "main", "drivers", None, 1)


@pytest.mark.parametrize(
    "status_code,text,expected",
    [
        (404, "not found", None),
        (
            200,
            "zigbeeManufacturer:\n  - model: YRD226 TSDB\n",
            {"zigbeeManufacturer": [{"model": "YRD226 TSDB"}]},
        ),
    ],
)
def test_fetch_remote_yaml_handles_missing_and_valid_documents_without_auth(
    monkeypatch: pytest.MonkeyPatch,
    status_code: int,
    text: str,
    expected: dict | None,
) -> None:
    url = "https://raw.githubusercontent.com/acme/drivers/main/drivers/lock/fingerprints.yml"
    calls = _install_fake_get(monkeypatch, {url: FakeResponse(status_code, text=text)})

    result = discover_drivers.fetch_remote_yaml("acme/drivers", "main", "/drivers/lock/fingerprints.yml", 2.5)

    assert result == expected
    assert calls == [(url, {"timeout": 2.5})]


def test_discover_from_github_skips_missing_driver_before_counting_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api_url = "https://api.github.com/repos/acme/drivers/contents/drivers"
    raw_root = "https://raw.githubusercontent.com/acme/drivers/main/drivers"
    routes = {
        api_url: FakeResponse(
            200,
            payload=[{"name": name, "type": "dir"} for name in ["missing", "alpha", "beta", "gamma"]],
        ),
        f"{raw_root}/missing/fingerprints.yml": FakeResponse(404),
        f"{raw_root}/alpha/fingerprints.yml": FakeResponse(200, text=_fingerprint_document("A1")),
        f"{raw_root}/beta/fingerprints.yml": FakeResponse(200, text=_fingerprint_document("B2")),
        f"{raw_root}/gamma/fingerprints.yml": FakeResponse(200, text=_fingerprint_document("G3")),
    }
    calls = _install_fake_get(monkeypatch, routes)

    result = discover_drivers.discover_from_github("acme/drivers", "main", "drivers", None, 2, 3)

    assert [item.driver for item in result] == ["alpha", "beta"]
    assert [url for url, _ in calls] == [
        api_url,
        f"{raw_root}/missing/fingerprints.yml",
        f"{raw_root}/alpha/fingerprints.yml",
        f"{raw_root}/beta/fingerprints.yml",
    ]


def test_discover_from_github_zero_limit_processes_all_drivers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api_url = "https://api.github.com/repos/acme/drivers/contents/drivers"
    raw_root = "https://raw.githubusercontent.com/acme/drivers/main/drivers"
    routes = {
        api_url: FakeResponse(
            200,
            payload=[{"name": name, "type": "dir"} for name in ["alpha", "beta"]],
        ),
        f"{raw_root}/alpha/fingerprints.yml": FakeResponse(200, text=_fingerprint_document("A1")),
        f"{raw_root}/beta/fingerprints.yml": FakeResponse(200, text=_fingerprint_document("B2")),
    }
    calls = _install_fake_get(monkeypatch, routes)

    # The production guard is deliberately falsy for 0, so zero currently means no limit.
    result = discover_drivers.discover_from_github("acme/drivers", "main", "drivers", None, 0, 3)

    assert [item.driver for item in result] == ["alpha", "beta"]
    assert len(calls) == 3


def test_discover_from_github_limit_counts_drivers_with_fingerprints(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A Matter-shaped fingerprints.yml (fetchable, zero Zigbee entries) must
    not consume the limit, or ``--limit 2`` against SmartThings returns nothing
    because the alphabetically-first drivers with a fingerprints.yml are Matter."""
    api_url = "https://api.github.com/repos/acme/drivers/contents/drivers"
    raw_root = "https://raw.githubusercontent.com/acme/drivers/main/drivers"
    routes = {
        api_url: FakeResponse(
            200,
            payload=[
                {"name": name, "type": "dir"}
                for name in ["matter-appliance", "matter-lock", "zigbee-a", "zigbee-b"]
            ],
        ),
        f"{raw_root}/matter-appliance/fingerprints.yml": FakeResponse(200, text=_matter_document("M1")),
        f"{raw_root}/matter-lock/fingerprints.yml": FakeResponse(200, text=_matter_document("M2")),
        f"{raw_root}/zigbee-a/fingerprints.yml": FakeResponse(200, text=_fingerprint_document("A1")),
        f"{raw_root}/zigbee-b/fingerprints.yml": FakeResponse(200, text=_fingerprint_document("B2")),
    }
    _install_fake_get(monkeypatch, routes)

    result = discover_drivers.discover_from_github("acme/drivers", "main", "drivers", None, 2, 3)

    assert [item.driver for item in result] == ["zigbee-a", "zigbee-b"]


def test_discover_from_local_limit_counts_drivers_with_fingerprints(tmp_path: Path) -> None:
    """The local path keeps the same accounting as the GitHub path."""
    base = tmp_path / "drivers"
    for name, document in [
        ("matter-appliance", _matter_document("M1")),
        ("matter-lock", _matter_document("M2")),
        ("zigbee-a", _fingerprint_document("A1")),
        ("zigbee-b", _fingerprint_document("B2")),
    ]:
        driver_dir = base / name
        driver_dir.mkdir(parents=True)
        (driver_dir / "fingerprints.yml").write_text(document, encoding="utf-8")

    result = discover_drivers.discover_from_local(tmp_path, "drivers", 2)

    assert [item.driver for item in result] == ["zigbee-a", "zigbee-b"]


def test_parse_fingerprints_maps_public_fields_and_ignores_other_shapes() -> None:
    payload = {
        "zigbeeManufacturer": [
            {
                "manufacturer": "Yale",
                "model": "YRD226 TSDB",
                "deviceProfileName": "base-lock",
                "id": "Yale/YRD226 TSDB",
                "deviceLabel": "Yale Door Lock",
            }
        ]
    }

    assert discover_drivers.parse_fingerprints("zigbee-lock", {}) == []
    assert discover_drivers.parse_fingerprints("zigbee-lock", payload) == [
        discover_drivers.DriverFingerprint(
            driver="zigbee-lock",
            manufacturer="Yale",
            model="YRD226 TSDB",
            profile="base-lock",
            device_id="Yale/YRD226 TSDB",
            label="Yale Door Lock",
        )
    ]


@pytest.mark.parametrize("fmt", ["json", "yaml"])
def test_write_output_creates_parent_and_round_trips(tmp_path: Path, fmt: str) -> None:
    output = tmp_path / "missing" / "nested" / f"catalog.{fmt}"
    payload = {"stats": {"driver_count": 1}, "drivers": [{"driver": "zigbee-lock"}]}

    discover_drivers.write_output(payload, output, fmt)

    assert output.is_file()
    if fmt == "json":
        restored = json.loads(output.read_text(encoding="utf-8"))
    else:
        restored = yaml.safe_load(output.read_text(encoding="utf-8"))
    assert restored == payload


def test_discover_from_local_rejects_missing_path(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="Local driver path not found"):
        discover_drivers.discover_from_local(tmp_path, "not-there", None)


def test_build_driver_catalog_requires_local_directory() -> None:
    with pytest.raises(ValueError, match="local_dir is required"):
        discover_drivers.build_driver_catalog(
            source="local",
            repo="",
            branch="",
            local_dir=None,
            driver_subpath="drivers",
            token=None,
            limit=None,
            timeout=1,
        )


def test_build_driver_catalog_rejects_unknown_source() -> None:
    with pytest.raises(ValueError, match="Unknown source 'other'"):
        discover_drivers.build_driver_catalog(
            source="other",
            repo="",
            branch="",
            local_dir=None,
            driver_subpath="drivers",
            token=None,
            limit=None,
            timeout=1,
        )
