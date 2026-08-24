"""Bounds on documents parsed from untrusted sources (#44, #45).

`yaml.safe_load` stores aliases as shared references, so a document with nested
anchors parses cheaply and only becomes expensive in whatever walks it —
`jsonschema` in validate, `json.dumps` in discover. A sub-kilobyte driver file
reached hundreds of megabytes that way.

These tests assert a *bound*, not the absence of a crash: the document must be
rejected with a diagnostic, quickly. A test that only checked "did not hang"
would pass on a fix that merely made the blow-up slower.
"""

from __future__ import annotations

import time

import pytest
import yaml

from edgeloom.boundedyaml import (
    DEFAULT_NODE_BUDGET,
    DocumentTooLargeError,
    check_bounds,
    expanded_node_count,
)
from edgeloom.schemas import SchemaError, load_document


def alias_bomb(levels: int, top_key: str = "components") -> str:
    text = "a0: &a0 [x,x,x,x,x,x,x,x,x]\n"
    for i in range(1, levels + 1):
        refs = ",".join([f"*a{i - 1}"] * 9)
        text += f"a{i}: &a{i} [{refs}]\n"
    return text + f"{top_key}: *a{levels}\n"


def test_a_real_profile_is_nowhere_near_the_budget(repo_root) -> None:
    """The budget must not be a trap for legitimate files."""
    profile = yaml.safe_load((repo_root / "auto_patch/zigbee-lock/profiles/base-lock.yml").read_text())
    fingerprints = yaml.safe_load((repo_root / "auto_patch/zigbee-lock/fingerprints.yml").read_text())
    assert expanded_node_count(profile) < DEFAULT_NODE_BUDGET / 1000
    assert expanded_node_count(fingerprints) < DEFAULT_NODE_BUDGET / 100


def test_counting_does_not_expand(tmp_path) -> None:
    """The check must cost the distinct nodes, not the expansion it describes."""
    document = yaml.safe_load(alias_bomb(8))

    started = time.monotonic()
    with pytest.raises(DocumentTooLargeError):
        check_bounds(document)
    elapsed = time.monotonic() - started

    # The document describes ~10^9 nodes. Anything that walked them could not
    # return in a second; memoised counting returns in microseconds.
    assert elapsed < 1.0


def test_recursive_alias_is_refused() -> None:
    """YAML permits self-reference; no consumer here can walk it."""
    document = yaml.safe_load("a: &a\n  b: *a\n")
    with pytest.raises(DocumentTooLargeError):
        check_bounds(document)


def test_validate_rejects_an_alias_bomb_rather_than_expanding_it(tmp_path) -> None:
    path = tmp_path / "base-lock.yml"
    path.write_text(alias_bomb(8) + "name: x\n", encoding="utf-8")

    started = time.monotonic()
    with pytest.raises(SchemaError, match="expands to"):
        load_document(path)
    assert time.monotonic() - started < 1.0


def test_load_document_reports_non_utf8_instead_of_raising(tmp_path) -> None:
    path = tmp_path / "bad.yml"
    path.write_bytes(b"name: caf\xe9\ncomponents: []\n")
    with pytest.raises(SchemaError, match="not valid UTF-8"):
        load_document(path)


def test_deep_nesting_is_reported_not_crashed(tmp_path) -> None:
    path = tmp_path / "deep.json"
    path.write_text("[" * 200_000 + "]" * 200_000, encoding="utf-8")
    with pytest.raises(SchemaError):
        load_document(path)
