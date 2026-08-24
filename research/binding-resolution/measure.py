"""Binding-resolution and semantic-fidelity measurement for door locks.

Question: can a neutral record for a device capability round-trip to a correct,
unambiguous, type-faithful binding on both Zigbee and Z-Wave?

Not "does the capability exist on both" — that question cannot fail, because all
nine capabilities exist on both protocols by specification and none is surfaced
by any SmartThings lock profile. This measures whether a binding RESOLVES.

Per (device, term) the cell is scored:
  RESOLVED-1:1    exactly one primary binding, type and unit faithful
  RESOLVED-LOSSY  exactly one primary binding, but type/unit/range differs
  AMBIGUOUS-1:N   several primary candidates that are not the same concept
  UNBOUND         no binding on this protocol for this device
"""

from __future__ import annotations

import collections
import json
import pathlib
import re

import yaml

HERE = pathlib.Path(__file__).parent
RESOLVED = "RESOLVED-1:1"
LOSSY = "RESOLVED-LOSSY"
AMBIGUOUS = "AMBIGUOUS-1:N"
UNBOUND = "UNBOUND"


def load_devices() -> dict[str, list[dict]]:
    """SmartThings zwave-lock fingerprints joined onto zwave-js configs."""
    index = json.loads((HERE / "results/zwave_index.json").read_text())
    fingerprints = yaml.safe_load((HERE / ".data/zwave-lock-fingerprints.yml").read_text())
    devices: dict[str, list[dict]] = {}
    for entry in fingerprints["zwaveManufacturer"]:
        key = f"{entry.get('manufacturerId')}|{entry.get('productType')}|{entry.get('productId')}"
        found = index.get(key)
        if not found:
            continue
        # A few configs carry a conditional label ($if on productId); fall back
        # to the filename, which identifies the product family either way.
        label = found["label"]
        name = label if isinstance(label, str) else found["file"].removesuffix(".json")
        devices.setdefault(name, found["params"])
    return devices


def zwave_type(param: dict) -> str:
    """Infer the Z-Wave parameter's value shape from its declared metadata."""
    if param.get("allowManualEntry") is False or param.get("options"):
        return "enum"
    lo, hi = param.get("minValue"), param.get("maxValue")
    if lo == 0 and hi == 1:
        return "bool"
    if isinstance(hi, int):
        return "uint"
    return "unknown"


def faithful(term: dict, param: dict) -> tuple[bool, list[str]]:
    """Would a value survive a round trip through the neutral record unchanged?"""
    losses: list[str] = []
    zcl = term["zcl"]
    kind = zwave_type(param)

    want = zcl["type"]
    if want == "bool" and kind not in ("bool", "enum"):
        losses.append(f"ZCL bool vs Z-Wave {kind}")

    # ZCL booleans are 0/1. Z-Wave overwhelmingly encodes true as 255, so a
    # neutral record has to carry the true-value or a round trip writes 1 into
    # a field the device reads as "not 255".
    if want == "bool" and kind == "enum":
        values = {o.get("value") for o in (param.get("options") or []) if isinstance(o, dict)}
        if values and values != {0, 1}:
            losses.append(f"boolean encoded as {sorted(v for v in values if v is not None)}, not 0/1")
    if want in ("uint8", "uint32") and kind == "bool":
        losses.append(f"ZCL {want} vs Z-Wave boolean")
    if want == "enum8" and kind == "bool":
        losses.append("ZCL enum vs Z-Wave boolean")
    if want == "string" and kind != "enum":
        losses.append(f"ZCL string vs Z-Wave {kind}")

    if zcl.get("unit") == "seconds" and param.get("unit") not in (None, "seconds"):
        losses.append(f"unit {param.get('unit')!r} vs seconds")

    # ZCL AutoRelockTime is uint32; a Z-Wave byte cannot carry its full domain.
    if want == "uint32" and isinstance(param.get("maxValue"), int) and param["maxValue"] < 65535:
        losses.append(f"range capped at {param['maxValue']} vs ZCL uint32")

    if param.get("readOnly"):
        losses.append("read-only on Z-Wave, writable in ZCL")

    return (not losses), losses


def score(term_name: str, term: dict, params: list[dict]) -> tuple[str, dict]:
    primary = set(term["zwave"]["primary"])
    related = set(term["zwave"]["related"])

    hits = [p for p in params if isinstance(p.get("label"), str) and p["label"] in primary]
    near = [p for p in params if isinstance(p.get("label"), str) and p["label"] in related]

    if len(hits) > 1:
        return AMBIGUOUS, {"candidates": [p["label"] for p in hits]}
    if not hits:
        return UNBOUND, {"related_present": [p["label"] for p in near]}

    ok, losses = faithful(term, hits[0])
    detail = {"binding": hits[0]["label"], "param": hits[0].get("#")}
    if near:
        detail["related_present"] = [p["label"] for p in near]
    if ok:
        return RESOLVED, detail
    detail["losses"] = losses
    return LOSSY, detail


