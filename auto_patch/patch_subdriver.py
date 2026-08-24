import argparse
import configparser
import logging
import re
import shutil
import sys
from pathlib import Path

try:  # imported as a package by edgeloom.patching and the test suite
    from auto_patch.paths import contained_path
except ImportError:  # executed directly: python auto_patch/patch_subdriver.py
    from paths import contained_path

LOGGER = logging.getLogger("edge_patcher.patch_subdriver")
SCRIPT_ROOT = Path(__file__).resolve().parent
DEFAULT_DRIVER_CONFIG = SCRIPT_ROOT / "driver2patch.config"
SUBDRIVER_SOURCE_DIR = SCRIPT_ROOT / "subdrivers"


def configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="[%(levelname)s] %(message)s")


def load_driver_config(config_path: Path) -> configparser.ConfigParser:
    config = configparser.ConfigParser()
    if not config_path.exists():
        raise FileNotFoundError(f"Driver config not found: {config_path}")
    config.read(config_path)
    return config


def copy_subdriver_template(driver_dir: Path, subdriver: str, dry_run: bool) -> bool:
    src_path = SUBDRIVER_SOURCE_DIR / subdriver
    if not src_path.exists():
        raise FileNotFoundError(f"Subdriver template not found: {src_path}")
    dest_path = contained_path(driver_dir, "src", subdriver)

    if dest_path.exists():
        LOGGER.info("[Step 3] subdriver already present at %s", dest_path)
        return False

    if dry_run:
        LOGGER.info("[Dry run] Would copy subdriver %s -> %s", src_path, dest_path)
    else:
        shutil.copytree(src_path, dest_path)
        LOGGER.info("Copied subdriver template to %s", dest_path)
    return True


def add_device_model(subdriver_path: Path, manufacturer: str, model: str, dry_run: bool) -> None:
    if not manufacturer:
        raise ValueError("Manufacturer is required when adding device models")
    if not model:
        raise ValueError("Model is required when adding device models")

    init_path = contained_path(subdriver_path, "init.lua")
    if not init_path.exists():
        if dry_run:
            LOGGER.info("[Dry run] Would create %s and add %s/%s", init_path, manufacturer, model)
            return
        raise FileNotFoundError(f"Subdriver init.lua not found: {init_path}")

    code = init_path.read_text(encoding="utf-8")
    pattern = re.compile(r"(^local PATCHED_DEVICE_MODELS = {(?:.|\n)*?^\})", re.MULTILINE)
    match = pattern.search(code)
    if not match:
        raise ValueError("Unable to locate PATCHED_DEVICE_MODELS block")

    block = match.group(0)
    new_model_line = f'    {{ mfr = "{manufacturer}", model = "{model}" }},'
    if new_model_line in block:
        LOGGER.info("[Step 3] model already present in patch list")
        return

    models = block.splitlines()
    updated_block = "\n".join([models[0], new_model_line, *models[1:]])
    if dry_run:
        LOGGER.info("[Dry run] Would add %s/%s to %s", manufacturer, model, init_path)
        return

    updated_code = code.replace(block, updated_block)
    init_path.write_text(updated_code, encoding="utf-8")
    LOGGER.info("Added %s/%s to %s", manufacturer, model, init_path)


def construct_new_subdrivers_block(existing_block: str, new_driver: str) -> str:
    require_pattern = re.compile(r'require\("(.*?)"\)')
    existing_drivers = require_pattern.findall(existing_block)
    drivers = [new_driver] + [drv for drv in existing_drivers if drv != new_driver]

    lines = existing_block.splitlines()
    indent_match = re.match(r"\s*", lines[1]) if len(lines) > 1 else None
    indent = indent_match.group(0) if indent_match else " " * 4
    closing_indent_match = re.match(r"\s*", lines[-1]) if lines else None
    closing_indent = closing_indent_match.group(0) if closing_indent_match else ""

    new_lines = [lines[0]] + [f'{indent}require("{drv}"),' for drv in drivers] + [f"{closing_indent}}}"]
    return "\n".join(new_lines)


def update_parent_driver_template(driver_dir: Path, subdriver: str, dry_run: bool) -> None:
    # Refuses a symlinked src/ or src/init.lua, either of which would
    # redirect this in-place rewrite onto a file outside the driver.
    parent_driver_path = contained_path(driver_dir, "src", "init.lua")
    if not parent_driver_path.exists():
        raise FileNotFoundError(f"Parent driver init.lua not found: {parent_driver_path}")

    code = parent_driver_path.read_text(encoding="utf-8")
    sub_driver_pattern = re.compile(r"(sub_drivers = \{(?:.|\n)*?\})", re.MULTILINE)
    matches = sub_driver_pattern.findall(code)

    if matches:
        new_block = construct_new_subdrivers_block(matches[0], subdriver)
        updated_code = code.replace(matches[0], new_block, 1)
    else:
        template_pattern = re.compile(r"(^local\s+\w+\s*=\s*\{(?:.|\n)*?^\})", re.MULTILINE)
        template_match = template_pattern.search(code)
        if not template_match:
            raise ValueError("Could not locate driver template to inject subdriver")
        template_block = template_match.group(0).splitlines()
        indent = len(template_block[1]) - len(template_block[1].lstrip())
        injection = " " * indent + f'sub_drivers = {{ require("{subdriver}") }},'
        new_template_block = "\n".join([template_block[0], injection, *template_block[1:]])
        updated_code = code.replace(template_match.group(0), new_template_block, 1)

    if dry_run:
        LOGGER.info("[Dry run] Would update parent driver to include %s", subdriver)
        return

    parent_driver_path.write_text(updated_code, encoding="utf-8")
    LOGGER.info("Updated parent driver to include %s", subdriver)


def patch_subdriver(
    driver: str,
    manufacturer: str,
    model: str,
    config_path: Path = DEFAULT_DRIVER_CONFIG,
    dry_run: bool = False,
) -> None:
    driver_dir = Path(driver).resolve()
    if not driver_dir.exists():
        raise FileNotFoundError(f"Driver directory not found: {driver_dir}")

    config = load_driver_config(config_path)
    driver_name = driver_dir.name
    if driver_name not in config:
        raise KeyError(f"Driver '{driver_name}' is not present in driver mapping")
    subdriver = config[driver_name]["subdriver"]

    created = copy_subdriver_template(driver_dir, subdriver, dry_run)
    subdriver_path = contained_path(driver_dir, "src", subdriver)
    if created or subdriver_path.exists():
        add_device_model(subdriver_path, manufacturer, model, dry_run)
        update_parent_driver_template(driver_dir, subdriver, dry_run)
    else:
        LOGGER.info("[Step 3] already patched")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Patch Zigbee subdrivers.")
    parser.add_argument(
        "--driver",
        type=str,
        required=True,
        help="Folder name (or path) of the Edge driver to patch",
    )
    parser.add_argument("--model", type=str, required=True, help="Device model to patch")
    parser.add_argument("--mfg", type=str, required=True, help="Device manufacturer to patch")
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
        patch_subdriver(
            driver=args.driver,
            manufacturer=args.mfg,
            model=args.model,
            config_path=args.config,
            dry_run=args.dry_run,
        )
    except Exception as exc:  # noqa: BLE001
        LOGGER.error("Failed to patch subdriver: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
