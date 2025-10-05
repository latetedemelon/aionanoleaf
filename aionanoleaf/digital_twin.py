# aionanoleaf/digital_twin.py
from __future__ import annotations

from typing import Dict, Iterable, List, Tuple, Optional, Any
import asyncio

__all__ = ["DigitalTwin", "_build_anim"]

RGB = Tuple[int, int, int]


def _clamp(v: int, lo: int = 0, hi: int = 255) -> int:
    return max(lo, min(hi, int(v)))


def _validate_rgb(rgb: RGB) -> RGB:
    try:
        r, g, b = (int(rgb[0]), int(rgb[1]), int(rgb[2]))
    except Exception as exc:  # pragma: no cover (defensive)
        raise ValueError("rgb must be a 3-tuple of integers") from exc
    for v in (r, g, b):
        if v < 0 or v > 255:
            raise ValueError("rgb components must be in [0,255]")
    return _clamp(r), _clamp(g), _clamp(b)


def _hex_to_rgb(s: str) -> RGB:
    if not isinstance(s, str) or not s:
        raise ValueError("hex string required")
    s = s.strip()
    if s.startswith("#"):
        s = s[1:]
    if len(s) != 6:
        raise ValueError("hex must be #RRGGBB")
    r = int(s[0:2], 16)
    g = int(s[2:4], 16)
    b = int(s[4:6], 16)
    return r, g, b


def _build_anim(
    ids: Iterable[int],
    colours: Dict[int, RGB],
    transition: int = 10,
) -> str:
    """
    Build Nanoleaf 'static' effect animData string.

    Format:
        <count> [panelId 1] 1 R G B 0 <transition_ms> ... (repeated for N panels)
    """
    id_list = list(ids)
    records: List[int] = []
    for pid in id_list:
        r, g, b = colours[pid]
        records += [pid, 1, int(r), int(g), int(b), 0, int(max(0, transition))]
    return " ".join(map(str, [len(id_list)] + records))


class _Panel:
    __slots__ = ("id", "x", "y")

    def __init__(self, id: int, x: int, y: int) -> None:
        self.id = int(id)
        self.x = int(x)
        self.y = int(y)


