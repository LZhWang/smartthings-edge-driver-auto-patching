from pathlib import Path

from ha2st_edge import cli
from ha2st_edge.ha_client import HomeAssistantError


def install_client_stub(monkeypatch, *, states=None, error=None):
    class StubClient:
        def __init__(self, **_kwargs):
            pass

        def get_states(self):
            if error is not None:
                raise error
            return states

    monkeypatch.setattr(cli, "HomeAssistantClient", StubClient)


def test_filter_entities_keeps_selected_domains_and_drops_malformed_ids():
    states = [
        {"entity_id": "light.lamp"},
        {"entity_id": "switch.plug"},
        {"entity_id": "sensor.temperature"},
        {"entity_id": "malformed"},
    ]

    assert cli.filter_entities(states, ["light", "switch"]) == states[:2]


def test_translate_returns_one_without_writes_when_client_fails(monkeypatch, tmp_path):
    install_client_stub(monkeypatch, error=HomeAssistantError("unreachable"))

    result = cli.translate("http://ha.local:8123", "token", tmp_path)

    assert result == 1
    assert list(tmp_path.iterdir()) == []


def test_translate_returns_one_without_profiles_when_nothing_maps(monkeypatch, tmp_path):
    install_client_stub(
        monkeypatch,
        states=[{"entity_id": "binary_sensor.noise", "attributes": {"device_class": "sound"}}],
    )

    result = cli.translate("http://ha.local:8123", "token", tmp_path)

    assert result == 1
    assert not (tmp_path / "profiles").exists()


def test_translate_writes_switch_profile_and_device_config(monkeypatch, tmp_path):
    install_client_stub(
        monkeypatch,
        states=[{"entity_id": "switch.plug", "attributes": {"friendly_name": "Plug"}}],
    )

    result = cli.translate("http://ha.local:8123", "token", tmp_path)

    assert result == 0
    assert (tmp_path / "profiles" / "ha_switch_basic.yaml").is_file()
    assert (tmp_path / "config" / "ha_devices.yaml").is_file()


def test_translate_accepts_equivalent_string_and_list_domains(monkeypatch, tmp_path):
    install_client_stub(
        monkeypatch,
        states=[
            {"entity_id": "light.lamp", "attributes": {}},
            {"entity_id": "switch.plug", "attributes": {}},
            {"entity_id": "lock.front", "attributes": {}},
        ],
    )
    string_output = tmp_path / "string"
    list_output = tmp_path / "list"

    assert cli.translate("http://ha.local:8123", "token", string_output, domains="light,switch") == 0
    assert cli.translate("http://ha.local:8123", "token", list_output, domains=["light", "switch"]) == 0

    def generated_files(root: Path):
        return {
            path.relative_to(root): path.read_text(encoding="utf-8")
            for path in root.rglob("*")
            if path.is_file()
        }

    assert generated_files(string_output) == generated_files(list_output)
