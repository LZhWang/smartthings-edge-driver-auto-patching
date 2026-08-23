import argparse
import logging
from pathlib import Path
from typing import List, Dict, Any

from .ha_client import HomeAssistantClient, HomeAssistantError
from .mapping import infer_profile, DeviceProfileSpec
from .generator import generate_profiles_and_config

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
LOG = logging.getLogger("ha2st_edge")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate SmartThings Edge proxy artifacts from Home Assistant."
    )
    parser.add_argument(
        "--ha-url",
        required=True,
        help="Base URL of Home Assistant (e.g., http://192.168.1.10:8123)",
    )
    parser.add_argument("--token", required=True, help="Long-lived Home Assistant token")
    parser.add_argument(
        "--domains",
        default="light,switch,lock,binary_sensor",
        help="Comma-separated HA domains to include (default: light,switch,lock,binary_sensor)",
    )
    parser.add_argument(
        "--output", required=True, help="Output directory for generated Edge artifacts"
    )
    return parser.parse_args()


def filter_entities(states: List[Dict[str, Any]], domains: List[str]) -> List[Dict[str, Any]]:
    filtered = []
    for state in states:
        entity_id = state.get("entity_id", "")
        domain = entity_id.split(".", 1)[0] if "." in entity_id else ""
        if domain in domains:
            filtered.append(state)
    return filtered


def main() -> int:
    args = parse_args()
    domains = [d.strip() for d in args.domains.split(",") if d.strip()]
    output_dir = Path(args.output)

    client = HomeAssistantClient(base_url=args.ha_url, token=args.token)
    try:
        states = client.get_states()
    except HomeAssistantError as exc:
        LOG.error("Failed to fetch states: %s", exc)
        return 1

    LOG.info("Fetched %d states from Home Assistant", len(states))
    entities = filter_entities(states, domains)
    LOG.info("Filtered to %d entities matching domains %s", len(entities), domains)

    mapped: List[Dict[str, Any]] = []
    skipped: List[str] = []
    for state in entities:
        spec: DeviceProfileSpec | None = infer_profile(state)
        if spec is None:
            skipped.append(state.get("entity_id", "unknown"))
            continue
        mapped.append({"state": state, "profile": spec})

    if skipped:
        LOG.warning("Skipped %d entities with no mapping: %s", len(skipped), ", ".join(skipped))

    if not mapped:
        LOG.error("No entities were mapped; nothing to generate.")
        return 1

    generate_profiles_and_config(mapped, output_dir, ha_base_url=args.ha_url, ha_token=args.token)
    LOG.info("Generation complete at %s", output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
