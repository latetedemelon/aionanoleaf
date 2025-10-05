# tests/test_digital_twin_temp.py
import pytest
from aionanoleaf.digital_twin import DigitalTwin, _build_anim


class DummyPanel:
    def __init__(self, pid, x, y):
        self.id = pid
        self.x = x
        self.y = y


class DummyLight:
    def __init__(self, effects):
        self.panels = [DummyPanel(10, 0, 0), DummyPanel(20, 1, 0)]
        self._writes = []
        self._effects = effects

    async def get_info(self):
        return {"ok": True}

    async def write_effect(self, payload):
        self._writes.append(payload)

    # EffectsClient will use these:
    @property
    def session(self):
        return self._effects.session

    @property
    def base_url(self):
        return self._effects.base_url


# Minimal fake EffectsClient backend
class _Resp:
    def __init__(self, status, payload):
        self.status = status
        self._payload = payload

    async def json(self):
        return self._payload

    async def text(self):
        return str(self._payload)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _Sess:
    def __init__(self):
        self._select = "Snowfall"

    def get(self, url):
        async def _do():
            if url.endswith("/effects/select"):
                return _Resp(200, self._select)
            return _Resp(404, {"err": "nope"})
        return _Ctx(_do)

    def put(self, url, json=None):
        async def _do():
            if url.endswith("/effects"):
                # update selected effect if {"select": ...}
                if isinstance(json, dict) and "select" in json:
                    self._select = str(json["select"])
                    return _Resp(200, {"ok": True})
                return _Resp(200, {"ok": True})
            return _Resp(404, {"err": "nope"})
        return _Ctx(_do)


class _Ctx:
    def __init__(self, fn):
        self.fn = fn

    def __call__(self, *a, **k):
        return _CM(self.fn, *a, **k)


class _CM:
    def __init__(self, fn, *a, **k):
        self.fn = fn
        self.args = a
        self.kw = k
        self._r = None

    async def __aenter__(self):
        self._r = await self.fn(*self.args, **self.kw)
        return self._r

    async def __aexit__(self, exc_type, exc, tb):
        return False


class DummyEffects:
    def __init__(self):
        self.session = _Sess()
        self.base_url = "http://127.0.0.1:16021/api/v1/TOKEN"


@pytest.mark.asyncio
async def test_apply_temp_restores_effect():
    effects = DummyEffects()
    nl = DummyLight(effects)
    twin = await DigitalTwin.create(nl)

    # Program a blink colour on one panel
    await twin.set_hex(10, "#FF0000")

    # Ensure a baseline selected effect
    # (Fake backend starts at "Snowfall")
    assert effects.session._select == "Snowfall"

    # Blink for a very short time to keep tests fast
    await twin.apply_temp(transition_ms=10, duration_ms=10, only=[10], brightness=100)

    # Effects client should restore the previous effect
    assert effects.session._select == "Snowfall"

    # A temp write should have been issued
    assert any(p["command"] == "displayTemp" for p in nl._writes)
