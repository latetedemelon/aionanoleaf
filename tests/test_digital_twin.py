"""Unit‑tests for the proposed `DigitalTwin` helper that will live in
`aionanoleaf.digital_twin`.

Requirements:
* pytest
* pytest‑asyncio ≥ 0.20 (for the async tests)

Run:   pytest -q test_digital_twin.py
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aionanoleaf.digital_twin import DigitalTwin, _build_anim  # helper exposed in module

# ---------------------------------------------------------------------------
# Test fixtures – a minimal fake Nanoleaf object
# ---------------------------------------------------------------------------
class FakePanel(SimpleNamespace):
    """Simple stand‑in for a layout.Panel from aionanoleaf."""
    def __init__(self, pid, x, y):
        super().__init__(id=pid, x=x, y=y)

class FakeLight(SimpleNamespace):
    """Mimics just enough of aionanoleaf.Nanoleaf for DigitalTwin."""

    def __init__(self, panels):
        super().__init__()
        self.layout = SimpleNamespace(panels=panels)
        # Async stub to satisfy DT.create()
        self.get_info = AsyncMock(return_value=None)
        # write_effect is where the HTTP body ends up
        self.write_effect = AsyncMock(return_value=None)

# Small deterministic layout: ids 30(left‑bottom), 10(left‑top), 20(right)
PANELS = [
    FakePanel(10, 0, 0),
    FakePanel(20, 100, 0),
    FakePanel(30, 0, 100),
]

@pytest.fixture
async def twin():
    light = FakeLight(PANELS)
    dt = await DigitalTwin.create(light)
    return dt

# ---------------------------------------------------------------------------
# 1) Panel‑sort test: verify that animData order is left‑to‑right then top‑to‑bottom
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_panel_sort_left_to_right(twin):
    """animData should list panelIds sorted by x, then y."""
    anim = _build_anim(twin._ids_ordered, {pid: (0, 0, 0) for pid in twin._ids})
    # Extract ids back from animData string after the leading count
    parts = list(map(int, anim.split()))
    ids_in_anim = [parts[i] for i in range(1, len(parts), 7)]
    assert ids_in_anim == [10, 30, 20]  # x asc (0,0) & (0,100) then x=100

# ---------------------------------------------------------------------------
# 2) animData build test: verify RGB insertion and record structure
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_animdata_build_colours(twin):
    colours = {pid: (0, 0, 0) for pid in twin._ids}
    colours[20] = (255, 0, 0)  # paint panel 20 red
    anim = _build_anim(twin._ids_ordered, colours, transition=5)
    expected = "3 10 1 0 0 0 0 5 30 1 0 0 0 0 5 20 1 255 0 0 0 5"
    assert anim == expected

# ---------------------------------------------------------------------------
# 3) HTTP body test: ensure sync() pushes valid static scene payload
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_sync_http_body(twin):
    # paint panel 10 green and sync
    await twin.set_color(10, (0, 255, 0))
    await twin.sync(transition_ms=10)

    twin._nl.write_effect.assert_awaited_once()
    payload = twin._nl.write_effect.call_args.args[0]

    # Basic structure checks
    assert payload["command"] == "display"
    assert payload["animType"] == "static"
    assert payload["palette"] == []
    # animData must start with number of panels and include 10 and RGB 0 255 0
    assert payload["animData"].startswith("3 ")
    assert "10 1 0 255 0" in payload["animData"]
