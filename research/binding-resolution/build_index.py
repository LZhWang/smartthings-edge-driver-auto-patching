"""Join SmartThings' zwave-lock fingerprints onto zwave-js device configs.

SmartThings identifies a Z-Wave device by (manufacturerId, productType,
productId) and records no product model. zwave-js keys on the same triple and
does carry a model label plus the device's Configuration CC parameters, so it is
the bridge that makes the measurement possible: the SmartThings corpus alone
cannot supply what a device's settings actually are.

    python research/binding-resolution/build_index.py
"""

from __future__ import annotations

import json
import pathlib
import sys

import json5
import yaml

HERE = pathlib.Path(__file__).parent
DEVICES = HERE / ".data/zwave-js/packages/config/config/devices"
# `~` in a zwave-js $import resolves against the devices root, which is where
# templates/master_template.json lives — not against packages/config/config.
CONFIG_ROOT = DEVICES

_templates: dict[pathlib.Path, dict] = {}


def load(path: pathlib.Path) -> dict:
    """zwave-js configs are JSON5: comments and trailing commas are legal."""
    try:
        return json5.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def template(path: pathlib.Path) -> dict:
    if path not in _templates:
        _templates[path] = load(path)
    return _templates[path]


def as_int(value: object) -> int | None:
    """zwave-js writes ids as '0x1234' strings; SmartThings writes ints."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    text = str(value)
    try:
        return int(text, 16) if text.lower().startswith("0x") else int(text)
    except ValueError:
        return None


def expand(entry: dict, path: pathlib.Path, depth: int = 0) -> dict:
    """Resolve a $import chain into a flat parameter definition.

    Imports nest. A device says `$import: templates/yale_template.json#one_touch`,
    and that entry in turn says
    `$import: ~/templates/master_template.json#base_enable_disable_255`, which is
    where minValue, maxValue and options actually live. Resolving only one level
    leaves every boolean parameter looking untyped, which silently turns correct
    bindings into apparent fidelity losses.
    """
    if depth > 8:  # a malformed cycle would otherwise hang the walk
        return dict(entry)
    reference = entry.get("$import")
    if not reference:
        return dict(entry)

    relative, _, key = reference.partition("#")
    if relative.startswith("~/"):
        target = (CONFIG_ROOT / relative[2:]).resolve()
    elif relative:
        target = (path.parent / relative).resolve()
    else:
        target = path

    base: dict = {}
    if target.is_file():
        source = template(target)
        raw = source.get(key, {}) if key else source
        if isinstance(raw, dict):
            base = expand(raw, target, depth + 1)

    return {**base, **{k: v for k, v in entry.items() if k != "$import"}}


def resolve_params(config: dict, path: pathlib.Path) -> list[dict]:
    resolved = []
    for entry in config.get("paramInformation") or []:
        merged = expand(entry, path)
        merged["_import_key"] = (entry.get("$import") or "").partition("#")[2] or None
        resolved.append(merged)
    return resolved


def main() -> int:
    fingerprints_path = HERE / ".data/zwave-lock-fingerprints.yml"
    if not fingerprints_path.is_file() or not DEVICES.is_dir():
        print("Missing corpora. Run: python research/binding-resolution/fetch_data.py")
        return 1

    fingerprints = yaml.safe_load(fingerprints_path.read_text())["zwaveManufacturer"]
    referenced = {entry.get("manufacturerId") for entry in fingerprints}

    index: dict[tuple, dict] = {}
    parsed = unreadable = 0
    for manufacturer in sorted(m for m in referenced if m is not None):
        directory = DEVICES / f"0x{manufacturer:04x}"
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.json")):
            config = load(path)
            if not config:
                unreadable += 1
                continue
            parsed += 1
            params = resolve_params(config, path)
            for device in config.get("devices") or []:
                key = (
                    as_int(config.get("manufacturerId")),
                    as_int(device.get("productType")),
                    as_int(device.get("productId")),
                )
                index[key] = {
                    "file": path.name,
                    "label": config.get("label"),
                    "description": config.get("description"),
                    "params": params,
                }

    print(f"parsed {parsed} zwave-js configs ({unreadable} unreadable) -> {len(index)} device keys")

    resolved = [
        entry
        for entry in fingerprints
        if (entry.get("manufacturerId"), entry.get("productType"), entry.get("productId")) in index
    ]
    unresolved = [
        str(entry.get("id"))
        for entry in fingerprints
        if (entry.get("manufacturerId"), entry.get("productType"), entry.get("productId")) not in index
    ]

    rate = len(resolved) / len(fingerprints) * 100
    print(f"\nSmartThings zwave-lock fingerprints : {len(fingerprints)}")
    print(f"  resolved against zwave-js         : {len(resolved)}  ({rate:.0f}%)")
    print(f"  unresolved                        : {len(unresolved)}")
    if unresolved:
        print("  " + ", ".join(unresolved))

    out = HERE / "results/zwave_index.json"
    out.write_text(json.dumps({f"{a}|{b}|{c}": v for (a, b, c), v in index.items()}, indent=1))
    print(f"\nwrote {out.relative_to(HERE)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
