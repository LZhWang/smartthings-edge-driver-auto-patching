import argparse
import configparser
import logging
import shutil
import sys
from pathlib import Path

LOGGER = logging.getLogger("edge_patcher.patch_handlers")
SCRIPT_ROOT = Path(__file__).resolve().parent
DEFAULT_DRIVER_CONFIG = SCRIPT_ROOT / "driver2patch.config"
PATCH_SOURCE_DIR = SCRIPT_ROOT / "cap-patches"


def configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="[%(levelname)s] %(message)s")


def load_driver_config(config_path: Path) -> configparser.ConfigParser:
    config = configparser.ConfigParser()
    if not config_path.exists():
        raise FileNotFoundError(f"Driver config not found: {config_path}")
    config.read(config_path)
    return config


def patch_handlers(
    driver: str,
    config_path: Path = DEFAULT_DRIVER_CONFIG,
    dry_run: bool = False,
) -> Path:
    driver_dir = Path(driver).resolve()
    if not driver_dir.exists():
        raise FileNotFoundError(f"Driver directory not found: {driver_dir}")

    config = load_driver_config(config_path)
    driver_name = driver_dir.name
    if driver_name not in config:
        raise KeyError(f"Driver '{driver_name}' is not present in driver mapping")
    filename = config[driver_name]["filename"]

    patch_src = PATCH_SOURCE_DIR / f"{filename}.lua"
    if not patch_src.exists():
        raise FileNotFoundError(f"Patch file not found: {patch_src}")

    patch_dest = driver_dir / "src" / f"{filename}.lua"
    if patch_dest.exists():
        LOGGER.info("[Step 2] handler already present at %s", patch_dest)
        return patch_dest

    if dry_run:
        LOGGER.info("[Dry run] Would copy %s -> %s", patch_src, patch_dest)
    else:
        patch_dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(patch_src, patch_dest)
        LOGGER.info("Copied handler patch to %s", patch_dest)
    return patch_dest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Patch Zigbee handlers.")
    parser.add_argument(
        "--driver",
        type=str,
        required=True,
        help="Folder name (or path) of the Edge driver to patch",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_DRIVER_CONFIG,
        help="Path to driver mapping config",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview file changes without writing")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    configure_logging(args.verbose)
    try:
        patch_handlers(driver=args.driver, config_path=args.config, dry_run=args.dry_run)
    except Exception as exc:  # noqa: BLE001
        LOGGER.error("Failed to patch handlers: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
