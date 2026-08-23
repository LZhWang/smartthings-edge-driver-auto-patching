from dataclasses import dataclass
from typing import List, Optional, Dict, Any

SUPPORTED_BINARY_SENSOR_CONTACT = {"door", "window", "opening"}
SUPPORTED_BINARY_SENSOR_MOTION = {"motion"}


@dataclass
class DeviceProfileSpec:
    profile_name: str
    capabilities: List[str]
    category: str


def infer_profile(state: Dict[str, Any]) -> Optional[DeviceProfileSpec]:
    entity_id = state.get("entity_id", "")
    if "." not in entity_id:
        return None
    domain, _ = entity_id.split(".", 1)
    attrs = state.get("attributes", {}) or {}

    if domain == "light":
        caps = ["switch"]
        profile = "ha_light_basic"
        if "brightness" in attrs:
            caps.append("switchLevel")
            profile = "ha_light_dimmable"
        if "hs_color" in attrs or "rgb_color" in attrs:
            caps.append("colorControl")
            profile = "ha_light_color"
        return DeviceProfileSpec(profile_name=profile, capabilities=caps, category="Light")

    if domain == "switch":
        return DeviceProfileSpec(profile_name="ha_switch_basic", capabilities=["switch"], category="Switch")

    if domain == "lock":
        return DeviceProfileSpec(profile_name="ha_lock_basic", capabilities=["lock"], category="SmartLock")

    if domain == "binary_sensor":
        device_class = attrs.get("device_class")
        if device_class in SUPPORTED_BINARY_SENSOR_CONTACT:
            return DeviceProfileSpec(
                profile_name="ha_contact_sensor", capabilities=["contactSensor"], category="ContactSensor"
            )
        if device_class in SUPPORTED_BINARY_SENSOR_MOTION:
            return DeviceProfileSpec(
                profile_name="ha_motion_sensor", capabilities=["motionSensor"], category="MotionSensor"
            )

    return None
