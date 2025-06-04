# aionanoleaf/digital_twin.py
from __future__ import annotations
from typing import Dict, Iterable, List, Tuple

__all__ = ["DigitalTwin", "_build_anim"]

def _build_anim(ids: Iterable[int], colours: Dict[int, Tuple[int, int, int]], transition: int = 10) -> str:
    """Return animData payload for a static scene.

    Parameters match those in ``DigitalTwin.sync`` and the helper is exposed so
    tests can verify the generated string independently.
    """
    id_list = list(ids)
    records: List[int] = []
    for pid in id_list:
        r, g, b = colours[pid]
        records += [pid, 1, r, g, b, 0, transition]
    return " ".join(map(str, [len(id_list)] + records))


class DigitalTwin:
    def __init__(self, nl):  # nl = aionanoleaf.Nanoleaf
        self._nl = nl
        # Preserve order left-to-right, then top-to-bottom for deterministic
        # animation payloads.  ``Panel`` objects from the library expose
        # ``x_coordinate``/``y_coordinate`` properties.  For tests we also fall
        # back to ``x``/``y`` attributes on the fake objects.
        panels = nl.layout.panels
        self._ids_ordered = tuple(
            p.id for p in sorted(
                panels,
                key=lambda p: (
                    getattr(p, "x_coordinate", getattr(p, "x")),
                    getattr(p, "y_coordinate", getattr(p, "y")),
                ),
            )
        )
        self._ids = set(pid for pid in self._ids_ordered)
        self.colors: Dict[int, Tuple[int, int, int]] = {
            pid: (0, 0, 0) for pid in self._ids
        }

    @classmethod
    async def create(cls, nl):
        await nl.get_info()              # ensure layout populated
        return cls(nl)

    async def set_color(self, pid: int, rgb: Tuple[int, int, int]) -> None:
        """Set the RGB colour for a single panel."""
        if pid not in self._ids:
            raise ValueError("panel id unknown")
        self.colors[pid] = rgb

    async def set_all_colors(self, rgb: Tuple[int, int, int]) -> None:
        """Apply the same RGB colour to all panels."""
        for pid in self._ids:
            self.colors[pid] = rgb

    async def sync(self, *, transition_ms: int = 10) -> None:
        """Push the current colour map to the device as a static scene."""
        anim = _build_anim(self._ids_ordered, self.colors, transition_ms)
        payload = {
            "command": "display",
            "version": "1.0",
            "animType": "static",
            "animData": anim,
            "palette": [],
            "loop": False,
        }
        await self._nl.write_effect(payload)
