"""Cross-platform orchestration of the three-step driver patch.

``auto_patch/auto_patch.sh`` remains the shell entrypoint, but it needs bash and
therefore excludes native Windows. This module drives the same three steps
directly through their Python functions, so ``edgeloom patch`` runs anywhere
Python does, and applies the same safety contract: take a backup first, and roll
it back if any step fails.
"""

from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass
from pathlib import Path

from auto_patch.patch_handlers import DEFAULT_DRIVER_CONFIG, patch_handlers
from auto_patch.patch_profiles import DEFAULT_CAPABILITY_CONFIG, patch_profiles
from auto_patch.patch_subdriver import patch_subdriver

LOGGER = logging.getLogger("edgeloom.patch")


class PatchError(RuntimeError):
    """Raised when a patch run fails after the driver has been restored."""


@dataclass(frozen=True)
class PatchResult:
    driver: Path
    backup: Path | None
    profile_name: str
    dry_run: bool


def _backup_path(driver_dir: Path) -> Path:
    return driver_dir.with_name(f"{driver_dir.name}-backup")


def create_backup(driver_dir: Path, *, dry_run: bool) -> Path | None:
    """Copy the driver aside before anything mutates it."""
    backup = _backup_path(driver_dir)
    if dry_run:
        LOGGER.info("[Dry run] Would back up %s to %s", driver_dir, backup)
        return None
    if backup.exists():
        LOGGER.info("Backup already exists at %s; it will be reused.", backup)
        return backup
    LOGGER.info("Creating driver backup at %s...", backup)
    shutil.copytree(driver_dir, backup)
    return backup


def restore_backup(driver_dir: Path, backup: Path | None) -> None:
    """Put the driver back exactly as it was found.

    Refuses to remove the driver when no backup is available, so a failure
    cannot escalate into losing the user's input.
    """
    if backup is None or not backup.is_dir():
        LOGGER.error(
            "No backup found for %s; leaving the tree untouched. It may be partially patched.",
            driver_dir,
        )
        return
    LOGGER.info("Restoring backup due to an error...")
    shutil.rmtree(driver_dir, ignore_errors=True)
    backup.replace(driver_dir)
    LOGGER.info("Backup restored.")


def run_patch(
    driver: str | Path,
    model: str,
    manufacturer: str,
    attributes: str = "ALL",
    *,
    capability_config: Path = DEFAULT_CAPABILITY_CONFIG,
    driver_config: Path = DEFAULT_DRIVER_CONFIG,
    dry_run: bool = False,
) -> PatchResult:
    """Back up the driver, run the three patch steps, roll back on failure."""
    driver_dir = Path(driver).resolve()
    if not driver_dir.is_dir():
        raise PatchError(f"Driver directory '{driver}' not found at {driver_dir}")

    backup = create_backup(driver_dir, dry_run=dry_run)
    try:
        LOGGER.info("Step 1: patching fingerprints...")
        profile_name = patch_profiles(
            driver=str(driver_dir),
            model=model,
            manufacturer=manufacturer,
            attributes=attributes,
            config_path=capability_config,
            dry_run=dry_run,
        )

        LOGGER.info("Step 2: patching handler functions...")
        patch_handlers(driver=str(driver_dir), config_path=driver_config, dry_run=dry_run)

        LOGGER.info("Step 3: patching subdriver...")
        patch_subdriver(
            driver=str(driver_dir),
            manufacturer=manufacturer,
            model=model,
            config_path=driver_config,
            dry_run=dry_run,
        )
    except Exception as exc:
        if not dry_run:
            restore_backup(driver_dir, backup)
        raise PatchError(f"Patch failed: {exc}") from exc

    LOGGER.info("All steps completed successfully; <%s> is now the patched driver.", driver_dir.name)
    return PatchResult(driver=driver_dir, backup=backup, profile_name=profile_name, dry_run=dry_run)
