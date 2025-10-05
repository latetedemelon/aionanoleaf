"""Digital Twin apply_temp blink-and-restore."""

# pylint: disable=missing-class-docstring,too-few-public-methods,duplicate-code

try:
    import pytest  # type: ignore
except ImportError:  # pragma: no cover
    pytest = None  # type: ignore

from aionanoleaf.digital_twin import DigitalTwin


class DummyPanel:
    def __init__(self, pid, x, y):
        self.id = pid
        self.x = x
        self.y = y


class DummyLight:
    """Stub client that supports panel layout, write_effect, and EffectsClient calls."""

    def __init__(self):
        self.panels = [DummyPanel(10, 0, 0), DummyPanel(20, 1, 0)]
        self._writes = []
        self._selected_effect = "Snowfall"

    async def get_info(self):
        return {"ok": True}

    async def write_effect(self, payload):
        self._writes.append(payload)

    # EffectsClient (used by DigitalTwin.apply_temp) calls these:
    async def _get_json(self, path: str):
        if path == "/effects/select":
            return self._selected_effect
        raise KeyError(path)

    async def _put_json(self, path: str, body):
        if path == "/effects" and isinstance(body, dict) and "select" in body:
            self._selected_effect = str(body["select"])
            return {"ok": True}
        return {"ok": True}


@pytest.mark.asyncio
async def test_apply_temp_restores_effect(monkeypatch):
    nl = DummyLight()
    twin = await DigitalTwin.create(nl)

    # Program a blink colour on one panel
    await twin.set_hex(10, "#FF0000")

    # Speed up test by stubbing sleep
    async def fast_sleep(_ms: int) -> None:
        return None

    monkeypatch.setattr(DigitalTwin, "_sleep_ms", staticmethod(fast_sleep))

    await twin.apply_temp(transition_ms=10, duration_ms=10, only=[10], brightness=100)

    # A temp write should have been issued
    assert any(p["command"] == "displayTemp" for p in nl._writes)

    # The previous effect should be restored
    assert nl._selected_effect == "Snowfall"
