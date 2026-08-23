"""Locate, load, and apply the published EdgeLoom JSON Schemas."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

SCHEMA_VERSION = "0.1"

PROFILE = "profile"
CAPABILITY_MAP = "capability-map"
KINDS = (PROFILE, CAPABILITY_MAP)

_YAML_SUFFIXES = {".yaml", ".yml"}
_JSON_SUFFIXES = {".json"}
DOCUMENT_SUFFIXES = _YAML_SUFFIXES | _JSON_SUFFIXES


class SchemaError(RuntimeError):
    """Raised when a schema cannot be located or a document cannot be read."""


def schema_dir() -> Path:
    """Return the directory holding the shipped schemas.

    Installed wheels carry the schemas inside the package; a source checkout
    keeps the canonical copy at the repository root so it stays browsable and
    citable. Prefer the packaged copy, fall back to the checkout.
    """
    packaged = Path(__file__).resolve().parent / "schema"
    if packaged.is_dir():
        return packaged
    checkout = Path(__file__).resolve().parents[1] / "schema"
    if checkout.is_dir():
        return checkout
    raise SchemaError("EdgeLoom schemas not found; the installation looks incomplete")


def schema_path(kind: str) -> Path:
    if kind not in KINDS:
        raise SchemaError(f"Unknown schema kind {kind!r}; expected one of {', '.join(KINDS)}")
    path = schema_dir() / f"{kind}.schema.json"
    if not path.is_file():
        raise SchemaError(f"Schema file missing: {path}")
    return path


def load_schema(kind: str) -> dict[str, Any]:
    return json.loads(schema_path(kind).read_text(encoding="utf-8"))


def load_document(path: Path) -> Any:
    """Read a YAML or JSON document from disk."""
    if path.suffix.lower() not in DOCUMENT_SUFFIXES:
        raise SchemaError(f"Unsupported document type {path.suffix!r}: {path}")
    text = path.read_text(encoding="utf-8")
    try:
        if path.suffix.lower() in _JSON_SUFFIXES:
            return json.loads(text)
        return yaml.safe_load(text)
    except (json.JSONDecodeError, yaml.YAMLError) as exc:
        raise SchemaError(f"{path}: could not be parsed: {exc}") from exc


def detect_kind(document: Any) -> str | None:
    """Infer which schema a document is meant to satisfy.

    Returns ``None`` when the document matches neither shape, so callers can
    skip unrelated YAML rather than reporting spurious failures.
    """
    if not isinstance(document, dict):
        return None
    if isinstance(document.get("drivers"), dict):
        return CAPABILITY_MAP
    if isinstance(document.get("components"), list):
        return PROFILE
    return None


@dataclass(frozen=True)
class ValidationResult:
    path: Path
    kind: str | None
    errors: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return self.kind is not None and not self.errors

    @property
    def skipped(self) -> bool:
        return self.kind is None


def validate_document(path: Path, kind: str | None = None) -> ValidationResult:
    """Validate one document. ``kind`` forces a schema instead of inferring one."""
    import jsonschema

    document = load_document(path)
    resolved = kind or detect_kind(document)
    if resolved is None:
        return ValidationResult(path=path, kind=None, errors=())

    validator = jsonschema.Draft202012Validator(load_schema(resolved))
    errors = []
    for error in sorted(validator.iter_errors(document), key=lambda e: list(e.absolute_path)):
        location = "/".join(str(part) for part in error.absolute_path) or "<document root>"
        errors.append(f"{location}: {error.message}")
    return ValidationResult(path=path, kind=resolved, errors=tuple(errors))


def iter_documents(targets: list[Path]) -> list[Path]:
    """Expand files and directories into a sorted list of candidate documents."""
    found: set[Path] = set()
    for target in targets:
        if target.is_dir():
            for suffix in sorted(DOCUMENT_SUFFIXES):
                found.update(p for p in target.rglob(f"*{suffix}") if p.is_file())
        elif target.is_file():
            found.add(target)
        else:
            raise SchemaError(f"No such file or directory: {target}")
    return sorted(found)
