# aionanoleaf/digital_twin.py
from __future__ import annotations
from typing import Dict, Tuple

class DigitalTwin:
    def __init__(self, nl):              # nl = aionanoleaf.Nanoleaf
        self._nl = nl
        self._ids = {p.id for p in nl.layout.panels}
        self.colors: Dict[int, Tuple[int,int,int]] = {pid: (0,0,0) for pid in self._ids}

    @classmethod
    async def create(cls, nl):
        await nl.get_info()              # ensure layout populated
        return cls(nl)

    async def set_color(self, pid: int, rgb: Tuple[int,int,int]) -> None:
        if pid not in self._ids:
            raise ValueError("panel id unknown")
        self.colors[pid] = rgb

    async def set_all_colors(self, rgb):
        for pid in self._ids:
            self.colors[pid] = rgb

    async def sync(self, transition: int = 10) -> None:
        rec = []
        for pid in self._ids:
            r,g,b = self.colors[pid]
            rec += [pid, 1, r, g, b, 0, transition]
        anim = " ".join(map(str, [len(self._ids)] + rec))
        payload = {
            "command":"display",
            "version":"1.0",
            "animType":"static",
            "animData":anim,
            "palette":[],
            "loop":False,
        }
        await self._nl.write_effect(payload)
