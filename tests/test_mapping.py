import pytest

from ha2st_edge.mapping import infer_profile


def test_light_dimmable():
    state = {"entity_id": "light.lamp", "attributes": {"brightness": 120}}
    spec = infer_profile(state)
    assert spec.profile_name == "ha_light_dimmable"
    assert "switch" in spec.capabilities and "switchLevel" in spec.capabilities


def test_light_color():
    state = {"entity_id": "light.rgb", "attributes": {"hs_color": [1, 2]}}
    spec = infer_profile(state)
    assert spec.profile_name == "ha_light_color"
    assert "colorControl" in spec.capabilities


def test_switch():
    state = {"entity_id": "switch.plug", "attributes": {}}
    spec = infer_profile(state)
    assert spec.profile_name == "ha_switch_basic"
    assert spec.capabilities == ["switch"]


def test_lock():
    state = {"entity_id": "lock.front", "attributes": {}}
    spec = infer_profile(state)
    assert spec.profile_name == "ha_lock_basic"
    assert spec.capabilities == ["lock"]


@pytest.mark.parametrize(
    "device_class,expected",
    [
        ("door", "ha_contact_sensor"),
        ("window", "ha_contact_sensor"),
        ("opening", "ha_contact_sensor"),
        ("motion", "ha_motion_sensor"),
    ],
)
def test_binary_sensor_mapping(device_class, expected):
    state = {"entity_id": "binary_sensor.sensor", "attributes": {"device_class": device_class}}
    spec = infer_profile(state)
    assert spec.profile_name == expected


def test_unsupported_binary_sensor():
    state = {"entity_id": "binary_sensor.unknown", "attributes": {"device_class": "sound"}}
    assert infer_profile(state) is None
