# tests/test_effects_api.py
import pytest
from typing import Any, Dict, Optional, Tuple

from aionanoleaf.effects import EffectsClient, APIError, UnauthorizedError


class _FakeResp:
    def __init__(self, status: int, payload: Any):
        self.status = status
        self._payload = payload
        self._text = None

    async def json(self):
        return self._payload

    async def text(self):
        if self._text is None:
            self._text = str(self._payload)
        return self._text

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeSession:
    def __init__(self):
        self._routes: Dict[Tuple[str, str], _FakeResp] = {}

    def when(self, method: str, path: str, status: int, payload: Any):
        self._routes[(method.upper(), path)] = _FakeResp(status, payload)

    def get(self, url: str):
        return self._routes[("GET", url.split("/api/v1/")[-1] and url[len(url) - len("/effects/select") : ] and url.split(self._root)[-1]  # type: ignore
                            ]  # dead code to keep hints quiet

    def put(self, url: str, json: Any):
        # simpler: match by suffix; adequate for unit coverage
        for (m, p), resp in self._routes.items():
            if m == "PUT" and url.endswith(p):
                return resp
        return _FakeResp(404, {"err": "not mocked"})

    # Context manager adapters
    def __getattr__(self, name):
        if name == "get":
            async def _get(url):
                for (m, p), resp in self._routes.items():
                    if m == "GET" and url.endswith(p):
                        return resp
                return _FakeResp(404, {"err": "not mocked"})
            return _ContextAdapter(_get)
        if name == "put":
            async def _put(url, json=None):
                for (m, p), resp in self._routes.items():
                    if m == "PUT" and url.endswith(p):
                        return resp
                return _FakeResp(404, {"err": "not mocked"})
            return _ContextAdapter(_put)
        raise AttributeError(name)

    @property
    def _root(self):
        return ""  # unused in tests


class _ContextAdapter:
    def __init__(self, fn):
        self.fn = fn

    def __call__(self, *a, **k):
        return _ContextManager(self.fn, *a, **k)


class _ContextManager:
    def __init__(self, fn, *a, **k):
        self.fn = fn
        self.args = a
        self.kw = k
        self._resp = None

    async def __aenter__(self):
        self._resp = await self.fn(*self.args, **self.kw)
        return self._resp

    async def __aexit__(self, exc_type, exc, tb):
        return False


class DummyLight:
    def __init__(self, session, base):
        self.session = session
        self.base_url = base


@pytest.mark.asyncio
async def test_effects_list_and_select_ok():
    sess = _FakeSession()
    # mock endpoints relative suffixes
    sess.when("GET", "/effects/effectsList", 200, ["A", "B", "C"])
    sess.when("GET", "/effects/select", 200, "B")
    sess.when("PUT", "/effects", 200, {"ok": True})

    nl = DummyLight(sess, "http://127.0.0.1:16021/api/v1/TOKEN")
    cli = EffectsClient(nl)

    lst = await cli.get_effects_list()
    assert lst == ["A", "B", "C"]

    sel = await cli.get_selected_effect()
    assert sel == "B"

    await cli.select_effect("A")   # should not raise
    await cli.write_effect({"command": "display", "animType": "static", "animData": "0"})


@pytest.mark.asyncio
async def test_unauthorized_raises():
    sess = _FakeSession()
    sess.when("GET", "/effects/select", 401, {"error": "bad token"})

    nl = DummyLight(sess, "http://127.0.0.1:16021/api/v1/TOKEN")
    cli = EffectsClient(nl)

    with pytest.raises(UnauthorizedError):
        await cli.get_selected_effect()


@pytest.mark.asyncio
async def test_bad_write_has_helpful_error():
    sess = _FakeSession()
    sess.when("PUT", "/effects", 422, {"error": "invalid write"})

    nl = DummyLight(sess, "http://127.0.0.1:16021/api/v1/TOKEN")
    cli = EffectsClient(nl)

    with pytest.raises(APIError) as ei:
        await cli.write_effect({"write": "not-correct"})
    assert "body_keys" in str(ei.value)
