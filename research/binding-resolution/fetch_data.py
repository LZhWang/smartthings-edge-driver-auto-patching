"""Fetch the corpora the binding-resolution measurement runs against.

Nothing is vendored into this repository. SmartThings' fingerprints are three
small files; zwave-js' device database is 2,384 files, of which this measurement
needs the 154 belonging to manufacturers the zwave-lock driver actually
references. Both are fetched here so the experiment can be reproduced from a
clean checkout, and so the corpora stay current rather than frozen at whatever
they were the day this was written.

    python research/binding-resolution/fetch_data.py

Licences: SmartThingsEdgeDrivers is Apache-2.0; zwave-js is MIT. Note that zigpy,
the other obvious source of ZCL attribute definitions, is GPL-3.0 and therefore
cannot be vendored into this Apache-2.0 project.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys
import urllib.request

HERE = pathlib.Path(__file__).parent
DATA = HERE / ".data"

ST_BASE = (
    "https://raw.githubusercontent.com/SmartThingsCommunity/SmartThingsEdgeDrivers/main/drivers/SmartThings"
)
ST_DRIVERS = ("zigbee-lock", "zwave-lock", "matter-lock")
ZWAVE_JS = "https://github.com/zwave-js/zwave-js.git"


def fetch_smartthings() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    for driver in ST_DRIVERS:
        target = DATA / f"{driver}-fingerprints.yml"
        url = f"{ST_BASE}/{driver}/fingerprints.yml"
        with urllib.request.urlopen(url, timeout=60) as response:  # noqa: S310 - fixed https host
            target.write_bytes(response.read())
        print(f"  {driver:14} {target.stat().st_size:>7} bytes")


def fetch_zwave_js() -> None:
    """Sparse-clone only the device config tree, not the whole monorepo."""
    checkout = DATA / "zwave-js"
    if (checkout / ".git").is_dir():
        print("  zwave-js already present; pulling")
        subprocess.run(["git", "-C", str(checkout), "pull", "--quiet", "--ff-only"], check=False)
        return

    subprocess.run(
        [
            "git",
            "clone",
            "--quiet",
            "--depth",
            "1",
            "--filter=blob:none",
            "--sparse",
            ZWAVE_JS,
            str(checkout),
        ],
        check=True,
    )
    # The $import chains reach templates/master_template.json under devices/,
    # so the whole devices tree is needed, but nothing else in the monorepo is.
    subprocess.run(
        ["git", "-C", str(checkout), "sparse-checkout", "set", "packages/config/config/devices"],
        check=True,
    )
    count = len(list((checkout / "packages/config/config/devices").rglob("*.json")))
    print(f"  zwave-js       {count} device config files")


def main() -> int:
    print("Fetching SmartThings lock fingerprints (Apache-2.0)")
    fetch_smartthings()
    print("Fetching zwave-js device configs (MIT)")
    fetch_zwave_js()
    print(f"\nData in {DATA}. Next: python research/binding-resolution/build_index.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
