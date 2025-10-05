"""Digital Twin core behaviours."""

# pylint: disable=missing-class-docstring,too-few-public-methods,duplicate-code

try:
    import pytest  # type: ignore
except ImportError:  # pragma: no cover
    pytest = None  # type: ignore

from aionanoleaf.digital_twin import DigitalTwin, _build_anim


class DummyPanel:
    def __init__(self, pid, x, y):
        self.id = pid
        self.x = x
        self.y = y


class DummyLight:
    def __init__(self):
        self.panels = [
            DummyPanel(20, 5, 0),
            DummyPanel(10, 0, 0),
            DummyPanel(30, 10, 10),
        ]
        self.writes = []

    async def get_info(self):
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
    assert parts[0] == 2
    assert parts[1:8] == [1, 1, 10, 20, 30, 0, 75]
    assert parts[8:15] == [5, 1, 1, 2, 3, 0, 75]


@pytest.mark.asyncio
async def test_sync_default_display_and_values():
    nl = DummyLight()
    twin = await DigitalTwin.create(nl)
    await twin.set_color(10, (255, 0, 0))
    await twin.set_color(20, (0, 0, 300))  # clamps to 255
    await twin.sync(transition_ms=50)

    payload = nl.writes[0]
    assert payload["command"] == "display"
    parts = list(map(int, payload["animData"].split()))
    assert parts[0] == 3
    idx = parts.index(10)
    assert parts[idx:idx + 7] == [10, 1, 255, 0, 0, 0, 50]
    idx = parts.index(20)
    assert parts[idx:idx + 7] == [20, 1, 0, 0, 255, 0, 50]
