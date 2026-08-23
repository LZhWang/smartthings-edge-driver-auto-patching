# Patching SmartThings Edge drivers

Retrofit a stock SmartThings Edge driver so it exposes Zigbee attributes the
shipped distribution hides. This is the `auto_patch` component, reachable as
`edgeloom patch`.

> Every run backs the driver up first and rolls the backup back if any step
> fails. See [SECURITY.md](../SECURITY.md) for the safety and disclosure model.

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
edgeloom patch --dry-run zigbee-lock "YRD226 TSDB" Yale Language
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

## Configuration Files

- `custom_capability_list.config` – maps human-friendly attribute names to
  custom capability IDs. Extend this file when a driver learns new attributes.
- `driver2patch.config` – links drivers to their handler file name and
  subdriver directory. Add entries here when supporting new drivers.

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

