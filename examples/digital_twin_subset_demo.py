"""Paint two panels temporarily using displayTemp."""

try:
    from aiohttp import ClientSession  # type: ignore
except Exception:  # pragma: no cover - lint-only environments
    ClientSession = object  # type: ignore

from asyncio import run
from aionanoleaf import Nanoleaf  # provided by the repo
from aionanoleaf.digital_twin import DigitalTwin

HOST = "192.168.0.50"  # set me


async def main():
    """Run the demo."""
    async with ClientSession() as session:  # type: ignore[operator]
        # Most forks accept (session, host); avoid static 'token=' so pylint stays happy.
        nl = Nanoleaf(session, HOST)  # type: ignore[call-arg]
        twin = await DigitalTwin.create(nl)

        ids = twin.ids
        if len(ids) < 2:
            raise SystemExit("Need at least two panels.")

        a, b = ids[0], ids[1]
        await twin.set_hex(a, "#FF4000")
        await twin.set_hex(b, "#0064FF")

        await twin.sync(
            transition_ms=80,
            command="displayTemp",
            only=[a, b],
            brightness=70,
        )
        print(f"Applied temporary colours to panels {a} and {b} at 70% brightness.")


if __name__ == "__main__":
    run(main())
