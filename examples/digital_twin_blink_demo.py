# examples/digital_twin_blink_demo.py
"""
Blink two panels temporarily and restore the previous effect.
"""

import asyncio
from aiohttp import ClientSession
from aionanoleaf import Nanoleaf
from aionanoleaf.digital_twin import DigitalTwin

HOST = "192.168.0.50"
TOKEN = None  # set if your fork requires explicit token


async def make_client(session: ClientSession) -> Nanoleaf:
    try:
        return Nanoleaf(session, HOST, token=TOKEN)  # type: ignore[arg-type]
    except TypeError:
        return Nanoleaf(session, HOST)


async def main():
    async with ClientSession() as session:
        nl = await make_client(session)
        twin = await DigitalTwin.create(nl)

        ids = twin.ids
        if len(ids) < 2:
            raise SystemExit("Need at least two panels.")

        a, b = ids[0], ids[1]
        await twin.set_hex(a, "#FF9900")
        await twin.set_hex(b, "#0099FF")

        # Blink temporarily at 70% brightness, then restore previous effect
        await twin.apply_temp(transition_ms=60, duration_ms=2000, only=[a, b], brightness=70)

        print(f"Blinked panels {a} and {b}, restored previous effect.")


if __name__ == "__main__":
    asyncio.run(main())
