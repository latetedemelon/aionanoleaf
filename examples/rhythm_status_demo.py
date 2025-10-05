# pylint: disable=import-error,broad-except
try:
    from aiohttp import ClientSession  # type: ignore
except Exception:  # pragma: no cover
    ClientSession = object  # type: ignore

from asyncio import run
from typing import Any, Dict
from aionanoleaf import Nanoleaf
from aionanoleaf.rhythm import RhythmClient

HOST = "192.168.0.50"
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
        rh = RhythmClient(nl)

        info = await rh.get_info()
        print("Rhythm info:", info)
        print("Active:", await rh.is_active())
        print("Mode:", await rh.get_mode())

        # Toggle mode if possible (0 <-> 1)
        mode = await rh.get_mode()
        if mode in (0, 1):
            await rh.set_mode(1 - mode)
            print("Toggled mode ->", await rh.get_mode())


if __name__ == "__main__":
    run(main())
