# Edge Driver Auto Patching Tool

Automation to retrofit SmartThings Edge drivers with Zigbee attributes that are
missing from the stock distributions. The tool keeps the original driver safe,
generates a patched profile, injects handler logic, and wires-in a companion
subdriver so you can immediately install the modified driver on your hub.

> This project accompanies the CCS 2025 paper **"Discovering and Exploiting IoT
> Device Hidden Attributes: A New Vulnerability in Smart Homes"**  
> Xuening Xu (Stevens Institute of Technology), Chenglong Fu (University of
> North Carolina at Charlotte), Xiaojiang Du (Stevens Institute of Technology),
> Bo Luo (University of Kansas). Please cite the paper if this code
> contributes to your research (see [How to Cite](#how-to-cite)).

## Highlights

- **Safety first** – automatic backups plus an optional `--dry-run` mode.
- **Deterministic workflow** – three Python steps invoked by one shell script.
- **Config driven** – capability IDs and handler/subdriver mappings live in
  simple INI files.
- **Tested & linted** – Pytest coverage for all core patchers and a GitHub
  Actions workflow to keep contributions healthy.

## Requirements

- Python 3.10+
- `pip` and (optionally) `make`
- Linux, macOS, or Windows with Git Bash/WSL
- SmartThings Edge driver source placed next to the tool (see layout below)

### Prefer Containers?

A ready-to-use Docker image is provided for contributors who would rather not
install Python/Make locally. See [Containerized Development](#containerized-development)
for details.

Install both runtime and dev dependencies with:

```bash
make install
# or
pip install -r requirements-dev.txt
```

## Quickstart

1. Clone this repository and `cd` into it.
2. Copy the Edge driver you want to patch inside the `auto_patch/` directory.
3. Run the patcher:

   ```bash
   cd auto_patch
   ./auto_patch.sh zigbee-lock "YRD226 TSDB" Yale ALL
   ```

4. The patched driver replaces the original folder, while a
   `zigbee-lock-backup` directory preserves the stock bits.

Use `--dry-run` when trying a new driver or attribute list:

```bash
./auto_patch.sh --dry-run zigbee-lock "YRD226 TSDB" Yale Language
```

Nothing is written to disk; you simply see the steps that would run.

## Usage Details

```
./auto_patch.sh [-n|--dry-run] [-v|--verbose] DriverName DeviceModel Manufacturer AttributeList
```

- `DriverName`: folder name under `auto_patch/` for the driver to patch.
- `DeviceModel`: model string from SmartThings Advanced Web App.
- `Manufacturer`: manufacturer string from the same page.
- `AttributeList`: colon (`:`) separated list (e.g. `Language:AutoRelockTime`)
  or `ALL`.

### Workflow Overview

1. **Profiles & fingerprints** – `patch_profiles.py`
   - Backs up `fingerprints.yml`
   - Points the requested model at a new `*-patch` profile
   - Clones the original profile and appends the desired capabilities
2. **Capability handlers** – `patch_handlers.py`
   - Copies the appropriate Lua handler from `cap-patches/`
   - Skips copies when you rerun the script
3. **Subdriver wiring** – `patch_subdriver.py`
   - Copies a subdriver template from `subdrivers/`
   - Adds the manufacturer/model to `PATCHED_DEVICE_MODELS`
   - Injects the new subdriver into the parent driver’s `sub_drivers` table

## Restoring to Stock Drivers

Every patch run preserves the original driver under `auto_patch/<driver>-backup`
(for example `zigbee-lock-backup`). Use the restore helper to undo a patch and
bring the stock driver back:

```
cd auto_patch
python restore_from_backup.py --driver zigbee-lock
```

`--dry-run` logs the moves without changing the filesystem, and `--verbose`
enables debug output. The script parks the patched driver in a timestamped
folder like `zigbee-lock-patched-YYYYMMDD-HHMMSS` and moves the backup back to
`zigbee-lock`.

## Driver Discovery Pipeline

Use the discovery CLI to scan either the public SmartThings Edge repository
directly from GitHub or any local clone that contains official drivers. The
tool aggregates every `fingerprints.yml`, summarizes the devices they target,
and highlights drivers that still lack capability mappings in
`custom_capability_list.config`.

Discover via GitHub (requires internet; optional `GITHUB_TOKEN` for higher
rate limits):

```bash
python -m discovery.discover_drivers \
  --source github \
  --repo SmartThingsCommunity/edge-drivers \
  --branch main \
  --output discovery/catalog.json
```

Work offline against a local clone (or any folder that holds driver
directories with `fingerprints.yml`):

```bash
python -m discovery.discover_drivers \
  --source local \
  --local-dir ~/edge-drivers \
  --driver-subpath drivers \
  --output discovery/catalog-local.yaml \
  --format yaml
```

`unsupported_drivers` in the generated report flags candidates that have no
entry in `custom_capability_list.config`, making it easy to decide which
drivers should be patched next.

## Repository Layout

```
.
├── Makefile
├── requirements.txt
├── requirements-dev.txt
├── auto_patch
│   ├── auto_patch.sh
│   ├── patch_profiles.py
│   ├── patch_handlers.py
│   ├── patch_subdriver.py
│   ├── custom_capability_list.config
│   ├── driver2patch.config
│   ├── cap-patches/
│   ├── subdrivers/
│   └── zigbee-lock/         <-- Sample SmartThings Edge driver
├── tests/
├── .github/
└── assets/
```

## Configuration Files

- `custom_capability_list.config` – maps human-friendly attribute names to
  custom capability IDs. Extend this file when a driver learns new attributes.
- `driver2patch.config` – links drivers to their handler file name and
  subdriver directory. Add entries here when supporting new drivers.

## Testing & Validation

Run quality checks locally with:

```bash
make lint
make test
```

GitHub Actions (`.github/workflows/ci.yml`) runs the exact commands on every PR
and on the `main`/`master` branches.

## Containerized Development

Build the reusable image (installs all dev dependencies):

```bash
make docker-build
```

Drop into a shell with the repo bind-mounted, ready to run scripts:

```bash
make docker-shell
# inside container
make test
```

Or execute the QA suite headlessly:

```bash
make docker-test
```

You can also use `docker compose run --rm dev bash` directly if you prefer the
Compose workflow. The container automatically honors `GITHUB_TOKEN`, making it
easy to run the discovery pipeline against the public SmartThings repos without
throttling.

## Find Device Model and Manufacturer

Use the [SmartThings web app](https://my.smartthings.com) and navigate to
**Advanced Users** to read the device’s model and manufacturer strings. These
values must match the inputs passed to `auto_patch.sh`.

![mysmartthings](assets/mysmartthings.png?raw=true)

## Currently Supported Drivers and Attributes

<table>
  <tr>
    <th> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; SmartThings Edge Drivers &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</th>
    <th> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Attributes &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</th>
  </tr>
  <tr>
    <td rowspan="9">zigbee-lock</td>
    <td>Language</td>
  </tr>
  <tr><td>AutoRelockTime</td></tr>
  <tr><td>SoundVolume</td></tr>
  <tr><td>OperatingMode</td></tr>
  <tr><td>EnableOneTouchLocking</td></tr>
  <tr><td>EnableInsideStatusLED</td></tr>
  <tr><td>EnablePrivacyModeButton</td></tr>
  <tr><td>WrongCodeEntryLimit</td></tr>
  <tr><td>UserCodeTemporaryDisableTime &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</td></tr>

  <tr>
    <td>zigbee-siren</td>
    <td>MaxDuration</td>
  </tr>

  <tr>
    <td rowspan="2">hue-motion</td>
    <td>PIROccupiedToUnoccupiedDelay</td>
  </tr>
  <tr><td>MotionSensitivity</td></tr>

  <tr>
    <td rowspan="7">zigbee-switch</td>
    <td>IdentifyTime</td>
  </tr>
  <tr><td>DeviceEnabled</td></tr>
  <tr><td>OnOffTransitionTime</td></tr>
  <tr><td>OnLevel</td></tr>
  <tr><td>OnTime</td></tr>
  <tr><td>StartUpOnOff</td></tr>
  <tr><td>StartUpColorTemperatureMireds</td></tr>

  <tr>
    <td rowspan="2">zigbee-dimmer-switch</td>
    <td>CheckInInterval</td>
  </tr>
  <tr><td>FastPollTimeout</td></tr>

  <tr>
    <td rowspan="4">zigbee-contact</td>
    <td>IdentifyTime</td>
  </tr>
  <tr><td>DeviceEnabled</td></tr>
  <tr><td>CheckInInterval</td></tr>
  <tr><td>FastPollTimeout</td></tr>

  <tr>
    <td rowspan="4">zigbee-water-leak-sensor</td>
    <td>IdentifyTime</td>
  </tr>
  <tr><td>DeviceEnabled</td></tr>
  <tr><td>CheckInInterval</td></tr>
  <tr><td>FastPollTimeout</td></tr>

  <tr>
    <td rowspan="4">zigbee-button</td>
    <td>IdentifyTime</td>
  </tr>
  <tr><td>DeviceEnabled</td></tr>
  <tr><td>CheckInInterval</td></tr>
  <tr><td>FastPollTimeout</td></tr>

  <tr>
    <td rowspan="4">zigbee-motion-sensor</td>
    <td>IdentifyTime</td>
  </tr>
  <tr><td>DeviceEnabled</td></tr>
  <tr><td>CheckInInterval</td></tr>
  <tr><td>FastPollTimeout</td></tr>

  <tr>
    <td rowspan="3">zigbee-presence-sensor</td>
    <td>IdentifyTime</td>
  </tr>
  <tr><td>CheckInInterval</td></tr>
  <tr><td>FastPollTimeout</td></tr>
</table>

## Roadmap

- Expand the library of subdrivers and handler templates.
- Add uninstall/restore helpers to undo patches without manual file copies.
- Publish the CLI on PyPI for easier installation.
- Improve Windows support (PowerShell wrapper + binary dependencies).

## How to Cite

If this project aids your research, cite the following work:

```
@inproceedings{xu2025hiddenattributes,
  title     = {Discovering and Exploiting IoT Device Hidden Attributes: A New Vulnerability in Smart Homes},
  author    = {Xuening Xu and Chenglong Fu and Xiaojiang Du and Bo Luo},
  booktitle = {Proceedings of the ACM Conference on Computer and Communications Security (CCS)},
  year      = {2025}
}
```

## Contributing

Bug reports and pull requests are welcome! Please review
[CONTRIBUTING.md](CONTRIBUTING.md) for the development workflow and the
[Code of Conduct](CODE_OF_CONDUCT.md) before participating.
