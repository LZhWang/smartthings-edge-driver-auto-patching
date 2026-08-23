"""Tests for schema discovery, kind inference, and validation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from edgeloom import schemas


def _write(path: Path, payload: dict) -> Path:
    if path.suffix == ".json":
        path.write_text(json.dumps(payload), encoding="utf-8")
    else:
        path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    return path


VALID_PROFILE = {
    "name": "base-lock",
    "components": [
        {
            "id": "main",
            "label": "Main",
            "capabilities": [{"id": "lock", "version": 1}],
            "categories": [{"name": "SmartLock"}],
        }
    ],
}

VALID_MAP = {
    "version": "0.1",
    "platform": "smartthings",
    "drivers": {"zigbee-lock": {"attributes": {"Language": "adminmusic34435.language"}}},
}


def test_both_schemas_are_shipped_and_parse() -> None:
    for kind in schemas.KINDS:
        schema = schemas.load_schema(kind)
        assert schema["$schema"].startswith("https://json-schema.org/draft/2020-12")
        assert schema["title"].startswith("EdgeLoom")


def test_unknown_schema_kind_is_rejected() -> None:
    with pytest.raises(schemas.SchemaError):
        schemas.load_schema("not-a-schema")


@pytest.mark.parametrize(
    "document,expected",
    [
        (VALID_PROFILE, schemas.PROFILE),
        (VALID_MAP, schemas.CAPABILITY_MAP),
        ({"unrelated": True}, None),
        ("not a mapping", None),
        (None, None),
    ],
)
def test_detect_kind(document: object, expected: str | None) -> None:
    assert schemas.detect_kind(document) == expected


def test_valid_profile_passes(tmp_path: Path) -> None:
    result = schemas.validate_document(_write(tmp_path / "p.yaml", VALID_PROFILE))
    assert result.ok
    assert result.kind == schemas.PROFILE


def test_valid_capability_map_passes(tmp_path: Path) -> None:
    result = schemas.validate_document(_write(tmp_path / "m.yaml", VALID_MAP))
    assert result.ok
    assert result.kind == schemas.CAPABILITY_MAP


def test_profile_missing_components_fails(tmp_path: Path) -> None:
    result = schemas.validate_document(_write(tmp_path / "p.yaml", {"name": "x"}), kind=schemas.PROFILE)
    assert not result.ok
    assert any("components" in message for message in result.errors)


def test_profile_with_empty_capabilities_fails(tmp_path: Path) -> None:
    bad = {"name": "x", "components": [{"id": "main", "capabilities": []}]}
    result = schemas.validate_document(_write(tmp_path / "p.yaml", bad))
    assert not result.ok


def test_capability_map_rejects_unnamespaced_capability(tmp_path: Path) -> None:
    """A bare id like 'language' would collide with the standard namespace."""
    bad = {"version": "0.1", "drivers": {"zigbee-lock": {"attributes": {"Language": "language"}}}}
    result = schemas.validate_document(_write(tmp_path / "m.yaml", bad))
    assert not result.ok


def test_capability_map_rejects_unknown_key(tmp_path: Path) -> None:
    bad = {"version": "0.1", "drivers": {"zigbee-lock": {"attributes": {"A": "ns.a"}, "oops": 1}}}
    result = schemas.validate_document(_write(tmp_path / "m.yaml", bad))
    assert not result.ok


def test_unrelated_yaml_is_skipped_not_failed(tmp_path: Path) -> None:
    result = schemas.validate_document(_write(tmp_path / "other.yaml", {"hello": "world"}))
    assert result.skipped
    assert result.errors == ()


def test_unparseable_document_raises(tmp_path: Path) -> None:
    path = tmp_path / "broken.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(schemas.SchemaError):
        schemas.validate_document(path)


def test_iter_documents_walks_directories(tmp_path: Path) -> None:
    _write(tmp_path / "a.yaml", VALID_PROFILE)
    (tmp_path / "nested").mkdir()
    _write(tmp_path / "nested" / "b.json", VALID_PROFILE)
    (tmp_path / "ignored.txt").write_text("not a document", encoding="utf-8")

    found = schemas.iter_documents([tmp_path])

    assert found == [tmp_path / "a.yaml", tmp_path / "nested" / "b.json"]


def test_iter_documents_rejects_missing_path(tmp_path: Path) -> None:
    with pytest.raises(schemas.SchemaError):
        schemas.iter_documents([tmp_path / "nope"])


def test_repo_capability_map_conforms(repo_root: Path) -> None:
    """The map generated from the legacy INI files must satisfy the schema."""
    result = schemas.validate_document(repo_root / "auto_patch" / "capability-map.yaml")
    assert result.ok, result.errors


def test_every_shipped_profile_conforms(repo_root: Path) -> None:
    """Both toolchain paths must emit profiles that satisfy one contract."""
    targets = [
        repo_root / "auto_patch" / "zigbee-lock" / "profiles",
        repo_root / "translator" / "ha_proxy_edge_driver" / "profiles",
    ]
    results = [schemas.validate_document(p) for p in schemas.iter_documents(targets)]
    assert results, "expected profiles to validate"
    assert all(r.ok for r in results), [r.errors for r in results if not r.ok]
