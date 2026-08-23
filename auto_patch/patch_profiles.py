from __future__ import annotations

import argparse
import configparser
import logging
import sys
from collections.abc import Iterable
from pathlib import Path

import yaml

LOGGER = logging.getLogger("edge_patcher.patch_profiles")
SCRIPT_ROOT = Path(__file__).resolve().parent
DEFAULT_CAPABILITY_CONFIG = SCRIPT_ROOT / "custom_capability_list.config"


class IndentDumper(yaml.Dumper):
    def increase_indent(self, flow: bool = False, indentless: bool = False):  # pragma: no cover - yaml hook
        return super().increase_indent(flow, False)


def configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="[%(levelname)s] %(message)s")


def load_capability_map(config_path: Path) -> configparser.ConfigParser:
    config = configparser.ConfigParser()
    if not config_path.exists():
        raise FileNotFoundError(f"Capability config not found: {config_path}")
    config.read(config_path)
    return config


def resolve_capabilities(
    config: configparser.ConfigParser,
    driver: str,
    attributes: str | None,
) -> list[str]:
    if driver not in config:
        raise KeyError(f"Driver '{driver}' is not present in capability config")

    if attributes in (None, "", "ALL"):
        return [value for _, value in config.items(driver)]

    requested = []
    for attr in attributes.split(":"):
        key = attr.strip()
        if not key:
            continue
        try:
            requested.append(config[driver][key])
        except KeyError as exc:
            raise KeyError(f"{driver} does not support attribute '{key}'") from exc
    if not requested:
        raise ValueError("No valid attributes provided")
    return requested


def patch_fingerprints(devices: Iterable[dict], model: str, manufacturer: str | None) -> str:
    for device in devices:
        if manufacturer and device.get("manufacturer") and device["manufacturer"] != manufacturer:
            continue
        if device.get("model") == model:
            profile_name = device["deviceProfileName"]
            device["deviceProfileName"] = f"{profile_name}-patch"
            LOGGER.debug(
                "Patched fingerprint for %s/%s -> %s",
                manufacturer or "*",
                model,
                device["deviceProfileName"],
            )
            return profile_name
    raise ValueError(
        f"Unable to find fingerprint for model '{model}' (manufacturer='{manufacturer}')",
    )


def load_yaml(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def write_yaml(path: Path, data: dict) -> None:
    with path.open("w", encoding="utf-8") as handle:
        yaml.dump(data, handle, sort_keys=False, Dumper=IndentDumper)


def ensure_backup(active: Path, backup: Path, dry_run: bool) -> None:
    if dry_run:
        LOGGER.info("[Dry run] Would back up %s to %s", active, backup)
        return

    if backup.exists():
        LOGGER.info("Reusing existing backup at %s", backup)
        active.unlink(missing_ok=True)
    else:
        LOGGER.info("Creating fingerprint backup at %s", backup)
        active.replace(backup)


def create_new_profile(
    profile_path: Path,
    new_profile_path: Path,
    capabilities: list[str],
    dry_run: bool,
) -> None:
    profiles = load_yaml(profile_path)
    profiles["name"] = f"{profiles['name']}-patch"
    additional_caps = [{"id": cap, "version": 1} for cap in capabilities]
    profiles["components"][0]["capabilities"].extend(additional_caps)

    if dry_run:
        LOGGER.info("[Dry run] Would create profile %s", new_profile_path)
        return

    write_yaml(new_profile_path, profiles)
    LOGGER.info("Wrote patched profile %s", new_profile_path)
    LOGGER.debug("Wrote new profile %s", new_profile_path)


def patch_profiles(
    driver: str,
    model: str,
    manufacturer: str | None,
    attributes: str | None,
    config_path: Path = DEFAULT_CAPABILITY_CONFIG,
    dry_run: bool = False,
) -> str:
    driver_dir = Path(driver).resolve()
    if not driver_dir.exists():
        raise FileNotFoundError(f"Driver directory not found: {driver_dir}")
    fingerprints_path = driver_dir / "fingerprints.yml"
    backup_path = driver_dir / "fingerprints-old.yml"

    config = load_capability_map(config_path)
    custom_capabilities = resolve_capabilities(config, driver_dir.name, attributes)

    fingerprints = load_yaml(fingerprints_path)
    profile_name = patch_fingerprints(fingerprints["zigbeeManufacturer"], model, manufacturer)

    ensure_backup(fingerprints_path, backup_path, dry_run)
    if dry_run:
        LOGGER.info("[Dry run] Would write patched fingerprints for %s", driver_dir)
    else:
        write_yaml(fingerprints_path, fingerprints)
        LOGGER.info("Patched fingerprints saved to %s", fingerprints_path)

    original_profile_path = driver_dir / "profiles" / f"{profile_name}.yml"
    patched_profile_path = driver_dir / "profiles" / f"{profile_name}-patch.yml"
    create_new_profile(original_profile_path, patched_profile_path, custom_capabilities, dry_run)

    return profile_name


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Patch Zigbee fingerprints.")
    parser.add_argument(
        "--driver",
        type=str,
        required=True,
        help="Folder name (or path) of the Edge driver to patch",
    )
    parser.add_argument("--model", type=str, required=True, help="Device model to patch")
    parser.add_argument("--mfg", type=str, help="Device manufacturer to patch", default=None)
    parser.add_argument(
        "--attributes",
        type=str,
        help="Attributes to patch, separated by ':'",
        default="ALL",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CAPABILITY_CONFIG,
        help="Path to capability config",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview file changes without writing")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    configure_logging(args.verbose)
    try:
        patch_profiles(
            driver=args.driver,
            model=args.model,
            manufacturer=args.mfg,
            attributes=args.attributes,
            config_path=args.config,
            dry_run=args.dry_run,
        )
    except Exception as exc:  # noqa: BLE001 - show friendly error message
        LOGGER.error("Failed to patch profiles: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
