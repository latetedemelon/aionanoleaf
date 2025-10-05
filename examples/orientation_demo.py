# pylint: disable=import-error,broad-except
try:
    from aiohttp import ClientSession  # type: ignore
except Exception:  # pragma: no cover
    ClientSession = object  # type: ignore

from asyncio import run
from typing import Any, Dict
from aionanoleaf import Nanoleaf
from aionanoleaf.layout import LayoutClient

HOST = "192.168.0.50"  # or IPv6 literal like "fe80::1"
TOKEN = None  # set if your fork requires explicit token


async def make_client(session: ClientSession) -> Nanoleaf:
    kwargs: Dict[str, Any] = {}
    if TOKEN is not None:
        kwargs["token"] = TOKEN
    try:
        return Nanoleaf(session, HOST, **kwargs)  # type: ignore[call-arg]
    except TypeError:
        return Nanoleaf(session, HOST)  # type: ignore[call-arg]


async def main() -> None:
    async with ClientSession() as session:  # type: ignore[operator]
        nl = await make_client(session)
        layout = LayoutClient(nl)

        current = await layout.get_global_orientation()
        print("Current orientation:", current)

        # Rotate by +15 (wrap 0..360)
        if current is not None:
            await layout.set_global_orientation((current + 15) % 360)
            print("Updated orientation:", await layout.get_global_orientation())


if __name__ == "__main__":
    run(main())
