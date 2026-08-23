from pathlib import Path

import yaml
from ha2st_edge.generator import generate_profiles_and_config
from ha2st_edge.mapping import DeviceProfileSpec


def test_generate_profiles_and_config(tmp_path: Path):
    mapped = [
        {
            "state": {"entity_id": "light.lamp", "attributes": {"friendly_name": "Lamp", "brightness": 50}},
            "profile": DeviceProfileSpec("ha_light_dimmable", ["switch", "switchLevel"], "Light"),
        },
        {
            "state": {"entity_id": "light.rgb", "attributes": {"friendly_name": "RGB", "hs_color": [1, 2]}},
            "profile": DeviceProfileSpec(
                "ha_light_color", ["switch", "switchLevel", "colorControl"], "Light"
            ),
        },
        {
            "state": {"entity_id": "switch.plug", "attributes": {"friendly_name": "Plug"}},
            "profile": DeviceProfileSpec("ha_switch_basic", ["switch"], "Switch"),
        },
    ]
    generate_profiles_and_config(mapped, tmp_path, ha_base_url="http://ha.local:8123", ha_token="TEST_TOKEN")

    profiles_dir = tmp_path / "profiles"
    config_dir = tmp_path / "config"
    assert (profiles_dir / "ha_light_dimmable.yaml").exists()
    assert (profiles_dir / "ha_light_color.yaml").exists()
    assert (profiles_dir / "ha_switch_basic.yaml").exists()
    cfg_path = config_dir / "ha_devices.yaml"
    assert cfg_path.exists()

    cfg = yaml.safe_load(cfg_path.read_text())
    assert cfg["ha_base_url"] == "http://ha.local:8123"
    assert cfg["ha_token"] == "TEST_TOKEN"
    # One device entry per mapped HA entity. Profiles are de-duplicated (three
    # entities, three distinct profiles here), but devices are not: each HA
    # entity has to surface as its own SmartThings device.
    assert len(cfg["devices"]) == 3
    assert [d["profile"] for d in cfg["devices"]] == [
        "ha_light_dimmable",
        "ha_light_color",
        "ha_switch_basic",
    ]
    assert [d["ha_entity_id"] for d in cfg["devices"]] == ["light.lamp", "light.rgb", "switch.plug"]