class DigitalTwin:
    """
    A lightweight 'digital twin' for Nanoleaf panel devices.

    - Collect per-panel RGB colours locally (by panelId)
    - Push them atomically as a single static effect over REST (no UDP)
    - Supports persistent ('display') or temporary ('displayTemp') application
    - Can target a subset of panels for small updates

    Not supported on Essentials bulbs/strips (no per-panel layout).
    """

    # -------------------------- construction --------------------------

    def __init__(self, nl: Any, panels: List[_Panel]) -> None:
        self._nl = nl
        # Sort deterministic: left-to-right (x asc), then top-to-bottom (y asc)
        panels_sorted = sorted(panels, key=lambda p: (p.x, p.y, p.id))
        self._ids_ordered: Tuple[int, ...] = tuple(p.id for p in panels_sorted)
        self._ids_set = set(self._ids_ordered)
        self.colors: Dict[int, RGB] = {pid: (0, 0, 0) for pid in self._ids_ordered}

    @classmethod
    async def create(cls, nl: Any) -> "DigitalTwin":
        """
        Factory that fetches layout/positions from the device and returns a twin.

        Tries multiple shapes so it works across forks:
          - await nl.get_panel_layout() → {"positionData":[{"panelId","x","y",...},...]}
          - nl.info / nl._info dictionaries with ["panelLayout"]["layout"]["positionData"]
          - nl.panels / nl._panels list of objects with id/x/y (or x_coordinate/y_coordinate)
        """
        # Ensure device info/layout is loaded if the client requires it
        get_info = getattr(nl, "get_info", None)
        if callable(get_info):
            res = get_info()
            if asyncio.iscoroutine(res):
                await res

        layout = None
        if callable(getattr(nl, "get_panel_layout", None)):
            layout = await nl.get_panel_layout()
        elif callable(getattr(nl, "panel_layout", None)):
            layout = await nl.panel_layout()

        panels: List[_Panel] = []
        pos = None

        # Dict-style layout
        if isinstance(layout, dict):
            pos = layout.get("positionData")

        # Try info dicts
        if pos is None:
            info = getattr(nl, "info", None) or getattr(nl, "_info", None)
            if isinstance(info, dict):
                try:
                    pos = (
                        info.get("panelLayout", {})
                        .get("layout", {})
                        .get("positionData", None)
                    )
                except Exception:
                    pos = None

        if isinstance(pos, list) and pos:
            for p in pos:
                pid = p.get("panelId")
                x = p.get("x")
                y = p.get("y")
                if pid is not None and x is not None and y is not None:
                    panels.append(_Panel(pid, x, y))

        # Try object-style panels if still empty
        if not panels:
            candidates = getattr(nl, "panels", None) or getattr(nl, "_panels", None)
            if isinstance(candidates, (list, tuple)) and candidates:
                for obj in candidates:
                    pid = getattr(obj, "id", None) or getattr(obj, "panelId", None)
                    x = getattr(obj, "x", None) or getattr(obj, "x_coordinate", None)
                    y = getattr(obj, "y", None) or getattr(obj, "y_coordinate", None)
                    if pid is not None and x is not None and y is not None:
                        panels.append(_Panel(pid, x, y))

        if not panels:
            raise RuntimeError(
                "Panel layout not found; per-panel control requires a panel device. "
                "Check that this device is not an Essentials bulb/strip and that "
                "your client exposes /panelLayout/layout or panel coordinates."
            )

        return cls(nl, panels)

    # -------------------------- introspection --------------------------

    @property
    def ids(self) -> List[int]:
        """List of panel IDs in deterministic (x,y,id) order."""
        return list(self._ids_ordered)

    def get_color(self, panel_id: int) -> RGB:
        return self.colors[int(panel_id)]

    def get_all_colors(self) -> Dict[int, RGB]:
        return dict(self.colors)

    # -------------------------- editing --------------------------

    async def set_color(self, pid: int, rgb: RGB) -> None:
        """Set RGB for a single panel ID."""
        pid = int(pid)
        if pid not in self._ids_set:
            raise ValueError(f"panel id unknown: {pid}")
        self.colors[pid] = _validate_rgb(rgb)

    async def set_hex(self, pid: int, hex_colour: str) -> None:
        """Set RGB for a single panel using a #RRGGBB hex string."""
        await self.set_color(pid, _hex_to_rgb(hex_colour))

    async def set_all_colors(self, rgb: RGB) -> None:
        """Set RGB for all panels."""
        rgb = _validate_rgb(rgb)
        for pid in self._ids_ordered:
            self.colors[pid] = rgb

    # -------------------------- rendering --------------------------

    async def sync(
        self,
        *,
        transition_ms: int = 10,
        command: str = "display",
        only: Optional[Iterable[int]] = None,
    ) -> None:
        """
        Push the current colour map as a single static effect over REST.

        Args:
            transition_ms: Per-panel transition time (ms).
            command: "display" (persistent) or "displayTemp" (ephemeral).
            only: Optional subset of panel IDs to include; others are left untouched.
        """
        if command not in ("display", "displayTemp"):
            raise ValueError('command must be "display" or "displayTemp"')

        if only is None:
            ids: Iterable[int] = self._ids_ordered
        else:
            only_set = set(int(x) for x in only)
            unknown = only_set - self._ids_set
            if unknown:
                raise ValueError(f"unknown panel ids: {sorted(unknown)}")
            # preserve layout order
            ids = tuple(pid for pid in self._ids_ordered if pid in only_set)

        anim = _build_anim(ids, self.colors, transition_ms)
        payload = {
            "command": command,
            "version": "1.0",
            "animType": "static",
            "animData": anim,
            "palette": [],
            "loop": False,
        }

        # Use the library's canonical write helper if present
        write_effect = getattr(self._nl, "write_effect", None)
        if callable(write_effect):
            res = write_effect(payload)
            if asyncio.iscoroutine(res):
                await res
            return

        # Fallback: call other common names or raise
        for name in ("effects_write", "display_effect"):
            meth = getattr(self._nl, name, None)
            if callable(meth):
                res = meth(payload)
                if asyncio.iscoroutine(res):
                    await res
                return

        raise RuntimeError(
            "Nanoleaf client does not expose a write_effect/effects_write/display_effect method."
        )
