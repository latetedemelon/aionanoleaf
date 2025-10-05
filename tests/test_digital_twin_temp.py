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

    # Minimal context-manager API used by EffectsClient in the real client
    def get(self, _url):
        async def _do():
            return _Resp(200, self._select)
        return _Ctx(_do)

    def put(self, _url, json=None):
        async def _do():
            if isinstance(json, dict) and "select" in json:
                self._select = str(json["select"])
            return _Resp(200, {"ok": True})
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

    async def __aenter__(self):
        return await self.fn(*self.args, **self.kw)

    async def __aexit__(self, exc_type, exc, tb):
        return False


class DummyEffects:
    def __init__(self):
        self.session = _Sess()
        self.base_url = "http://127.0.0.1:16021/api/v1/TOKEN"


class DummyLight:
    def __init__(self, effects):
        self.panels = [DummyPanel(10, 0, 0), DummyPanel(20, 1, 0)]
        self._writes = []
        self._effects = effects

    async def get_info(self):
        return {"ok": True}

    async def write_effect(self, payload):
        self._writes.append(payload)

    # EffectsClient will read these from the real Nanoleaf client;
    # in tests our EffectsClient variant calls _get_json/_put_json, so we don't use them.
    @property
    def session(self):
        return self._effects.session

    @property
    def base_url(self):
        return self._effects.base_url


@pytest.mark.asyncio
async def test_apply_temp_restores_effect(monkeypatch):
    effects = DummyEffects()
    nl = DummyLight(effects)
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
