# tests/test_digital_twin.py
import pytest
from aionanoleaf.digital_twin import DigitalTwin, _build_anim


class DummyPanel:
    def __init__(self, pid, x, y):
        self.id = pid
        self.x = x
        self.y = y


class DummyLight:
    def __init__(self):
        # Unordered on purpose to verify layout ordering
        self.panels = [
            DummyPanel(20,  5,  0),
            DummyPanel(10,  0,  0),
            DummyPanel(30, 10, 10),
        ]
        self.writes = []

    async def get_info(self):
        # no-op; in some clients this populates layout
        return {"ok": True}

    async def write_effect(self, payload):
        self.writes.append(payload)


@pytest.mark.asyncio
async def test_create_orders_ids_by_xy():
    nl = DummyLight()
    twin = await DigitalTwin.create(nl)
    assert twin.ids == [10, 20, 30]  # x asc, then y asc


def test_build_anim_string_shape_basic():
    colours = {1: (10, 20, 30), 5: (1, 2, 3)}
    s = _build_anim([1, 5], colours, transition=75)
    parts = list(map(int, s.split()))
    # count + 2 records x 7 ints each = 1 + 14 = 15 parts
    assert len(parts) == 15
    assert parts[0] == 2
    # record 1 (panel 1)
    assert parts[1:8] == [1, 1, 10, 20, 30, 0, 75]
    # record 2 (panel 5)
    assert parts[8:15] == [5, 1, 1, 2, 3, 0, 75]


def test_build_anim_string_with_brightness():
    colours = {2: (100, 50, 0)}
    s = _build_anim([2], colours, transition=10, brightness=50)
    parts = list(map(int, s.split()))
    # count
    assert parts[0] == 1
    # 100,50,0 scaled by 0.5 -> 50,25,0
    assert parts[1:8] == [2, 1, 50, 25, 0, 0, 10]


@pytest.mark.asyncio
async def test_sync_default_display_and_values():
    nl = DummyLight()
    twin = await DigitalTwin.create(nl)
    # paint two panels
    await twin.set_color(10, (255, 0, 0))
    await twin.set_color(20, (0, 0, 300))  # clamps to 255
    await twin.sync(transition_ms=50)      # default command="display"

    assert len(nl.writes) == 1
    payload = nl.writes[0]
    assert payload["command"] == "display"
    assert payload["animType"] == "static"
    parts = list(map(int, payload["animData"].split()))
    # 3 panels total (we didn't limit to subset)
    assert parts[0] == 3
    # panel 10 frame => 255,0,0
    idx = parts.index(10)
    assert parts[idx:idx+7] == [10, 1, 255, 0, 0, 0, 50]
    # panel 20 frame => 0,0,255 (clamped)
    idx = parts.index(20)
    assert parts[idx:idx+7] == [20, 1, 0, 0, 255, 0, 50]


@pytest.mark.asyncio
async def test_sync_subset_display_temp_and_brightness():
    nl = DummyLight()
    twin = await DigitalTwin.create(nl)
    await twin.set_color(10, (10, 10, 10))
    await twin.set_color(20, (100, 80, 60))
    # Only push panel 20, temporary, with brightness overlay 50
    await twin.sync(transition_ms=5, command="displayTemp", only=[20], brightness=50)

    assert len(nl.writes) == 1
    payload = nl.writes[0]
    assert payload["command"] == "displayTemp"
    parts = list(map(int, payload["animData"].split()))
    # subset => 1 record
    assert parts[0] == 1
    # record for panel 20 should be scaled: 100,80,60 -> 50,40,30
    assert parts[1:8] == [20, 1, 50, 40, 30, 0, 5]


@pytest.mark.asyncio
async def test_set_hex_and_validation_errors():
    nl = DummyLight()
    twin = await DigitalTwin.create(nl)
    await twin.set_hex(10, "#0A0B0C")
    assert twin.get_color(10) == (10, 11, 12)

    with pytest.raises(ValueError):
        await twin.set_hex(10, "GGHHII")  # invalid hex

    with pytest.raises(ValueError):
        await twin.set_color(9999, (1, 2, 3))  # unknown panel id

    with pytest.raises(ValueError):
        await twin.set_color(10, (256, 0, 0))  # out of range
