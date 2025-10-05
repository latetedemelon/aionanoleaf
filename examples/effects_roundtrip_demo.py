# examples/effects_roundtrip_demo.py
"""
List current effects, show the selected one, select a different one,
and write a trivial static effect.

Adapt the Nanoleaf(...) constructor to your fork (session+host [+token]).
"""

import asyncio
from aiohttp import ClientSession
from aionanoleaf import Nanoleaf
from aionanoleaf.effects import EffectsClient

HOST = "192.168.0.50"   # set me
TOKEN = None            # set if your fork requires explicit token


async def make_client(session: ClientSession) -> Nanoleaf:
    try:
        return Nanoleaf(session, HOST, token=TOKEN)  # type: ignore[arg-type]
    except TypeError:
        return Nanoleaf(session, HOST)


async def main():
    async with ClientSession() as session:
        nl = await make_client(session)
        ef = EffectsClient(nl)

        lst = await ef.get_effects_list()
        cur = await ef.get_selected_effect()
        print("Available:", lst)
        print("Selected :", cur)

        if lst:
            target = lst[0]
            print("Selecting:", target)
            await ef.select_effect(target)

        # Push a trivial (empty) static scene write (no panels)
        await ef.write_effect({"command": "display", "animType": "static", "animData": "0"})


if __name__ == "__main__":
    asyncio.run(main())
