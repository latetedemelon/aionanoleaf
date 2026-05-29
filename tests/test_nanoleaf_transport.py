# Copyright 2021, Milan Meulemans.
#
# This file is part of aionanoleaf.
#
# aionanoleaf is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# aionanoleaf is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with aionanoleaf.  If not, see <https://www.gnu.org/licenses/>.

"""Transport-level tests.

These exercise the JSON helpers (``_get_json``/``_put_json``/``write_effect``)
that wire the high-level helper clients (:class:`EffectsClient`,
:class:`LayoutClient`, :class:`RhythmClient`, :class:`DigitalTwin`) to the real
:class:`Nanoleaf` HTTP transport, using a fake ``aiohttp`` session so no real
device is required.
"""

import json

try:
    import pytest  # type: ignore
except ImportError:  # pragma: no cover - lint-only environments
    pytest = None  # type: ignore

from aionanoleaf import (
    DigitalTwin,
    EffectsClient,
    LayoutClient,
    Nanoleaf,
    RhythmClient,
)

TOKEN = "tok123"


def _loads(data):
    """Decode the JSON string ``Nanoleaf._request`` passes to the session."""
    if data is None:
        return None
    try:
        return json.loads(data)
    except (TypeError, ValueError):
        return data


class FakeResponse:
    """Minimal stand-in for ``aiohttp.ClientResponse``."""

    def __init__(self, status=200, payload=None, content_length=None):
        self.status = status
        self._payload = payload
        self.content_length = content_length

    def raise_for_status(self):
        if self.status >= 400:
            raise AssertionError(f"unexpected HTTP {self.status}")

    async def json(self, content_type=None):  # noqa: D401 - mimic aiohttp
        if self._payload is None:
            raise ValueError("no json body")
        return self._payload


_NO_CONTENT = lambda: FakeResponse(status=204, content_length=0)  # noqa: E731


class FakeSession:
    """Record requests and serve canned responses keyed by (method, path)."""

    def __init__(self, routes):
        self._routes = routes
        self.calls = []

    async def request(self, method, url, data=None, timeout=None):
        path = url.split(f"/{TOKEN}/", 1)[1]
        self.calls.append((method.lower(), path, _loads(data)))
        factory = self._routes[(method.lower(), path)]
        return factory()

    def last(self, method, path):
        for m, p, body in reversed(self.calls):
            if m == method and p == path:
                return body
        raise AssertionError(f"no {method} {path} call recorded")


def _make(routes):
    session = FakeSession(routes)
    return Nanoleaf(session, "10.0.0.5", TOKEN), session


# --------------------------------------------------------------------------- #
# URL formatting
# --------------------------------------------------------------------------- #


def test_api_url_plain_host():
    nl = Nanoleaf(FakeSession({}), "192.168.0.10", TOKEN)
    assert nl._api_url == "http://192.168.0.10:16021/api/v1"


def test_api_url_wraps_ipv6_literal():
    nl = Nanoleaf(FakeSession({}), "fe80::1", TOKEN)
    assert nl._api_url == "http://[fe80::1]:16021/api/v1"


# --------------------------------------------------------------------------- #
# JSON transport helpers
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_get_json_returns_payload():
    nl, _ = _make({("get", "effects/select"): lambda: FakeResponse(payload="Nemo")})
    assert await nl._get_json("/effects/select") == "Nemo"


@pytest.mark.asyncio
async def test_put_json_handles_no_content():
    nl, session = _make({("put", "state"): _NO_CONTENT})
    assert await nl._put_json("state", {"on": {"value": True}}) is None
    assert session.last("put", "state") == {"on": {"value": True}}


@pytest.mark.asyncio
async def test_write_effect_wraps_payload_and_targets_effects():
    nl, session = _make({("put", "effects"): _NO_CONTENT})
    await nl.write_effect({"command": "display", "animType": "static"})
    assert session.last("put", "effects") == {
        "write": {"command": "display", "animType": "static"}
    }


# --------------------------------------------------------------------------- #
# Helper clients against the real transport
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_effects_client_through_real_transport():
    nl, session = _make(
        {
            ("get", "effects/effectsList"): lambda: FakeResponse(payload=["A", "B"]),
            ("get", "effects/select"): lambda: FakeResponse(payload="B"),
            ("put", "effects"): _NO_CONTENT,
        }
    )
    client = EffectsClient(nl)
    assert await client.get_effects_list() == ["A", "B"]
    assert await client.get_selected_effect() == "B"
    await client.select_effect("A")
    assert session.last("put", "effects") == {"select": "A"}


@pytest.mark.asyncio
async def test_layout_client_through_real_transport():
    nl, session = _make(
        {
            ("get", "panelLayout/globalOrientation"): lambda: FakeResponse(
                payload={"value": 90}
            ),
            ("put", "panelLayout/globalOrientation"): _NO_CONTENT,
        }
    )
    client = LayoutClient(nl)
    assert await client.get_global_orientation() == 90
    await client.set_global_orientation(180)
    assert session.last("put", "panelLayout/globalOrientation") == {"value": 180}


@pytest.mark.asyncio
async def test_rhythm_client_through_real_transport():
    nl, session = _make(
        {
            ("get", "rhythm"): lambda: FakeResponse(
                payload={"rhythmActive": True, "rhythmMode": 0}
            ),
            ("put", "rhythm"): _NO_CONTENT,
        }
    )
    client = RhythmClient(nl)
    assert await client.is_active() is True
    assert await client.get_mode() == 0
    await client.set_mode("aux")
    assert session.last("put", "rhythm") == {"rhythmMode": 1}


# --------------------------------------------------------------------------- #
# Digital twin end-to-end against the real transport
# --------------------------------------------------------------------------- #


def _full_info(position_data):
    return {
        "name": "Shapes ABCD",
        "serialNo": "SN123",
        "manufacturer": "Nanoleaf",
        "firmwareVersion": "7.0.0",
        "hardwareVersion": "3.0",
        "model": "NL42",
        "state": {
            "on": {"value": True},
            "brightness": {"value": 50, "max": 100, "min": 0},
            "hue": {"value": 120, "max": 360, "min": 0},
            "sat": {"value": 80, "max": 100, "min": 0},
            "ct": {"value": 4000, "max": 6500, "min": 1200},
            "colorMode": "effect",
        },
        "effects": {"effectsList": ["Nemo", "Snowfall"], "select": "Snowfall"},
        "panelLayout": {"layout": {"positionData": position_data}},
    }


@pytest.mark.asyncio
async def test_digital_twin_sync_through_real_transport():
    position_data = [
        {"panelId": 10, "x": 0, "y": 0, "o": 0},
        {"panelId": 20, "x": 1, "y": 0, "o": 0},
    ]
    nl, session = _make(
        {
            ("get", ""): lambda: FakeResponse(payload=_full_info(position_data)),
            ("put", "effects"): _NO_CONTENT,
        }
    )
    twin = await DigitalTwin.create(nl)
    assert twin.ids == [10, 20]
    await twin.set_color(10, (255, 0, 0))
    await twin.sync(transition_ms=50)

    body = session.last("put", "effects")["write"]
    assert body["command"] == "display"
    assert body["animType"] == "static"
    # Panel 10 should carry the red colour we set.
    parts = list(map(int, body["animData"].split()))
    assert parts[0] == 2  # two panels in the scene
    assert parts[1:8] == [10, 1, 255, 0, 0, 0, 50]
