"""Blink two panels temporarily, then restore the previous effect."""

try:
    from aiohttp import ClientSession  # type: ignore
except Exception:  # pragma: no cover
    ClientSession = object  # type: ignore

from asyncio import run
from aionanoleaf import Nanoleaf
from aionanoleaf.digital_twin import DigitalTwin

HOST = "192.168.0.50"  # set me


async def main():
    """Run the demo."""
    async with ClientSession() as session:  # type: ignore[operator]
        nl = Nanoleaf(session, HOST)  # type: ignore[call-arg]
        twin = await DigitalTwin.create(nl)

        ids = twin.ids
        if len(ids) < 2:
            raise SystemExit("Need at least two panels.")

        a, b = ids[0], ids[1]
        await twin.set_hex(a, "#FF9900")
        await twin.set_hex(b, "#0099FF")

        await twin.apply_temp(transition_ms=60, duration_ms=2000, only=[a, b], brightness=70)
        print(f"Blinked panels {a} and {b}, restored previous effect.")


if __name__ == "__main__":
    run(main())
