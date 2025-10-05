"""Digital Twin helpers for per-panel static colour control over REST.

Features:
- Persistent or temporary application (display/displayTemp)
- Subset updates (only=[...])
- Optional brightness overlay (0..100)
- apply_temp(): blink a set of panels then restore previous effect
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Tuple, Optional

from aionanoleaf.effects import EffectsClient  # top-level import

RGB = Tuple[int, int, int]
__all__ = ["DigitalTwin", "_build_anim"]


def _clamp(value: int, lo: int = 0, hi: int = 255) -> int:
    """Clamp integer to [lo, hi]."""
    return max(lo, min(hi, int(value)))


def _validate_rgb(rgb: RGB) -> RGB:
    """Validate and clamp an (R,G,B) 0..255 tuple."""
    try:
        r, g, b = (int(rgb[0]), int(rgb[1]), int(rgb[2]))
    except Exception as exc:  # noqa: BLE001 (defensive parse)
        raise ValueError("rgb must be a 3-tuple of integers") from exc
    for v in (r, g, b):
        if v < 0 or v > 255:
            raise ValueError("rgb components must be in [0,255]")
    return _clamp(r), _clamp(g), _clamp(b)


def _hex_to_rgb(s: str) -> RGB:
    """Convert #RRGGBB string to an (R,G,B) tuple."""
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


def _apply_brightness(rgb: RGB, brightness: Optional[int]) -> RGB:
    """Apply optional brightness overlay (0..100) to RGB."""
    if brightness is None:
        return rgb
    if not 0 <= int(brightness) <= 100:
        raise ValueError("brightness must be between 0 and 100")
    if brightness == 100:
        return rgb
    scale = brightness / 100.0
    r, g, b = rgb
    return (_clamp(round(r * scale)), _clamp(round(g * scale)), _clamp(round(b * scale)))


def _build_anim(
    ids: Iterable[int],
    colours: Dict[int, RGB],
    transition: int = 10,
    *,
    brightness: Optional[int] = None,
) -> str:
    """Build Nanoleaf 'static' effect animData string: N [id] 1 R G B 0 T ..."""
    id_list = list(ids)
    records: List[int] = []
    t = int(max(0, transition))
    for panel_id in id_list:
        r, g, b = _apply_brightness(colours[panel_id], brightness)
        records += [int(panel_id), 1, int(r), int(g), int(b), 0, t]
    return " ".join(map(str, [len(id_list)] + records))


@dataclass  # data container; keep tiny
class _Panel:  # pylint: disable=too-few-public-methods
    """Minimal panel record."""
    panel_id: int
    x: int
    y: int


class DigitalTwin:
    """Per-panel static colour control via REST Effects write."""

    def __init__(self, nl: Any, panels: List[_Panel]) -> None:
        """Create a twin given a Nanoleaf client and panel list."""
        self._nl = nl
        # Deterministic order: x asc, then y asc, then id asc
        panels_sorted = sorted(panels, key=lambda p: (p.x, p.y, p.panel_id))
        self._ids_ordered: Tuple[int, ...] = tuple(p.panel_id for p in panels_sorted)
        self._ids_set = set(self._ids_ordered)
        self.colors: Dict[int, RGB] = {pid: (0, 0, 0) for pid in self._ids_ordered}

    @classmethod
    async def create(cls, nl: Any) -> "DigitalTwin":
        """Fetch layout/positions from the device and return a twin."""
        # Some clients lazily populate info/layout
        get_info = getattr(nl, "get_info", None)
        if callable(get_info):
            result = get_info()
            if hasattr(result, "__await__"):
                await result

        layout = None
        if callable(getattr(nl, "get_panel_layout", None)):
            layout = await nl.get_panel_layout()
        elif callable(getattr(nl, "panel_layout", None)):
            layout = await nl.panel_layout()

        panels: List[_Panel] = []
        pos = None

        if isinstance(layout, dict):
            pos = layout.get("positionData")

        if pos is None:
            info = getattr(nl, "info", None) or getattr(nl, "_info", None)
            if isin
