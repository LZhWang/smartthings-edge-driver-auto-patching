"""The unified ``edgeloom`` command line interface."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from edgeloom import __version__, schemas

LOGGER = logging.getLogger("edgeloom")


def _configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="[%(levelname)s] %(message)s",
    )


# --------------------------------------------------------------------------- patch


def _cmd_patch(args: argparse.Namespace) -> int:
    from edgeloom.patching import PatchError, run_patch

    try:
        result = run_patch(
            driver=args.driver,
            model=args.model,
            manufacturer=args.manufacturer,
            attributes=args.attributes,
            dry_run=args.dry_run,
        )
    except PatchError as exc:
        LOGGER.error("%s", exc)
        return 1

    if result.dry_run:
        print(f"Dry run complete for {result.driver.name}; nothing was written.")
    else:
        print(f"Patched {result.driver.name} (profile '{result.profile_name}').")
        if result.backup is not None:
            print(f"Original preserved at {result.backup}")
    return 0


# ----------------------------------------------------------------------- translate


def _cmd_translate(args: argparse.Namespace) -> int:
    from ha2st_edge.cli import translate

    token = args.token or os.environ.get("HA_TOKEN")
    if not token:
        LOGGER.error("A Home Assistant token is required; pass --token or set HA_TOKEN.")
        return 1
    return translate(ha_url=args.ha_url, token=token, output=args.output, domains=args.domains)


# ------------------------------------------------------------------------ discover


def _cmd_discover(args: argparse.Namespace) -> int:
    from discovery.discover_drivers import (
        build_driver_catalog,
        detect_unsupported_drivers,
        summarize_fingerprints,
        write_output,
    )

    if args.source == "local" and args.local_dir is None:
        LOGGER.error("--local-dir is required when --source local is used.")
        return 1

    try:
        fingerprints = build_driver_catalog(
            source=args.source,
            repo=args.repo,
            branch=args.branch,
            local_dir=args.local_dir,
            driver_subpath=args.driver_subpath,
            token=args.token or os.environ.get("GITHUB_TOKEN"),
            limit=args.limit,
            timeout=args.timeout,
        )
    except (RuntimeError, FileNotFoundError, ValueError) as exc:
        LOGGER.error("Discovery failed: %s", exc)
        return 1

    drivers, stats = summarize_fingerprints(fingerprints)
    unsupported = detect_unsupported_drivers(drivers, args.cap_config)
    catalog = {
        "generated_at": datetime.now(UTC).isoformat(),
        "source": args.source,
        "stats": stats,
        "unsupported_drivers": unsupported,
        "drivers": drivers,
    }
    write_output(catalog, args.output, args.format)
    print(
        f"Discovered {stats['fingerprint_count']} fingerprints across "
        f"{stats['driver_count']} drivers -> {args.output}"
    )
    if unsupported:
        print(f"{len(unsupported)} driver(s) have no capability mapping yet: {', '.join(unsupported)}")
    return 0


# ------------------------------------------------------------------------ validate


def _cmd_validate(args: argparse.Namespace) -> int:
    try:
        documents = schemas.iter_documents(args.paths)
    except schemas.SchemaError as exc:
        LOGGER.error("%s", exc)
        return 1

    checked = 0
    skipped = 0
    failures: list[schemas.ValidationResult] = []

    for path in documents:
        try:
            result = schemas.validate_document(path, kind=args.kind)
        except schemas.SchemaError as exc:
            LOGGER.error("%s", exc)
            return 1
        if result.skipped:
            skipped += 1
            continue
        checked += 1
        if result.ok:
            if getattr(args, "verbose", False):
                print(f"ok       {path} ({result.kind})")
        else:
            failures.append(result)

    for failure in failures:
        print(f"FAIL     {failure.path} ({failure.kind})")
        for message in failure.errors:
            print(f"           {message}")

    if checked == 0:
        # Silence here would read as success. It is not: nothing was checked.
        LOGGER.error("No profile or capability-map documents found in the given paths.")
        return 1

    summary = f"{checked} document(s) checked, {len(failures)} failed"
    if skipped:
        summary += f", {skipped} unrelated file(s) skipped"
    print(summary)
    return 1 if failures else 0


# ---------------------------------------------------------------------- entrypoint


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="edgeloom",
        description=(
            "An open toolchain for validating, patching, and translating smart-home "
            "edge drivers across platforms."
        ),
    )
    parser.add_argument("--version", action="version", version=f"edgeloom {__version__}")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")

    # Accept -v on either side of the subcommand. SUPPRESS keeps the subparser
    # from overwriting a global -v with its own default.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=argparse.SUPPRESS,
        help="Enable debug logging",
    )

    subparsers = parser.add_subparsers(dest="command", metavar="<command>")

    patch = subparsers.add_parser(
        "patch",
        parents=[common],
        help="Patch a SmartThings Edge driver to expose hidden device attributes",
    )
    patch.add_argument("driver", help="Path to (or folder name of) the Edge driver to patch")
    patch.add_argument("model", help="Device model string as reported by SmartThings")
    patch.add_argument("manufacturer", help="Device manufacturer string as reported by SmartThings")
    patch.add_argument(
        "attributes",
        nargs="?",
        default="ALL",
        help="Colon-separated attribute list, or ALL (default: ALL)",
    )
    patch.add_argument("-n", "--dry-run", action="store_true", help="Preview every change without writing")
    patch.set_defaults(func=_cmd_patch)

    translate = subparsers.add_parser(
        "translate",
        parents=[common],
        help="Generate SmartThings Edge proxy artifacts from Home Assistant entities",
    )
    translate.add_argument("--ha-url", required=True, help="Home Assistant base URL")
    translate.add_argument("--token", help="Long-lived HA token (or set HA_TOKEN)")
    translate.add_argument(
        "--domains",
        default="light,switch,lock,binary_sensor",
        help="Comma-separated HA domains to include",
    )
    translate.add_argument("--output", required=True, help="Output directory for generated artifacts")
    translate.set_defaults(func=_cmd_translate)

    discover = subparsers.add_parser(
        "discover", parents=[common], help="Enumerate Edge drivers and their Zigbee fingerprints"
    )
    discover.add_argument("--source", choices=["github", "local"], default="github")
    discover.add_argument("--repo", default="SmartThingsCommunity/edge-drivers")
    discover.add_argument("--branch", default="main")
    discover.add_argument("--driver-subpath", default="drivers")
    discover.add_argument("--local-dir", type=Path, help="Local directory containing drivers")
    discover.add_argument("--output", type=Path, default=Path("discovery/catalog.json"))
    discover.add_argument("--format", choices=["json", "yaml"], default="json")
    discover.add_argument("--limit", type=int, help="Stop after this many drivers")
    discover.add_argument("--timeout", type=float, default=15.0)
    discover.add_argument(
        "--cap-config",
        type=Path,
        default=Path("auto_patch/custom_capability_list.config"),
        help="Capability config used to flag drivers with no mapping",
    )
    discover.add_argument("--token", help="GitHub token (or set GITHUB_TOKEN)")
    discover.set_defaults(func=_cmd_discover)

    validate = subparsers.add_parser(
        "validate",
        parents=[common],
        help="Check device profiles and capability maps against the EdgeLoom schema",
    )
    validate.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=[Path(".")],
        help="Files or directories to check (default: the current directory)",
    )
    validate.add_argument(
        "--kind",
        choices=list(schemas.KINDS),
        help="Force a schema instead of inferring it from each document",
    )
    validate.set_defaults(func=_cmd_validate)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "func", None) is None:
        parser.print_help()
        return 2
    _configure_logging(getattr(args, "verbose", False))
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
