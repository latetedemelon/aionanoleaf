"""Unit tests for EffectsClient (no real HTTP)."""

try:
    import pytest  # type: ignore
except ImportError:  # pragma: no cover - lint-only environments
    pytest = None  # type: ignore

from aionanoleaf.effects import EffectsClient


class DummyNL:
    """Tiny stub exposing _get_json/_put_json like the real client does."""

    def __init__(self) -> None:
        self.get_map = {
            "/effects/effectsList": ["A", "B", "C"],
            "/effects/select": "B",
        }
        self.put_calls = []

    async def _get_json(self, path: str):
        return self.get_map[path]

    async def _put_json(self, path: str, body):
        self.put_calls.append((path, body))
        return {"ok": True}


@pytest.mark.asyncio
async def test_effects_list_and_select_ok():
    nl = DummyNL()
    cli = EffectsClient(nl)

    lst = await cli.get_effects_list()
    assert lst == ["A", "B", "C"]

    sel = await cli.get_selected_effect()
    assert sel == "B"

    await cli.select_effect("A")
    await cli.write_custom_effect("X", "0")
    await cli.display_temp_static("0")

    # Ensure the right endpoints were called
    assert nl.put_calls[0][0] == "/effects"
    assert "select" in nl.put_calls[0][1] or "write" in nl.put_calls[0][1]
