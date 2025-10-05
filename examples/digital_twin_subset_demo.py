# examples/digital_twin_subset_demo.py
"""
Minimal demo: paint two specific panels with different colours and apply
the change as a temporary (displayTemp) static effect via REST.

Usage:
  - Ensure your Nanoleaf client is authorized already.
  - Adjust host/token/constructor per your client (see NOTE below).
"""

import asyncio
from aiohttp import ClientSession

# NOTE: The exact Nanoleaf constructor may differ by fork.
# If your client takes (session, host, token), use that signature.
# If it uses (session, host) and manages token internally, adapt accordingly.
from aionanoleaf import Nanoleaf
from aionanoleaf.digital_twin import DigitalTwin


HOST = "192.168.0.50"   # <-- set your device IP or hostname
TOKEN = None            # <-- set if your client requires an explicit token


async def make_client(session: ClientSession) -> Nanoleaf:
    """
    Adapt this function to your fork's Nanoleaf constructor.
    Examples:
      - Nanoleaf(session, HOST)                         # token managed elsewhere
      - Nanoleaf(session, HOST, token=TOKEN)            # explicit token
      - Nanoleaf(session=session, host=HOST, token=...)
    """
    try:
        return Nanoleaf(session, HOST, token=TOKEN)  # type: ignore[arg-type]
    except TypeError:
        return Nanoleaf(session, HOST)               # fallback


async def main() -> None:
    async with ClientSession() as session:
        nl = await make_client(session)

        # Build the digital twin by reading the panel layout
        twin = await DigitalTwin.create(nl)

        # Pick first two panel IDs deterministically (x asc, then y asc)
        ids = twin.ids
        if len(ids) < 2:
            raise SystemExit("Need at least two panels on this device.")

        a, b = ids[0], ids[1]

        # Paint two panels with different colours
        await twin.set_hex(a, "#FF4000")   # orange-red
        await twin.set_hex(b, "#0064FF")   # azure-ish

        # Apply the change as a temporary override (displayTemp)
        await twin.sync(
            transition_ms=80,
            command="displayTemp",  # use "display" to persist
            only=[a, b],            # just update these two
        )

        print(f"Applied temporary colours to panels {a} and {b}.")


if __name__ == "__main__":
    asyncio.run(main())