def main() -> None:
    lexicon = yaml.safe_load((HERE / "lexicon.yaml").read_text())
    terms = lexicon["terms"]
    devices = load_devices()

    tally: collections.Counter[str] = collections.Counter()
    per_term: dict[str, collections.Counter[str]] = {t: collections.Counter() for t in terms}
    rows = []

    for device, params in sorted(devices.items()):
        for name, term in terms.items():
            verdict, detail = score(name, term, params)
            tally[verdict] += 1
            per_term[name][verdict] += 1
            rows.append({"device": device, "term": name, "verdict": verdict, **detail})

    total = sum(tally.values())
    print(f"{len(devices)} Z-Wave lock products x {len(terms)} terms = {total} cells\n")

    print("OVERALL")
    for verdict in (RESOLVED, LOSSY, AMBIGUOUS, UNBOUND):
        n = tally[verdict]
        print(f"  {verdict:15} {n:4}  {n / total * 100:5.1f}%")

    print("\nPER TERM")
    print(f"  {'term':30} {'1:1':>5} {'lossy':>6} {'ambig':>6} {'unbound':>8}")
    for name, counts in per_term.items():
        print(f"  {name:30} {counts[RESOLVED]:5} {counts[LOSSY]:6} {counts[AMBIGUOUS]:6} {counts[UNBOUND]:8}")

    # UNBOUND means the device does not implement the capability at all. That is
    # feature absence, not a failure of the description, so the decision rule is
    # evaluated over cells where a binding actually exists. The all-cells figure
    # is reported too, because it is the honest measure of matrix coverage.
    bound = tally[RESOLVED] + tally[LOSSY] + tally[AMBIGUOUS]
    resolved_pct = tally[RESOLVED] / bound * 100 if bound else 0.0
    ambiguous_pct = tally[AMBIGUOUS] / bound * 100 if bound else 0.0

    print(f"\nDECISION RULE (over the {bound} cells where a binding exists)")
    print(f"  RESOLVED-1:1  = {resolved_pct:.1f}%")
    print(f"  AMBIGUOUS-1:N = {ambiguous_pct:.1f}%")
    print(
        f"  (matrix coverage over all {total} cells: {tally[RESOLVED] / total * 100:.1f}% 1:1, "
        f"{tally[UNBOUND] / total * 100:.1f}% the device lacks the feature)"
    )

    if resolved_pct >= 60 and ambiguous_pct < 10:
        print("  -> BUILD THE FORMAT. A neutral row is a description, not a pointer.")
    elif ambiguous_pct > 40 or resolved_pct < 25:
        print("  -> STOP. Capability is not well defined at the observable granularity.")
    else:
        print("  -> BUILD A LEXICON PLUS INDEX. Concepts port; encodings do not.")

    control(terms, devices, tally)

    (HERE / "results/cells.json").write_text(json.dumps(rows, indent=1))
    print(f"\nwrote results/cells.json ({len(rows)} cells)")


def control(terms: dict, devices: dict[str, list[dict]], curated: collections.Counter) -> None:
    """How much of the disambiguation is the curated lexicon actually doing?

    Re-scores with naive keyword matching — the thing you get for free — so the
    hand-authored primary/related split can be priced.
    """
    naive: collections.Counter[str] = collections.Counter()
    for params in devices.values():
        for name in terms:
            # split CamelCase into keywords: AutoRelockTime -> {auto, relock, time}
            words = {w.lower() for w in re.findall(r"[A-Z][a-z]+", name)}
            hits = [
                p
                for p in params
                if isinstance(p.get("label"), str)
                and words & {w.lower() for w in re.findall(r"[A-Za-z]+", p["label"])}
            ]
            if len(hits) > 1:
                naive[AMBIGUOUS] += 1
            elif hits:
                naive[RESOLVED] += 1
            else:
                naive[UNBOUND] += 1

    n_bound = naive[RESOLVED] + naive[AMBIGUOUS]
    c_bound = curated[RESOLVED] + curated[LOSSY] + curated[AMBIGUOUS]
    print("\nCONTROL: naive keyword matching vs the curated lexicon")
    print(
        f"  naive   ambiguous: {naive[AMBIGUOUS]:4} of {n_bound} bound cells "
        f"({naive[AMBIGUOUS] / n_bound * 100:.1f}%)"
        if n_bound
        else "  naive: no bindings"
    )
    print(
        f"  curated ambiguous: {curated[AMBIGUOUS]:4} of {c_bound} bound cells "
        f"({curated[AMBIGUOUS] / c_bound * 100:.1f}%)"
        if c_bound
        else ""
    )
    print("  The gap is the work the lexicon does. It is not a wrapper.")


if __name__ == "__main__":
    main()
