import pytest
from ha2st_edge import ha_client
from ha2st_edge.ha_client import HomeAssistantClient, HomeAssistantError


class FakeResponse:
    def __init__(self, payload=None, *, status_code=200, text=""):
        self.payload = [] if payload is None else payload
        self.status_code = status_code
        self.text = text

    def json(self):
        return self.payload


def test_get_states_strips_trailing_slash(monkeypatch):
    requested_urls = []

    def fake_get(url, **_kwargs):
        requested_urls.append(url)
        return FakeResponse()

    monkeypatch.setattr(ha_client.requests, "get", fake_get)

    HomeAssistantClient("http://ha.local:8123/", "token").get_states()

    assert requested_urls == ["http://ha.local:8123/api/states"]


def test_get_states_sends_auth_headers_and_timeout(monkeypatch):
    request_kwargs = {}

    def fake_get(_url, **kwargs):
        request_kwargs.update(kwargs)
        return FakeResponse()

    monkeypatch.setattr(ha_client.requests, "get", fake_get)

    HomeAssistantClient("http://ha.local:8123", "secret-token").get_states()

    assert request_kwargs == {
        "headers": {
            "Authorization": "Bearer secret-token",
            "Content-Type": "application/json",
        },
        "timeout": 10.0,
    }


def test_get_states_raises_for_non_200(monkeypatch):
    monkeypatch.setattr(
        ha_client.requests,
        "get",
        lambda *_args, **_kwargs: FakeResponse(status_code=401, text="Unauthorized"),
    )

    with pytest.raises(HomeAssistantError, match="401"):
        HomeAssistantClient("http://ha.local:8123", "bad-token").get_states()


def test_get_states_wraps_invalid_json(monkeypatch):
    class InvalidJsonResponse(FakeResponse):
        def json(self):
            raise ValueError("invalid JSON")

    monkeypatch.setattr(ha_client.requests, "get", lambda *_args, **_kwargs: InvalidJsonResponse())

    with pytest.raises(HomeAssistantError, match="Invalid JSON"):
        HomeAssistantClient("http://ha.local:8123", "token").get_states()


def test_get_states_rejects_non_list_payload(monkeypatch):
    monkeypatch.setattr(
        ha_client.requests,
        "get",
        lambda *_args, **_kwargs: FakeResponse({"entity_id": "switch.plug"}),
    )

    with pytest.raises(HomeAssistantError, match="Unexpected states payload type"):
        HomeAssistantClient("http://ha.local:8123", "token").get_states()


def test_get_states_returns_list_unchanged(monkeypatch):
    states = [{"entity_id": "switch.plug", "attributes": {}}]
    monkeypatch.setattr(ha_client.requests, "get", lambda *_args, **_kwargs: FakeResponse(states))

    result = HomeAssistantClient("http://ha.local:8123", "token").get_states()

    assert result is states
