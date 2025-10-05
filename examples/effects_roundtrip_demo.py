"""List effects, select one, push a trivial static scene write."""

try:
    from aiohttp import ClientSession  # type: ignore
except Exception:  # pragma: no cover
    ClientSession = object  # type: ignore

from asyncio import run
from aionanoleaf import Nanoleaf
from aionanoleaf.effects import EffectsClient

HOST = "192.168.0.50"  # set me


async def main():
    """Run the demo."""
    async with ClientSession() as session:  # type: ignore[operator]
        nl = Nanoleaf(session, HOST)  # type: ignore[call-arg]
        ef = EffectsClient(nl)

        effects = await ef.get_effects_list()
        current = await ef.get_selected_effect()
        print("Available:", effects)
        print("Selected :", current)

        if effects:
            await ef.select_effect(effects[0])

        # Push an empty static scene (no panels) just to exercise the write path
        await ef.write_effect({"command": "display", "animType": "static", "animData": "0"})


if __name__ == "__main__":
    run(main())
