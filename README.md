# Home Assistant → SmartThings Edge Bridge

A minimal scaffold to generate SmartThings Edge proxy artifacts for Home Assistant entities.

## Overview
- `ha2st_edge`: Python CLI that queries HA `/api/states`, maps supported entities to SmartThings capabilities, and generates Edge device profiles plus a `ha_devices.yaml` config.
- `ha_proxy_edge_driver`: SmartThings Edge LAN driver that reads the generated config, forwards commands to HA REST services, and can refresh state. Lua code is stubbed to match Edge patterns.

## Quickstart
1. `python -m venv .venv && source .venv/bin/activate`
2. `pip install -r requirements.txt`
3. Run generator (writes `ha_token` into config):  
   `python -m ha2st_edge.cli --ha-url http://homeassistant.local:8123 --token YOUR_HA_TOKEN --domains light,switch,lock,binary_sensor --output ./generated_edge`
4. Copy or point the Edge driver to `generated_edge/profiles` and `generated_edge/config/ha_devices.yaml`.  
   - Override paths with env `HA_EDGE_CONFIG_PATH`.  
   - Override HA connection at runtime with env `HA_EDGE_BASE_URL` and `HA_EDGE_TOKEN` (otherwise values come from YAML).
5. Package the Edge driver with SmartThings CLI (outside scope here) and install to your hub.

## Notes
- Supported HA domains: `light`, `switch`, `lock`, `binary_sensor` (door/window/motion).
- Capabilities mapped: `switch`, `switchLevel`, `lock`, `contactSensor`, `motionSensor`, optional `colorControl` for color lights.
- Ensure the SmartThings hub can reach your HA base URL on the LAN. Store HA tokens securely (env vars recommended).
